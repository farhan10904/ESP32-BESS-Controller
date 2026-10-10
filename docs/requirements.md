# BESS Supervisory Controller - Requirements and Verification

## 1. Project Scope

Develop an ESP32-based battery energy storage supervisory controller using a Python battery simulation and USB serial hardware-in-the-loop (HIL) testing.

The Python model simulates battery energy and thermal behaviour. The ESP32 independently evaluates operating limits, approves requested charging or discharging power, and handles selected faults.

**Scope limitation:** The battery is entirely simulated. The ESP32 does not control a physical battery or electrical power converter. This project is not a production battery management system or safety-certified protection device.

## 2. Design Assumptions

| Parameter                      | Value       |
| ------------------------------ | ----------- |
| Battery energy capacity        | 10 kWh      |
| Initial SOC                    | 60%         |
| Operating SOC range            | 20-90%      |
| Maximum charge/discharge power | 2 kW        |
| Charge efficiency              | 95%         |
| Discharge efficiency           | 95%         |
| Initial ambient temperature    | 25°C        |
| Thermal capacity               | 60,000 J/K  |
| Thermal conductance            | 5 W/K       |
| Thermal derating begins        | Above 40°C  |
| Overtemperature shutdown       | 60°C        |
| Fault reset temperature        | Below 55°C  |
| Simulation time step           | 1 s nominal |
| Communication watchdog         | 3 s         |

All battery parameters are demonstration assumptions rather than manufacturer specifications.

**Sign convention:** Positive power represents discharging. Negative power represents charging.

## 3. Requirements and Verification Matrix

| ID  | Requirement                                                          | Verification evidence                                 | Status                        |
| --- | -------------------------------------------------------------------- | ----------------------------------------------------- | ----------------------------- |
| R01 | Integrate battery SOC accounting for charging/discharging efficiency | Numerical calculations and Python simulation          | Tested                        |
| R02 | Simulate lumped battery heating and cooling                          | Python heating/cooling tests and HIL thermal logs     | Tested                        |
| R03 | Execute supervisory control independently on ESP32                   | Python-to-ESP32 HIL simulation                        | Verified for tested scenarios |
| R04 | Restrict approved charge/discharge power to ±2 kW                    | Normal, dynamic and 100-request HIL tests             | Passed                        |
| R05 | Prevent predicted SOC boundary overshoot                             | Python tests and six ESP32 boundary scenarios         | Passed                        |
| R06 | Apply thermal derating and overtemperature shutdown                  | Thermal scenario and overtemperature HIL tests        | Passed                        |
| R07 | Detect and latch invalid sensor measurements                         | Invalid SOC and malformed-input HIL tests             | Passed for tested cases       |
| R08 | Detect missing communication and enter a latched fault               | Automated watchdog HIL test                           | Passed                        |
| R09 | Require controlled fault recovery                                    | Automated overtemperature and watchdog recovery tests | Passed                        |
| R10 | Record test results and generate engineering graphs                  | CSV logs, automated tests and Matplotlib figures      | Implemented                   |

## 4. Key Experimental Results

### Normal HIL Operation

- Simulation duration: 900 simulated seconds.
- Requested discharge power: 3 kW.
- Approved discharge power: 2 kW.
- Final SOC: 54.737%.
- Final simulated temperature: 26.52°C.

### Thermal Derating

- Initial simulated temperature: 50°C.
- Final simulated temperature: 48.99°C.
- Approved discharge power increased from approximately 1.00 kW to 1.10 kW as the simulated battery cooled.
- Final SOC: 57.233%.

### Dynamic Power Control

- Successfully exercised discharge, idle, charge and power-limited discharge operation over 300 simulated seconds.
- Final SOC: 59.615%.

### Fault and Robustness Testing

- Six Python unit tests passed.
- Eight Python-to-ESP32 controller equivalence scenarios passed.
- Six ESP32 SOC boundary scenarios passed after implementing a numerical guard band.
- One hundred consecutive changing power requests matched the Python reference controller.
- The watchdog triggered after approximately 3.00 seconds during the automated test.
- Automated overtemperature, fault latching and recovery tests passed.

These are results from the completed test scenarios, not exhaustive proof of safety or performance.

## 5. Engineering Limitations

- Battery characteristics are simplified and not calibrated against physical measurements.
- SOC is modelled using energy integration rather than a cell-level electrochemical model.
- Temperature is represented by one lumped thermal state.
- No battery cells, contactors, inverters or power electronics are controlled.
- Communication and fault handling are implemented in software only.
- Serial numerical precision and timing may affect boundary behaviour.
- Recovery relies on simulated measurements and does not provide independent physical safety validation.
- The test suite does not establish industrial safety-standard compliance.

## 6. Further Development

Potential extensions include cell-level battery simulation, a more detailed thermal model, broader communications fault testing, firmware execution-time profiling, and integration with a representative low-voltage physical test rig.
