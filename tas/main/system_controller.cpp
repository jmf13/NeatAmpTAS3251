/**
 * @file system_controller.cpp
 * @brief SystemController implementation. See system_controller.hpp for the
 *        public API and tas/README.md for the state diagram this mirrors.
 */
#include "system_controller.hpp"

#include <cinttypes>

#include "esp_app_desc.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace tas {
namespace {
constexpr char kTag[] = "SystemController";

const char *resetReasonToString(esp_reset_reason_t reason)
{
    switch (reason) {
        case ESP_RST_POWERON:
            return "power-on";
        case ESP_RST_EXT:
            return "external pin";
        case ESP_RST_SW:
            return "software (esp_restart)";
        case ESP_RST_PANIC:
            return "panic/exception";
        case ESP_RST_INT_WDT:
            return "interrupt watchdog";
        case ESP_RST_TASK_WDT:
            return "task watchdog";
        case ESP_RST_WDT:
            return "other watchdog";
        case ESP_RST_DEEPSLEEP:
            return "deep sleep wakeup";
        case ESP_RST_BROWNOUT:
            return "brownout";
        case ESP_RST_SDIO:
            return "SDIO";
        case ESP_RST_USB:
            return "USB";
        case ESP_RST_JTAG:
            return "JTAG";
        case ESP_RST_EFUSE:
            return "efuse error";
        case ESP_RST_PWR_GLITCH:
            return "power glitch";
        case ESP_RST_CPU_LOCKUP:
            return "CPU lockup (double exception)";
        case ESP_RST_UNKNOWN:
        default:
            return "unknown";
    }
}

/**
 * @brief Log everything readily available about the running chip and
 *        firmware image, so a serial capture always identifies exactly
 *        what is on the board (target, revision, flash, firmware version,
 *        MAC, why it last reset) without needing a debugger attached.
 */
void logChipInfo()
{
    esp_chip_info_t chipInfo;
    esp_chip_info(&chipInfo);

    uint32_t flashSizeBytes = 0;
    esp_flash_get_size(nullptr, &flashSizeBytes);

    uint8_t mac[6] = {0};
    esp_read_mac(mac, ESP_MAC_WIFI_STA);

    const esp_app_desc_t *app = esp_app_get_description();

    ESP_LOGI(kTag, "Chip: %s, %d core(s), silicon revision v%d.%d, %s%s%s%sflash %" PRIu32 " MB (%s)",
             CONFIG_IDF_TARGET, chipInfo.cores, chipInfo.revision / 100, chipInfo.revision % 100,
             (chipInfo.features & CHIP_FEATURE_WIFI_BGN) ? "WiFi/" : "",
             (chipInfo.features & CHIP_FEATURE_BT) ? "BT/" : "",
             (chipInfo.features & CHIP_FEATURE_BLE) ? "BLE/" : "",
             (chipInfo.features & CHIP_FEATURE_IEEE802154) ? "802.15.4/" : "",
             flashSizeBytes / (1024 * 1024),
             (chipInfo.features & CHIP_FEATURE_EMB_FLASH) ? "embedded" : "external");
    ESP_LOGI(kTag, "MAC (WiFi STA): %02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    ESP_LOGI(kTag, "Heap: %" PRIu32 " bytes free now, %" PRIu32 " bytes minimum free since boot",
             esp_get_free_heap_size(), esp_get_minimum_free_heap_size());
    ESP_LOGI(kTag, "Firmware: project \"%s\" v%s, built %s %s, ESP-IDF %s", app->project_name, app->version,
             app->date, app->time, app->idf_ver);
    ESP_LOGI(kTag, "Last reset reason: %s", resetReasonToString(esp_reset_reason()));
}

/**
 * @note Per hardware bring-up spec: lets the 13.2V->12V LDO chain and 3.3V
 *       analog rail begin settling before GOOD_13.2V is polled.
 */
constexpr uint32_t kPowerStabilizeDelayMs = 2;

/**
 * @note Per hardware bring-up spec: settle time after enabling the 12V/3.3V
 *       analog rails, before starting the I2C configuration sequence that
 *       eventually leads to releasing RESET_AMP (see kDspStandbyToUnmuteDelayMs
 *       / kUnmuteToResetReleaseDelayMs below for the rest of that path).
 */
constexpr uint32_t kPreResetReleaseDelayMs = 5;

/**
 * @note Per hardware bring-up spec: delay after bringing the DSP out of
 *       standby (Tas3251::setDspStandby(true), DEVICE_CTRL_2 bit7 DSPR)
 *       before releasing DAC_MUTE.
 */
constexpr uint32_t kDspStandbyToUnmuteDelayMs = 200;

/**
 * @note Per hardware bring-up spec: additional delay after releasing
 *       DAC_MUTE before releasing RESET_AMP — the last step of startup().
 */
constexpr uint32_t kUnmuteToResetReleaseDelayMs = 205;

/**
 * @note Conservative "low" volume, used both as the startup default and as
 *       the volume applied when a fault mutes the amp. Deliberately chosen
 *       independently of whether Tas3251::setVolumeDb()'s dB-to-register-code
 *       formula is correct (see its @warning) — a wrong-but-quiet result is
 *       safe, a wrong-and-loud one is not.
 */
constexpr float kLowVolumeDb = -60.0f;

constexpr uint32_t kMonitorLoopPeriodMs = 50;

/** @note How long the CLIP/OTW visual flash (LED index 1, U9) stays lit.
 *  Purely cosmetic — see SystemController::handleClipOtw(). */
constexpr uint32_t kClipFlashMs = 120;

/** @name Status LED colors (see SystemController::Status) */
///@{
constexpr RgbColor kColorBooting{0, 0, 255};
constexpr RgbColor kColorReady{0, 255, 0};
constexpr RgbColor kColorFault{255, 0, 0};
constexpr RgbColor kColorStartupFailed{255, 140, 0};
constexpr RgbColor kColorClipFlash{255, 180, 0};
constexpr RgbColor kColorOff{0, 0, 0};
///@}
} // namespace

