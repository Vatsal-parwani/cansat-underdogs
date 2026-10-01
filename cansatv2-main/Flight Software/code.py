import sensor_manager   
import radio_manager  
import time 
import microcontroller
import watchdog

# Watchdog setup (5.0s gives safe margin for LoRa transmission & sensor bus recovery)
wdt = microcontroller.watchdog
wdt.timeout = 5.0
wdt.mode = watchdog.WatchDogMode.RESET
wdt.feed()

start_time = time.monotonic()
last_transmit_time = start_time
packet_id = 0

print("CanSat Flight Software Started")

while True:
    wdt.feed()
    current_time = time.monotonic()
         
    if current_time - last_transmit_time >= 1.0:
        packet_id += 1
        readings = sensor_manager.get_readings()
        readings["packet_id"] = packet_id
        readings["mission_time"] = int(current_time - start_time)

        print(f"Pkt #{packet_id} (T+{readings['mission_time']}s) -> Temp: {readings['temperature']:.1f} C, Press: {readings['pressure']:.1f} hPa")
        radio_manager.send_data(readings)
        last_transmit_time = current_time

    # Small delay yields CPU cycles, cools RP2040 chip, and saves power
    time.sleep(0.01)
