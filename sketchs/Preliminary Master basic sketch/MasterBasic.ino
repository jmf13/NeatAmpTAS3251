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

#include <Wire.h>
#include <TAS3251.h>

// Declaration of the State Machine: Sates, Events, Functions
enum State_enum {WAIT_POWER, ACTIVE, FORCED_RESET, SLEEP};

// Declaration of all inpouts - outputs with Applicative names
int voltagePin =  PA1;   // select the input pin for the potentiometer
int volumePin =   PA0;   // select the input pin for the potentiometer
int resetAmpPin = PF7;   // select the pin for the TAS3251 ResetAmp
int resetAmpConn =PB9;   // select the pin for the forced ResetAmp from connector or reset jumper
int faultPin =    PB3;   // select the pin for the Red LED ResetAmp
int sleepPin =    PA2;   // select the pin for SleepPin
int clipOtwPin =  PA15;  // select the pin for clipOtwPin
int dacMutePin = PB8;    // select the pin for dacMutePin

// Define constants for applicative constants
#define VOLTAGE_MIN 700  // Corresponds to GVDD about 11.3V 

//Declaration of global variables
uint8_t volume = TAS3251_VOL_MIN;
int     voltageValue = 0;  // variable to store the value coming from the sensor
int     volumeValue = 0; //for tests
uint8_t state = WAIT_POWER;

void state_machine_run();
void startup_sequence();
void shutdown_sequence();
void fault_sequence();
void reset_sequence();
void adjust_volume();
void init_registers(cfg_reg *r, int n);

// the setup function runs once when you press reset or power the board
void setup() {
  // declare the folllowing pins as OUTPUTs and initialize them
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  
  pinMode(resetAmpPin, OUTPUT);
  digitalWrite(resetAmpPin, LOW);

  pinMode(dacMutePin, OUTPUT);
  digitalWrite(dacMutePin, LOW);
  
  // declare the folllowing pins as an INPUT:
  pinMode(faultPin, INPUT);
  pinMode(clipOtwPin, INPUT);
  pinMode(sleepPin, INPUT);
  pinMode(resetAmpConn, INPUT);

  // join i2c bus (address optional for master)
  Wire.begin(); 

  // for test delay before init
  delay (5);
  
  // initialize the TAS3251
  init_registers(registers, sizeof(registers)/sizeof(registers[0]));

  //delay (5);

  // initialize Serial1:
  Serial.begin(9600);
  Serial.println("End of Setup");
  
}

// the loop function runs over and over again forever
void loop() {

  // run the state machine
  state_machine_run();
  
  digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
  // digitalWrite(resetAmpPin, HIGH);
  delay(200);                       // wait for a second
  
  digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
  // digitalWrite(resetAmpPin, LOW);
  delay(300);                       // wait for a second
}

// State Machine core code
void state_machine_run() 
{
  switch(state)
  {
    case WAIT_POWER:
      // If the voltage is above min (with -10 / +10 hysteresis), the TAS3251 startup sequence is performed
      Serial.println("WAIT_POWER");
      if(analogRead(voltagePin) > (VOLTAGE_MIN +10)){
        startup_sequence();
        state = ACTIVE;
        Serial.println("ACTIVE");
      }
      break;
       
    case ACTIVE:
      // If the voltage is below min (with -10 / +10 hysteresis), the TAS3251 shutdown sequence is performed
      Serial.println("ACTIVE");
      if(analogRead(voltagePin) < (VOLTAGE_MIN -10)){
        shutdown_sequence();
        state = WAIT_POWER;
      }
      else if(digitalRead(faultPin) == LOW){
        Serial.println("FAULT");
        fault_sequence();
        state = ACTIVE;
      }
      else if(digitalRead(sleepPin) == HIGH){
        shutdown_sequence();
        state = SLEEP;
      }
       else if(digitalRead(resetAmpConn) == HIGH){
        reset_sequence();
        state = FORCED_RESET;
      }
      else{
        adjust_volume();
        state = ACTIVE;
      }
      break;
 
    case FORCED_RESET:
      // ## to assess the behaviour for the sleep input: 2 positions swith or push button
      // assumption here that it is a 2 positions switch
      // When exiting the sleep mode, go to WAIT_POWER to perform the startup sequence
      Serial.println("FORCED_RESET");
      
      if(digitalRead(resetAmpConn) == LOW){
        state = WAIT_POWER;
      }
      break;
      
    case SLEEP:
      // ## to assess the behaviour for the sleep input: 2 positions swith or push button
      // assumption here that it is a 2 positions switch
      // When exiting the sleep mode, go to WAIT_POWER to perform the startup sequence
      Serial.println("SLEEP");
      if(digitalRead(sleepPin) == LOW){
        state = WAIT_POWER;
      }
      else if(digitalRead(faultPin) == LOW){
        fault_sequence();
        state = ACTIVE;
      }
      else if(digitalRead(sleepPin) == HIGH){
        shutdown_sequence();
        state = SLEEP;
      }
      else{
        adjust_volume();
        state = ACTIVE;
      }
      break;
  }
}


