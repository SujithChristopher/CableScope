#include "HX711_ADC.h"
#include <Encoder.h>

// Communication protocol constants
#define HEADER1 0xFF
#define HEADER2 0xFF
#define CMD_SET_TORQUE 0x01
#define CMD_GET_DATA 0x02
#define DATA_PACKET_SIZE 9  // 1 byte cmd + 4 bytes torque + 4 bytes angle

// Calibration factors for torque sensor
#define calibration_factor5 91160.52  //-842222//91160.52

//Torque Sensor
#define torqueSensor_DOUT_PIN 32
#define torqueSensor_SCK_PIN 33

#define ENC1A 3  //27// 23//6//28//2//2//27//3//6//2//5//26
#define ENC1B 2  //2//28// 22//27//3//3//28//2//7//3//4//25

#define ENC1MAXCOUNT 4 * 4096 * 53       //4*43*4096//4*2500//4 * 90500//4*43*2048//
#define ENC1COUNT2DEG 0.25f * 0.001658f  //0.25f*0.002044f//0.25f*0.002044f//0.25f * 0.0039779f//0.25f*0.0040879f//

// Encoder objects.
Encoder angle(ENC1A, ENC1B);
long _enccount;

// Motor control pins
const int pwmPin = 8;         // PWM pin for controlling motor speed
const int enablePin = 9;      // Enable pin to turn motor on/off
const int directionPin = 10;  // Direction pin to control motor direction

float torque;
float pwm_value;

float Theta;  // angle measured

float desiredTorque = 0.0;  // Torque given from Python
float angleD;
float motor_current;

float t;
float TS;

// Communication variables
bool dataReady = false;
unsigned long lastDataTime = 0;
const unsigned long dataInterval = 100; // Send data every 100ms

//Torque Sensor instance
HX711_ADC torqueSensor(torqueSensor_DOUT_PIN, torqueSensor_SCK_PIN);

void setup() {

  Serial.begin(115200);  // Higher baud rate for better communication

  // Torque Sensor setup
  torqueSensor.begin();

  torqueSensor.setCalFactor(calibration_factor5);

  //Torque Sensor
  torqueSensor.tare();

  //Motor Setup
  pinMode(pwmPin, OUTPUT);
  pinMode(enablePin, OUTPUT);
  pinMode(directionPin, OUTPUT);

  // Encoder reading pins for Motor 1
  pinMode(ENC1A, INPUT_PULLUP);
  pinMode(ENC1B, INPUT_PULLUP);

  digitalWrite(enablePin, LOW);

  analogWriteResolution(12);
  analogReadResolution(12);
}

void loop() {
  // Handle incoming serial commands
  handleSerialCommands();
  
  // Update torque sensor
  torqueSensor.update();
  TS = torqueSensor.getData();

  // Read encoder angle
  Theta = angle_motor();

  // Control motor based on desired torque
  controlMotor();

  // Send data to Python at regular intervals
  if (millis() - lastDataTime >= dataInterval) {
    sendDataPacket();
    lastDataTime = millis();
  }
}

// Function to read encoder angle in degrees
float angle_motor() {
  _enccount = angle.read();
  float angleDegrees = _enccount * ENC1COUNT2DEG;
  return angleDegrees;
}

// Handle incoming serial commands from Python
void handleSerialCommands() {
  if (Serial.available() >= 3) {
    uint8_t header1 = Serial.read();
    if (header1 == HEADER1) {
      uint8_t header2 = Serial.read();
      if (header2 == HEADER2) {
        uint8_t command = Serial.read();
        
        if (command == CMD_SET_TORQUE && Serial.available() >= 4) {
          // Receive desired torque as float (4 bytes)
          union {
            float f;
            uint8_t bytes[4];
          } torqueData;
          
          for (int i = 0; i < 4; i++) {
            torqueData.bytes[i] = Serial.read();
          }
          
          desiredTorque = torqueData.f;
          
          // Send acknowledgment
          Serial.write(HEADER1);
          Serial.write(HEADER2);
          Serial.write(0xAA); // ACK
        }
      }
    }
  }
}

// Control motor based on desired torque
void controlMotor() {
  motor_current = desiredTorque / 3.35;  // Calculate motor current
  
  // Limit current to safe range
  motor_current = constrain(motor_current, -2.0, 2.0);
  
  if (abs(motor_current) < 0.01) {
    // Disable motor for very small currents
    digitalWrite(enablePin, LOW);
    analogWrite(pwmPin, 0);
  } else {
    // Set direction
    digitalWrite(directionPin, motor_current > 0 ? HIGH : LOW);
    
    // Calculate PWM value
    pwm_value = 409.6 + 410 * abs(motor_current);
    pwm_value = constrain(pwm_value, 0, 4095); // 12-bit PWM
    
    digitalWrite(enablePin, HIGH);
    analogWrite(pwmPin, (int)pwm_value);
  }
}

// Send data packet to Python
void sendDataPacket() {
  // Create data packet: Header(2) + Size(1) + Data(8) + Checksum(1)
  uint8_t packet[12];
  
  packet[0] = HEADER1;
  packet[1] = HEADER2;
  packet[2] = DATA_PACKET_SIZE; // Size of data + checksum
  packet[3] = CMD_GET_DATA;     // Command type
  
  // Pack torque as float (4 bytes)
  union {
    float f;
    uint8_t bytes[4];
  } torqueData;
  torqueData.f = TS;
  
  for (int i = 0; i < 4; i++) {
    packet[4 + i] = torqueData.bytes[i];
  }
  
  // Pack angle as float (4 bytes)
  union {
    float f;
    uint8_t bytes[4];
  } angleData;
  angleData.f = Theta;
  
  for (int i = 0; i < 4; i++) {
    packet[8 + i] = angleData.bytes[i];
  }
  
  // Calculate checksum
  uint8_t checksum = 0;
  for (int i = 2; i < 12; i++) {
    checksum += packet[i];
  }
  checksum = (~checksum) + 1; // Two's complement
  
  // Add checksum
  packet[11] = checksum;
  
  // Send packet
  Serial.write(packet, 12);
}
