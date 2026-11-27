/**
 * @file tas3251.cpp
 * @brief Tas3251 implementation. See tas3251.hpp for the public API and the
 *        warnings about unverified register encodings.
 */
#include "tas3251.hpp"

#include <algorithm>
#include <cmath>

#include "driver/gpio.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "tas_pins.h"

namespace tas {
namespace {
constexpr char kTag[] = "Tas3251";

/** 8-bit hardware addresses from the hardware README ("ADR -> GND: 0x90,
 *  ADR -> 3.3V: 0x92"), shifted right to the 7-bit form the ESP-IDF I2C
 *  driver expects. */
constexpr uint8_t kAddress7BitAdrLow = 0x90 >> 1;
constexpr uint8_t kAddress7BitAdrHigh = 0x92 >> 1;

constexpr int kI2cTimeoutMs = 1000;
} // namespace

esp_err_t Tas3251::init(const I2cBus &bus)
{
    const gpio_config_t inputIrqConfig = {
        .pin_bit_mask = (1ULL << TAS_PIN_AMP_FAULT) | (1ULL << TAS_PIN_AMP_CLIP_OTW),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    esp_err_t err = gpio_config(&inputIrqConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_config(/FAULT, /CLIP_OTW) failed: %s", esp_err_to_name(err));
        return err;
    }

    const gpio_config_t addressInputConfig = {
        .pin_bit_mask = (1ULL << TAS_PIN_AMP_ADDRESS),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&addressInputConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_config(AMP ADDRESS) failed: %s", esp_err_to_name(err));
        return err;
    }

    /* Safe power-up defaults: held in reset, muted, until SystemController
     * runs the sequence in tas/README.md. SystemController::startup() also
     * calls this directly, earlier, before this init() runs — see its
     * @note. */
    err = assertSafeState();
    if (err != ESP_OK) {
        return err;
    }

    err = gpio_install_isr_service(0);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        /* ESP_ERR_INVALID_STATE means some other driver already installed
         * the shared GPIO ISR service, which is fine — we just add our
         * handlers to it below. */
        ESP_LOGE(kTag, "gpio_install_isr_service failed: %s", esp_err_to_name(err));
        return err;
    }

    err = gpio_isr_handler_add(TAS_PIN_AMP_FAULT, &Tas3251::faultIsrThunk, this);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_isr_handler_add(/FAULT) failed: %s", esp_err_to_name(err));
        return err;
    }
    err = gpio_isr_handler_add(TAS_PIN_AMP_CLIP_OTW, &Tas3251::clipOtwIsrThunk, this);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_isr_handler_add(/CLIP_OTW) failed: %s", esp_err_to_name(err));
        return err;
    }

    const uint8_t address = resolveI2cAddress();
    ESP_LOGI(kTag, "AMP ADDRESS strap resolved to I2C address 0x%02X (7-bit)", address);
    err = bus.addDevice(address, &dev_);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "i2c_master_bus_add_device failed: %s", esp_err_to_name(err));
        return err;
    }

    return ESP_OK;
}

uint8_t Tas3251::resolveI2cAddress() const
{
    return gpio_get_level(TAS_PIN_AMP_ADDRESS) ? kAddress7BitAdrHigh : kAddress7BitAdrLow;
}

esp_err_t Tas3251::assertSafeState()
{
    const gpio_config_t outputConfig = {
        .pin_bit_mask = (1ULL << TAS_PIN_AMP_RESET) | (1ULL << TAS_PIN_DAC_MUTE),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&outputConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_config(RESET_AMP, DAC_MUTE) failed: %s", esp_err_to_name(err));
        return err;
    }

    /* Both are active low, and per hardware bring-up spec must go down
     * together, as early as this call runs. */
    err = reset(true);
    if (err != ESP_OK) {
        return err;
    }
    return mute(true);
}

esp_err_t Tas3251::reset(bool assertReset)
{
    /* Active low: asserted (in reset) = 0, released = 1. */
    return gpio_set_level(TAS_PIN_AMP_RESET, assertReset ? 0 : 1);
}

