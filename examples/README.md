# LoRa GPS Tracker Examples

This directory contains example scripts demonstrating how to use the LoRa GPS Tracker modules.

## Examples Overview

### simple_gps_example.py

A minimal example that demonstrates the basic usage of the GPS module. This example:
- Initializes the GPS module
- Connects to the GPS hardware
- Waits for a GPS fix (with timeout)
- Displays the GPS position and data
- Properly cleans up resources

Run with:
```
python examples/simple_gps_example.py
```

### gps_example.py

A more comprehensive example that continuously monitors GPS data. This example:
- Initializes the GPS module
- Connects to the GPS hardware
- Continuously displays GPS data (position, speed, course, etc.)
- Updates every 2 seconds
- Properly handles keyboard interrupts and cleanup

Run with:
```
python examples/gps_example.py
```

### lora_gps_example.py

A complete example showing how to integrate both GPS and LoRa modules. This example:
- Initializes both GPS and LoRa modules
- Connects to both hardware modules
- Waits for a GPS fix
- Sends GPS data via LoRa every 10 seconds
- Displays data and message transmission status
- Properly handles cleanup

Run with:
```
python examples/lora_gps_example.py
```

## Requirements

These examples require the LoRa GPS Tracker package to be properly installed or the project root to be in your Python path. The examples handle this automatically by adding the parent directory to the Python path.

## Hardware Requirements

- Raspberry Pi (tested on Raspberry Pi 4 and 5)
- GPS module connected to the configured serial port
- LoRa module (for lora_gps_example.py) connected via SPI

## Configuration

All configuration parameters are loaded from `beacon/config.py`. You may need to adjust the settings in this file to match your hardware setup, particularly:

- `GPS_PORT`: Serial port for the GPS module (default: "/dev/ttyAMA0")
- `GPS_BAUD_RATE`: Baud rate for GPS communication (default: 9600)
- LoRa SPI pins and configuration for the LoRa example 