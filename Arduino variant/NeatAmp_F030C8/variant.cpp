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

#include "pins_arduino.h"

#ifdef __cplusplus
extern "C" {
#endif

// Pin number
const PinName digitalPin[] = {
  PA_2,  // D0
  PA_3,  // D1
  PA_4,  // D2
  PA_5,  // D3
  PA_6,  // D4
  PA_7,  // D5
  PB_0,  // D6
  PB_1,  // D7
  PB_2,  // D8
  PF_7,  // D9  - RESET_AMP_TAS
  PB_3,  // D10 - FAULT
  PB_4,  // D11 - ADR_CONN
  PB_8,  // D12 - DAC_MUTE
  PB_9,  // D13 - RESET_AMP_CONN
  PC_14, // D14 - LED
  PA_0,  // D15 - A0 - VOLUME
  PA_1,  // D16 - A1 - VOLTAGE
  PB_6,  // D17 - I2C1_SCL
  PB_7,  // D18 - I2C1_SDA
  PB_13, // D19 - Not used
  PB_10, // D20 - I2C2_SCL
  PB_11, // D21 - I2C2_SDA
  PA_8,  // D22 - Not used
  PA_9,  // D23 - USART_TX
  PA_10, // D24 - USART_RX
  PA_11, // D25 - not used
  PA_12, // D26 - not used
  PA_15, // D27 - CLIP_OTW
  PB_5,  // D28 - not used
  PB_12, // D29 - not used
  PB_14, // D30 - not used
  PB_15, // D31 - not used
  PC_13, // D32 - not used
  PC_15, // D33 - not used
  PF_0,  // D34 - not used
  PF_1,  // D35 - not used
  PF_6,  // D36 - not used
  PA_13, // D37 - SWDIO
  PA_14, // D38 - SWCLK

};

// Analog (Ax) pin number array
const uint32_t analogInputPin[] = {
  15, //A0
  16, //A1
};

#ifdef __cplusplus
}
#endif

// ----------------------------------------------------------------------------

#ifdef __cplusplus
extern "C" {
#endif

/**
  * @brief  System Clock Configuration
  *         The system Clock is configured as follow :
  *            System Clock source            = PLL (HSI/2)
  *            SYSCLK(Hz)                     = 48000000
  *            HCLK(Hz)                       = 48000000
  *            AHB Prescaler                  = 1
  *            APB1 Prescaler                 = 1
  *            HSE Frequency(Hz)              = 16000000
  *            PREDIV                         = 1
  *            PLLMUL                         = 3
  *            Flash Latency(WS)              = 1
  * @param  None
  * @retval None
  */
WEAK void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the CPU, AHB and APB busses clocks 
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI|RCC_OSCILLATORTYPE_HSI14;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSI14State = RCC_HSI14_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.HSI14CalibrationValue = 16;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }
  /** Initializes the CPU, AHB and APB busses clocks 
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USART1|RCC_PERIPHCLK_I2C1;
  PeriphClkInit.Usart1ClockSelection = RCC_USART1CLKSOURCE_PCLK1;
  PeriphClkInit.I2c1ClockSelection = RCC_I2C1CLKSOURCE_HSI;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

#ifdef __cplusplus
}
#endif
