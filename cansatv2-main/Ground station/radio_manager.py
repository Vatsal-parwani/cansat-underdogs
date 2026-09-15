import busio
import board
import digitalio
import adafruit_rfm9x

RADIO_FREQ_MHZ = 433.0

SPI = busio.SPI(
    clock=board.GP2,
    MOSI=board.GP3,
    MISO=board.GP4
)

cs = digitalio.DigitalInOut(board.GP5)
reset = digitalio.DigitalInOut(board.GP6)

radio = adafruit_rfm9x.RFM9x(
    SPI,
    cs,
    reset,
    RADIO_FREQ_MHZ
)

def receive_data():
    packet = radio.receive()
    if packet is not None:
        try:
            data_string = packet.decode("utf-8")
            print(f"{data_string},{radio.last_rssi},{radio.last_snr}")
        except UnicodeError:
            print("ERROR: Corrupted bits from radio interference!!!!!")


