# cansat-underdog

Contains all of the code for the Pico computers on the Cansat and Ground station, along with the code on the PC connected to the Ground station.
Also has all of the docs, such as the notes, circuits, and CAD files

### Drivers and Firmware:
- CircuitPython 10.2.1 Firmware for Picos: https://circuitpython.org/board/raspberry_pi_pico2/
- Adafruit .mpy drivers for BMP280 and RFM9XW are needed. The library of all Adafruit 10.x drivers: https://circuitpython.org/libraries

> [!IMPORTANT]
> These drivers and firmware are needed for the code to run without errors

### To use
 When code finalised or used for testing, copy the contents of the `CanSat_Pico` directory onto the Pico that goes onto the Cansat and copy the contents of the `Ground_Station_Pico` directory onto the Pico that acts as the Ground Station
