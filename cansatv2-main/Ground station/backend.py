import serial
import serial.tools.list_ports
import csv
import datetime
import os
import sys
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# --- Serial Port Configuration ---
DEFAULT_PORT = 'COM3'
BAUD_RATE = 115200

def get_serial_port():
    """Select COM port from CLI argument, detected Pico, or default fallback."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or "").lower()
        if "pico" in desc or "raspberry" in desc or "usb serial" in desc:
            print(f"Auto-detected Ground Station Pico on {p.device} ({p.description})")
            return p.device
            
    # Default fallback
    print(f"No specific Pico detected; falling back to {DEFAULT_PORT}")
    return DEFAULT_PORT

SERIAL_PORT = get_serial_port()

# --- Baseline Pressure & Telemetry State ---
BASELINE_PRESSURE = None
calibration_samples = []
CALIBRATION_TARGET_COUNT = 5

last_packet_id = None
time_data, temp_data, alt_data = [], [], []

error_log = {
    "PACKET_CORRUPTED": 0,
    "PACKET_LOSS": 0,
    "SUCCESSFUL_PACKET": 0,
    "TEMP_ERROR": 0,
    "TOTAL_PACKETS": 0,
}

# --- System & File Setup ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
except serial.SerialException as e:
    print(f"Error connecting to {SERIAL_PORT}: {e}")
    print("Please check that the Ground Station Pico is plugged in and no other serial monitor (e.g. Mu, Thonny, PuTTY) is using the port.")
    exit(1)

os.makedirs("logs", exist_ok=True)
filename = f"logs/cansat_flight_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
file = open(filename, mode='w', newline='')
writer = csv.writer(file)
writer.writerow(["Timestamp", "Packet_ID", "Mission_Time_s", "Temperature_C", "Pressure_hPa", "Altitude_m", "RSSI_dBm", "SNR_dB"])
print(f"Connection established! Saving telemetry to {filename}")

# --- Graph Setup ---
fig, (ax_temp, ax_alt) = plt.subplots(2, 1, figsize=(9, 6))
fig.suptitle('CanSat Live Telemetry Ground Station')

# --- Listener & Graphing Loop ---
def update(frame):
    global BASELINE_PRESSURE, last_packet_id
    data_received_this_tick = False

    # Drain all lines currently waiting in the serial buffer
    while ser.in_waiting > 0:
        raw_bytes = ser.readline()
        try:
            decoded_string = raw_bytes.decode('utf-8', errors='replace').strip()
            if not decoded_string:
                continue

            if "ERROR" in decoded_string:
                error_log["PACKET_CORRUPTED"] += 1
                current_time = datetime.datetime.now().strftime('%H:%M:%S')
                writer.writerow([current_time, "ERR", "ERR", "CORRUPT", "CORRUPT", "CORRUPT", "CORRUPT", "CORRUPT"])
                file.flush()
                continue

            data_list = decoded_string.split(',')

            # Format 1 (Standard): [packet_id, mission_time, temp, pressure, rssi, snr]
            if len(data_list) == 6:
                pkt_id = int(data_list[0])
                mission_time = int(data_list[1])
                raw_temp = float(data_list[2])
                pressure = float(data_list[3])
                rssi = float(data_list[4])
                snr = float(data_list[5])
            # Format 2 (Legacy fallback): [temp, pressure, rssi, snr]
            elif len(data_list) == 4:
                pkt_id = error_log["SUCCESSFUL_PACKET"] + 1
                mission_time = 0
                raw_temp = float(data_list[0])
                pressure = float(data_list[1])
                rssi = float(data_list[2])
                snr = float(data_list[3])
            else:
                error_log["PACKET_CORRUPTED"] += 1
                continue

            # Detect dropped packets from sequence gaps
            if last_packet_id is not None and pkt_id > (last_packet_id + 1):
                dropped = pkt_id - (last_packet_id + 1)
                error_log["PACKET_LOSS"] += dropped
                error_log["TOTAL_PACKETS"] += dropped
                print(f"[!] Warning: Dropped {dropped} packet(s) between #{last_packet_id} and #{pkt_id}")
            last_packet_id = pkt_id

            error_log["TOTAL_PACKETS"] += 1

            # Validate temperature range (-40°C to +85°C for BMP280)
            if -40.0 <= raw_temp <= 85.0:
                temp = raw_temp
            else:
                temp = -999.0
                error_log["TEMP_ERROR"] += 1

            # Baseline Pressure Calibration (average over first N stable readings)
            if BASELINE_PRESSURE is None:
                if pressure > 0 and pressure != -999.0:
                    calibration_samples.append(pressure)
                    if len(calibration_samples) >= CALIBRATION_TARGET_COUNT:
                        BASELINE_PRESSURE = sum(calibration_samples) / len(calibration_samples)
                        print(f"[*] Ground baseline pressure calibrated to: {BASELINE_PRESSURE:.2f} hPa (averaged over {CALIBRATION_TARGET_COUNT} samples)")

            # Altitude calculation using the barometric formula
            if pressure != -999.0 and BASELINE_PRESSURE is not None:
                altitude = 44330.0 * (1.0 - (pressure / BASELINE_PRESSURE) ** (1.0 / 5.255))
            else:
                altitude = -999.0

            current_time = datetime.datetime.now().strftime('%H:%M:%S')

            # Log to CSV immediately
            row_to_save = [
                current_time,
                pkt_id,
                mission_time,
                f"{temp:.1f}" if temp != -999.0 else "ERR",
                f"{pressure:.1f}" if pressure != -999.0 else "ERR",
                f"{altitude:.1f}" if altitude != -999.0 else "ERR",
                f"{rssi:.1f}",
                f"{snr:.1f}"
            ]
            writer.writerow(row_to_save)
            file.flush()
            print(f"Received #{pkt_id} (T+{mission_time}s): Temp={temp:.1f}C, Press={pressure:.1f}hPa, Alt={altitude:.1f}m, RSSI={rssi:.1f}dBm, SNR={snr:.1f}dB")

            # Update graphing data buffer (keep valid points only)
            if temp != -999.0 and altitude != -999.0:
                error_log["SUCCESSFUL_PACKET"] += 1
                time_data.append(current_time)
                temp_data.append(temp)
                alt_data.append(altitude)

                # Keep last 25 points in view
                time_data[:] = time_data[-25:]
                temp_data[:] = temp_data[-25:]
                alt_data[:] = alt_data[-25:]
                data_received_this_tick = True

        except (ValueError, IndexError) as err:
            error_log["PACKET_CORRUPTED"] += 1
            print("Packet parse error:", err)

    # Redraw plots if fresh telemetry arrived
    if data_received_this_tick and len(time_data) > 0:
        ax_temp.clear()
        ax_temp.plot(time_data, temp_data, color='red', marker='o', linewidth=2)
        ax_temp.set_title(f"Temperature: {temp_data[-1]:.1f} °C")
        ax_temp.set_ylabel("°C")
        ax_temp.grid(True, linestyle='--', alpha=0.6)
        ax_temp.tick_params(axis='x', rotation=30)

        ax_alt.clear()
        ax_alt.plot(time_data, alt_data, color='blue', marker='o', linewidth=2)
        base_str = f"{BASELINE_PRESSURE:.1f} hPa" if BASELINE_PRESSURE else "Calibrating..."
        ax_alt.set_title(f"Altitude: {alt_data[-1]:.1f} m  (Ground Base: {base_str})")
        ax_alt.set_ylabel("Meters (m)")
        ax_alt.grid(True, linestyle='--', alpha=0.6)
        ax_alt.tick_params(axis='x', rotation=30)

        plt.tight_layout()

# Run update loop every 500ms for responsive graph rendering
ani = animation.FuncAnimation(fig, update, interval=500)

try:
    plt.show()
finally:
    file.close()
    ser.close()
    print("\n--- Telemetry Session Summary ---")
    if error_log["TOTAL_PACKETS"] > 0:
        success_rate = (error_log['SUCCESSFUL_PACKET'] / error_log['TOTAL_PACKETS']) * 100
        print(f"Total Expected Packets: {error_log['TOTAL_PACKETS']}")
        print(f"Successful Packets:     {error_log['SUCCESSFUL_PACKET']} ({success_rate:.1f}%)")
    else:
        print("No telemetry packets received during session.")
    print(f"Corrupted Packets:      {error_log['PACKET_CORRUPTED']}")
    print(f"Lost / Dropped Packets: {error_log['PACKET_LOSS']}")
    print(f"Sensor Read Errors:     {error_log['TEMP_ERROR']}")
    print(f"Log file saved to:      {filename}")