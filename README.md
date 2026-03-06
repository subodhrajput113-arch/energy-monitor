# ⚡ ESP32 Real-Time Energy Monitor

A production-grade IoT energy monitoring system built on ESP32 that measures, analyzes, and visualizes real-time electrical parameters — voltage, current, power factor, THD, and energy consumption — through a live web dashboard.

Built by a **Senior Technical Facility Executive** to solve real-world energy management and asset performance analysis challenges in facility operations.

---

## 📸 Dashboard Preview

> Live dashboard showing real-time P·Q·S power triangle, power factor gauge, slab tariff cost tracking, and voltage/current trend charts.

![Dashboard](docs/dashboard.png)

---

## ✨ Key Features

- **Real-time monitoring** — voltage, current, active/reactive/apparent power updated every 5 seconds
- **IEEE 1459 compliant** power factor calculation — true PF, displacement PF, and phase angle
- **Current THD measurement** — Goertzel DFT algorithm, harmonics H2–H7
- **Lead/Lag detection** — zero-crossing based phase detection
- **Slab tariff billing** — automatic cost calculation with Indian electricity tariff slabs
- **Peak demand tracking** — 15-minute interval demand monitoring
- **CO₂ emission estimate** — based on energy consumed
- **Power quality alerts** — voltage deviation, THD threshold, load warnings
- **Dark/Light theme** — professional dashboard with DM Serif Display typography
- **CSV export** — one-click data export for any time range
- **Local MQTT broker** — Mosquitto on Termux, no cloud dependency

---

## 🏗 System Architecture

```
┌─────────────────┐         MQTT          ┌──────────────────────┐
│   ESP32 DevKit  │ ──────────────────►  │   Mosquitto Broker   │
│                 │   subodh/energy/home1 │   (Termux / Local)   │
│  ZMPT101B  (V)  │                       └──────────┬───────────┘
│  ACS712-20A (I) │                                  │
└─────────────────┘                                  ▼
                                           ┌──────────────────────┐
                                           │   Flask Server       │
                                           │   server.py          │
                                           │   SQLite DB          │
                                           └──────────┬───────────┘
                                                      │
                                                      ▼
                                           ┌──────────────────────┐
                                           │   Web Dashboard      │
                                           │   dashboard.html     │
                                           │   Chart.js + Live    │
                                           │   polling every 5s   │
                                           └──────────────────────┘
```

---

## 🔧 Hardware

| Component | Model | Purpose |
|-----------|-------|---------|
| Microcontroller | ESP32 DevKit V1 | Main controller + WiFi |
| Voltage Sensor | ZMPT101B | AC voltage measurement (isolated) |
| Current Sensor | ACS712-20A | AC/DC current measurement |
| Resistors | 4× 10kΩ | DC bias dividers for ADC |
| Capacitors | 2× 100nF | ADC input noise filtering |

### Pin Assignment

```
ESP32 GPIO 35 (ADC1_CH7)  ←──  ZMPT101B OUT  (via bias divider)
ESP32 GPIO 34 (ADC1_CH6)  ←──  ACS712 OUT    (via bias divider)
ESP32 VIN (5V)            ──►  ACS712 VCC
ESP32 3.3V                ──►  ZMPT101B VCC
ESP32 GND                 ──►  Both sensor GNDs
```

> **Note:** ADC2 pins are disabled when WiFi is active on ESP32. Always use ADC1 pins (GPIO 32–39).

---

## 📊 Measured Parameters

| Parameter | Symbol | Unit | Method |
|-----------|--------|------|--------|
| RMS Voltage | V | Volts | Sampling + RMS calculation |
| RMS Current | I | Amps | Sampling + RMS calculation |
| Active Power | P | Watts | Instantaneous V×I integration |
| Reactive Power | Q | VAR | √(S²−P²) |
| Apparent Power | S | VA | V×I |
| True Power Factor | PF | — | P/S (IEEE 1459) |
| Displacement PF | DPF | — | cos(φ₁) — phase component only |
| Phase Angle | φ | degrees | Zero-crossing detection |
| PF Type | — | — | Lagging / Leading / Unity |
| Voltage THD | THD-V | % | Goertzel DFT H2–H7 |
| Current THD | THD-I | % | Goertzel DFT H2–H7 |
| Energy | E | kWh | Accumulated P×t |
| Peak Demand | PD | kW | 15-minute interval average |
| Load % | — | % | P / MAX_LOAD × 100 |

---

## 🗂 Project Structure

```
energy-monitor/
├── main.py                    # ESP32 MicroPython firmware v4.0
├── server.py                  # Flask backend server
├── templates/
│   └── dashboard.html         # Jinja2 HTML template
├── static/
│   ├── styles.css             # All dashboard styling
│   └── scripts.js             # Chart.js + live polling
├── requirements.txt           # Python dependencies
├── Procfile                   # For cloud deployment (Railway/Render)
├── start.sh                   # Local startup script (Termux)
├── upload.sh                  # ESP32 firmware upload script
├── README.md
└── SETUP.md
```

---

## 🧮 Power Factor Calculation

This system implements **IEEE 1459** compliant power factor measurement — the industry standard for non-sinusoidal waveforms.

```
True PF  =  P / S                          (accounts for phase + distortion)
Disp. PF =  True PF × √(1 + THD_I²)       (phase component only, cos φ₁)
Phase φ  =  arccos(Disp. PF)               (electrical angle V vs I)
```

For linear resistive loads (heaters, incandescent bulbs), True PF ≈ Displacement PF.
For non-linear loads (induction stoves, VFDs, SMPS), the difference is significant.

---

## 📡 MQTT Payload

The ESP32 publishes a JSON payload every 5 seconds:

```json
{
  "voltage": 237.5,
  "current": 4.35,
  "power": 985.2,
  "reactive_power": 198.3,
  "apparent_power": 1006.4,
  "power_factor": 0.9789,
  "displacement_pf": 0.9754,
  "phi_degrees": 12.7,
  "pf_type": "Lagging",
  "thd_v": 2.14,
  "thd_i": 6.82,
  "frequency": 50.0,
  "energy_kwh": 0.0218,
  "peak_demand_kw": 1.006,
  "load_pct": 19.7,
  "voltage_status": "Normal",
  "pf_quality": "Very Good",
  "load_quality": "Light"
}
```

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Live dashboard |
| `/api/latest` | GET | Latest reading as JSON |
| `/api/history?range=live` | GET | Historical readings |
| `/api/stats?range=today` | GET | Aggregated statistics |
| `/api/export?range=today` | GET | Download CSV |
| `/recalibrate` | GET | Send recalibration command to ESP32 |
| `/stream` | GET | Server-sent events stream |

---

## 🛠 Tech Stack

**Firmware**
- MicroPython on ESP32 DevKit V1
- umqtt.simple for MQTT
- machine.ADC for sensor reading

**Backend**
- Python 3 + Flask
- SQLite (local) / PostgreSQL (cloud)
- paho-mqtt
- Gunicorn (production)

**Frontend**
- Jinja2 templates
- Chart.js 4.4
- DM Serif Display + DM Sans + JetBrains Mono
- Vanilla JS — no framework dependency

**Infrastructure**
- Mosquitto MQTT broker (local on Termux)
- Android Termux (local hosting)
- Railway / Render (cloud deployment)

---

## 👤 Author

**Subodh Kumar**
Senior Technical Facility Executive

- GitHub: [@Subodh113](https://github.com/Subodh113)
- LinkedIn: [linkedin.com/in/subodh](https://linkedin.com)

---

## 📄 License

MIT License — free to use, modify, and distribute with attribution.
