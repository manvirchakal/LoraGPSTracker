"""
Configuration for the LoRa GPS Tracker (Receiver)

This file contains all configuration parameters for the receiver/tracker.
"""

import os
import logging
from typing import Dict, Any, Tuple

# Logging configuration
LOG_LEVEL = logging.INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "tracker.log")

# Application settings
APP_NAME = "LoRa GPS Tracker"
SHUTDOWN_TIMEOUT = 5  # seconds to wait during graceful shutdown

# Screen display settings
DISPLAY_ENABLED = True  # Set to False if no display is connected
DISPLAY_WIDTH = 320     # LCD width in pixels (if used)
DISPLAY_HEIGHT = 240    # LCD height in pixels (if used)
DISPLAY_UPDATE_INTERVAL = 1.0  # seconds between display updates
DISPLAY_TIMEOUT = 60    # seconds before dimming the display (0 = never)
DISPLAY_ROTATION = 0    # 0, 90, 180, or 270 degrees

# Map settings
MAP_CENTER_ON_BEACON = True  # Center map on beacon location
MAP_SCALE = 50  # meters per 100 pixels (approximate)
MAP_TRAIL_LENGTH = 10  # Number of previous beacon positions to show
MAP_SHOW_COMPASS = True  # Show compass on display

# LoRa SPI configuration
LORA_USING_SPI = True   # Set to True to use SPI instead of UART
LORA_SPI_BUS = 0        # SPI bus ID
LORA_SPI_CS = 0         # Chip select ID (0 for /dev/spidev0.0)
LORA_RESET_PIN = 18     # Reset pin (GPIO 18)
LORA_BUSY_PIN = 20      # Busy pin (GPIO 20)
LORA_DIO1_PIN = 16      # DIO1 pin (GPIO 16)
LORA_IRQ_PIN = LORA_DIO1_PIN  # Alias for IRQ pin
LORA_TXEN_PIN = 6       # TX enable pin
LORA_RXEN_PIN = -1      # RX enable pin (not used with SX126X)
LORA_SPI_SPEED = 2000000  # SPI speed in Hz (2 MHz)

# GPS configuration (if GPS is available on the receiver)
GPS_ENABLED = True      # Set to False if no GPS module is connected
GPS_PORT = "/dev/ttyAMA0"  # Serial port for GPS module
GPS_BAUD_RATE = 9600    # Baud rate for GPS module
GPS_TIMEOUT = 1.0       # Serial timeout for GPS module

# LoRa configuration
LORA_CONFIG = {
    "frequency": 868000000,  # 868 MHz
    "bandwidth": 125000,     # 125 kHz
    "spreading_factor": 7,
    "coding_rate": 5,        # 4/5
    "preamble_length": 8,
    "sync_word": 0x12,
    "power": 20,             # dBm
    "current_limit": 100,    # mA
    "crc": True
}
LORA_ENCRYPTION_KEY = "0123456789ABCDEF"  # 16-byte AES key (must match transmitter)
LORA_MESSAGE_QUEUE_SIZE = 20
LORA_RX_CONTINUOUS = True  # Continuously listen for packets

# Data storage settings
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
LOCATION_LOG_FILE = os.path.join(DATA_DIR, "location_log.csv")
LOCATION_HISTORY_SIZE = 1000  # Number of locations to keep in memory

# Alert settings
ALERT_SOUND_ENABLED = False  # Sound alerts when beacon is detected
ALERT_DISTANCE_THRESHOLD = 100  # Distance in meters to trigger proximity alert

# Debug settings
DEBUG_MODE = True  # Enable debug mode
SIMULATE_BEACON = False  # Simulate beacon data (for testing without transmitter)
# Default simulated location (for testing)
SIMULATE_BEACON_LOCATION = (51.5074, -0.1278)  # London coordinates 