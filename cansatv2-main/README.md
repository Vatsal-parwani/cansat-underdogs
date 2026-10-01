# CanSat Flight & Ground Station Software

Comprehensive CircuitPython flight software and ground station telemetry system for a secondary-school / university CanSat mission running on two **Raspberry Pi Picos** with an **RFM9x LoRa (433 MHz)** transceiver and a **BMP280** pressure/temperature sensor.

---

## 1. System Architecture & Code Structure

The repository is organized into three main subsystems:

```
cansatv2-main/
├── Flight Software/            <-- Copy directly to the CanSat Pico (CIRCUITPY)
│   ├── boot.py                 <-- CircuitPython boot initialization
│   ├── code.py                 <-- 1 Hz sampling loop, mission timer, and watchdog
│   ├── radio_manager.py        <-- LoRa packet formatting and transmission
│   ├── sensor_manager.py       <-- I2C recovery, auto-detection (0x76/0x77), BMP280 acquisition
│   └── lib/                    <-- Pre-installed drivers:
│       ├── adafruit_bmp280.mpy
│       ├── adafruit_rfm9x.mpy
│       └── adafruit_bus_device/
│
├── Ground station/
│   ├── code.py                 <-- Loop deployed to Ground Station Pico
│   ├── radio_manager.py        <-- Receives LoRa packets and streams to USB serial with RSSI/SNR
│   ├── lib/                    <-- Pre-installed drivers:
│   │   ├── adafruit_rfm9x.mpy
│   │   └── adafruit_bus_device/
│   ├── backend.py              <-- PC telemetry dashboard (Matplotlib GUI, CSV logger, drop tracker)
│   └── logs/                   <-- Automatic timestamped CSV flight logs
│
└── README.md                   <-- Full setup and operating manual
```

---

## 2. Drivers and Firmware

