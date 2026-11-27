/**
 * @file power_supplies.cpp
 * @brief PowerSupplies implementation. See power_supplies.hpp for the
 *        public API.
 */
#include "power_supplies.hpp"

#include "driver/gpio.h"
#include "esp_log.h"
#include "tas_pins.h"

namespace tas {
namespace {
constexpr char kTag[] = "PowerSupplies";
} // namespace

esp_err_t PowerSupplies::init()
{
    const gpio_config_t inputConfig = {
        .pin_bit_mask = (1ULL << TAS_PIN_GOOD_13V2),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&inputConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_config(GOOD_13.2V) failed: %s", esp_err_to_name(err));
        return err;
    }

    const gpio_config_t outputConfig = {
        .pin_bit_mask = (1ULL << TAS_PIN_ENABLE_12V) | (1ULL << TAS_PIN_ENABLE_3V3_ANALOG),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&outputConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_config(ENABLE_12V, ENABLE_3.3V) failed: %s", esp_err_to_name(err));
        return err;
    }

    err = enable12VAnalog(false);
    if (err != ESP_OK) {
        return err;
    }
    return enable3V3Analog(false);
}

bool PowerSupplies::isRail13V2Good() const
{
    return gpio_get_level(TAS_PIN_GOOD_13V2) != 0;
}

esp_err_t PowerSupplies::enable12VAnalog(bool enable)
{
    esp_err_t err = gpio_set_level(TAS_PIN_ENABLE_12V, enable ? 1 : 0);
    if (err == ESP_OK) {
        enabled12VAnalog_ = enable;
    } else {
        ESP_LOGE(kTag, "Failed to set ENABLE_12V: %s", esp_err_to_name(err));
    }
    return err;
}

esp_err_t PowerSupplies::enable3V3Analog(bool enable)
{
    esp_err_t err = gpio_set_level(TAS_PIN_ENABLE_3V3_ANALOG, enable ? 1 : 0);
    if (err == ESP_OK) {
        enabled3V3Analog_ = enable;
    } else {
        ESP_LOGE(kTag, "Failed to set ENABLE_3.3V: %s", esp_err_to_name(err));
    }
    return err;
}

} // namespace tas
