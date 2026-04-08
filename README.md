# Smart Building Simulation (IoT)

## Overview

This project is a simulation of an IoT monitoring system for a 4-floor commercial building. It focuses on HVAC, indoor air quality, and electrical monitoring, with data generated in Node-RED and delivered through a full pipeline to the web dashboard. The building scope follows the assessment structure, including chillers, pumps, cooling towers, AHUs, VAVs, IAQ sensors, weather data, and power meters.

The system is designed around four operating scenarios: Peak Day, Medium Day, Night, and Fault Chiller 2. These scenarios change load, equipment status, environmental conditions, and power usage so the dashboards reflect different building conditions in a more realistic way. From the simulation code, Peak Day runs at the highest load, Medium Day represents normal operation, Night reduces load and active equipment, and Fault Chiller 2 simulates a chiller trip while the rest of the plant continues operating.

---

## System Architecture

```
Node-RED → MQTT → Backend → PostgreSQL → API → Dashboard
```
### Technology Choices

Node-RED was selected as the integration layer because it supports multiple protocols such as BACnet, Modbus RTU/TCP, MQTT, and API integration, while also allowing fast scenario-based simulation and payload preparation.

MQTT was used as the telemetry transport protocol because it is lightweight, efficient, and well suited for real-time IoT data exchange using a publish/subscribe model.

Python with FastAPI was chosen for the backend because it enables fast development and clean API design for dashboard data services.

PostgreSQL was used for data storage because it is reliable and suitable for storing telemetry history, latest values, and dashboard queries.

For larger-scale systems, a time-series database would be considered for handling high-frequency data and long-term storage more efficiently.

The frontend was built using HTML and JavaScript to create a lightweight dashboard that is easy to run and sufficient for demonstrating the required monitoring features.

Architecture diagram:
- `diagrams/software-architecture/software_architecture.png`
- Source: `diagrams/software-architecture/software_architecture.drawio`

---

## Network Design

This project follows a typical building communication structure, where data flows from field-level systems to a centralized platform for monitoring and visualization.

Field devices such as chillers, pumps, AHUs, VAVs, and meters are conceptually connected through standard building protocols like BACnet and Modbus. These protocols are commonly used in real buildings for communication between controllers and equipment.

In this simulation, Node-RED represents the data source and acts as a gateway that publishes telemetry data through MQTT. The backend service subscribes to the data, processes it, and stores it for further use in the dashboard.

This approach reflects how real systems are typically designed, where data from multiple protocols is aggregated and forwarded into a unified platform.

Detailed network configuration, including IP addressing, device mapping, and protocol-level details such as Modbus Slave IDs and BACnet device instances, are documented in the network diagram.

Note:
The IP addresses, BACnet device IDs, and Modbus slave IDs shown in these diagrams are used to illustrate the proposed network and communication design.
They are included for clarity only and are not tied to the actual software configuration.

Network diagrams:
- `diagrams/network/system_overview_network.png`
- `diagrams/network/bacnet_network.png`
- `diagrams/network/modbus_network.png`
- Source files are included as `.drawio` in the same folders.

---

## Building Scope

This project simulates a 4-floor commercial office building with a total cooling capacity of 1,500 RT. The model includes the main HVAC systems, environmental monitoring, and electrical metering across the building.

### HVAC equipment
- 3 chillers
- 3 chilled water pumps
- 3 condenser water pumps
- 3 cooling towers
- 4 AHUs, one per floor
- 16 VAVs, four per floor

### Environmental monitoring
- 8 IAQ sensors, two per floor
- 1 outdoor weather station on the rooftop

### Electrical metering
- 1 main building meter
- 4 floor sub-meters
- 3 chiller sub-meters
- 3 chilled water pump sub-meters
- 3 condenser water pump sub-meters
- 3 cooling tower sub-meters
- 4 AHU sub-meters

---

## Features

The system is designed to show how a commercial building can be monitored through a complete IoT workflow, from simulation and messaging to storage, API access, and dashboard visualization.

- Real-time data simulation using Node-RED
- Scenario-based operation for different building conditions
- HVAC monitoring for chillers, pumps, cooling towers, AHUs, and VAVs
- Indoor air quality monitoring for temperature, humidity, CO₂, and PM2.5
- Electrical monitoring at building, floor, and equipment level
- Time-based energy accumulation for power and energy tracking
- Centralized data storage in PostgreSQL
- REST API for dashboard and data access
- Multi-page web dashboard for main, chiller, air, and electrical views
- Support for normal and fault conditions through simulation scenario

