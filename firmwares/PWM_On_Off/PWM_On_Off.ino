#include <Encoder.h>

// -------------------- Encoder --------------------
#define ENC_A          27
#define ENC_B          28
#define ENC_MAXCOUNT   (4 * 4096 * 53)
#define ENC_TO_DEG     (0.25f * 0.001658f)

Encoder encoder(ENC_A, ENC_B);
long encoderZeroOffset = 0;

// -------------------- Motor Driver Pins --------------------
const int PIN_PWM    = 8;
const int PIN_ENABLE = 9;
const int PIN_DIR    = 10;

// -------------------- Timing --------------------
const uint32_t CMD_TIME_MS = 5000;  // 5s per PWM value

// -------------------- PWM Values --------------------
const int PWM_HIGH = 800;   // High PWM value
const int PWM_LOW = 410;    // Low PWM value (motor off)
const int TOTAL_CYCLES = 5; // Number of cycles to repeat

int currentCycle = 0;
bool isHighPWM = true;  // Start with high PWM

// -------------------- Current State --------------------
uint32_t phaseStartTime = 0;
uint16_t pwmDuty = 410;

// ======================================================
// ENCODER FUNCTIONS
// ======================================================

float getAngleDeg() {
  long count = encoder.read() - encoderZeroOffset;
  
  // Handle wraparound
  if (count >= ENC_MAXCOUNT) {
    encoderZeroOffset += ENC_MAXCOUNT;
    count -= ENC_MAXCOUNT;
  } else if (count <= -ENC_MAXCOUNT) {
    encoderZeroOffset -= ENC_MAXCOUNT;
    count += ENC_MAXCOUNT;
  }
  
  return ENC_TO_DEG * count;
}

// ======================================================
// PWM FUNCTIONS
// ======================================================

void setPWM(uint16_t pwm) {
  pwmDuty = constrain(pwm, 410, 3686);
  analogWrite(PIN_PWM, pwmDuty);
}

// ======================================================
// SETUP
// ======================================================

void setup() {
  Serial.begin(9600);
  
  // Initialize motor pins
  pinMode(PIN_PWM, OUTPUT);
  pinMode(PIN_ENABLE, OUTPUT);
  pinMode(PIN_DIR, OUTPUT);
  pinMode(ENC_A, INPUT_PULLUP);
  pinMode(ENC_B, INPUT_PULLUP);
  
  analogWriteResolution(12);
  analogReadResolution(12);
  
  // Motor OFF during initialization
  digitalWrite(PIN_ENABLE, LOW);
  digitalWrite(PIN_DIR, HIGH);
  analogWrite(PIN_PWM, 410);
  
  // Print configuration
  Serial.print("High PWM: ");
  Serial.print(PWM_HIGH);
  Serial.print(", Low PWM: ");
  Serial.print(PWM_LOW);
  Serial.print(", Cycles: ");
  Serial.println(TOTAL_CYCLES);
  
  Serial.println("\n=== PWM Cycling: 800->410 (5s each, 5 cycles) ===");
  Serial.println("PWM,AngleDeg");
  
  // Start motor with high PWM
  digitalWrite(PIN_ENABLE, HIGH);
  setPWM(PWM_HIGH);
  currentCycle = 0;
  isHighPWM = true;
  
  phaseStartTime = millis();
}

// ======================================================
// MAIN LOOP
// ======================================================

void loop() {
  uint32_t elapsed = millis() - phaseStartTime;
  
  // Check if it's time to switch PWM
  if (elapsed >= CMD_TIME_MS) {
    // Toggle between high and low PWM
    if (isHighPWM) {
      // Switch to low PWM
      setPWM(PWM_LOW);
      isHighPWM = false;
      Serial.print("Cycle ");
      Serial.print(currentCycle + 1);
      Serial.println(": Switching to LOW PWM (410)");
    } else {
      // Switch to high PWM and increment cycle
      currentCycle++;
      
      if (currentCycle >= TOTAL_CYCLES) {
        // All cycles complete, stop motor
        analogWrite(PIN_PWM, 410);
        digitalWrite(PIN_ENABLE, LOW);
        Serial.println("\n=== Complete. All cycles finished. Motor stopped. ===");
        while(1);
      } else {
        setPWM(PWM_HIGH);
        isHighPWM = true;
        Serial.print("Cycle ");
        Serial.print(currentCycle + 1);
        Serial.println(": Switching to HIGH PWM (800)");
      }
    }
    
    phaseStartTime = millis();
  }
  
  // -------------------- DATA LOGGING --------------------
  Serial.print(pwmDuty);
  Serial.print(',');
  Serial.println(getAngleDeg(), 3);
  
  delay(100);  // 10 Hz sampling rate
}
