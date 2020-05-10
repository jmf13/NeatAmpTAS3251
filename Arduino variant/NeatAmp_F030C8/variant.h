/*
NeatAmp - TAS3251
Copyright (C) 2020  JMF11 JM. Fourneron

Declaration of all TAS3251 specific types and constants 

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

*/

#ifndef _VARIANT_ARDUINO_STM32_
#define _VARIANT_ARDUINO_STM32_

#ifdef __cplusplus
extern "C" {
#endif // __cplusplus

/*----------------------------------------------------------------------------
 *        Pins
 *----------------------------------------------------------------------------*/

// P1 connector Right side (bottom view)
#define PA2  0  // GPIO A2
#define PA3  1  // GPIO A3
#define PA4  2  // GPIO A4
#define PA5  3  // GPIO A5
#define PA6  4  // GPIO A6
#define PA7  5  // GPIO A7
#define PB0  6  // GPIO B0
#define PB1  7  // GPIO B1
#define PB2  8  // GPIO B2
#define PF7  9  // RESET_AMP_TAS
#define PB3  10 // FAULT
#define PB4  11 // ADR_CONN
#define PB8  12 // DAC_MUTE
#define PB9  13 // RESET_AMP_CONN
#define PC14 14 // LED
#define PA0  15 // A0 - VOLUME
#define PA1  16 // A1 - VOLTAGE
#define PB6  17 // I2C1_SCL
#define PB7  18 // I2C1_SDA
#define PB13 19 // Not used
#define PB10 20 // I2C2_SCL
#define PB11 21 // I2C2_SDA
#define PA8  22 // Not used
#define PA9  23 // USART_TX
#define PA10 24 // USART_RX
#define PA11 25 // Not used
#define PA12 26 // Not used
#define PA15 27 // CLIP_OTW
#define PB5  28 // Not used
#define PB12 29 // Not used
#define PB14 30 // Not used
#define PB15 31 // Not used
#define PC13 32 // Not used
#define PC15 33 // Not used
#define PF0  34 // Not used
#define PF1  35 // Not used
#define PF6  36 // Not used
#define PA13 37 // SWDIO
#define PA14 38 // SWDIO

// This must be a literal
#define NUM_DIGITAL_PINS        39
// This must be a literal with a value less than or equal to to MAX_ANALOG_INPUTS
#define NUM_ANALOG_INPUTS       2
#define NUM_ANALOG_FIRST        15

//On-board LED pin number
#define LED_BUILTIN             PC14

//On-board user button
//#define USER_BTN                -1

// SPI definitions
// SPI1 is used
//#define PIN_SPI_SS              -1
//#define PIN_SPI_MOSI            PA7
//#define PIN_SPI_MISO            PA6
//#define PIN_SPI_SCK             PA5

// I2C Definitions
// I2C1 is used
#define PIN_WIRE_SDA            PB7
#define PIN_WIRE_SCL            PB6

// Timer Definitions
// Use TIM6 when possible as servo and tone don't need GPIO output pin
#define TIMER_TONE              TIM6
#define TIMER_SERVO             TIM14

// UART Definitions
#define SERIAL_UART_INSTANCE    1 // USART 1

// Mandatory for Firmata
#define PIN_SERIAL_RX           PA10
#define PIN_SERIAL_TX           PA9

#ifdef __cplusplus
} // extern "C"
#endif
/*----------------------------------------------------------------------------
 *        Arduino objects - C++ only
 *----------------------------------------------------------------------------*/

#ifdef __cplusplus
// These serial port names are intended to allow libraries and architecture-neutral
// sketches to automatically default to the correct port name for a particular type
// of use.  For example, a GPS module would normally connect to SERIAL_PORT_HARDWARE_OPEN,
// the first hardware serial port whose RX/TX pins are not dedicated to another use.
//
// SERIAL_PORT_MONITOR        Port which normally prints to the Arduino Serial Monitor
//
// SERIAL_PORT_USBVIRTUAL     Port which is USB virtual serial
//
// SERIAL_PORT_LINUXBRIDGE    Port which connects to a Linux system via Bridge library
//
// SERIAL_PORT_HARDWARE       Hardware serial port, physical RX & TX pins.
//
// SERIAL_PORT_HARDWARE_OPEN  Hardware serial ports which are open for use.  Their RX & TX
//                            pins are NOT connected to anything by default.
#define SERIAL_PORT_MONITOR     Serial
#define SERIAL_PORT_HARDWARE    Serial
#endif
