/**
 * @file power_supplies.hpp
 * @brief Controls the power-sequencing signals the ESP32-S3 senses/drives
 *        for three of the board's rails: the 13.2V intermediate rail
 *        (sensed only), the 12V GVDD analog rail, and the 3.3V analog
 *        (DAC_AVDD) rail. See the hardware README "Power Supply
 *        Architecture" section for the full multi-rail design — the other
 *        rails (PVDD, 5V, 3.3V digital) are not firmware-controlled.
 */
#ifndef TAS_POWER_SUPPLIES_HPP
#define TAS_POWER_SUPPLIES_HPP

#include "esp_err.h"

namespace tas {

/**
 * @brief GPIO-level control for the three ESP32-visible power rails.
 *
 * - **13.2V** (LMQ66410 buck output): sense-only, GOOD_13.2V input.
 * - **12V GVDD analog** (TPS7A4701 LDO): ESP32-enabled, ENABLE_12V output.
 * - **3.3V analog** (TPS7A2033 LDO, DAC_AVDD only): ESP32-enabled,
 *   ENABLE_3.3V output. Hardware default is enabled (100 kOhm pull-up to
 *   3.3V digital); this class still drives it explicitly so firmware state
 *   matches hardware state.
 */
/*
 * TODO(HW V1.3, hw_review P0-7): PVDD monitor + pop-free shutdown.
 *
 * Hardware: TAS_PIN_PVDD_SENSE (V1.3: IO8, ADC1_CH7; reworked V1.0/V1.1:
 * IO4, ADC1_CH3), divider 100k / 6.8k,
 * PVDD = V_pin * 106.8 / 6.8 (factor about 15.7). See tas_pins.h.
 *
 * 1. ADC: adc_oneshot on ADC1_CH7, ADC_ATTEN_DB_12, plus adc_cali (curve
 *    fitting) so the result is in mV. The usable range is about 0-3.1 V. Do
 *    not use ADC2.
 * 2. Sampling: every <= 1 ms from a high-priority task or esp_timer.
 *    Light averaging only (e.g. 4 samples). Total detection latency must
 *    stay < 2 ms, because at full music load PVDD falls about 750 V/s
 *    (6600 uF, ~5 A), which gives ~8 ms from 36 V to 30 V. At idle it's
 *    ~60 V/s.
 * 3. Thresholds (with hysteresis):
 *      PVDD_LOW  = 30.0 V (or 85 % of the PVDD measured after start-up)
 *      PVDD_OK   = 33.0 V, held continuously for >= 500 ms before restart
 * 4. On PVDD < PVDD_LOW (also on TAS_FAULT, and before esp_restart/OTA):
 *      a) fast soft-mute: set the volume ramp to fastest (B0-P0-R64)
 *         and the I2C soft-mute (B0-P0-R3); or skip I2C if the bus is
 *         busy and go straight to b)
 *      b) DAC_MUTE low (TAS_PIN_DAC_MUTE)
 *      c) wait ~2-5 ms for the ramp
 *      d) RESET_AMP low (TAS_PIN_AMP_RESET), so the power stage is in Hi-Z
 *      e) enable12VAnalog(false), so GVDD is off
 *      f) latch state POWER_LOST. Do not touch the amp until step 5.
 *    The whole path from detection to RESET_AMP low should finish in < 6 ms.
 * 5. Recovery (brown-out or quick mains off/on, the ESP32 may stay alive):
 *    when PVDD >= PVDD_OK for >= 500 ms, re-run the normal start-up
 *    sequence from the ENABLE_12V state.
 * 6. At boot, don't run the start-up sequence until PVDD >= PVDD_OK
 *    (in addition to the existing GOOD_13.2V check).
 * 7. Expose pvddMillivolts() for logging/status. Calibrate the divider
 *    gain once against a DMM (1 % resistors give about +/-2 %).
 *
 * Also add a manual soft-off (needed on V1.0/V1.1 without PVDD sense):
 * a long press on SW2 (IO10, after the SW2 rework) and/or an `off` console
 * command running the same steps 4a-4f; short press or `on` re-runs
 * start-up.
 *
 * Hardware defaults that this relies on (V1.3; V1.0/V1.1 after rework P1): R45 pulls RESET_AMP low,
 * R7 pulls ENABLE_12V low, and R35 pulls DAC_MUTE low. So if the ESP32
 * resets or browns out, the amp ends up muted and in reset by itself.
 */
class PowerSupplies {
public:
    PowerSupplies() = default;

    /**
     * @brief Configure GOOD_13.2V as input and ENABLE_12V/ENABLE_3.3V as
     *        outputs, both driven low (disabled) initially.
     */
    esp_err_t init();

    /** @brief Read the 13.2V-good sense line. */
    bool isRail13V2Good() const;

    /** @brief Enable/disable the 12V GVDD analog rail. */
    esp_err_t enable12VAnalog(bool enable);

    /** @brief Last commanded state of the 12V GVDD analog rail. */
    bool isEnabled12VAnalog() const { return enabled12VAnalog_; }

    /** @brief Enable/disable the 3.3V analog (DAC_AVDD) rail. */
    esp_err_t enable3V3Analog(bool enable);

    /** @brief Last commanded state of the 3.3V analog rail. */
    bool isEnabled3V3Analog() const { return enabled3V3Analog_; }

private:
    bool enabled12VAnalog_ = false;
    bool enabled3V3Analog_ = false;
};

} // namespace tas

#endif
