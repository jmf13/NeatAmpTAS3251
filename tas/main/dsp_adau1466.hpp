/**
 * @file dsp_adau1466.hpp
 * @brief Driver stub for the optional Analog Devices ADAU1466 DSP
 *        daughterboard (I2S input connector, power supply and I2C
 *        interface are prepared on the board, per the hardware README —
 *        the DSP itself is not populated on current boards).
 */
#ifndef TAS_DSP_ADAU1466_HPP
#define TAS_DSP_ADAU1466_HPP

#include <cstdint>
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "i2c_bus.hpp"

namespace tas {

/**
 * @brief Controls the ADAU1466 RESET/SELF_BOOT straps and, if the chip is
 *        physically present, attaches an I2C device handle for future
 *        register access.
 *
 * @warning kI2cAddress7Bit below is a placeholder default for the ADAU1466
 *          family and has NOT been confirmed against the populated part's
 *          datasheet/address strapping. Since the DSP is not yet populated
 *          on any assembled board, isPresent() is expected to return false
 *          until this is revisited alongside real hardware and DSP
 *          firmware.
 */
class Dsp {
public:
    Dsp() = default;

    /**
     * @brief Configure DSP_RESET/DSP_SELFBOOT as outputs (holding the DSP in
     *        reset by default) and probe the I2C bus for its presence.
     * @param bus Already-initialized shared I2C bus (see I2cBus::init()).
     * @return ESP_OK if GPIO configuration succeeded, regardless of whether
     *         the DSP was detected — check isPresent() for that.
     */
    esp_err_t init(const I2cBus &bus);

    /** @brief Drive DSP_RESET. @param assertReset true = hold in reset. */
    esp_err_t reset(bool assertReset);

    /** @brief Drive DSP_SELFBOOT (self-boot-from-EEPROM strap). */
    esp_err_t setSelfBoot(bool selfBoot);

    /** @brief True if the DSP acknowledged its I2C address during init(). */
    bool isPresent() const { return present_; }

private:
    i2c_master_dev_handle_t dev_ = nullptr;
    bool present_ = false;
};

} // namespace tas

#endif
