# Multi-Disaster Early Warning System (Hardware + Software)

A production-grade, modular multi-disaster early-warning system designed to detect, track, and alert against three major environmental hazards:

1. **Landslides** ⛰️
2. **Flash Floods** 🌊
3. **Wildfires** 🔥

Built with a decoupled hardware-software architecture, central receiver data ingestion with GPS association, independent processing engines, NASA FIRMS satellite active-fire corroboration, simultaneous multi-disaster state tracking, an interactive Leaflet digital map dashboard, and automated Telegram bot alerts.

---

## 1. System Architecture

```
                    THREE INDEPENDENT HARDWARE SYSTEMS
        ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
        │   LANDSLIDE    │   │  FLASH FLOOD   │   │    WILDFIRE    │
        │     SYSTEM     │   │     SYSTEM     │   │     SYSTEM     │
        │ (Tilt/Moist/Vib)│  │ (Water/Rain/Flow)│ │(Temp/Smoke/Hum)│
        └───────┬────────┘   └───────┬────────┘   └───────┬────────┘
                │                    │                    │
                └────────────────────┼────────────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │    CENTRAL RECEIVER     │
                        │ • Multi-channel Ingest  │
                        │ • Receiver GPS Module   │
                        │ • Packet Normalization  │
                        └────────────┬────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │     DATA CLASSIFIER     │
                        │  (Hardware ID & Hazard) │
                        └────────────┬────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
  ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
  │ LANDSLIDE ENGINE│       │  FLOOD ENGINE   │       │ WILDFIRE ENGINE │
  │ • Slope Tilt    │       │ • Water Depth   │       │ • Temp & Smoke  │
  │ • Soil Moisture │       │ • Rate of Rise  │       │ • Humidity Drop │
  │ • Vibration     │       │ • Rain Rate     │       └────────┬────────┘
  └────────┬────────┘       └────────┬────────┘                ▼
           │                         │                ┌─────────────────┐
           │                         │                │ NASA FIRMS CHECK│
           │                         │                │ • Hotspot Query │
           │                         │                │ • Haversine Dist│
           │                         │                │ • +15% Boost    │
           │                         │                └────────┬────────┘
           └─────────────────────────┼─────────────────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │       RISK ENGINE       │
                        │ • Detection vs Risk     │
                        │ • Configurable Levels   │
                        └────────────┬────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │   STATE STORE (SYNC)    │
                        │ • Independent 3-Hazard  │
                        │ • Simultaneous Support  │
                        └────────────┬────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
         ┌─────────────────────┐           ┌─────────────────────┐
         │  DIGITAL MAP & UI   │           │    ALERT ENGINE     │
         │ • Leaflet Map       │           │ • Telegram Bot API  │
         │ • Custom Hazard Pins│           │ • Rate Limiting     │
         │ • Multi-hazard View │           │ • Emoji Formatters  │
         │ • Event Inspector   │           │ • Multi-channel Bus │
         └─────────────────────┘           └─────────────────────┘
```

---

## 2. Core Design Principles

1. **Three Completely Separate Hardware Systems**:
   - Each hardware system is dedicated to exactly one disaster type with its own sensors, microcontroller, and transmitter.
   - Nodes are identified by prefixes: `LANDSLIDE_*`, `FLOOD_*`, and `FIRE_*`.
2. **Central Receiver & GPS Location**:
   - Central receiver continuously collects packets from all three systems.
   - Pairs telemetry with precise GPS coordinates (either node GPS or Central Receiver GPS module).
3. **Software Classification**:
   - Automatically identifies originating hardware and routes packets to domain-specific processing engines.
4. **NASA FIRMS Corroboration (Wildfire Only)**:
   - When wildfire conditions are detected by hardware, the system queries NASA FIRMS satellite data.
   - Calculates Haversine distance to the nearest active thermal hotspot.
   - If a satellite hotspot exists within the configured radius (e.g. 25 km), it applies a **+15 percentage point corroboration bonus** (capped at 100%).
   - Non-wildfire hazards never touch NASA FIRMS.
5. **Simultaneous Multi-Disaster Support**:
   - The state manager maintains independent statuses for Landslide, Flash Flood, and Wildfire simultaneously.
   - Detection of one hazard **never** clears, suppresses, or overwrites another hazard's state.
6. **Digital Map Dashboard**:
   - Interactive Leaflet.js map with custom hazard markers (🔥, 🌊, ⛰️) and pulsating danger rings.
   - Clickable inspector showing node ID, GPS coordinates, detection status, risk score & level, sensor readings, and FIRMS confirmation.
7. **Telegram Alert System**:
   - Sends formatted emergency warnings with disaster emojis, Google Maps links, telemetry summaries, and FIRMS corroboration details.
   - Built-in cooldown throttling prevents notification flooding.

---

## 3. Standard Data Packet

Every hardware system or receiver emits the standardized JSON format:

