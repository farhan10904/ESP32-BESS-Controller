
#ifndef BATTERY_CONTROLLER_H
#define BATTERY_CONTROLLER_H

struct ControllerResult {
    double approvedPower;
    const char* state;
    const char* fault;
};

class BatteryController {
public:
    BatteryController();

    ControllerResult update(
        double soc,
        double requestedPower,
        double temperature,
        double dt
    );

    bool resetFault(double soc, double temperature);
    void triggerCommunicationFault();
    void triggerSensorFault();

private:
    const double minSoc = 20.0;
    const double maxSoc = 90.0;
    const double maxPower = 2.0;

    const double deratingTemp = 40.0;
    const double maxTemp = 60.0;
    const double resetTemp = 55.0;

    const double capacityKwh = 10.0;
    const double efficiency = 0.95;

    bool faultLatched;
    const char* faultReason;

    ControllerResult triggerFault(const char* reason);
};

#endif

