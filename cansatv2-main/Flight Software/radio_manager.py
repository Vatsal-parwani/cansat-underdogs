import busio
import board
import digitalio
import adafruit_rfm9x
import time

RADIO_FREQ_MHZ = 433.0

spi = None
cs = None
reset = None
radio = None

def init_radio():
    """Safely initialize the RFM9x LoRa radio without crashing on boot."""
    global spi, cs, reset, radio
    if radio is not None:
        return True
    try:
        if spi is None:
            spi = busio.SPI(
                clock=board.GP2,
                MOSI=board.GP3,
                MISO=board.GP4
            )
        if cs is None:
            cs = digitalio.DigitalInOut(board.GP5)
        if reset is None:
            reset = digitalio.DigitalInOut(board.GP6)

        radio = adafruit_rfm9x.RFM9x(
            spi,
            cs,
            reset,
            RADIO_FREQ_MHZ
        )
        print("RFM9x radio initialized successfully")
        return True
    except Exception as problem:
        print("Radio initialization error (check wiring/SPI):", problem)
        radio = None
        return False

# Attempt initial setup
init_radio()

def send_data(data):
    """Format and transmit telemetry payload over LoRa."""
    global radio
    if radio is None:
        if not init_radio():
            return False

    try:
        packet_id = data.get("packet_id", 0)
        mission_time = data.get("mission_time", 0)
        temperature = data.get("temperature", -999.0)
        pressure = data.get("pressure", -999.0)

        # Telemetry packet: <packet_id>,<mission_time>,<temp>,<pressure>
        message = f"{packet_id},{mission_time},{temperature:.1f},{pressure:.1f}"
        message_bytes = message.encode("utf-8")
        radio.send(message_bytes)
        return True
    except Exception as problem:
        print("Radio transmission error:", problem)
        return False