esp_err_t SystemController::fail(esp_err_t err)
{
    status_ = Status::StartupFailed;
    statusLed_.setColor(0, kColorStartupFailed);
    return err;
}

esp_err_t SystemController::startup()
{
    /* State: AMP_RESET — RESET_AMP and DAC_MUTE asserted (both active low)
     * together, as the very first action, before touching any other
     * peripheral — per hardware bring-up spec. See Tas3251::assertSafeState()
     * for why this needs nothing but GPIO. amp_.init() below repeats this
     * harmlessly as part of its own GPIO configuration. */
    esp_err_t err = amp_.assertSafeState();
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to assert RESET_AMP/DAC_MUTE at boot: %s", esp_err_to_name(err));
        return fail(err);
    }

    logChipInfo();

    err = statusLed_.init();
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "StatusLed init failed: %s", esp_err_to_name(err));
        return fail(err);
    }
    statusLed_.setColor(0, kColorBooting);

    ESP_LOGI(kTag, "State: INIT — configuring I2C bus, GPIOs and interrupts");
    err = i2cBus_.init();
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "I2C bus init failed: %s", esp_err_to_name(err));
        return fail(err);
    }

    err = power_.init();
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "PowerSupplies init failed: %s", esp_err_to_name(err));
        return fail(err);
    }

    /* Tas3251::init() also drives RESET_AMP and DAC_MUTE to their safe
     * (asserted) defaults as part of GPIO configuration. */
    err = amp_.init(i2cBus_);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Tas3251 init failed: %s", esp_err_to_name(err));
        return fail(err);
    }

    err = dsp_.init(i2cBus_);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Dsp init failed: %s", esp_err_to_name(err));
        return fail(err);
    }
    if (!dsp_.isPresent()) {
        ESP_LOGI(kTag, "ADAU1466 DSP not detected on the I2C bus — continuing without it "
                       "(expected on boards where it is not populated)");
    }

    ESP_LOGI(kTag, "State: WAIT_POWER_STABLE — waiting %" PRIu32 " ms for supplies to settle",
             kPowerStabilizeDelayMs);
    vTaskDelay(pdMS_TO_TICKS(kPowerStabilizeDelayMs));

    ESP_LOGI(kTag, "State: CHECK_13V2 — polling GOOD_13.2V");
    if (!power_.isRail13V2Good()) {
        ESP_LOGE(kTag, "13.2V rail not good — aborting startup, amplifier stays in reset and muted");
        return fail(ESP_ERR_INVALID_STATE);
    }
    ESP_LOGI(kTag, "13.2V rail confirmed good");

    ESP_LOGI(kTag, "State: ENABLE_12V — enabling 12V GVDD analog rail");
    err = power_.enable12VAnalog(true);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to enable 12V GVDD rail: %s", esp_err_to_name(err));
        return fail(err);
    }

    /* @note Enabled immediately after the 12V rail rather than with an
     * explicit relative delay. TODO: confirm against the TAS3251 datasheet
     * whether AVDD (3.3V analog) must be sequenced a fixed time before/after
     * GVDD (12V) — if so, add a delay here rather than assuming
     * simultaneous enable is safe. */
    ESP_LOGI(kTag, "State: ENABLE_3V3_ANALOG — enabling 3.3V analog (DAC_AVDD) rail");
    err = power_.enable3V3Analog(true);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to enable 3.3V analog rail: %s", esp_err_to_name(err));
        return fail(err);
    }

    ESP_LOGI(kTag, "State: WAIT_PRE_RESET_RELEASE — waiting %" PRIu32 " ms before releasing RESET_AMP",
             kPreResetReleaseDelayMs);
    vTaskDelay(pdMS_TO_TICKS(kPreResetReleaseDelayMs));

    /* RESET_AMP is still asserted at this point — only DAC_MUTE and
     * DEVICE_CTRL_2 (bit7 DSPR) are configured over I2C below, before
     * RESET_AMP is finally released at the end of this sequence. */
    ESP_LOGI(kTag, "State: MUTE_I2C — muting DACs via I2C (B0-P0-R3, bit0+bit4)");
    err = amp_.setSoftMuteRegister(true);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to set I2C soft-mute (B0-P0-R3): %s", esp_err_to_name(err));
        return fail(err);
    }

    /* TODO: DSP configuration (EQ / crossover biquads, Book 0x8C pages,
     * safeload via B0x8C-P5-R7C) and volume setup (Tas3251::setVolumeDb(),
     * Tas3251::setVolumeRampSpeed()) go here once coefficients/levels are
     * finalized — see Tas3251::selectBookPage()/writeRegister(). Placeholder
     * only: nothing is written here yet. */

    ESP_LOGI(kTag, "State: DSP_STANDBY — bringing DSP out of standby (B0-P0-R2, bit7 DSPR)");
    err = amp_.setDspStandby(true);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to bring DSP out of standby (B0-P0-R2): %s", esp_err_to_name(err));
        return fail(err);
    }

    ESP_LOGI(kTag, "State: WAIT_BEFORE_UNMUTE — waiting %" PRIu32 " ms before releasing DAC_MUTE",
             kDspStandbyToUnmuteDelayMs);
    vTaskDelay(pdMS_TO_TICKS(kDspStandbyToUnmuteDelayMs));

    ESP_LOGI(kTag, "State: UNMUTE — releasing DAC_MUTE");
    err = amp_.mute(false);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to release DAC_MUTE: %s", esp_err_to_name(err));
        return fail(err);
    }

    ESP_LOGI(kTag, "State: WAIT_BEFORE_RESET_RELEASE — waiting %" PRIu32 " ms before releasing RESET_AMP",
             kUnmuteToResetReleaseDelayMs);
    vTaskDelay(pdMS_TO_TICKS(kUnmuteToResetReleaseDelayMs));

    ESP_LOGI(kTag, "State: RELEASE_RESET — releasing RESET_AMP, audio path active");
    err = amp_.reset(false);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to release RESET_AMP: %s", esp_err_to_name(err));
        return fail(err);
    }

    ESP_LOGI(kTag, "State: READY — startup sequence complete");
    status_ = Status::Ready;
    statusLed_.setColor(0, kColorReady);
    return ESP_OK;
}

