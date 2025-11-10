#include "HX711_ADC.h"
#include <Encoder.h>
#include <math.h>

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
  Serial.begin(9600);
  
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
  
  Serial.println("PHASE 1: Initial 1.00 Nm for 10s, then hold at zero for 10s");
  Serial.println("DesiredNm,AngleDeg,PWM");
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
        Serial.println("\nPHASE 2: Random torque commands (10 commands, 5s each)");
        Serial.println("AppliedNm,DesiredNm,AngleDeg");
        
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
          Serial.println("\nAll commands complete. Motor disabled.");
          while(1); // Stop execution
        }
      }
      break;
  }
  
  // ----- Logging -----
  float angle_deg = angle_motor_deg();
  float TS = loadcell1.getData();
  
  if (currentPhase == PHASE1_INITIAL || currentPhase == PHASE1_HOLD_ZERO) {
    // Phase 1 format: DesiredNm(TS), AngleDeg, PWM
      Serial.print(appliedNm, 2);
    Serial.print(',');
    Serial.print(TS, 3);
    Serial.print(',');
    Serial.print(angle_deg, 3);
    Serial.print(',');
    Serial.println(pwm_value, 2);
  } else {
    // Phase 2 format: AppliedNm, DesiredNm(TS), AngleDeg
    Serial.print(appliedNm, 2);
    Serial.print(',');
    Serial.print(TS, 3);
    Serial.print(',');
    Serial.println(angle_deg, 3);
  }
  
  delay(5);  // ~200 Hz service rate
}
