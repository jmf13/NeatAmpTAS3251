/**
 * @file i2s_bus.cpp
 * @brief I2sBus implementation. See i2s_bus.hpp for the public API and the
 *        warning about the current hardware not routing these GPIOs.
 */
#include "i2s_bus.hpp"

#include "driver/i2s_std.h"
#include "esp_log.h"

namespace tas {
namespace {
constexpr char kTag[] = "I2sBus";
} // namespace

esp_err_t I2sBus::init(const I2sPins &pins, uint32_t sampleRateHz, uint16_t bitsPerSample)
{
    if (pins.mclk == GPIO_NUM_NC || pins.bclk == GPIO_NUM_NC || pins.ws == GPIO_NUM_NC ||
        pins.dout == GPIO_NUM_NC) {
        ESP_LOGE(kTag, "I2S pins not assigned — see the class-level warning in i2s_bus.hpp");
        return ESP_ERR_INVALID_ARG;
    }

    const i2s_chan_config_t channelConfig = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    esp_err_t err = i2s_new_channel(&channelConfig, &txChannel_, nullptr);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "i2s_new_channel failed: %s", esp_err_to_name(err));
        return err;
    }

    const auto bitWidth = static_cast<i2s_data_bit_width_t>(bitsPerSample);
    const i2s_std_config_t stdConfig = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(sampleRateHz),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(bitWidth, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = pins.mclk,
            .bclk = pins.bclk,
            .ws = pins.ws,
            .dout = pins.dout,
            .din = pins.din,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };
    err = i2s_channel_init_std_mode(txChannel_, &stdConfig);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "i2s_channel_init_std_mode failed: %s", esp_err_to_name(err));
        return err;
    }

    return ESP_OK;
}

esp_err_t I2sBus::start()
{
    return i2s_channel_enable(txChannel_);
}

esp_err_t I2sBus::stop()
{
    return i2s_channel_disable(txChannel_);
}

esp_err_t I2sBus::writeSamples(const void *data, size_t bytes, size_t &bytesWritten, uint32_t timeoutMs)
{
    return i2s_channel_write(txChannel_, data, bytes, &bytesWritten, timeoutMs);
}

} // namespace tas
