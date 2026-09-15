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

def send_data(data):
    try:
        message = "{:.1f},{:.1f}".format(
            data["temperature"],
            data["pressure"]
        )
        message_bytes = message.encode("utf-8")
        radio.send(message_bytes)
    except Exception as problem:
        print(problem, "Radio transmission error")
