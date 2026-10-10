
#include "BatteryController.h"
#include <math.h>

BatteryController::BatteryController() {
    faultLatched = false;
    faultReason = "NONE";
}

ControllerResult BatteryController::triggerFault(
    const char* reason
) {
    if (!faultLatched) {
        faultLatched = true;
        faultReason = reason;
    }

    return {0.0, "FAULT", faultReason};
}


void BatteryController::triggerCommunicationFault() {
    triggerFault("COMMUNICATION_TIMEOUT");
}

void BatteryController::triggerSensorFault() {
    triggerFault("INVALID_INPUT");
}

bool BatteryController::resetFault(
    double soc,
    double temperature
) {
    if (!isfinite(soc) || !isfinite(temperature)) {
        return false;
    }

    if (soc < 0.0 || soc > 100.0) {
        return false;
    }

    if (temperature >= resetTemp) {
        return false;
    }

    faultLatched = false;
    faultReason = "NONE";
    return true;
}

ControllerResult BatteryController::update(
    double soc,
    double requestedPower,
    double temperature,
    double dt
) {
    // 1. Validate inputs
    if (!isfinite(soc) ||
        !isfinite(requestedPower) ||
        !isfinite(temperature) ||
        !isfinite(dt) ||
        soc < 0.0 ||
        soc > 100.0 ||
        dt <= 0.0) {

        return triggerFault("INVALID_INPUT");
    }

    // 2. Overtemperature protection
    if (temperature >= maxTemp) {
        return triggerFault("OVERTEMPERATURE");
    }

    // 3. Fault latching
    if (faultLatched) {
        return {0.0, "FAULT", faultReason};
    }

    // 4. Rated power limit
    double approvedPower = fmax(
        -maxPower,
        fmin(requestedPower, maxPower)
    );

    // 5. Thermal derating
    double thermalLimit = maxPower;

    if (temperature > deratingTemp) {
        thermalLimit = maxPower * (
            (maxTemp - temperature) /
            (maxTemp - deratingTemp)
        );
    }

    bool derated = fabs(approvedPower) > thermalLimit;

    approvedPower = fmax(
        -thermalLimit,
        fmin(approvedPower, thermalLimit)
    );

    // SOC guard band in percentage points.
    // Accounts for input and power quantisation.
    const double margin = 1e-4;

    if (approvedPower > 0.0) {
        double availableSoc = fmax(
            0.0, soc - minSoc - margin
        );

        double availableEnergy = (
            availableSoc / 100.0 * capacityKwh
        );

        double maxDischargePower = (
            availableEnergy * 3600.0 *
            efficiency / dt
        );

        approvedPower = fmin(
            approvedPower, maxDischargePower
        );
    }
    else if (approvedPower < 0.0) {
        double availableSoc = fmax(
            0.0, maxSoc - soc - margin
        );

        double availableEnergy = (
            availableSoc / 100.0 * capacityKwh
        );

        double maxChargePower = (
            availableEnergy * 3600.0 /
            (efficiency * dt)
        );

        approvedPower = fmax(
            approvedPower, -maxChargePower
        );
    }

    // 7. Determine operating state
    const char* state;

    if (approvedPower == 0.0) {
        state = "IDLE";
    }
    else if (derated) {
        state = "DERATED";
    }
    else if (approvedPower > 0.0) {
        state = "DISCHARGING";
    }
    else {
        state = "CHARGING";
    }

    return {approvedPower, state, "NONE"};
}
