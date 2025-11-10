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
const uint32_t RUN_TIME_MS = 86400000UL;  // 24 hours in milliseconds

// -------------------- PWM Value --------------------
const int CONSTANT_PWM = 700;  // Constant PWM value to apply for 24 hours

// -------------------- Current State --------------------
uint32_t startTime = 0;
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
  Serial.print("Constant PWM: ");
  Serial.print(CONSTANT_PWM);
  Serial.println(" for 24 hours");
  Serial.println("Sampling rate: 10 Hz");
  
  Serial.println("\n=== Applying constant PWM 700 for 24 hours ===");
  Serial.println("PWM,AngleDeg");
  
  // Start motor
  digitalWrite(PIN_ENABLE, HIGH);
  setPWM(CONSTANT_PWM);
  
  startTime = millis();
}

// ======================================================
// MAIN LOOP
// ======================================================

void loop() {
  uint32_t elapsed = millis() - startTime;
  
  // Check if 24 hours have elapsed
  if (elapsed >= RUN_TIME_MS) {
    // Stop motor after 24 hours
    analogWrite(PIN_PWM, 410);
    digitalWrite(PIN_ENABLE, LOW);
    Serial.println("\n=== Complete. 24 hours elapsed. Motor stopped. ===");
    while(1);
  }
  
  // -------------------- DATA LOGGING --------------------
  Serial.print(pwmDuty);
  Serial.print(',');
  Serial.println(getAngleDeg(), 3);
  
  delay(100);  // 10 Hz sampling rate (100ms delay)
}
