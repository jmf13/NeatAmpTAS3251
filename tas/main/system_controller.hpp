/**
 * @file system_controller.hpp
 * @brief Orchestrates the amplifier startup sequence and the steady-state
 *        monitoring loop described in the tas/README.md "Firmware
 *        Architecture" section.
 */
#ifndef TAS_SYSTEM_CONTROLLER_HPP
#define TAS_SYSTEM_CONTROLLER_HPP

#include "dsp_adau1466.hpp"
#include "esp_err.h"
#include "i2c_bus.hpp"
#include "power_supplies.hpp"
#include "status_led.hpp"
#include "tas3251.hpp"

namespace tas {

/**
 * @brief Top-level state machine: bring the amplifier up in a safe,
 *        logged sequence, then hand off to a steady-state monitoring loop.
 *
 * Every state transition is logged at ESP_LOGI; every failure aborts the
 * sequence (leaving the amplifier held in reset and muted) and is logged
 * at ESP_LOGE.
 */
class SystemController {
public:
    /**
     * @brief Overall device status, also reflected on the U8 status LED.
     *        /CLIP_OTW does NOT change this — it is logged only (see
     *        runForever()). /FAULT moves this to Fault, mutes the amp at a
     *        conservative low volume, and stays there (no automatic
     *        recovery yet — see the runForever() TODO).
     */
    enum class Status {
        Booting,       ///< startup() is running. LED: blue.
        Ready,         ///< startup() succeeded, amp unmuted and nominal. LED: green.
        Fault,         ///< /FAULT latched: amp muted at low volume. LED: red.
        StartupFailed, ///< startup() aborted before reaching Ready. LED: amber.
    };

    SystemController() = default;

    /**
     * @brief Run the startup sequence: assert RESET_AMP/DAC_MUTE, init
     *        peripherals, sequence the power rails, mute the DACs and bring
     *        the DSP out of standby over I2C while still in reset, then
     *        release DAC_MUTE and finally RESET_AMP. See tas/README.md
     *        "Startup sequence" for the full state list and timing.
     * @return ESP_OK if the amplifier reached the "ready" state.
     */
    esp_err_t startup();

    /**
     * @brief Steady-state monitoring loop: polls /FAULT, /CLIP_OTW and the
     *        13.2V-good line. Does not return under normal operation.
     */
    void runForever();

    /** @brief Current status (see Status). */
    Status status() const { return status_; }

private:
    esp_err_t fail(esp_err_t err);
    void handleFault();
    void handleClipOtw();

    I2cBus i2cBus_;
    PowerSupplies power_;
    Tas3251 amp_;
    Dsp dsp_;
    StatusLed statusLed_;
    Status status_ = Status::Booting;
};

} // namespace tas

#endif
