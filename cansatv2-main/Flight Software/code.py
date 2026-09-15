import sensor_manager   
import radio_manager  
import time 
import microcontroller
import watchdog

wdt = microcontroller.watchdog
wdt.timeout = 3.0
wdt.mode = watchdog.WatchDogMode.RESET
wdt.feed()

last_transmit_time = time.monotonic()

while True:
    wdt.feed()
    readings = sensor_manager.get_readings()               
    current_time = time.monotonic()
         
    if current_time - last_transmit_time >= 1.0:
        print(readings)
        radio_manager.send_data(readings)
        last_transmit_time = current_time