---

## Simulation Scenarios

This project simulates how a commercial building behaves under different operating conditions.  
Each scenario reflects realistic situations that typically occur in daily building operations.

---

### 1. Peak Day

Represents a high-demand situation, typically during hot weather and full occupancy (e.g., weekday afternoons).

- Outdoor temperature is high  
- Cooling demand increases significantly  
- Chillers, pumps, and AHUs run at higher capacity  
- Power consumption is at its highest  
- Energy accumulates quickly  

This scenario shows how the system performs under maximum load.

---

### 2. Medium Day

Represents normal operating conditions, such as a typical working day.

- Moderate outdoor temperature  
- Stable cooling demand  
- Systems operate in a balanced state  
- Power consumption is steady  

This is used as a baseline for comparison.

---

### 3. Night

Represents low-load conditions during nighttime when the building has minimal occupancy.

- Lower outdoor temperature  
- Reduced cooling demand  
- Equipment operates at partial or minimal load  
- Power consumption is low  

This scenario shows how the system behaves during off-hours.

---

### 4. Fault – Chiller 2

Represents a fault condition where one chiller becomes unavailable (can occur at any time during operation).

- Chiller 2 is offline or failed  
- Remaining equipment compensates for the load  
- System efficiency decreases  
- Power distribution becomes unbalanced  

This scenario demonstrates how the system reacts to abnormal conditions.

---

All scenarios are generated dynamically in Node-RED and streamed via MQTT.  
The backend processes and stores the data in PostgreSQL, allowing real-time visualization and historical analysis through the dashboard.

---

## How to Run

### System Requirements

This project requires Docker to run.

Before starting the system, make sure Docker is installed and running on your machine.

- Windows / macOS: Docker Desktop
- Linux: Docker Engine with Docker Compose support

The system will automatically start generating simulated data via Node-RED upon startup.  
No manual trigger is required.

### 1. Clone the Repository

```bash
git clone https://github.com/Touch1997/smart-building-sim.git
cd smart-building-sim
```
### 2. Start the System
```bash
docker compose up -d
```
### 3. Access the System
- Dashboard: http://localhost:8000/dashboard
- Node-RED: http://localhost:1880
### 4. Stop the System (Optional)
```bash
docker compose down
```
---
## How to Use Node-RED

Node-RED is used to control the simulation flow and scenario behavior.

---

### Open Node-RED

After the system is running, open:

- http://localhost:1880

---

### Available Scenarios

This project includes four scenarios:

- Peak Day
- Medium Day
- Night
- Fault Chiller 2

---

### Automatic Schedule

The simulation is designed to run automatically every 5 minutes to simulate a full-day building operation.

The current setup is:

- Peak Day: every 5 minutes on weekdays, from 09:00 to 17:00  
- Medium Day: every 5 minutes on weekends, from 09:00 to 17:00  
- Night: every 5 minutes every day, from 17:00 to 09:00  
- Fault Chiller 2: manual trigger only  

This setup reflects a simple day-to-night operating pattern of a commercial building.

---

### Configure Inject Nodes (Optional)

Each scenario is controlled by an inject node in Node-RED.  
You can adjust the timing if you want to simulate different conditions.

To configure:

1. Open Node-RED  
2. Go to the simulation flow  
3. Double-click the inject node of a scenario  
4. Set:

   - Repeat: `interval between times`  
   - Every: `5 minutes`  

---

### Recommended Schedule Setup

#### Peak Day (Weekdays)

- Every: 5 minutes  
- Between: 09:00 – 17:00  
- Days: Monday – Friday  

Represents high load during working hours.

---

#### Medium Day (Weekend)

- Every: 5 minutes  
- Between: 09:00 – 17:00  
- Days: Saturday – Sunday  

Represents lower occupancy during weekends.

---

#### Night (All Days)

- Every: 5 minutes  
- Between: 17:00 – 09:00  

Represents low-load conditions during nighttime.

---

#### Fault Chiller 2 (Manual Only)

- No repeat schedule  
- Trigger manually using the inject button  

