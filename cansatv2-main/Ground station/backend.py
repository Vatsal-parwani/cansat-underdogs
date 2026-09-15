import serial
import csv
import datetime
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# --- Configuration ---
SERIAL_PORT = 'COM3'  # Change to your Pico's actual USB port
BAUD_RATE = 115200
BASELINE_PRESSURE = None #we will auto calibrate instead of hardcoding

# --- Graph Setup ---
# Creates a window with 2 subplots (Temperature on top, Altitude on bottom)
fig, (ax_temp, ax_alt) = plt.subplots(2, 1, figsize=(8, 6))
fig.suptitle('CanSat Live Telemetry')

# Empty lists to hold the graphing data
time_data, temp_data, alt_data = [], [], []

# --- System Setup ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except serial.SerialException:
    print(f"Error connecting to {SERIAL_PORT}. Is the Ground Station plugged in?")
    exit()

filename = f"logs/cansat_flight_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
file = open(filename, mode='w', newline='')
writer = csv.writer(file)
writer.writerow(["Timestamp", "Temperature (C)", "Pressure (hPa)", "Altitude (m)", "RSSI (dBm)", "SNR (dB)"])
print(f"Connection established! Saving data to {filename}")

error_log = {
    "PACKET_CORRUPTED": 0,
    "PACKET_LOSS": 0,
    "SUCCESSFUL_PACKET": 0,
    "TEMP_ERROR": 0,
    "TOTAL_PACKETS": 0,
}

# --- The Listener & Graphing Loop ---
def update(frame):
    error = ""
    error_log["TOTAL_PACKETS"] += 1
    if ser.in_waiting > 0:
        raw_bytes = ser.readline()
        decoded_string = raw_bytes.decode('utf-8').strip()

        if decoded_string:
            if "ERROR" not in decoded_string:
                data_list = decoded_string.split(',')

                # Ensure we didn't receive a half-packet
                if len(data_list) == 4:
                    try:
                        raw_temp = float(data_list[0])
                        pressure = float(data_list[1])
                        rssi = float(data_list[2])
                        snr = float(data_list[3])

                        # Data Bounds Checking for Temperature (-15 to +60)
                        if -15.0 <= raw_temp <= 100.0:
                            temp = raw_temp
                        else:
                            temp = -999.0  # Throw the error code if it glitches

                        # Calculate Altitude
                        global BASELINE_PRESSURE
                        if BASELINE_PRESSURE is None:
                            if pressure > 0:
                                BASELINE_PRESSURE = pressure
                                print(f"Ground baseline pressure calibrated to: {BASELINE_PRESSURE:.2f} hPa")
                        if pressure != -999.0 and BASELINE_PRESSURE is not None:
                            altitude = 44330 * (1 - (pressure / BASELINE_PRESSURE) ** (1 / 5.255))
                        else:
                            altitude = -999.0

                        current_time = datetime.datetime.now().strftime('%H:%M:%S')

                        # Log to CSV instantly
                        row_to_save = [current_time, f"{temp:.1f}", str(pressure), f"{altitude:.1f}", f"{rssi:.1f}", f"{snr:.1f}"]
                        writer.writerow(row_to_save)
                        file.flush()
                        print(f"Received: {row_to_save}")

                        # --- Update the Graphs ---
                        # We only plot valid data; we skip plotting the -999.0 errors
                        if temp != -999.0 and altitude != -999.0:
                            error_log["SUCCESSFUL_PACKET"] += 1
                            time_data.append(current_time)
                            temp_data.append(temp)
                            alt_data.append(altitude)

                            # Keep only the last 20 points so the graph doesn't get squished over time
                            time_data[:] = time_data[-20:]
                            temp_data[:] = temp_data[-20:]
                            alt_data[:] = alt_data[-20:]

                            # Draw Temperature Graph
                            ax_temp.clear()
                            ax_temp.plot(time_data, temp_data, color='red', marker='o')
                            ax_temp.set_title("Temperature (°C)")
                            ax_temp.set_ylim(-15, 60) # Locks the Y-axis to your bounds

                            # Draw Altitude Graph
                            ax_alt.clear()
                            ax_alt.plot(time_data, alt_data, color='blue', marker='o')
                            ax_alt.set_title("Altitude (m)")

                            plt.tight_layout()
                        else:
                            error_log["TEMP_ERROR"] += 1
                    except:
                        error_log["PACKET_CORRUPTED"] += 1
                        error = "corrupt"
                else:
                    error_log["PACKET_CORRUPTED"] += 1
                    error = "corrupt"
            else:
                error_log["PACKET_CORRUPTED"] += 1
                error = "corrupt"
        else:
            error_log["PACKET_CORRUPTED"] += 1
            error = "corrupt"
    else:
        error_log["PACKET_LOSS"] += 1
        current_time = datetime.datetime.now().strftime('%H:%M:%S')
        writer.writerow([current_time, "LOST", "LOST", "LOST", "LOST", "LOST"])
        file.flush()
    if error == "corrupt":
        current_time = datetime.datetime.now().strftime('%H:%M:%S')
        writer.writerow([current_time, "CORRUPT", "CORRUPT", "CORRUPT", "CORRUPT", "CORRUPT"])
        file.flush()


# This is the engine that runs the 'update' function every 1000ms (1 second)
ani = animation.FuncAnimation(fig, update, interval=1000)

# Opens the window and starts the loop
plt.show() 

# When you close the graphing window, it safely shuts down the file and port
file.close()
ser.close()

if error_log["TOTAL_PACKETS"] > 0:
    success_rate = (error_log['SUCCESSFUL_PACKET'] / error_log['TOTAL_PACKETS']) * 100
    print(f"Successful Packets: {error_log['SUCCESSFUL_PACKET']} ({success_rate:.1f}%)")
else:
    print("No packets received.")
print(f"Corrupted Packets:  {error_log['PACKET_CORRUPTED']}")
print(f"Lost Packets:       {error_log['PACKET_LOSS']}")
print(f"Sensor Errors:      {error_log['TEMP_ERROR']}")