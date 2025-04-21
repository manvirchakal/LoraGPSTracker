"""
Configuration settings for the LoRa GPS Tracker

This file contains all configurable parameters for the tracker device.
For local overrides, create a config.local.py file with the specific
values you want to override.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# LoRa Configuration
LORA_SERIAL_PORT = "/dev/ttyAMA10"  # Replace with your actual serial port
LORA_BAUD_RATE = 9600
LORA_FREQ = 868.0  # MHz, adjust for your region (EU: 868, US: 915)
LORA_BANDWIDTH = 125.0  # kHz
LORA_SPREADING_FACTOR = 9  # 7-12, higher means longer range but slower
LORA_CODING_RATE = 7
LORA_SYNC_WORD = 0x34  # Private network (non-LoRaWAN)
LORA_PREAMBLE_LENGTH = 8

# LoRa module pins (for SPI mode)
LORA_CS_PIN = 8
LORA_RESET_PIN = 27
LORA_DIO1_PIN = 17
LORA_BUSY_PIN = 22

# GPS Configuration (for tracker GPS if available)
GPS_SERIAL_PORT = "/dev/ttyS0"  # Replace with your actual serial port
GPS_BAUD_RATE = 9600
GPS_TIMEOUT = 5  # seconds
GPS_ENABLED = True  # Set to False if the tracker doesn't have GPS

# Receiver Configuration
RX_TIMEOUT = 30  # seconds to wait before declaring no reception
RX_BEACON_TIMEOUT = 120  # seconds before declaring a beacon as "lost"
RX_MIN_SIGNAL_STRENGTH = -120  # dBm, minimum signal strength to consider valid

# Display Configuration
DISPLAY_ENABLED = True  # Set to False for headless operation
DISPLAY_TYPE = "HDMI"  # HDMI, LCD, OLED, etc.
DISPLAY_UPDATE_INTERVAL = 1  # seconds between display updates
DISPLAY_COORDINATES_FORMAT = "DD.DDDDDD"  # DD.DDDDDD or DD°MM'SS"

# Logging Configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = os.path.join(BASE_DIR, "logs", "tracker.log")
LOG_RETENTION = "7 days"
LOG_ROTATION = "1 day"

# Data Storage
STORAGE_DIR = os.path.join(BASE_DIR, "data")
BEACON_DATA_FILE = os.path.join(STORAGE_DIR, "beacons.json")
TRACKING_HISTORY_FILE = os.path.join(STORAGE_DIR, "tracking_history.csv")
HISTORY_MAX_ENTRIES = 10000

# Known Beacons Configuration
KNOWN_BEACONS = {
    "beacon01": {
        "name": "Primary Beacon",
        "color": "red",
        "priority": 1,
    }
}

# Load local overrides if available
try:
    from config_local import *  # noqa
except ImportError:
    pass 