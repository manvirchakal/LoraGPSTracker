# LoRa GPS Tracker

A GPS tracking system using LoRa (Long Range) radio communication for remote tracking and monitoring. 
This implementation targets Raspberry Pi based devices and uses serial communication to interface with
GPS and LoRa hardware modules.

## Features

- Real-time GPS position tracking
- Long-range LoRa communication
- Configurable position update intervals
- Geofencing capabilities
- Waypoint tracking
- Low power consumption mode
- Encrypted communication
- Data logging

## Hardware Requirements

- Raspberry Pi (any model)
- GPS module with serial interface (UART)
- LoRa transceiver module with serial interface (UART)
- Power supply (battery for portable applications)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/username/lora-gps-tracker.git
   cd lora-gps-tracker
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the hardware connections:
   - Connect the GPS module to the Raspberry Pi's UART pins (default: `/dev/ttyAMA0`)
   - Connect the LoRa module to the Raspberry Pi's UART pins (default: `/dev/ttyAMA10`)
   - Configure the serial ports as needed in `beacon/config.py`

## Configuration

The system configuration is managed through the `beacon/config.py` file. You can customize:

- Serial port settings for GPS and LoRa modules
- LoRa radio parameters (frequency, bandwidth, spreading factor, etc.)
- Tracking parameters (update intervals, position thresholds)
- Geofencing settings
- Data logging options

Configuration can also be loaded from a JSON file at runtime using the `--config` flag.

## Usage

Start the beacon application:

```
python beacon/main.py
```

Optional command-line arguments:
- `--config <file>`: Load configuration from a JSON file
- `--debug`: Enable debug-level logging
- `--simulate-gps`: Simulate GPS data (for testing without hardware)

## System Architecture

The system consists of several modules:

- `gps.py`: Handles GPS hardware communication and data parsing
- `lora.py`: Manages LoRa radio communication
- `config.py`: Contains system configuration parameters
- `controller.py`: Coordinates GPS and LoRa modules, implements tracking logic
- `main.py`: Entry point for application, handles system signals and command-line arguments

## Message Protocol

The beacon sends several types of messages:

1. **Position**: Regular GPS position updates
2. **Heartbeat**: Periodic status messages to indicate the device is active
3. **Alert**: Notifications for events like geofence violations, low battery, etc.
4. **Status**: Detailed device status information

Messages are JSON-encoded and optionally encrypted using AES.

## Development

To extend or modify the system:

1. Fork the repository
2. Make your changes
3. Test thoroughly with your hardware setup
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [PySerial](https://github.com/pyserial/pyserial) for serial communication
- [PyCryptodome](https://github.com/Legrandin/pycryptodome) for encryption
