
#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "BatteryController.h"

BatteryController controller;

const unsigned long BAUD_RATE = 115200;
const unsigned long WATCHDOG_TIMEOUT_MS = 3000;

unsigned long lastValidMessageTime = 0;
bool communicationStarted = false;
bool watchdogTriggered = false;

// Latest validated battery measurements
float lastMeasuredSoc = 0.0f;
float lastMeasuredTemperature = 0.0f;
bool recoveryDataReady = false;

// Serial message buffer
const size_t BUFFER_SIZE = 128;
char serialBuffer[BUFFER_SIZE];
size_t bufferIndex = 0;
bool messageOverflow = false;


// Convert text into a finite floating-point number
bool parseNumber(const char* text, float& value) {
    if (text == nullptr || *text == '\0') {
        return false;
    }

    char* endPointer;
    errno = 0;

    float parsed = strtof(text, &endPointer);

    if (endPointer == text || *endPointer != '\0') {
        return false;
    }

    if (errno == ERANGE || !isfinite(parsed)) {
        return false;
    }

    value = parsed;
    return true;
}


// Handle a serial message
void processMessage(char* message) {

    // 1. Handle RESET command
    if (strcmp(message, "RESET") == 0) {

        // Require recent validated measurements
        if (!recoveryDataReady ||
            !communicationStarted ||
            millis() - lastValidMessageTime >= WATCHDOG_TIMEOUT_MS) {

            Serial.println("RESET,REJECTED");
            return;
        }

        // Reset using previously received measurements
        bool success = controller.resetFault(
            lastMeasuredSoc,
            lastMeasuredTemperature
        );

        if (success) {
            watchdogTriggered = false;
            lastValidMessageTime = millis();
            recoveryDataReady = false;

            Serial.println("RESET,OK");
        } else {
            Serial.println("RESET,REJECTED");
        }

        return;
    }

    // 2. Expected format: DATA,SOC,TEMP,POWER,DT
    char* fields[5];
    size_t fieldCount = 0;

    fields[fieldCount++] = message;

    for (char* position = message;
         *position != '\0';
         position++) {

        if (*position == ',') {
            if (fieldCount >= 5) {
                Serial.println("ERROR,INVALID_FORMAT");
                return;
            }

            *position = '\0';
            fields[fieldCount++] = position + 1;
        }
    }

    if (fieldCount != 5 ||
        strcmp(fields[0], "DATA") != 0) {

        Serial.println("ERROR,INVALID_FORMAT");
        return;
    }

    float soc;
    float temperature;
    float requestedPower;
    float dt;

    // 3. Validate measurement values
    if (!parseNumber(fields[1], soc) ||
        !parseNumber(fields[2], temperature) ||
        !parseNumber(fields[3], requestedPower) ||
        !parseNumber(fields[4], dt)) {

        recoveryDataReady = false;
        controller.triggerSensorFault();

        Serial.println("ERROR,INVALID_DATA");
        return;
    }

    if (soc < 0.0f || soc > 100.0f || dt <= 0.0f) {
        recoveryDataReady = false;
        controller.triggerSensorFault();

        Serial.println("ERROR,INVALID_DATA");
        return;
    }

    // 4. Record validated measurements
    lastMeasuredSoc = soc;
    lastMeasuredTemperature = temperature;

    lastValidMessageTime = millis();
    communicationStarted = true;

    // Recovery requires a zero-power request.
    // A new DATA message replaces the previous
    // recovery measurement.
    recoveryDataReady = (requestedPower == 0.0f);

    // 5. Calculate controller decision
    ControllerResult result = controller.update(
        soc,
        requestedPower,
        temperature,
        dt
    );

    // 6. Transmit result
    Serial.print("RESULT,");
    Serial.print(result.approvedPower, 6);
    Serial.print(",");
    Serial.print(result.state);
    Serial.print(",");
    Serial.println(result.fault);
}


void setup() {
    Serial.begin(BAUD_RATE);
    Serial.println("BESS_READY");
}


void loop() {

    // Non-blocking serial receiver
    while (Serial.available() > 0) {

        char incoming = (char)Serial.read();

        if (incoming == '\n') {

            if (messageOverflow) {
                recoveryDataReady = false;
                Serial.println("ERROR,MESSAGE_TOO_LONG");
            } else {
                serialBuffer[bufferIndex] = '\0';
                processMessage(serialBuffer);
            }

            bufferIndex = 0;
            messageOverflow = false;
        }
        else if (incoming != '\r') {

            if (messageOverflow) {
                continue;
            }

            if (bufferIndex < BUFFER_SIZE - 1) {
                serialBuffer[bufferIndex++] = incoming;
            } else {
                messageOverflow = true;
            }
        }
    }

    // 7. Communication watchdog
    if (communicationStarted && !watchdogTriggered) {

        if (millis() - lastValidMessageTime >=
            WATCHDOG_TIMEOUT_MS) {

            watchdogTriggered = true;
            recoveryDataReady = false;

            controller.triggerCommunicationFault();

            Serial.println("EVENT,COMMUNICATION_TIMEOUT");
        }
    }
}
