"""
Embedded Firmware Resources for CableScope Motor Control
Contains Arduino firmware code embedded as string constants to ensure
availability in distributed applications.
"""

# Main firmware.ino content
FIRMWARE_INO_CONTENT = '''#include "HX711_ADC.h"
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

#define ENC1A 27  //27// 23//6//28//2//2//27//3//6//2//5//26
#define ENC1B 28  //2//28// 22//27//3//3//28//2//7//3//4//25

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

// Function to read encoder angle in degrees is defined in angle_motor.ino

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
          
          // Convert torque to motor current and apply to motor
          // Assuming direct torque-to-current mapping (you may need to adjust this)
          motor_current = desiredTorque; // Simple 1:1 mapping, adjust as needed
          
          // Apply motor control immediately
          applyMotorControl();
          
          // Send acknowledgment
          Serial.write(HEADER1);
          Serial.write(HEADER2);
          Serial.write(0xAA); // ACK
        }
      }
    }
  }
}

// Apply motor control immediately when torque command is received
void applyMotorControl() {
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

// Control motor based on desired torque
void controlMotor() {
  applyMotorControl();  // Use the same logic as immediate control
}

// Send data packet to Python
void sendDataPacket() {
  // Create data packet: Header(2) + Size(1) + Data(9) + Checksum(1)
  uint8_t packet[13];
  
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
  packet[12] = checksum;
  
  // Send packet
  Serial.write(packet, 13);
}

// Function to read encoder angle in degrees with overflow handling
float angle_motor()
{
  _enccount = angle.read();
  
  // Handle encoder overflow/underflow
  if (_enccount >= ENC1MAXCOUNT) {
    angle.write(_enccount - ENC1MAXCOUNT);
  } else if (_enccount <= -ENC1MAXCOUNT) {
    angle.write(_enccount + ENC1MAXCOUNT);
  }
  
  // Convert encoder counts to degrees
  return ENC1COUNT2DEG * _enccount;
}
'''

# angle_motor.ino content (kept separate for compatibility)
ANGLE_MOTOR_INO_CONTENT = '''// Function to read encoder angle in degrees with overflow handling
float angle_motor()
{
  _enccount = angle.read();
  
  // Handle encoder overflow/underflow
  if (_enccount >= ENC1MAXCOUNT) {
    angle.write(_enccount - ENC1MAXCOUNT);
  } else if (_enccount <= -ENC1MAXCOUNT) {
    angle.write(_enccount + ENC1MAXCOUNT);
  }
  
  // Convert encoder counts to degrees
  return ENC1COUNT2DEG * _enccount;
}
'''

def get_firmware_content(firmware_type: str = "main") -> str:
    """
    Get embedded firmware content by type.
    
    Args:
        firmware_type: Type of firmware ("main" for firmware.ino, 
                      "angle_motor" for angle_motor.ino, or "combined")
    
    Returns:
        Firmware source code as string
    
    Raises:
        ValueError: If firmware_type is not recognized
    """
    if firmware_type == "main":
        return FIRMWARE_INO_CONTENT
    elif firmware_type == "angle_motor":
        return ANGLE_MOTOR_INO_CONTENT
    elif firmware_type == "combined":
        # For Arduino compilation, we need a single .ino file
        return FIRMWARE_INO_CONTENT
    else:
        raise ValueError(f"Unknown firmware type: {firmware_type}")

def get_available_firmware_types() -> list:
    """Get list of available firmware types."""
    return ["main", "angle_motor", "combined"]

def create_firmware_files(target_dir: str) -> dict:
    """
    Create firmware files in the specified directory.
    Arduino CLI requires the main .ino file to have the same name as its directory.
    
    Args:
        target_dir: Directory to create firmware files in
    
    Returns:
        Dictionary with firmware file paths created
        
    Raises:
        OSError: If directory creation or file writing fails
    """
    import os
    from pathlib import Path
    
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    created_files = {}
    
    # Arduino CLI requires main .ino file to have same name as directory
    dir_name = target_path.name
    main_firmware_name = f"{dir_name}.ino"
    
    # Create main firmware file with directory name
    firmware_path = target_path / main_firmware_name
    with open(firmware_path, 'w', encoding='utf-8') as f:
        f.write(get_firmware_content("combined"))
    created_files["firmware.ino"] = str(firmware_path)  # Keep consistent key name
    
    # Create separate angle_motor.ino for reference (optional)
    angle_motor_path = target_path / "angle_motor.ino"
    with open(angle_motor_path, 'w', encoding='utf-8') as f:
        f.write(get_firmware_content("angle_motor"))
    created_files["angle_motor.ino"] = str(angle_motor_path)
    
    return created_files