Used to simulate abnormal conditions at any time.

---

### Manual Testing

If you want to test a scenario directly:

1. Open the simulation flow in Node-RED  
2. Click the inject button of the scenario  

This is useful for:

- checking dashboard behavior  
- testing a single scenario without waiting  
- triggering Fault Chiller 2 manually  

---

### What to Expect

When a scenario is triggered:

- Node-RED generates simulated HVAC, IAQ, and electrical data  
- Data is published via MQTT  
- Backend stores data in PostgreSQL  
- Dashboard updates in real-time  

---

### Notes

- The inject node uses system time from your machine  
- The simulation schedule is based on your system time  
- If the time is not aligned, scenarios may run at unexpected periods  
- You can disable scheduling and run scenarios manually if needed  

   This setup allows the system to simulate a full 24-hour building operation cycle.
---

## Dashboard Overview

The dashboard provides a simple visualization of the building system across four main views.

### Main Dashboard
- Overall building performance
- Power, energy, and peak demand
- Indoor air quality (Temperature, CO₂, PM2.5)
- Trend charts (power and IAQ)

### Chiller Plant
- Chiller status (ON/OFF, alarm, command)
- Power, cooling load (RT), efficiency (kW/RT)
- CHW supply/return temperature, Delta T, flow rate
- Chiller energy consumption
- Trend options:
  - Power (kW)
  - Cooling Load (RT)
  - Efficiency (kW/RT)

### Air System
- AHU status and performance
- Airflow, temperature, efficiency (kW/CFM)
- Floor-level temperature and humidity
- Air energy consumption
- Trend options:
  - Power (kW)
  - Air Flow (CFM)
  - Efficiency (kW/CFM)

### Electrical
- Main power and energy consumption
- Floor-level power monitoring
- Equipment-level (chiller, pumps, AHU, cooling tower)
- Power factor monitoring
- Trend options:
  - Power (kW)
  - Energy (kWh)
  - Current (A)
  - Power Factor

---

## Data Structure

Data is stored in PostgreSQL.

The main telemetry structure includes:

- device
- point
- value
- timestamp

The stored data covers key building telemetry such as:

- Electrical data (power, energy, current, voltage, power factor)
- Chiller data (cooling load, efficiency, temperatures, flow rate, %RLA)
- Pump and cooling tower data (status, frequency, power, efficiency)
- AHU data (status, temperature, humidity, power)
- VAV data (damper position, airflow)
- IAQ data (temperature, humidity, CO₂, PM2.5)
- Weather data (dry-bulb temperature, humidity, wet-bulb temperature)

This structure is used to support real-time monitoring, trend analysis, and dashboard visualization.

---

## Brick Schema

Brick Schema is an open-source ontology designed to standardize metadata in building automation systems (BAS). It provides a consistent way to describe buildings, equipment, sensors, and their relationships.

Using Brick helps improve interoperability between systems, enables better data organization, and supports advanced applications such as analytics and optimization.

In this project, Brick is used as a conceptual layer to represent:

- Building structure (floors)
- HVAC equipment (chillers, AHUs, pumps)
- Sensors (temperature, humidity, CO₂, PM2.5)

The model is structured in five main layers:

- **Building structure**: building → floors → HVAC zones
- **Chiller plant**: chillers, chilled water pumps, condenser water pumps, and cooling towers
- **Air distribution**: 4 AHUs and 16 VAVs with floor assignments
- **Environmental monitoring**: IAQ sensors per floor and rooftop weather station
- **Electrical metering**: main meter, floor sub-meters, and equipment meters

Key relationships used in the model include:
- `brick:isPartOf` for hierarchy
- `brick:hasLocation` for physical placement
- `brick:feeds` for system flow
- `brick:hasPoint` / `brick:isPointOf` for telemetry mapping
- `brick:hasSubMeter` and `brick:meters` for metering structure

File:
- `brick/building_model.ttl`

---

## Project Structure

```text
iot-assessment/
├── backend/          # FastAPI backend service
├── node-red/         # IoT data simulation flows
├── brick/            # Brick semantic model (.ttl)
├── diagrams/         # Network & architecture diagrams
├── presentation/     # Project presentation slides
├── screenshots/      # Dashboard preview images
├── docker-compose.yml
├── mosquitto.conf
└── README.md
