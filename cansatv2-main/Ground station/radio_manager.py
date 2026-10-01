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
    """Safely initialize the Ground Station RFM9x radio without crashing on boot."""
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
        print("Ground Station RFM9x initialized successfully")
        return True
    except Exception as problem:
        print("Radio initialization error (check wiring/SPI):", problem)
        radio = None
        return False

# Attempt initial setup
init_radio()

def receive_data():
    """Listen for incoming LoRa packet and output to USB serial console."""
    global radio
    if radio is None:
        if not init_radio():
            time.sleep(1.0)
            return

    try:
        packet = radio.receive(timeout=0.5)
        if packet is not None:
            try:
                data_string = packet.decode("utf-8")
                # Format printed to USB Serial: <data_string>,<rssi>,<snr>
                print(f"{data_string},{radio.last_rssi},{radio.last_snr:.1f}")
            except UnicodeError:
                print("ERROR: Corrupted bits from radio interference!!!!!")
    except Exception as problem:
        print("Radio reception error:", problem)
        radio = None
