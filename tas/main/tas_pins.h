/**
 * @file tas_pins.h
 * @brief Raw ESP32-S3 GPIO/I2C pin assignments for the NeatAmpTAS3251 board.
 *
 * These constants are the single source of truth for the pin mapping
 * documented in the "ESP32-S3 Hardware IO" and "Potential DSP (ADAU1466)
 * Connectivity" tables in the top-level README.md of this firmware project.
 * They are consumed by tas::PowerSupplies, tas::Tas3251 and tas::Dsp; no
 * other file should hardcode a GPIO number.
 */
#ifndef TAS_PINS_H
#define TAS_PINS_H

#include "driver/gpio.h"
#include "driver/i2c_master.h"

/** @name Shared I2C control bus (TAS3251 + optional ADAU1466 registers) */
///@{
#define TAS_I2C_PORT I2C_NUM_0
#define TAS_I2C_FREQUENCY_HZ 400000

#define TAS_PIN_I2C_SDA GPIO_NUM_0
#define TAS_PIN_I2C_SCL GPIO_NUM_45
///@}

/** @name TAS3251 amplifier control/status lines */
///@{
#define TAS_PIN_AMP_RESET GPIO_NUM_42
#define TAS_PIN_DAC_MUTE GPIO_NUM_1
#define TAS_PIN_AMP_FAULT GPIO_NUM_41
#define TAS_PIN_AMP_CLIP_OTW GPIO_NUM_2
#define TAS_PIN_AMP_ADDRESS GPIO_NUM_12
///@}

/** @name Power sequencing lines (see PowerSupplies) */
///@{
#define TAS_PIN_GOOD_13V2 GPIO_NUM_39
#define TAS_PIN_ENABLE_12V GPIO_NUM_38
#define TAS_PIN_ENABLE_3V3_ANALOG GPIO_NUM_40
///@}

/*
 * TODO(HW V1.3, hw_review P0-7): PVDD sense on IO8 = ADC1_CH7.
 *   Divider: R53 100k (PVDD) / R54 6.8k (GND) + C70 100nF at the pin.
 *   V_pin = PVDD * 6.8 / 106.8  ->  36 V = 2.29 V, 30 V = 1.91 V, 40 V = 2.55 V.
 *   Source impedance about 6.4 kOhm, tau about 0.64 ms.
 *   Not enabled yet: on the V1.2 map below, IO8 is still TAS_PIN_STATUS_LED_SDI.
 *   Add this line together with the V1.3 pin-map update from hw_review P0-2
 *   (LED_DATA -> IO46, LED_CLK -> IO3):
 *     #define TAS_PIN_PVDD_SENSE GPIO_NUM_8   // ADC1_CHANNEL_7, input only
 *   Reworked V1.0/V1.1 (tas/README "pop-free rework" step P2): the same
 *   divider is built off-board on U7 pin 3, i.e. GPIO_NUM_4 (ADC1_CHANNEL_3).
 *   Make the pin a board-revision option (Kconfig) instead of a fixed value.
 *   Use ADC1 only (ADC2 isn't available while Wi-Fi is on).
 *   See PowerSupplies for the monitor and shutdown logic still to be written.
 */

/** @name Optional ADAU1466 DSP control lines (connector U10) */
///@{
#define TAS_PIN_DSP_RESET GPIO_NUM_47
#define TAS_PIN_DSP_SELFBOOT GPIO_NUM_48
///@}

/**
 * @name Status LED chain (U8, U9 — SK9822, APA102-compatible clocked RGB)
 * U8 is first in the chain (data/clock in from the ESP32-S3), its CKO/SDO
 * feed U9's CKI/SDI.
 *
 * HW V1.0/V1.1 routed these to IO36/IO37 (module pins 29/30) through R18/R17,
 * but on the ESP32-S3-WROOM-1U-N8R8 those pins belong to the internal Octal
 * PSRAM and must not be used. From HW V1.2 the chain is driven from IO8/IO9
 * through R18/R17 (Netlist_Class_D_amp_2026-10-30.enet). V1.0/V1.1 boards get
 * the same mapping with the documented rework: R17/R18 removed, H2 pins 7/8
 * (IO8/IO9 on those revisions) wired to the LED side of R18/R17.
 */
///@{
#define TAS_PIN_STATUS_LED_SDI GPIO_NUM_8
#define TAS_PIN_STATUS_LED_CKI GPIO_NUM_9
///@}

/**
 * @note GPIO35, GPIO36 and GPIO37 (module pins 28, 29, 30) are wired
 * internally to the Octal PSRAM on the N8R8 module and are reserved. Driving
 * them corrupts PSRAM accesses and crashes the firmware. The check below
 * stops any pin assignment in this file from landing on them.
 */
#include <assert.h>
#include "sdkconfig.h"

#if CONFIG_SPIRAM_MODE_OCT
#define TAS_PIN_IS_OPI_PSRAM(pin) ((pin) >= GPIO_NUM_35 && (pin) <= GPIO_NUM_37)
static_assert(!TAS_PIN_IS_OPI_PSRAM(TAS_PIN_I2C_SDA) && !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_I2C_SCL) &&
                  !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_AMP_RESET) && !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_DAC_MUTE) &&
                  !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_AMP_FAULT) && !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_AMP_CLIP_OTW) &&
                  !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_AMP_ADDRESS) && !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_GOOD_13V2) &&
                  !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_ENABLE_12V) && !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_ENABLE_3V3_ANALOG) &&
                  !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_DSP_RESET) && !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_DSP_SELFBOOT) &&
                  !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_STATUS_LED_SDI) && !TAS_PIN_IS_OPI_PSRAM(TAS_PIN_STATUS_LED_CKI),
              "GPIO35-37 are reserved for the Octal PSRAM on ESP32-S3-WROOM-1U-N8R8");
#endif

/**
 * @note I2S audio bus (MCLK/BCLK/LRCK/SDIN) is NOT currently wired to any
 * ESP32-S3 GPIO. Per Netlist_Class_D_amp_2026-07-23.enet (repository root),
 * connector U11 (the external DIR9001/DSP I2S header) only connects to the
 * TAS3251 (U12 pins 47-50) through 22 Ohm series resistors — the ESP32-S3
 * (U6) has no net in common with MCLK/LRCK/SCLK/SDIN on the current board
 * revision. tas::I2sBus therefore takes its pin assignment as a runtime
 * parameter rather than a macro defined here; do not add ESP32 I2S pin
 * macros to this file until a board revision actually routes them.
 */

#endif
