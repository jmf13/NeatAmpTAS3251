/*
NeatAmp - TAS3251
Copyright (C) 2020  JMF11

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


typedef unsigned char cfg_u8;
typedef union {
    struct {
        cfg_u8 offset;
        cfg_u8 value;
    };
    struct {
        cfg_u8 command;
        cfg_u8 param;
    };
} cfg_reg;

#define CFG_META_SWITCH (255)
#define CFG_META_DELAY  (254)
#define CFG_META_BURST  (253)


// To check - credit to  chipdipru N7DAMP-digital-power-amplifier-TAS325-x-2-quadro
// https://github.com/chipdipru/N7DAMP-digital-power-amplifier-TAS325-x-2-quadro-/blob/master/RDC2-0032_DSP_TAS3251x2/Inc/TAS3251.h#L70


#define   TAS3251_1_I2C_ADDRESS            0x4B
#define   TAS3251_2_I2C_ADDRESS            0x96

#define   TAS3251_CHANGE_PAGE_REG          0x00
#define   TAS3251_CHANGE_BOOK_REG          0x7F
#define   TAS3251_DSP_BOOK                 0x8C
#define   TAS3251_DSP_SWAP_FLAG_PAGE       0x23
#define   TAS3251_DSP_SWAP_REG             0x14

//PAGE0 Registers
#define   TAS3251_OPERATION_MODES_REG      0x02
#define   TAS3251_MUTE_REG                 0x03
   #define   TAS3251_MUTE_ENABLE           0x11
   #define   TAS3251_MUTE_DISABLE          0x00
#define   TAS3251_LEFT_VOLUME_REG          0x3D
#define   TAS3251_RIGHT_VOLUME_REG         0x3E


#define   TAS3251_VOL_MIN                  0xA4 // -58 dB
#define   TAS3251_VOL_MAX                  0x30 //   0 dB
// ADC_STEPS_PER_VOLUME_UNIT should be calculated by 1024/(TAS3251_VOL_MIN - TAS3251_VOL_MAX)
#define ADC_STEPS_PER_VOLUME_UNIT          9

#define   TAS3251_VOL_MUTE                 0x0A // index for -38 dB

// End of credit to N7DAMP



// ----------------------------------------------------
// Export of config file from PPC3
// It defines the complete configuration of the TAS3251
// ----------------------------------------------------


cfg_reg registers[] = {
//program memory
  { 0x00, 0x00 },   
    { 0x7f, 0x00 },   // Switch to Book 0
    { 0x02, 0x11 },   // PowerDown DSP. Bit 0 not documented
    { 0x00, 0x00 },
    { 0x00, 0x00 },
    { 0x01, 0x11 },   // Reset module & registers. Bits are auto cleared
    { 0x00, 0x00 },   // Wait
    { 0x00, 0x00 },
    { 0x00, 0x00 }, 
    { 0x00, 0x00 },
    { 0x00, 0x00 },
    { 0x03, 0x11 },   // Mute L&R
    { 0x2a, 0x00 },   // Zero Data path L&R (= mute...)
    { 0x25, 0x18 },   // Ignore MCLK error detection
    { 0x0d, 0x00 },   // Clk config... Auto clock mode SDSP=000
    { 0x28, 0x03 },   // Set I2S 32bits
    { 0x02, 0x00 },   // Wake up DSP
//Sample rate update
    { 0x00, 0x00 },   
    { 0x7f, 0x00 },   // Switch to Book0 ... again
    { 0x02, 0x80 },   //Reset DSP
    { 0x00, 0x00 },   
    { 0x7f, 0x00 },   // Switch to Book0 ... again
// speed 03-48k 04-96k
//dynamically reading speed
    { 0x22, 0x03 },   // Set FS Speed. Ignored in auto clock mode  
    { 0x00, 0x00 },   // Switch to Book0 ... again
    { 0x7f, 0x00 },
    { 0x02, 0x00 },   //Restart DSP
    { 0x00, 0x00 },
    { 0x00, 0x00 }, 
    { 0x00, 0x00 },
    { 0x00, 0x00 },
//write coefficients of various components
    { 0x00, 0x00 },   // Switch to Book8c
    { 0x7f, 0x8c },
    { 0x00, 0x1e },
    { 0x44, 0x00 },   // Vol to 0dB L&R
    { 0x45, 0x80 },
    { 0x46, 0x00 },
    { 0x47, 0x00 },
    { 0x48, 0x00 },
    { 0x49, 0x80 },
    { 0x4a, 0x00 },
    { 0x4b, 0x00 },

//swap command
    { 0x00, 0x00 },   
    { 0x7f, 0x8c },   // Switch to Book8c
    { 0x00, 0x23 },   // Goto Page 23
    { 0x14, 0x00 },   // Write 00 00 00 01 in reg 0x14+
    { 0x15, 0x00 },
    { 0x16, 0x00 },
    { 0x17, 0x01 },

//register tuning
    { 0x00, 0x00 },   
    { 0x7f, 0x00 },   // Switch to Book0
    { 0x00, 0x00 },
    { 0x07, 0x00 },   // SDOut is post processing output 
    { 0x08, 0x20 },   // SDOut is output. No mute from PCM
    { 0x55, 0x16 },   // SDOut mux selector - DSP Boot done
    { 0x00, 0x00 },   
    { 0x7f, 0x00 },   // Switch to Book0
    { 0x00, 0x00 },
    { 0x3d, 0x58 },   // Digital volume Left 58-> -24dB-20dB = -44dB -> 88=0x58
    { 0x3e, 0x48 },   // Digital volume Right
    { 0x00, 0x00 },   
    { 0x7f, 0x00 },   // Switch to Book0
    { 0x00, 0x01 },   // Switch to Page1
    { 0x02, 0x00 },   // Analog Gain set to 0dB  
    { 0x06, 0x01 },   // Analog mute follows digital mute  


//Unmute the device
    { 0x00, 0x00 },   // Switch to Book0
    { 0x7f, 0x00 },
    { 0x03, 0x00 },   // UnMute L&R  
    { 0x2a, 0x11 },   // Enable data path (L-L & R-R)

};
