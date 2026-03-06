# 🔧 Setup Guide — ESP32 Energy Monitor

Complete installation and configuration guide for the ESP32 Real-Time Energy Monitor system.

---

## 📋 Prerequisites

### Hardware Required
- ESP32 DevKit V1
- ZMPT101B voltage sensor module
- ACS712-20A current sensor module
- 4× 10kΩ resistors
- 2× 100nF ceramic capacitors
- Breadboard + jumper wires
- USB cable (micro USB)
- Android phone with Termux (for local server)

### Software Required
- Python 3.8+ on PC
- mpremote (`pip install mpremote`)
- MicroPython firmware on ESP32
- Termux on Android phone

---

## Part 1 — Hardware Setup

### 1.1 — DC Bias Circuit (Required)

The ESP32 ADC reads 0–3.3V only. AC sensors output a signal that swings negative — this would damage the ADC. A DC bias circuit lifts the midpoint to 1.65V.

Build this circuit for **each sensor**:

```
Sensor OUT ──┬── 10kΩ ──► ESP32 GPIO pin
             │
             └── 10kΩ ──► 3.3V

Also add:
GPIO pin ──── 100nF ──► GND   (noise filter)
```

### 1.2 — Voltage Sensor (ZMPT101B)

```
ZMPT101B VCC  ──►  ESP32 3.3V
ZMPT101B GND  ──►  ESP32 GND
ZMPT101B OUT  ──►  Bias circuit  ──►  GPIO 35
```

> ⚠️ The ZMPT101B is mains-isolated and safe for 230V AC. Never connect mains directly to the ESP32.

### 1.3 — Current Sensor (ACS712-20A)

```
ACS712 VCC    ──►  ESP32 VIN (5V from USB)   ← must be 5V, not 3.3V
ACS712 GND    ──►  ESP32 GND
ACS712 OUT    ──►  Bias circuit  ──►  GPIO 34

Load wire passes through the ACS712 ring
```

> ⚠️ The load's live wire (phase) must pass through the ACS712 current sensing ring. Do NOT connect mains directly to OUT/VCC/GND pins.

### 1.4 — Complete Wiring Diagram

```
                    ┌─────────────────────────────┐
                    │       ESP32 DevKit V1        │
                    │                              │
  ZMPT101B OUT ───► │ GPIO35 (ADC1_CH7)            │
  ACS712 OUT   ───► │ GPIO34 (ADC1_CH6)            │
                    │                              │
  ACS712 VCC   ◄─── │ VIN  (5V)                   │
  ZMPT101B VCC ◄─── │ 3.3V                         │
  Both GNDs    ◄─── │ GND                          │
                    │                              │
                    │ USB ◄──── PC (for flashing)  │
                    └─────────────────────────────┘
```

### 1.5 — Verify Bias Circuit

After wiring, check the midpoint voltage with a multimeter:

- Expected: **~1.65V** at the GPIO pin with no load connected
- If reading 0V: bias resistors not connected properly
- If reading 3.3V: short circuit — check wiring

---

## Part 2 — ESP32 Firmware

### 2.1 — Flash MicroPython to ESP32

If MicroPython is not already installed:

```bash
# Install esptool
pip install esptool

# Download MicroPython firmware from micropython.org
# Choose: ESP32 → Generic → latest .bin file

# Erase flash
esptool.py --port /dev/ttyUSB0 erase_flash

# Flash MicroPython
esptool.py --port /dev/ttyUSB0 --baud 460800 \
  write_flash -z 0x1000 esp32-20240602-v1.23.0.bin
```

### 2.2 — Configure main.py

Open `main.py` on your PC and update these settings:

```python
# ── WiFi ────────────────────────────────────────
WIFI_NETWORKS = [
    ("YourWiFiName",     "YourPassword"),
    ("BackupWiFiName",   "BackupPassword"),   # optional
]

# ── MQTT ────────────────────────────────────────
MQTT_BROKER = "192.168.1.100"   # Your phone's static IP
MQTT_PORT   = 1883
MQTT_TOPIC  = "subodh/energy/home1"

# ── Calibration ─────────────────────────────────
VOLTAGE_CAL          = 386.0    # Adjust until V matches multimeter
CURRENT_SENSITIVITY  = 0.100    # 0.185=5A, 0.100=20A, 0.066=30A
FREQUENCY_HZ         = 50.0     # 50Hz India

# ── Load capacity ───────────────────────────────
MAX_LOAD_W = 5000.0             # Your circuit's maximum load in watts
```

