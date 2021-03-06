/*
NeatAmp - TAS3251 - Slave

Slave board shall be configured with I2C ADR Jumper "set"

This is the Slave version to be used controlled by a Master Board. Slave uC
- monitors that there is sufficient voltage
- put in reset mode and wait temp to lower in case of Overload,
- set the board in Reset/DAC Muted/Sleep mode depending on resetAmpConn state

Master board feeds:
- the I2C for DSP config,
- the I2C for Volume,
- the resetAmpConn for resets and sleep modes



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

// Declaration of the State Machine: Sates, Events, Functions
enum State_enum {WAIT_POWER, ACTIVE, FORCED_RESET};

// Declaration of all inpouts - outputs with Applicative names
int voltagePin =  PA1;   // select the input pin for the voltage monitoring
int resetAmpPin = PF7;   // select the pin for the TAS3251 ResetAmp
int resetAmpConn =PB9;   // select the pin for the forced ResetAmp from connector or reset jumper
int faultPin =    PB3;   // select the pin for the Red LED ResetAmp
int clipOtwPin =  PA15;  // select the pin for clipOtwPin
int dacMutePin =  PB8;    // select the pin for dacMutePin

// Define constants for applicative constants
#define VOLTAGE_MIN 700  // Corresponds to GVDD about 11.3V 

//Declaration of global variables
int     voltageValue = 0;  // variable to store the value coming from the sensor
uint8_t state = WAIT_POWER;

void state_machine_run();
void startup_sequence();
void shutdown_sequence();
void fault_sequence();

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
  pinMode(resetAmpConn, INPUT);

  
  
  // Delay to ensure that Master is started before TBD may be detrimental to correct operation 
  //delay (10);
  
  // initialize Serial1:
  Serial.begin(9600);
  Serial.println("End of Setup Slave");
  Serial.println("WAIT_POWER");

}

// the loop function runs over and over again forever
void loop() {

  // run the state machine
  state_machine_run();
  
  digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
  delay(100);                       // wait for a second
  
  digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
  delay(100);                       // wait for a second
}

// State Machine core code
void state_machine_run() 
{
  switch(state)
  {
    case WAIT_POWER:
      // If the voltage is above min (with -10 / +10 hysteresis)and resetAmpConn == LOW , as you don't want the slave to start when Master would be already 
      // active and DSP config not foreseen. If HIGH, it will stay in "WAIT_POWER" state
      // ResetAmpConn, when not connected, is pulled down to GND and is LOW. This shall correspond to TAS3251 Reset LOW (amp is shutdowned)
      // When Master board raises ResetAmpConn, TAS3251 Reset shall be set to HIGH (amp is activated)   
 
      if((analogRead(voltagePin) > (VOLTAGE_MIN +10)) and
        (digitalRead(resetAmpConn) == LOW)){
        state = FORCED_RESET;
        Serial.println("FORCED_RESET");
      }
      break;
       
    case ACTIVE:
      // If the voltage is below min (with -10 / +10 hysteresis), the TAS3251 shutdown sequence is performed
      //Serial.println("ACTIVE");
      if(analogRead(voltagePin) < (VOLTAGE_MIN -10)){
        shutdown_sequence();
        state = WAIT_POWER;
        Serial.println("WAIT_POWER");
      }
      
      else if(digitalRead(faultPin) == LOW){
        Serial.println("FAULT");
        fault_sequence();
        state = ACTIVE;
        Serial.println("ACTIVE");
      }
      
      else if(digitalRead(resetAmpConn) == LOW){
        shutdown_sequence();
        state = FORCED_RESET;
        Serial.println("FORCED_RESET");
      }
      break;
 
    case FORCED_RESET:
      // If not enough Voltage => go to Wait Power
      // If resetAmpConn goes to High => go to Active
      
      if(analogRead(voltagePin) < (VOLTAGE_MIN -10)){
        state = WAIT_POWER;
        Serial.println("WAIT_POWER");
      }
      
      else if(digitalRead(resetAmpConn) == HIGH){
        startup_sequence();
        state = ACTIVE;
        Serial.println("ACTIVE");
      }
      break;
  }
}


void startup_sequence()
{
    //Enable the amplifier output stage by setting the RESET_AMP pin high.
    digitalWrite(resetAmpPin, HIGH);

    // Enable DAC
    digitalWrite(dacMutePin, HIGH);

    Serial.println("Activate Amp");
    // Now ready to Play audio through I2S or TDM.

}
 
void shutdown_sequence()
{
  // Disable DAC and ResetAmp
  digitalWrite(dacMutePin, LOW);
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
