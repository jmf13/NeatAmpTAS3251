/**
 * @file i2s_bus.hpp
 * @brief Wraps the ESP-IDF standard-mode I2S driver for the audio data path
 *        shared by the TAS3251 and the optional ADAU1466 DSP.
 *
 * @warning Per Netlist_Class_D_amp_2026-07-23.enet (repository root), the
 *          current board revision does NOT wire any ESP32-S3 GPIO to the
 *          I2S bus — connector U11 (MCLK/LRCK/SCLK/SDIN) only reaches the
 *          TAS3251 (through 22 Ohm series resistors), not the ESP32-S3.
 *          This class is a working scaffold for a future revision (or an
 *          external jumper/rework) that does connect them; init() will
 *          fail with ESP_ERR_INVALID_ARG if given GPIO_NUM_NC pins.
 */
#ifndef TAS_I2S_BUS_HPP
#define TAS_I2S_BUS_HPP

#include <cstddef>
#include <cstdint>
#include "driver/i2s_common.h"
#include "esp_err.h"
#include "hal/gpio_types.h"

namespace tas {

/** @brief GPIO assignment for the I2S bus. See the class-level warning —
 *  none of these currently have a valid value in tas_pins.h. */
struct I2sPins {
    gpio_num_t mclk = GPIO_NUM_NC;
    gpio_num_t bclk = GPIO_NUM_NC;
    gpio_num_t ws = GPIO_NUM_NC;   ///< LRCK
    gpio_num_t dout = GPIO_NUM_NC; ///< SDIN, ESP32-S3 -> TAS3251/DSP
    gpio_num_t din = GPIO_NUM_NC;  ///< Not wired on current hardware; leave GPIO_NUM_NC
};

/**
 * @brief Transmit-only I2S standard-mode channel, ESP32-S3 as bus master.
 */
class I2sBus {
public:
    I2sBus() = default;

    /**
     * @brief Allocate and configure the I2S TX channel.
     * @param pins GPIO assignment; mclk/bclk/ws/dout must be valid pins.
     * @param sampleRateHz e.g. 48000 or 96000.
     * @param bitsPerSample e.g. 16, 24 or 32.
     * @return ESP_OK on success.
     */
    esp_err_t init(const I2sPins &pins, uint32_t sampleRateHz, uint16_t bitsPerSample);

    /** @brief Start the channel (must be init()-ed first). */
    esp_err_t start();

    /** @brief Stop the channel. */
    esp_err_t stop();

    /**
     * @brief Write interleaved stereo samples, blocking up to @p timeoutMs.
     * @param data Pointer to interleaved sample data.
     * @param bytes Number of bytes in @p data to write.
     * @param[out] bytesWritten Number of bytes actually written.
     * @param timeoutMs Maximum time to block waiting for DMA buffer space.
     */
    esp_err_t writeSamples(const void *data, size_t bytes, size_t &bytesWritten, uint32_t timeoutMs);

private:
    i2s_chan_handle_t txChannel_ = nullptr;
};

} // namespace tas

#endif
