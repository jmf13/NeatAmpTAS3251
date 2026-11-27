/**
 * @file status_led.cpp
 * @brief StatusLed implementation. See status_led.hpp for the public API
 *        and the SK9822 frame format this writes.
 */
#include "status_led.hpp"

#include "driver/gpio.h"
#include "esp_log.h"
#include "tas_pins.h"

namespace tas {
namespace {
constexpr char kTag[] = "StatusLed";
} // namespace

esp_err_t StatusLed::init()
{
    const gpio_config_t outputConfig = {
        .pin_bit_mask = (1ULL << TAS_PIN_STATUS_LED_SDI) | (1ULL << TAS_PIN_STATUS_LED_CKI),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&outputConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "gpio_config(status LED SDI/CKI) failed: %s", esp_err_to_name(err));
        return err;
    }

    return clear();
}

void StatusLed::clockOutByte(uint8_t value)
{
    for (int bit = 7; bit >= 0; --bit) {
        gpio_set_level(TAS_PIN_STATUS_LED_SDI, (value >> bit) & 0x01);
        gpio_set_level(TAS_PIN_STATUS_LED_CKI, 1);
        gpio_set_level(TAS_PIN_STATUS_LED_CKI, 0);
    }
}

esp_err_t StatusLed::writeFrame()
{
    /* Start frame: 32 bits of 0. */
    for (int i = 0; i < 4; ++i) {
        clockOutByte(0x00);
    }

    /* One frame per LED, in chain order (index 0 = U8 = first in chain). */
    for (size_t i = 0; i < kNumLeds; ++i) {
        clockOutByte(0xE0 | (brightness_[i] & 0x1F));
        clockOutByte(colors_[i].b);
        clockOutByte(colors_[i].g);
        clockOutByte(colors_[i].r);
    }

    /* End frame: enough clock-only bytes to flush the last LED's data
     * through the chain. 4 bytes (32 clock pulses) is comfortably more
     * than the minimum for a 2-LED chain and matches the start frame. */
    for (int i = 0; i < 4; ++i) {
        clockOutByte(0xFF);
    }

    return ESP_OK;
}

esp_err_t StatusLed::setColor(size_t index, RgbColor color, uint8_t brightness)
{
    if (index >= kNumLeds) {
        return ESP_ERR_INVALID_ARG;
    }
    colors_[index] = color;
    brightness_[index] = brightness;
    return writeFrame();
}

esp_err_t StatusLed::setAll(RgbColor color, uint8_t brightness)
{
    for (size_t i = 0; i < kNumLeds; ++i) {
        colors_[i] = color;
        brightness_[i] = brightness;
    }
    return writeFrame();
}

esp_err_t StatusLed::clear()
{
    return setAll(RgbColor{0, 0, 0}, 0);
}

} // namespace tas
