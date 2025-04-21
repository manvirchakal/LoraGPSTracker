import os, sys
import time

# Add path to the LoRaRF module
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sx126x_lorawan_hat_code/python/lora'))
from LoRaRF import SX126x

# Pin definitions for Waveshare SX1262 LoRaWAN/GNSS HAT
busId = 0       # SPI bus 0
csId = 0        # CS 0
resetPin = 18   # Reset pin (GPIO 18)
busyPin = 20    # Busy pin (GPIO 20)
irqPin = 16     # IRQ pin (GPIO 16)
txenPin = 6     # TXEN pin (GPIO 6)
rxenPin = -1    # RXEN not used

print("Initializing SX1262 LoRa module...")
LoRa = SX126x()

# Begin LoRa radio and set pins
if not LoRa.begin(busId, csId, resetPin, busyPin, irqPin, txenPin, rxenPin):
    print("Failed to initialize SX1262 LoRa module. Make sure the hardware is properly connected.")
    sys.exit(1)

# Configure DIO2 as RF switch control
print("Setting DIO2 as RF switch...")
LoRa.setDio2RfSwitch()

# Set frequency to 868 MHz (for Europe) or 915 MHz (for US)
print("Setting frequency to 868 MHz...")
LoRa.setFrequency(868000000)

# Set RX gain to power saving mode
print("Setting RX gain to power saving mode...")
LoRa.setRxGain(LoRa.RX_GAIN_POWER_SAVING)

# Configure modulation parameters
print("Setting modulation parameters:")
print("  Spreading factor = 7")
print("  Bandwidth = 125 kHz")
print("  Coding rate = 4/5")
sf = 7
bw = 125000
cr = 5  # 4/5 coding rate
LoRa.setLoRaModulation(sf, bw, cr)

# Configure packet parameters
print("Setting packet parameters:")
print("  Explicit header")
print("  Preamble length = 12")
print("  Payload length = 15")
print("  CRC enabled")
headerType = LoRa.HEADER_EXPLICIT
preambleLength = 12
payloadLength = 15
crcType = True
LoRa.setLoRaPacket(headerType, preambleLength, payloadLength, crcType)

# Set sync word for public network (0x3444)
print("Setting sync word to 0x3444 (public network)...")
LoRa.setSyncWord(0x3444)

print("\n-- SX1262 LoRa Initialization Complete --\n")

print("Testing transmit functionality...")
message = "Hello from SX1262!"
messageList = list(message)
for i in range(len(messageList)):
    messageList[i] = ord(messageList[i])

# Transmit the test message
LoRa.beginPacket()
LoRa.write(messageList, len(messageList))
LoRa.endPacket()

# Wait for transmission to complete
LoRa.wait()
print(f"Transmitted: {message}")
print(f"Transmit time: {LoRa.transmitTime():.2f} ms")
print(f"Data rate: {LoRa.dataRate():.2f} bytes/s")

print("\nSwitching to receive mode for 10 seconds...")
LoRa.request(LoRa.RX_SINGLE)

end_time = time.time() + 10
while time.time() < end_time:
    if LoRa.available():
        received = ""
        while LoRa.available():
            received += chr(LoRa.read())
        print(f"Received: {received}")
        print(f"RSSI: {LoRa.packetRssi():.2f} dBm")
        print(f"SNR: {LoRa.snr():.2f} dB")
        break
    time.sleep(0.1)

print("\nTest complete!") 