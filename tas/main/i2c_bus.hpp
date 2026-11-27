/**
 * @file i2c_bus.hpp
 * @brief Thin RAII-ish wrapper around the single shared ESP-IDF I2C master
 *        bus used for both the TAS3251 amplifier and the optional ADAU1466
 *        DSP register interfaces.
 */
#ifndef TAS_I2C_BUS_HPP
#define TAS_I2C_BUS_HPP

#include "driver/i2c_master.h"
#include "esp_err.h"

namespace tas {

/**
 * @brief Owns the ESP-IDF I2C master bus (TAS_I2C_PORT, see tas_pins.h) and
 *        hands out device handles to it. There is exactly one instance of
 *        this class, owned by SystemController, and it must be initialized
 *        before Tas3251::init() or Dsp::init() are called.
 */
class I2cBus {
public:
    I2cBus() = default;

    /**
     * @brief Configure the SDA/SCL pins and create the I2C master bus.
     * @return ESP_OK on success, otherwise the underlying driver error.
     */
    esp_err_t init();

    /**
     * @brief Attach a new device on this bus.
     * @param address7Bit 7-bit I2C device address (without the R/W bit).
     * @param[out] outHandle Receives the created device handle.
     * @return ESP_OK on success, otherwise the underlying driver error.
     */
    esp_err_t addDevice(uint8_t address7Bit, i2c_master_dev_handle_t *outHandle) const;

    /**
     * @brief Probe for a device without attaching it, e.g. to detect
     *        whether an optional chip (like the ADAU1466 DSP) is
     *        physically populated.
     * @param address7Bit 7-bit I2C device address to probe.
     * @param timeoutMs Probe timeout in milliseconds.
     * @return true if a device acknowledged the address.
     */
    bool probe(uint8_t address7Bit, int timeoutMs) const;

private:
    i2c_master_bus_handle_t bus_ = nullptr;
};

} // namespace tas

#endif
