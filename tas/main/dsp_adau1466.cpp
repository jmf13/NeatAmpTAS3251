/**
 * @file dsp_adau1466.cpp
 * @brief Dsp implementation. See dsp_adau1466.hpp for the public API and
 *        the warning about the placeholder I2C address.
 */
#include "dsp_adau1466.hpp"

#include "driver/gpio.h"
#include "esp_log.h"
#include "tas_pins.h"

namespace tas {
namespace {
constexpr char kTag[] = "Dsp";

/** @warning Placeholder, unverified — see class-level warning in the header. */
constexpr uint8_t kI2cAddress7Bit = 0x38;
constexpr int kProbeTimeoutMs = 50;
} // namespace

esp_err_t Dsp::init(const I2cBus &bus)
{
    const gpio_config_t outputConfig = {
        .pin_bit_mask = (1ULL << TAS_PIN_DSP_RESET) | (1ULL << TAS_PIN_DSP_SELFBOOT),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&outputConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_config(DSP_RESET, DSP_SELFBOOT) failed: %s", esp_err_to_name(err));
        return err;
    }

    err = reset(true);
    if (err != ESP_OK) {
        return err;
    }
    err = setSelfBoot(false);
    if (err != ESP_OK) {
        return err;
    }

    present_ = bus.probe(kI2cAddress7Bit, kProbeTimeoutMs);
    if (present_) {
        ESP_LOGI(kTag, "ADAU1466 detected at I2C address 0x%02X (7-bit)", kI2cAddress7Bit);
        err = bus.addDevice(kI2cAddress7Bit, &dev_);
        if (err != ESP_OK) {
            ESP_LOGE(kTag, "i2c_master_bus_add_device failed despite successful probe: %s",
                     esp_err_to_name(err));
            present_ = false;
            return err;
        }
    }

    return ESP_OK;
}

esp_err_t Dsp::reset(bool assertReset)
{
    /* Active low, matching TAS_PIN_AMP_RESET convention on this board. */
    return gpio_set_level(TAS_PIN_DSP_RESET, assertReset ? 0 : 1);
}

esp_err_t Dsp::setSelfBoot(bool selfBoot)
{
    return gpio_set_level(TAS_PIN_DSP_SELFBOOT, selfBoot ? 1 : 0);
}

} // namespace tas