**Finding your CURRENT_SENSITIVITY:**
Check the label printed on your ACS712 chip:
- `ACS712-05B` → `0.185`
- `ACS712-20A` → `0.100`
- `ACS712-30A` → `0.066`

### 2.3 — Verify Syntax

```bash
python3 -m py_compile main.py && echo "SYNTAX OK"
```

Fix any errors before uploading.

### 2.4 — Upload Firmware

```bash
# Upload firmware
mpremote connect /dev/ttyUSB0 fs cp main.py :main.py

# Verify line count
mpremote connect /dev/ttyUSB0 exec \
  "f=open('main.py');l=f.readlines();f.close();print(len(l),'lines')"

# Reset and monitor
mpremote connect /dev/ttyUSB0 reset
sleep 2
mpremote connect /dev/ttyUSB0
```

Press `Ctrl+]` to exit serial monitor.

### 2.5 — Expected Boot Output

```
==================================================
  ESP32 Smart Energy Monitor v4.0
==================================================
[CAL] Ensure load is OFF. Calibrating in 3s...
[CAL] V_OFFSET = 1.6234 V  (expected ~1.65V)
[CAL] I_OFFSET = 1.6187 V  (expected ~1.65V)
[WIFI] Connecting to: YourWiFiName
[WIFI] Connected | IP: 192.168.1.105
[MQTT] Connected to 192.168.1.100:1883
[WDT]  Watchdog armed
[RUN]  Monitoring started. Publishing every 5s
V= 237.1V  I=4.370A  P= 985.20W  PF=0.9789
```

> ⚠️ **Important:** Always boot the ESP32 with load OFF. The 3-second calibration captures the sensor zero point. If load is ON during boot, current will read as 0.

### 2.6 — Voltage Calibration

1. Measure mains voltage with a calibrated multimeter
2. Note the value shown by ESP32 in serial output
3. Adjust:

```python
# Formula:
VOLTAGE_CAL = VOLTAGE_CAL × (multimeter_reading / esp32_reading)

# Example:
# Multimeter = 235.0V, ESP32 shows 228.5V
# New VOLTAGE_CAL = 386.0 × (235.0 / 228.5) = 396.99
VOLTAGE_CAL = 397.0
```

4. Re-upload and verify.

---

## Part 3 — Server Setup on Termux (Android Phone)

### 3.1 — Install Termux

Download Termux from **F-Droid** (not Play Store — Play Store version is outdated):
```
https://f-droid.org/packages/com.termux/
```

### 3.2 — Install Dependencies

```bash
pkg update && pkg upgrade
pkg install python mosquitto git
pip install flask paho-mqtt
```

### 3.3 — Set Static IP on Phone

This prevents your phone's IP from changing and breaking ESP32 connection:

```
Android Settings
→ WiFi
→ Long press your network
→ Modify network
→ Advanced options
→ IP settings → Static
→ IP address  → 192.168.1.100
→ Gateway     → 192.168.1.1
→ DNS 1       → 8.8.8.8
→ Save
```

### 3.4 — Clone the Repository

```bash
cd ~
git clone https://github.com/Subodh113/energy-monitor.git ems
cd ems
```

Or copy files manually:
```bash
mkdir -p ~/ems/static ~/ems/templates
# copy server.py, static/styles.css, static/scripts.js, templates/dashboard.html
```

### 3.5 — Configure server.py

```bash
nano ~/ems/server.py
```

Update these lines:

```python
BROKER = "127.0.0.1"       # Local Mosquitto broker
PORT   = 1883
TOPIC  = "subodh/energy/home1"
DB     = "/data/data/com.termux/files/home/ems/energy_v3.db"
```

### 3.6 — Create start.sh

```bash
nano ~/ems/start.sh
```

```bash
#!/bin/bash
pkill -f mosquitto 2>/dev/null
pkill -f server.py 2>/dev/null
sleep 1

echo "Starting Mosquitto broker..."
mosquitto -d -p 1883
sleep 2

echo "Starting Energy Monitor server..."
cd ~/ems
while true; do
    python server.py
    echo "Server stopped. Restarting in 5s..."
    sleep 5
done
```

```bash
chmod +x ~/ems/start.sh
```

