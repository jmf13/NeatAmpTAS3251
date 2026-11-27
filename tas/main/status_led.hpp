/**
 * @file status_led.hpp
 * @brief Bit-banged driver for the two-LED SK9822 (APA102-compatible)
 *        status chain (U8, U9) on TAS_PIN_STATUS_LED_SDI/CKI.
 */
#ifndef TAS_STATUS_LED_HPP
#define TAS_STATUS_LED_HPP

#include <cstddef>
#include <cstdint>
#include "esp_err.h"

namespace tas {

/** @brief 8-bit-per-channel RGB color. */
struct RgbColor {
    uint8_t r = 0;
    uint8_t g = 0;
    uint8_t b = 0;
};

/**
 * @brief Drives a short chain of SK9822 LEDs over a bit-banged two-wire
 *        (data/clock) link — no SPI peripheral needed at this chain length
 *        and update rate.
 *
 * SK9822 frame format (identical to APA102): a 4-byte all-zero start frame,
 * one 4-byte frame per LED (`0xE0 | 5-bit brightness`, then B, G, R), and an
 * end frame of clock-only bytes to flush the last LED's data through the
 * chain. LEDs are addressed in chain order: index 0 is U8 (first, closest
 * to the ESP32-S3), index 1 is U9.
 */
class StatusLed {
public:
    /** @brief Number of LEDs in the chain (U8, U9). */
    static constexpr size_t kNumLeds = 2;

    /** @brief Default global brightness (0-31, SK9822's 5-bit range). Kept
     *  low — this is a status indicator, not room lighting. */
    static constexpr uint8_t kDefaultBrightness = 6;

    StatusLed() = default;

    /** @brief Configure the SDI/CKI GPIOs as outputs and blank the chain. */
    esp_err_t init();

    /** @brief Set one LED's color and push the whole chain out. */
    esp_err_t setColor(size_t index, RgbColor color, uint8_t brightness = kDefaultBrightness);

    /** @brief Set every LED to the same color and push the chain out. */
    esp_err_t setAll(RgbColor color, uint8_t brightness = kDefaultBrightness);

    /** @brief Turn every LED off. */
    esp_err_t clear();

private:
    void clockOutByte(uint8_t value);
    esp_err_t writeFrame();

    RgbColor colors_[kNumLeds] = {};
    uint8_t brightness_[kNumLeds] = {};
};

} // namespace tas

#endif