esp_err_t Tas3251::mute(bool muteOn)
{
    /* Active low: muted = 0, unmuted = 1. */
    return gpio_set_level(TAS_PIN_DAC_MUTE, muteOn ? 0 : 1);
}

esp_err_t Tas3251::setSoftMuteRegister(bool muteOn)
{
    esp_err_t err = selectBookPage(0, 0);
    if (err != ESP_OK) {
        return err;
    }
    return writeRegister(kRegDacMute, muteOn ? kMuteBothChannelsMask : 0x00);
}

esp_err_t Tas3251::setDspStandby(bool exitStandby)
{
    esp_err_t err = selectBookPage(0, 0);
    if (err != ESP_OK) {
        return err;
    }
    return writeRegister(kRegDeviceCtrl2, exitStandby ? kDeviceCtrl2DspStandbyBit : 0x00);
}

esp_err_t Tas3251::setVolumeDb(Channel channel, float db)
{
    /* Common TI PurePath convention: 0x00 == +24 dB, -0.5 dB per LSB down
     * to the -103 dB floor. UNVERIFIED for TAS3251 — see header warning. */
    const float clampedDb = std::clamp(db, -103.0f, 24.0f);
    const int code = std::lround((24.0f - clampedDb) * 2.0f);
    const uint8_t regValue = static_cast<uint8_t>(std::clamp(code, 0, 255));

    esp_err_t err = selectBookPage(0, 0);
    if (err != ESP_OK) {
        return err;
    }
    const uint8_t reg = (channel == Channel::Left) ? kRegVolumeLeft : kRegVolumeRight;
    return writeRegister(reg, regValue);
}

esp_err_t Tas3251::setVolumeRampSpeed(uint8_t code)
{
    esp_err_t err = selectBookPage(0, 0);
    if (err != ESP_OK) {
        return err;
    }
    return writeRegister(kRegVolumeRampSpeed, code);
}

esp_err_t Tas3251::readFaultStatus(FaultStatus &status)
{
    esp_err_t err = selectBookPage(0, 0);
    if (err != ESP_OK) {
        return err;
    }
    err = readRegister(kRegFaultStatus1, status.reg94);
    if (err != ESP_OK) {
        return err;
    }
    return readRegister(kRegFaultStatus2, status.reg95);
}

esp_err_t Tas3251::selectBookPage(uint8_t book, uint8_t page)
{
    esp_err_t err = ESP_OK;
    if (book != currentBook_ || currentPage_ == 0xFF) {
        err = writeRegister(kRegPageSelect, 0x00);
        if (err != ESP_OK) {
            return err;
        }
        err = writeRegister(kRegBookSelect, book);
        if (err != ESP_OK) {
            return err;
        }
        currentBook_ = book;
        currentPage_ = 0;
    }
    if (page != currentPage_) {
        err = writeRegister(kRegPageSelect, page);
        if (err != ESP_OK) {
            return err;
        }
        currentPage_ = page;
    }
    return ESP_OK;
}

esp_err_t Tas3251::writeRegister(uint8_t reg, uint8_t value)
{
    const uint8_t frame[2] = {reg, value};
    esp_err_t err = i2c_master_transmit(dev_, frame, sizeof(frame), kI2cTimeoutMs);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "writeRegister(0x%02X, 0x%02X) failed: %s", reg, value, esp_err_to_name(err));
    }
    return err;
}

esp_err_t Tas3251::readRegister(uint8_t reg, uint8_t &value)
{
    esp_err_t err = i2c_master_transmit_receive(dev_, &reg, 1, &value, 1, kI2cTimeoutMs);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "readRegister(0x%02X) failed: %s", reg, esp_err_to_name(err));
    }
    return err;
}

void IRAM_ATTR Tas3251::faultIsrThunk(void *arg)
{
    static_cast<Tas3251 *>(arg)->faultLatched_ = true;
}

void IRAM_ATTR Tas3251::clipOtwIsrThunk(void *arg)
{
    static_cast<Tas3251 *>(arg)->clipOtwLatched_ = true;
}

} // namespace tas