### 3.7 — Prevent Android from Killing Termux

```bash
# Run wake lock
termux-wake-lock
```

Also in Android settings:
```
Settings → Apps → Termux → Battery → Unrestricted
```

### 3.8 — Start the System

```bash
cd ~/ems
termux-wake-lock
./start.sh
```

Expected output:
```
Starting Mosquitto broker...
Starting Energy Monitor server...
MQTT listening: subodh/energy/home1
 * Running on http://0.0.0.0:5000
RX: V=237.1V  I=4.37A  P=985.2W  PF=0.9789  Load=19.7%
```

### 3.9 — Run in Background

To keep running after closing Termux:

```bash
nohup ./start.sh > ~/ems/server.log 2>&1 &
```

Check logs:
```bash
tail -f ~/ems/server.log
```

Stop everything:
```bash
pkill -f server.py && pkill -f mosquitto
```

---

## Part 4 — Access the Dashboard

### Local Access (Same WiFi)

Open on any device connected to the same WiFi network:

```
http://192.168.1.100:5000
```

### Dashboard Features

| Feature | How to Use |
|---------|-----------|
| Time range | Click Live / Today / Week / Month / All |
| Dark mode | Click 🌓 button in topbar |
| Export CSV | Click ↓ button in topbar |
| Recalibrate | Visit `/recalibrate` URL |
| Live JSON | Visit `/api/latest` |

---

## Part 5 — Cloud Deployment (Optional)

To access the dashboard from outside your home WiFi:

### Railway

```bash
# In your project folder
echo "web: gunicorn --bind 0.0.0.0:\$PORT --timeout 120 --workers 1 --threads 2 server:app" > Procfile

git add .
git commit -m "deploy"
git push
```

Then connect Railway to your GitHub repo at `railway.app`.

> **Note:** Cloud deployment only serves the dashboard. The MQTT broker and ESP32 must remain on your local network. Update `BROKER` in server.py to point to your HiveMQ or cloud MQTT broker for remote data collection.

---

## Part 6 — Troubleshooting

### Current always reads 0

| Check | How |
|-------|-----|
| Load connected? | Plug in a device |
| ACS712 VCC = 5V? | Measure with multimeter — must be 5V not 3.3V |
| Loose wire? | Run raw ADC check below |
| Wrong sensitivity? | Check chip label for 05B/20A/30A |
| Calibration offset wrong? | Restart ESP32 with load OFF |

```bash
# Raw ADC check
mpremote connect /dev/ttyUSB0 exec "
from machine import ADC, Pin
import time
adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)
for i in range(10):
    v = adc.read()
    print(v, '=', round(v/4095*3.3,3), 'V')
    time.sleep(0.3)
"
```

Expected with no load: readings near `2048` (~1.65V).

### Server crashes / stops

```bash
# Check logs
tail -50 ~/ems/server.log

# Restart
pkill -f server.py
cd ~/ems && python server.py
```

### MQTT not connecting

```bash
# Check Mosquitto is running
ps aux | grep mosquitto

# Start if not running
mosquitto -d -p 1883

# Test broker
mosquitto_sub -t "subodh/energy/home1" -v
```

### Dashboard page loading slowly

```bash
# Check database size
ls -lh ~/ems/energy_v3.db

# If > 100MB, clean old data
sqlite3 ~/ems/energy_v3.db \
  "DELETE FROM readings WHERE timestamp < datetime('now', '-30 days');"
```

---

## Part 7 — Calibration Reference

### Voltage Calibration Procedure

1. Connect a known load (heater or iron works best)
2. Measure voltage with calibrated multimeter at the socket
3. Check ESP32 serial output for `V=` value
4. Calculate: `new_cal = old_cal × (multimeter / esp32)`
5. Update `VOLTAGE_CAL` in main.py and re-upload

### Current Calibration Procedure

1. Connect a known resistive load (e.g. 1000W heater)
2. Expected current = Power / Voltage (e.g. 1000W / 230V = 4.35A)
3. Compare with ESP32 reading
4. Calculate: `new_sensitivity = old_sensitivity × (esp32_I / expected_I)`
5. Update `CURRENT_SENSITIVITY` in main.py and re-upload

---

## 📞 Support

For issues or questions raise a GitHub Issue at:
```
https://github.com/Subodh113/energy-monitor/issues
```