```json
{
  "device_id": "FIRE_001",
  "hazard_type": "WILDFIRE",
  "latitude": 17.3850,
  "longitude": 78.4867,
  "timestamp": "2026-09-27T11:30:00Z",
  "sensor_data": {
    "temperature": 48.2,
    "humidity": 21.0,
    "smoke": 734.0,
    "flame_detected": true
  }
}
```

---

## 4. Quickstart

### Prerequisites
- Python 3.10+
- Virtual environment with dependencies from `requirements.txt`

### 1. Launch the Backend & Web Dashboard
```bash
./venv/bin/python3 run.py
```
By default, the server starts on `http://localhost:8000`.

- **Web Dashboard & Digital Map**: `http://localhost:8000/`
- **Interactive REST API Docs (Swagger)**: `http://localhost:8000/docs`
- **Real-Time WebSocket Stream**: `ws://localhost:8000/ws`

### 2. Run Automated Test Suite
```bash
./venv/bin/pytest -v
```
All 24 unit and integration tests will run, verifying classifier routing, engine calculations, NASA FIRMS cross-checking, simultaneous state preservation, and Telegram alerts.

### 3. Trigger Interactive Simulations
You can test the system directly from the **Web Dashboard** using the 1-click buttons in the **Hardware Simulation Bench**:
- ⚡ **SIMULTANEOUS MULTI-DISASTER (ALL 3)**: Simultaneously triggers critical alerts for Fire, Flood, and Landslide to demonstrate concurrent independent handling.
- 🔥 **Wildfire (+FIRMS)**: Triggers wildfire node telemetry and tests NASA FIRMS satellite corroboration.
- 🌊 **Flash Flood**: Triggers rapid surge water rise and torrential rainfall.
- ⛰️ **Landslide**: Triggers excessive slope tilt and soil moisture saturation.
- 🔄 **Reset All Nodes to Normal**: Returns all nodes to safe monitoring baseline.

Alternatively, run from the command-line:
```bash
./venv/bin/python3 simulator/run_simulation.py --scenario multi
```

---

## 5. Configuration & Environment Variables

Copy `.env.example` to `.env` to configure optional live credentials:

```bash
# Central Receiver GPS Location
RECEIVER_LATITUDE=17.3850
RECEIVER_LONGITUDE=78.4867

# NASA FIRMS API (Get free key: https://firms.modaps.eosdis.nasa.gov/api/map_key/)
NASA_FIRMS_MAP_KEY=
FIRMS_MATCH_RADIUS_KM=25.0
FIRMS_RISK_BOOST=15.0
FIRMS_MOCK_FALLBACK=true

# Telegram Alert Configuration (Create bot with @BotFather, get ID with @userinfobot)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_ALERT_COOLDOWN_SECONDS=60.0
TELEGRAM_MIN_RISK_LEVEL=HIGH
```

*(Note: If `TELEGRAM_BOT_TOKEN` or `NASA_FIRMS_MAP_KEY` are not set, the system automatically runs in local test/simulation mode with mock satellite hotspots and console/UI alert logging.)*

---

## 6. Project Structure

```
.
├── config/
│   └── settings.py              # System configuration and thresholds
├── core/
│   ├── models.py                # Pydantic schemas (StandardPacket, HazardEvent, etc.)
│   └── event_bus.py             # Asynchronous Pub/Sub event bus
├── receiver/
│   ├── central_receiver.py      # Telemetry ingestion & GPS coordination
│   └── serial_adapter.py        # Serial/UART adapter for physical microcontrollers
├── classifier/
│   └── data_classifier.py       # Hardware identification & engine router
├── engines/
│   ├── base_engine.py           # Base hazard engine interface
│   ├── landslide_engine.py      # Slope tilt, moisture, vibration analysis
│   ├── flood_engine.py          # Stage, rate of rise, rainfall analysis
│   └── wildfire_engine.py       # Temperature, smoke + NASA FIRMS cross-check
├── firms/
│   ├── distance.py              # Haversine distance calculator
│   └── client.py                # NASA FIRMS API client & mock hotspot generator
├── risk/
│   └── risk_engine.py           # Qualitative risk level classification
├── state/
│   └── state_manager.py         # Simultaneous multi-disaster independent state store
├── alerts/
│   ├── formatter.py             # Markdown message formatter with emojis
│   └── telegram_bot.py          # Telegram Bot dispatcher with cooldown
├── api/
│   ├── app.py                   # FastAPI REST API & WebSocket endpoints
│   └── websocket_manager.py     # Live dashboard broadcaster
├── simulator/
│   ├── hardware_nodes.py        # Independent hardware node simulators
│   └── run_simulation.py        # CLI simulation runner
├── static/                      # Web Mission Control Dashboard
│   ├── index.html               # Tactical UI layout
│   ├── css/style.css            # Dark mode emergency response styling
│   └── js/
│       ├── map.js               # Leaflet map, custom hazard markers, popups
│       ├── dashboard.js         # WebSocket subscriber & card updates
│       └── simulator.js         # In-browser test bench triggers
├── tests/                       # Automated pytest suite (24 tests)
├── run.py                       # Main application entrypoint
└── requirements.txt             # Python dependencies
```
