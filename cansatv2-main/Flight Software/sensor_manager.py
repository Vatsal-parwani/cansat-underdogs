import time                 # needed for the bit-banging I2C recovery code, for the pulses and delays
import board                # ALREADY THERE
import busio                # ALREADY THERE
import digitalio            # Lets us control the SDA and SCL pins directly, for I2C recovery
import adafruit_bmp280      # ALREADY THERE

# These start empty, so a sensor problem cannot stop the file importing.
i2c = None
bmp280 = None


# ENTIRE FUNCTION NEW
def clear_i2c_bus():
    """Try to release an I2C data wire that is stuck LOW."""

    # GP1 is your clock wire; GP0 is your data wire.
    with digitalio.DigitalInOut(board.GP1) as scl:
        with digitalio.DigitalInOut(board.GP0) as sda:       # once repair is finished, the sensor will be released automatically

            # Let both wires return to their normal HIGH state.
            scl.switch_to_input(pull=digitalio.Pull.UP)
            sda.switch_to_input(pull=digitalio.Pull.UP)

            if not scl.value:
                print("I2C recovery failed: SCL is stuck LOW")
                return False

            if sda.value:
                return True  # Data wire is fine; nothing to repair.

            print("SDA stuck LOW; attempting I2C bus recovery")

            # Give the sensor up to nine clock pulses, to completely clock out the stuck bit + it's ACK/NACK, if it requires the full 9.
            for pulse_number in range(9):
                scl.switch_to_output(
                    value=False,
                    drive_mode=digitalio.DriveMode.OPEN_DRAIN
                )
                time.sleep(0.00005)

                scl.switch_to_input(pull=digitalio.Pull.UP) # switches ot input allows line to go high
                time.sleep(0.00005)

                if not scl.value:
                    print("I2C recovery failed: SCL did not rise")
                    return False

                if sda.value:
                    print(
                        "SDA released after",
                        pulse_number + 1,
                        "clock pulses"
                    )
                    break # when high, data line is no longer stuck so we can stop and exit the loop

            if not sda.value:
                print("I2C recovery failed: SDA is still stuck LOW")
                return False

            # Signal that the interrupted conversation is over.
            sda.switch_to_output(
                value=False,
                drive_mode=digitalio.DriveMode.OPEN_DRAIN
            )
            time.sleep(0.00005)
            sda.switch_to_input(pull=digitalio.Pull.UP)

            return scl.value and sda.value

# ENTIRE FUNCTION NEW
def disconnect_sensor():
    """Release the old connection so we can try a fresh one."""
    global i2c, bmp280

    bmp280 = None

    if i2c is not None:
        i2c.deinit()       # throw away broken connection so we can make fresh one next time
        i2c = None

# ENTIRE FUNCTION NEW
def connect_sensor():
    """Repair the bus if needed, then connect to the BMP280."""
    global i2c, bmp280

    try:
        if not clear_i2c_bus():     # if bus is stuck, try to fix it before connecting to the sensor
            return False

        # This line used to at the top however moved here because we shold only assign after the bus is cleared. If the bus is stuck, this line will throw an error and the program will crash.
        i2c = busio.I2C(
            scl=board.GP1,
            sda=board.GP0
        )
        bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)

        print("BMP280 connected")
        return True

    except (OSError, RuntimeError, ValueError) as problem:
        print("BMP280 connection failed:", problem)
        bmp280 = None
        disconnect_sensor()  # throw away the broken connection so we can try again next time

        return False




# CHANGED FUNCTION: it keeps the same name and same dictionary keys.
def get_readings():

    # NEW: connect here, rather than when the file is imported.
    # If connecting fails, the program still gets a dictionary back.
    if bmp280 is None:
        if not connect_sensor():
            return {
                "temperature": -999.0,
                "pressure": -999.0
            } # return empty readings if the sensor connection fails

    try:
        # ALREADY THERE: these are your original sensor readings.
        temperature = bmp280.temperature
        pressure = bmp280.pressure

        # treat an empty reading as an error.
        if temperature is None or pressure is None:
            raise ValueError("BMP280 returned an empty reading")
        
        return {
            "temperature": temperature,
            "pressure": pressure
        }

    # catch sensor/connection errors and prepare to retry.
    except (OSError, RuntimeError, ValueError) as problem:
        print("Sensor communication error:", problem)
        disconnect_sensor()

        return {
            "temperature": -999.0,
            "pressure": -999.0
        }
