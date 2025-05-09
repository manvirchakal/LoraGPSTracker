"""
Configuration file for LoRa GPS Tracker

This file contains all configuration parameters for the LoRa and GPS modules.
"""

import os
import logging
import json
from typing import Dict, Any

# Logging configuration
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# Create a logs directory in the project root
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)  # Create logs directory if it doesn't exist
LOG_FILE = os.path.join(LOG_DIR, "beacon.log")
USE_FILE_LOGGING = True

# Application settings
SHUTDOWN_TIMEOUT = 5  # seconds to wait during graceful shutdown

# Serial port configuration - deprecated, now using SPI for LoRa
# LORA_PORT = "/dev/ttyAMA10"  # Serial port for LoRa module - deprecated, using SPI now
# LORA_BAUD_RATE = 9600         # Baud rate for LoRa module - deprecated, using SPI now
# LORA_TIMEOUT = 1.0            # Serial timeout for LoRa module - deprecated, using SPI now

# LoRa SPI configuration
LORA_USING_SPI = True           # Set to True to use SPI instead of UART
LORA_SPI_BUS = 0                # SPI bus ID
LORA_SPI_CS = 0                 # Chip select ID (0 for /dev/spidev0.0)
LORA_RESET_PIN = 18             # Reset pin (BCM 18)
LORA_BUSY_PIN = 20              # Busy pin (BCM 20)
LORA_DIO1_PIN = 16              # DIO1 pin (BCM 16)
LORA_IRQ_PIN = LORA_DIO1_PIN    # Alias for IRQ pin 
LORA_TXEN_PIN = 6               # TX enable pin (BCM 6)
LORA_RXEN_PIN = -1              # RX enable pin (not used with SX126X)
LORA_SPI_SPEED = 1000000        # Reduced SPI speed to 1 MHz for better stability
LORA_USE_POLLING = True         # Use polling instead of interrupts for Pi Zero 2 W

# GPS configuration for SX1262 HAT
GPS_ENABLE_PIN = 17             # GPIO pin to enable GPS on SX1262 HAT
GPS_PORT = "/dev/ttyAMA0"       # Serial port for GPS module
GPS_BAUD_RATE = 9600           # Baud rate for GPS module
GPS_TIMEOUT = 1.0              # Serial timeout for GPS module
GPS_UPDATE_INTERVAL = 1.0      # How often to update GPS status (seconds)
GPS_MIN_SATELLITES = 3         # Minimum satellites for a valid fix
GPS_MIN_HDOP = 5.0             # Maximum HDOP value for a valid fix
GPS_REQUIRE_3D_FIX = False     # Whether to require a 3D fix

# LoRa configuration
LORA_FREQ = 868.0  # MHz
LORA_BW = 125.0  # kHz
LORA_SF = 7  # Spreading factor
LORA_CR = 5  # Coding rate (5 means 4/5)
LORA_PREAMBLE = 8
LORA_SYNC_WORD = 0x12
LORA_POWER = 20  # dBm (max 20)
LORA_CURRENT_LIMIT = 100  # mA
LORA_CRC = True
LORA_USE_POLLING = True  # Use polling instead of interrupts for Pi Zero 2 W

# LoRa message configuration
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
LORA_ENCRYPTION_KEY = "0123456789ABCDEF"  # 16-byte AES key (change for production)
LORA_MESSAGE_QUEUE_SIZE = 20
LORA_TX_INTERVAL = 100      # milliseconds between transmissions
LORA_ACK_TIMEOUT = 5.0      # seconds to wait for an acknowledgment
LORA_RETRIES = 3            # number of retries for failed transmissions

# IDs
TRACKER_ID = os.environ.get("TRACKER_ID", "TRACKER01")  # Unique ID for this tracker
SERVER_ID = "SERVER"        # ID of the server that receives messages

# LoRa message settings
MESSAGE_RETRY_COUNT = 3
MESSAGE_RETRY_DELAY = 2  # seconds
MESSAGE_QUEUE_SIZE = 20
MESSAGE_TTL = 60  # Time-to-live in seconds for messages in queue
ACK_TIMEOUT = 5  # seconds to wait for acknowledgement

# GPS configuration
GPS_SERIAL_PORT = "/dev/ttyS0"
GPS_BAUD_RATE = 9600
GPS_TIMEOUT = 1.0  # seconds
GPS_UPDATE_RATE = 1  # Hz
GPS_FIX_TIMEOUT = 60  # seconds to wait for initial GPS fix

# Tracker settings
LOCATION_UPDATE_INTERVAL = 60  # seconds between location updates
HEARTBEAT_INTERVAL = 300  # seconds between heartbeat messages
POSITION_HISTORY_SIZE = 24  # Number of positions to keep in history
LOW_BATTERY_THRESHOLD = 20  # percentage
CRITICAL_BATTERY_THRESHOLD = 10  # percentage
POWER_SAVE_MODE = True
SLEEP_BETWEEN_UPDATES = True  # Sleep between location updates to save power

# Network settings
SERVER_ADDRESS = "0"  # LoRa server address (0 is broadcast)
GATEWAY_ADDRESS = "1"  # LoRa gateway address

# Notification thresholds
GEOFENCE_RADIUS = 100                # Geofence radius in meters
GEOFENCE_CENTER = (0.0, 0.0)         # Geofence center (latitude, longitude)
SPEED_ALERT_THRESHOLD = 100          # Speed alert threshold (km/h)

# Debug settings
DEBUG_MODE = True                    # Enable debug mode
SIMULATE_GPS = False                 # Simulate GPS data
SIMULATE_LOCATION = (51.5074, -0.1278)  # London coordinates for simulation

def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Dict containing configuration values
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        # Update global variables with values from the config file
        for key, value in config.items():
            if key in globals():
                globals()[key] = value
                
        return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return {}
