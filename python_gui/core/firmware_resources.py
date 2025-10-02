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
#define DATA_PACKET_SIZE 13  // 1 byte cmd + 4 bytes torque + 4 bytes angle + 4 bytes PWM

// Calibration factors for torque sensor
#define calibration_factor5 130433  //-842222//91160.52

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
const unsigned long dataInterval = 10; // Send data every 10ms

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
        
        if (command == CMD_SET_TORQUE) {
          // Wait for all 4 torque bytes with timeout
          unsigned long startTime = millis();
          while (Serial.available() < 4 && millis() - startTime < 100) {
            // Wait up to 100ms for complete torque data
          }

          if (Serial.available() >= 4) {
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

            // Send acknowledgment after motor control is applied
            Serial.write(HEADER1);
            Serial.write(HEADER2);
            Serial.write(0xAA); // ACK
          }
        }
      }
    }
  }
}

// Apply motor control immediately when torque command is received
void applyMotorControl() {
  motor_current = desiredTorque / 3.35;  // Calculate motor current
  
  // Limit current to safe range
  motor_current = constrain(motor_current, -2.0, 10.0);
  
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
  // Create data packet: Header(2) + Size(1) + Data(13) + Checksum(1)
  uint8_t packet[17];

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

  // Pack PWM as float (4 bytes)
  union {
    float f;
    uint8_t bytes[4];
  } pwmData;
  pwmData.f = pwm_value;

  for (int i = 0; i < 4; i++) {
    packet[12 + i] = pwmData.bytes[i];
  }

  // Calculate checksum
  uint8_t checksum = 0;
  for (int i = 2; i < 16; i++) {
    checksum += packet[i];
  }
  checksum = (~checksum) + 1; // Two's complement

  // Add checksum
  packet[16] = checksum;

  // Send packet
  Serial.write(packet, 17);
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

# Random torque firmware - autonomous operation with preprogrammed torque patterns
RANDOM_TORQUE_FIRMWARE_CONTENT = '''#include "HX711_ADC.h"
#include <Encoder.h>
#include <math.h>

// -------------------- Binary Protocol --------------------
#define HEADER1 0xFF
#define HEADER2 0xFF
#define CMD_GET_DATA 0x02
#define DATA_PACKET_SIZE 13  // 1 byte cmd + 4 bytes torque + 4 bytes angle + 4 bytes PWM

// -------------------- Torque Sensor --------------------
#define calibration_factor1  91160.52
#define LOADCELL1_DOUT_PIN   32
#define LOADCELL1_SCK_PIN    33
HX711_ADC loadcell1(LOADCELL1_DOUT_PIN, LOADCELL1_SCK_PIN);

// -------------------- Encoder --------------------
#define ENC1A          27
#define ENC1B          28
#define ENC1MAXCOUNT   (4 * 4096 * 53)
#define ENC1COUNT2DEG  (0.25f * 0.001658f)

Encoder angle(ENC1A, ENC1B);
long _enccount;
volatile long encZeroOffset = 0;
volatile bool forceZeroAngle = false;

// -------------------- Motor Driver Pins --------------------
const int pwmPin       = 8;
const int enablePin    = 9;
const int directionPin = 10;

// -------------------- Timing --------------------
unsigned long lastDataTime = 0;
const unsigned long dataInterval = 10; // Send data every 10ms

// -------------------- Phase Control --------------------
enum Phase { PHASE1_INITIAL, PHASE1_HOLD_ZERO, PHASE2_RANDOM };
Phase currentPhase = PHASE1_INITIAL;

const uint32_t PHASE1_INITIAL_MS = 10000;  // 10s initial hold
const uint32_t PHASE1_HOLD_MS    = 10000;  // 10s hold at zero
const uint32_t PHASE2_CMD_MS     = 5000;   // 5s per random command

// Phase 2: Random torque commands
const float RANDOM_TORQUES[] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
const int NUM_RANDOM_CMDS = 10;
float randomCommands[NUM_RANDOM_CMDS];
int currentCmdIndex = 0;

// Current command values
float appliedNm     = 1.00f;
float motor_current = 0.0f;
float pwm_value     = 0.0f;
uint16_t duty       = 0;

// -------------------- Helpers --------------------
static inline long readEncRaw() { return angle.read(); }

void softZeroEncoder() {
  noInterrupts();
  encZeroOffset = readEncRaw();
  interrupts();
}

void hardZeroEncoder() {
  noInterrupts();
  angle.write(0);
  encZeroOffset = 0;
  forceZeroAngle = true;
  interrupts();
}

float angle_motor_deg() {
  if (forceZeroAngle) return 0.0f;

  long c = readEncRaw() - encZeroOffset;
  if (c >= ENC1MAXCOUNT)       encZeroOffset += ENC1MAXCOUNT, c -= ENC1MAXCOUNT;
  else if (c <= -ENC1MAXCOUNT) encZeroOffset -= ENC1MAXCOUNT, c += ENC1MAXCOUNT;

  return ENC1COUNT2DEG * (float)c;
}

void setTorqueCommand(float torqueNm) {
  appliedNm = torqueNm;
  motor_current = torqueNm / 3.35f;
  pwm_value = 409.6f + 410.0f * fabsf(motor_current);
  duty = (uint16_t)constrain(lroundf(pwm_value), 410, 3686);
  analogWrite(pwmPin, duty);
}

void generateRandomCommands() {
  randomSeed(analogRead(A0));
  for (int i = 0; i < NUM_RANDOM_CMDS; i++) {
    randomCommands[i] = RANDOM_TORQUES[random(0, 5)];
  }
}

void setup() {
  Serial.begin(115200);

  // ---- Torque Sensor: tare ONCE at startup ----
  loadcell1.begin();
  loadcell1.setCalFactor(calibration_factor1);
  loadcell1.tare();
  for (uint16_t i = 0; i < 50; ++i) {
    loadcell1.update();
    delay(5);
  }

  // ---- Motor & Encoder ----
  pinMode(pwmPin, OUTPUT);
  pinMode(enablePin, OUTPUT);
  pinMode(directionPin, OUTPUT);
  pinMode(ENC1A, INPUT_PULLUP);
  pinMode(ENC1B, INPUT_PULLUP);

  analogWriteResolution(12);
  analogReadResolution(12);

  digitalWrite(enablePin, HIGH);
  digitalWrite(directionPin, HIGH);

  // Initialize software zero at starting position
  softZeroEncoder();

  // Set initial 1 Nm command
  setTorqueCommand(1.00f);

  // Generate random commands for Phase 2
  generateRandomCommands();
}

void loop() {
  static uint32_t phaseStartTime = millis();
  uint32_t elapsed = millis() - phaseStartTime;

  // Keep torque sensor updating
  loadcell1.update();

  // Apply current PWM command
  analogWrite(pwmPin, duty);

  // Phase state machine
  switch (currentPhase) {
    case PHASE1_INITIAL:
      if (elapsed >= PHASE1_INITIAL_MS) {
        // Hard-zero the encoder after 10s
        long rawBefore = readEncRaw();
        hardZeroEncoder();
        long rawAfter = readEncRaw();

        Serial.print("Encoder hard-zeroed. Raw before: ");
        Serial.print(rawBefore);
        Serial.print(" | Raw after: ");
        Serial.print(rawAfter);
        Serial.print(" | Reported angle: ");
        Serial.print(angle_motor_deg(), 3);
        Serial.println(" deg");
        Serial.println("Holding at zero for 10s...");

        currentPhase = PHASE1_HOLD_ZERO;
        phaseStartTime = millis();
      }
      break;

    case PHASE1_HOLD_ZERO:
      if (elapsed >= PHASE1_HOLD_MS) {
        // Transition to Phase 2
        Serial.println("\\nPHASE 2: Random torque commands (10 commands, 5s each)");
        Serial.println("Millis,DesiredTorque,ActualTorque,PWM,Angle");

        forceZeroAngle = false;  // Allow encoder to move freely now
        currentCmdIndex = 0;
        setTorqueCommand(randomCommands[currentCmdIndex]);

        currentPhase = PHASE2_RANDOM;
        phaseStartTime = millis();
      }
      break;

    case PHASE2_RANDOM:
      if (elapsed >= PHASE2_CMD_MS) {
        currentCmdIndex++;

        if (currentCmdIndex < NUM_RANDOM_CMDS) {
          // Apply next random command
          setTorqueCommand(randomCommands[currentCmdIndex]);
          phaseStartTime = millis();
        } else {
          // All commands complete - disable motor
          analogWrite(pwmPin, 410);
          digitalWrite(enablePin, LOW);
          Serial.println("\\nAll commands complete. Motor disabled.");
          while(1); // Stop execution
        }
      }
      break;
  }

  // ----- Send Data via Binary Protocol -----
  if (millis() - lastDataTime >= dataInterval) {
    sendDataPacket();
    lastDataTime = millis();
  }

  delay(5);  // ~200 Hz service rate
}

// Send data packet using binary protocol (same as interactive firmware)
void sendDataPacket() {
  // Create data packet: Header(2) + Size(1) + Data(13) + Checksum(1)
  uint8_t packet[17];

  packet[0] = HEADER1;
  packet[1] = HEADER2;
  packet[2] = DATA_PACKET_SIZE;
  packet[3] = CMD_GET_DATA;

  float angle_deg = angle_motor_deg();
  float TS = loadcell1.getData();

  // Pack actual torque as float (4 bytes)
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
  angleData.f = angle_deg;

  for (int i = 0; i < 4; i++) {
    packet[8 + i] = angleData.bytes[i];
  }

  // Pack PWM as float (4 bytes)
  union {
    float f;
    uint8_t bytes[4];
  } pwmData;
  pwmData.f = pwm_value;

  for (int i = 0; i < 4; i++) {
    packet[12 + i] = pwmData.bytes[i];
  }

  // Calculate checksum
  uint8_t checksum = 0;
  for (int i = 2; i < 16; i++) {
    checksum += packet[i];
  }
  checksum = (~checksum) + 1; // Two's complement

  // Add checksum
  packet[16] = checksum;

  // Send packet
  Serial.write(packet, 17);
}
'''

def get_firmware_content(firmware_type: str = "main") -> str:
    """
    Get embedded firmware content by type.

    Args:
        firmware_type: Type of firmware ("main" for firmware.ino,
                      "angle_motor" for angle_motor.ino, "combined", or "random_torque")

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
    elif firmware_type == "random_torque":
        return RANDOM_TORQUE_FIRMWARE_CONTENT
    else:
        raise ValueError(f"Unknown firmware type: {firmware_type}")

def get_available_firmware_types() -> list:
    """Get list of available firmware types."""
    return ["combined", "random_torque"]

def get_firmware_display_name(firmware_type: str) -> str:
    """Get user-friendly display name for firmware type."""
    display_names = {
        "combined": "Interactive Control (Default)",
        "random_torque": "Random Torque (Autonomous)"
    }
    return display_names.get(firmware_type, firmware_type)

def create_firmware_files(target_dir: str, firmware_type: str = "combined") -> dict:
    """
    Create firmware files in the specified directory.
    Arduino CLI requires the main .ino file to have the same name as its directory.

    Args:
        target_dir: Directory to create firmware files in
        firmware_type: Type of firmware to create ("combined" or "random_torque")

    Returns:
        Dictionary with firmware file paths created

    Raises:
        OSError: If directory creation or file writing fails
    """
    from pathlib import Path

    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    created_files = {}

    # Arduino CLI requires main .ino file to have same name as directory
    dir_name = target_path.name
    main_firmware_name = f"{dir_name}.ino"

    # Create main firmware file with directory name (contains everything)
    firmware_path = target_path / main_firmware_name
    with open(firmware_path, 'w', encoding='utf-8') as f:
        f.write(get_firmware_content(firmware_type))
    created_files["firmware.ino"] = str(firmware_path)  # Keep consistent key name
    created_files["firmware_type"] = firmware_type  # Store type for reference

    return created_files