void SystemController::handleFault()
{
    FaultStatus faultStatus{};
    esp_err_t err = amp_.readFaultStatus(faultStatus);
    if (err == ESP_OK) {
        ESP_LOGE(kTag, "AMP FAULT latched: B0-P0-R94=0x%02X R95=0x%02X", faultStatus.reg94, faultStatus.reg95);
    } else {
        ESP_LOGE(kTag, "AMP FAULT latched, and fault status read failed: %s", esp_err_to_name(err));
    }
    amp_.clearFaultLatch();

    ESP_LOGE(kTag, "State: FAULT — muting at low volume");
    err = amp_.mute(true);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to assert DAC_MUTE after fault: %s", esp_err_to_name(err));
    }
    err = amp_.setVolumeDb(Channel::Left, kLowVolumeDb);
    if (err == ESP_OK) {
        err = amp_.setVolumeDb(Channel::Right, kLowVolumeDb);
    }
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to lower volume after fault: %s", esp_err_to_name(err));
    }

    status_ = Status::Fault;
    statusLed_.setColor(0, kColorFault);
    /* TODO: recovery policy — e.g. wait for thermal recovery then toggle
     * RESET_AMP to clear a latched OTE fault, per the hardware README
     * "Fault Handling" section. Status intentionally stays Fault (muted,
     * red LED) until that recovery path exists. */
}

void SystemController::handleClipOtw()
{
    ESP_LOGW(kTag, "AMP CLIP/OTW asserted");
    amp_.clearClipOtwLatch();

    /* Log-only by design: no mute, no volume change, no Status change.
     * The second LED (U9) gets a brief flash purely as a "clipping just
     * happened" visual cue, independent of the persistent status on U8. */
    statusLed_.setColor(1, kColorClipFlash);
    vTaskDelay(pdMS_TO_TICKS(kClipFlashMs));
    statusLed_.setColor(1, kColorOff);
}

void SystemController::runForever()
{
    ESP_LOGI(kTag, "Entering monitor loop (/FAULT, /CLIP_OTW, 13.2V-good)");
    bool lastRail13V2Good = true;

    for (;;) {
        if (amp_.isFaultLatched()) {
            handleFault();
        }

        if (amp_.isClipOtwLatched()) {
            handleClipOtw();
        }

        const bool rail13V2Good = power_.isRail13V2Good();
        if (rail13V2Good != lastRail13V2Good) {
            if (rail13V2Good) {
                ESP_LOGI(kTag, "13.2V rail recovered");
            } else {
                ESP_LOGE(kTag, "13.2V rail lost while running");
            }
            lastRail13V2Good = rail13V2Good;
        }

        vTaskDelay(pdMS_TO_TICKS(kMonitorLoopPeriodMs));
    }
}

} // namespace tas