### Firmware
* Flash **CircuitPython 10.x** onto both Raspberry Pi Picos.
  * Hold **BOOTSEL** while connecting via USB, then drag the appropriate `.uf2` file onto the `RPI-RP2` drive:
  * Pico 1 (RP2040): [circuitpython.org/board/raspberry_pi_pico/](https://circuitpython.org/board/raspberry_pi_pico/)
  * Pico 2 (RP2350): [circuitpython.org/board/raspberry_pi_pico2/](https://circuitpython.org/board/raspberry_pi_pico2/)

### Pre-Installed Drivers in `lib/`
The necessary `.mpy` drivers from the official **Adafruit CircuitPython 10.x Bundle** have already been downloaded and placed into the respective `lib/` directories:
* **CanSat Pico (`Flight Software/lib/`)**:
  * `adafruit_bmp280.mpy`
  * `adafruit_rfm9x.mpy`
  * `adafruit_bus_device/` (`i2c_device.mpy`, `spi_device.mpy`)
* **Ground Station Pico (`Ground station/lib/`)**:
  * `adafruit_rfm9x.mpy`
  * `adafruit_bus_device/`

*(If you ever reformat the Pico drives, simply copy the `lib/` folders back across).*

---

## 3. Hardware Wiring & Pin Assignments

Both Picos share the same SPI0 pinout for the RFM9x radio:

### RFM9x LoRa Transceiver (CanSat & Ground Station Picos)
| RFM9x Pin | Raspberry Pi Pico Pin | Function |
|---|---|---|
| **VCC** | 3V3 (Pin 36) | 3.3V Power |
| **GND** | GND (Pin 3, 8, 13, 18, 23, 28, or 38) | Ground |
| **SCK / CLK** | **GP2** (Pin 4) | SPI0 SCK |
| **MOSI** | **GP3** (Pin 5) | SPI0 TX |
| **MISO** | **GP4** (Pin 6) | SPI0 RX |
| **CS / NSS** | **GP5** (Pin 7) | Chip Select |
| **RST / RESET** | **GP6** (Pin 9) | Radio Reset |
| **ANT** | 433 MHz Antenna (approx. 17.3 cm wire or whip) | RF signal |

### BMP280 Sensor (CanSat Pico Only)
| BMP280 Pin | Raspberry Pi Pico Pin | Function |
|---|---|---|
| **VCC** | 3V3 (Pin 36) | 3.3V Power |
| **GND** | GND (Pin 3 or 8) | Ground |
| **SDA** | **GP0** (Pin 1) | I2C0 SDA |
| **SCL** | **GP1** (Pin 2) | I2C0 SCL |
| **SDO** | GND (0x76) or 3V3 (0x77) | Automatically detected |

---

## 4. Telemetry Format

* **Transmitted Over-The-Air (433.0 MHz)**:
  ```
  <packet_id>,<mission_time_s>,<temperature_c>,<pressure_hpa>
  Example: 15,15,21.8,1012.4
  ```
* **Output to PC via USB Serial**:
  ```
  <packet_id>,<mission_time_s>,<temperature_c>,<pressure_hpa>,<rssi_dbm>,<snr_db>
  Example: 15,15,21.8,1012.4,-67.0,8.2
  ```

---

## 5. How to Run the Code

### Step 1: Deploy to CanSat Pico
1. Plug the CanSat Pico into your PC via USB (it will mount as `CIRCUITPY`).
2. Copy the entire contents of the `Flight Software/` directory (`code.py`, `boot.py`, `radio_manager.py`, `sensor_manager.py`, and `lib/`) into the root of `CIRCUITPY`.
3. The CanSat is now ready and can be powered via battery (VSYS/GND or USB power bank).

### Step 2: Deploy to Ground Station Pico
1. Plug the Ground Station Pico into your PC via USB.
2. Copy the entire contents of the `Ground station/` directory (`code.py`, `radio_manager.py`, and `lib/`) into the root of `CIRCUITPY`.
3. Keep this Pico connected to your PC via USB.

### Step 3: Install PC Dependencies
Open a command prompt or terminal and install the required Python packages:
```bash
pip install pyserial matplotlib
```

### Step 4: Start the Ground Station Telemetry Dashboard
Navigate to the `Ground station` directory and run:
```bash
# Auto-detects the connected Pico:
python backend.py

# Or specify your COM port manually if needed:
python backend.py COM3
```

---

## 6. What to Expect When Running the Code

1. **Auto-Connection**: `backend.py` scans your system's serial ports, identifies the Ground Station Pico, and opens communication at 115200 baud.
2. **Flight Log Created**: A timestamped CSV file is immediately initialized in `logs/` (e.g., `logs/cansat_flight_20261001_123000.csv`).
3. **Ground Baseline Calibration**:
   - The first 5 valid telemetry packets received are averaged to calculate the ground-level baseline atmospheric pressure ($P_0$).
   - Relative altitude is calculated in real time using the international barometric formula:
     $$\text{Altitude} = 44330 \times \left(1 - \left(\frac{P}{P_0}\right)^{\frac{1}{5.255}}\right)$$
4. **Live Graph Window**:
   - Displays two responsive graphs:
     - **Top**: Live temperature reading (°C).
     - **Bottom**: Relative altitude above ground (meters).
   - The graphs display the last 25 telemetry points.
5. **Real Dropped Packet Tracking**:
   - The software checks for sequence gaps in the incoming `packet_id`. If packet #10 is followed directly by packet #13, 2 dropped packets are immediately logged.
6. **Session Diagnostics on Window Close**:
   - Closing the graph window safely closes the CSV file and COM port, printing a complete mission report:
     - Total Expected Packets
     - Successful Packets & Success Percentage
     - Corrupted Packets
     - Lost / Dropped Packets
     - Sensor Communication Errors

---

## 7. Troubleshooting

* **`Error connecting to COMx`**:
  * Ensure the Ground Station Pico is plugged in.
  * Close any active serial monitors (e.g., Thonny, Mu, Arduino IDE serial monitor, PuTTY) that might be locking the COM port.
* **Temperature/Pressure displays `ERR` / `-999.0`**:
  * Check the BMP280 wiring (GP0 = SDA, GP1 = SCL, VCC = 3V3).
  * The sensor auto-detects `0x76` and `0x77`. If it still fails, inspect the soldering on the header pins.
* **`Radio initialization error (check wiring/SPI)`**:
  * Check GP2 (SCK), GP3 (MOSI), GP4 (MISO), GP5 (CS), GP6 (RST).
  * Ensure an antenna wire (approx. 17.3 cm) is securely attached to the ANT pin.
