/**
 * @file i2c_bus.cpp
 * @brief I2cBus implementation. See i2c_bus.hpp for the public API.
 */
#include "i2c_bus.hpp"
#include "tas_pins.h"

namespace tas {

esp_err_t I2cBus::init()
{
    const i2c_master_bus_config_t config = {
        .i2c_port = TAS_I2C_PORT,
        .sda_io_num = TAS_PIN_I2C_SDA,
        .scl_io_num = TAS_PIN_I2C_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .intr_priority = 0,
        .trans_queue_depth = 0,
        .flags = {
            .enable_internal_pullup = false,
            .allow_pd = false,
        },
    };
    return i2c_new_master_bus(&config, &bus_);
}

esp_err_t I2cBus::addDevice(uint8_t address7Bit, i2c_master_dev_handle_t *outHandle) const
{
    const i2c_device_config_t config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = address7Bit,
        .scl_speed_hz = TAS_I2C_FREQUENCY_HZ,
        .scl_wait_us = 0,
        .flags = {
            .disable_ack_check = false,
        },
    };
    return i2c_master_bus_add_device(bus_, &config, outHandle);
}

bool I2cBus::probe(uint8_t address7Bit, int timeoutMs) const
{
    return i2c_master_probe(bus_, address7Bit, timeoutMs) == ESP_OK;
}

} // namespace tas