void startup_sequence()
{
    Serial.println("Config DSP");
    //!!! Have some mecanism to detect if the I2S source is not here, and wait for it in that case !!!
    // According to TAS3251 datasheet 8.3.11.1 Power Up and Startup Sequence
    // Activation of thois procedure means there is voltage above the Min Threshold
    // Apply I2S or TDM clocks to the device to enable the internal system clocks
    // this is done by other components and may not be achieved. If not, I2C communication with the TAS3251 won't be possible
    // Set DSP coefficients and configuration settings through I2C (optional). The DSP will pass-through audio if no registers are changed.
    // includes Mute the left and right DAC channels, by setting Register 0x03, Bits 0 (right) and 4 (left) to '1'.
    // includes ring the DSP out of standby by setting Register 0x02, Bit 7 (DSPR) to '1'.
    // includes Unmute the left and right DAC channels, by setting Register 0x03, Bits 0 (right) and 4 (left) to '0'.
    init_registers(registers, sizeof(registers)/sizeof(registers[0]));
    
    // Delay 400ms mini as of datasheet 8.3.11.9 Output Power Stage Startup Timing: The TAS3251 output power stage 
    // does not require a specific power-up sequence, but it is recommended to hold RESET low for a minimum of 400 ms 
    // after PVDD supply voltage is powered on.
    delay(400);

    adjust_volume();
    
    //Enable the amplifier output stage by setting the RESET_AMP pin high.
    digitalWrite(resetAmpPin, HIGH);

    // Enable DAC
    digitalWrite(dacMutePin, HIGH);

    Serial.println("Activate Amp");
    // Now ready to Play audio through I2S or TDM.

}
 
void shutdown_sequence()
{
  //code for shutdown_sequence
  digitalWrite(resetAmpPin, LOW);  
}

//code for fault_sequence
void fault_sequence()
{
  // Wait until system temperature gets back to normal temperature: /CLIP_OTW high
  while (digitalRead(clipOtwPin) == LOW)
  {
    delay (100);
  }
  digitalWrite(resetAmpPin, LOW);
  delay (10);
  digitalWrite(resetAmpPin, HIGH);
}

void reset_sequence()
{
  //## Mute DAC and DSP
  // Disable Power stage
  digitalWrite(resetAmpPin, LOW);
}

void adjust_volume()
{
  int     volumeValue;
  uint8_t volumeScaled;
  
  //code for adjust_volume, with small hysteresis
  // Read Volume pot
  // assumed default resolution of 10 bits: value 0-1023 for 10 bits
  // then scaled to 8 bits
  
  volumeValue = analogRead(volumePin);
  
  // Scale the value to cope with TAS3251 range
  volumeValue = volumeValue/ADC_STEPS_PER_VOLUME_UNIT;
  volumeScaled = (uint8_t) volumeValue + TAS3251_VOL_MAX;
  
  // Serial.println("volumeScaled");               
  // Serial.println(volumeScaled, HEX);

  if (volumeScaled != volume) {
     //Serial.println("Change volume");               
     //Serial.println(volume, HEX);                   // print volume as an ASCII-encoded hexadecimal
     volume = volumeScaled;
     writeRegister (TAS3251_1_I2C_ADDRESS, TAS3251_LEFT_VOLUME_REG, volume);
     writeRegister (TAS3251_1_I2C_ADDRESS, TAS3251_RIGHT_VOLUME_REG, volume);
  }
}

// Example implementation.  Call like:
//     init_registers(registers, sizeof(registers)/sizeof(registers[0]));

void init_registers(cfg_reg *r, int n)
    {
        int i = 0;
        
        while (i < n) {
            switch (r[i].command) {
            case CFG_META_SWITCH:
                // Used in legacy applications.  Ignored here.
                break;
            case CFG_META_DELAY:
                delay(r[i].param);
                break;
            // case CFG_META_BURST:
            //     Wire.write((unsigned char *)&r[i+1], r[i].param);
            //    i +=  (r[i].param + 1)/2;
            //    break;
            default:
                writeRegister (TAS3251_1_I2C_ADDRESS, r[i].offset, r[i].value);
                break;
            }
            i++;
        }
    }

void readRegister (char address, char reg)
  {
    Wire.beginTransmission(address);  // Connects TAS
    Wire.write(reg);                  // move your register pointer to reg
    Wire.endTransmission();           // close write
    Wire.requestFrom(address, 1);     // now get the data from the TAS
    Wire.read(); // receive a byte
  }

void writeRegister (char address, char reg, char value)
  {
    Wire.beginTransmission(address);  // Connects TAS
    Wire.write(reg);            // move register pointer back to reg
    Wire.write(value);          // write value
    Wire.endTransmission();     // close write
  }
  
