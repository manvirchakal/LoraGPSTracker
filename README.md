# LoRa GPS Tracker for Rescue Scenarios

A Raspberry Pi-based GPS tracking system for offline use in rescue scenarios using LoRa (Long Range) radio communication. The system consists of two components:

1. **Beacon (Transmitter)**: A small Raspberry Pi Zero 2 W that transmits GPS coordinates via LoRa
2. **Tracker (Receiver)**: A Raspberry Pi that receives the coordinates and displays them, optionally calculating distance and bearing

## Features

- **Offline Operation**: Functions without internet connectivity
- **Long Range**: LoRa communication for extended range (up to several km depending on conditions)
- **Real-time Tracking**: Continuous beacon position tracking
- **Distance & Bearing**: Calculates distance and bearing from tracker to beacon
- **Visual Display**: Shows beacon location and navigation information (with optional pygame display)
- **Data Logging**: Records all location data for analysis
- **Self-Location**: Optional GPS on the tracker for relative positioning
- **Low Power Consumption**: Optimized for battery operation

## Hardware Requirements

### Beacon (Transmitter)
- Raspberry Pi Zero 2 W
- SX1262 LoRaWAN + GNSS HAT
- Power source (battery)

### Tracker (Receiver)
- Raspberry Pi 3 or 4
- SX1262 LoRaWAN + GNSS HAT
- Optional display (HDMI monitor or LCD)
- Power source

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/username/lora-gps-tracker.git
   cd lora-gps-tracker
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure the GPIO pins for the LoRa module:
   - The default configuration uses:
     - Reset pin: GPIO 18
     - Busy pin: GPIO 20
     - IRQ pin: GPIO 16
     - TX enable pin: GPIO 6

## Project Structure

```
lora-gps-tracker/
├── beacon/                # Transmitter component
│   ├── config.py          # Configuration settings
│   ├── gps.py             # GPS reader module
│   ├── lora.py            # LoRa transmitter
│   └── main.py            # Main program for beacon
├── tracker/               # Receiver component
│   ├── config.py          # Configuration settings
│   ├── display.py         # Display handler
│   ├── gps.py             # GPS reader (if available)
│   ├── lora.py            # LoRa receiver
│   ├── navigation.py      # Distance/bearing calculator
│   └── main.py            # Main program for tracker
├── shared/                # Shared components
│   ├── packet_parser.py   # LoRa packet formatting/parsing
│   └── utils.py           # Common utilities
├── data/                  # Data storage directory
├── logs/                  # Log files directory
└── requirements.txt       # Python dependencies
```

## Configuration

Both components are configured through their respective `config.py` files:

- `beacon/config.py`: Configuration for the transmitter
- `tracker/config.py`: Configuration for the receiver

Key configuration parameters:

- **LoRa settings**: Frequency, bandwidth, spreading factor, etc.
- **GPS settings**: Serial port, baud rate, update interval
- **Display settings**: Resolution, update interval, map scale
- **Logging settings**: Log levels, file paths

## Usage

### Running the Beacon (Transmitter)

```
python beacon/main.py
```

The beacon will:
1. Initialize the GPS module
2. Wait for a GPS fix
3. Begin transmitting coordinates via LoRa at regular intervals

### Running the Tracker (Receiver)

```
python tracker/main.py
```

Optional arguments:
- `--simulate`: Simulate beacon signals for testing without actual beacon hardware
- `--debug`: Enable debug-level logging

The tracker will:
1. Initialize the LoRa receiver and listen for beacon transmissions
2. If enabled, initialize its own GPS module for self-location
3. Display the beacon's position and navigation information
4. Log all received location data

## Development

### Adding New Features

To extend the system:

1. For beacon enhancements (transmitter):
   - Modify the relevant modules in the `beacon/` directory
   - Update the `beacon/main.py` to integrate the new functionality

2. For tracker enhancements (receiver):
   - Modify the relevant modules in the `tracker/` directory
   - Update the `tracker/main.py` to integrate the new functionality

3. For shared functionality:
   - Add or modify modules in the `shared/` directory

### Dependencies

The project depends on several libraries:
- `pyserial`: For GPS communication
- `pynmea2`: For GPS data parsing
- `pycryptodome`: For LoRa message encryption
- `pygame` (optional): For graphical display

## Troubleshooting

### Common Issues

1. **No GPS Fix**:
   - Make sure the GPS module has a clear view of the sky
   - Wait several minutes for the module to acquire satellites
   - Check the GPS serial connection and configuration

2. **LoRa Communication Issues**:
   - Verify the LoRa module pins are correctly configured
   - Ensure both devices use the same frequency, spreading factor, etc.
   - Check that the encryption keys match on both devices

3. **Display Problems**:
   - If using pygame, ensure it's properly installed
   - For console-only operation, set `DISPLAY_ENABLED = False` in `tracker/config.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [SX126x Python Library](https://github.com/YOUR-USERNAME/sx126x_lorawan_hat_code) for LoRa communication
- [PySerial](https://github.com/pyserial/pyserial) for serial communication
- [PyCryptodome](https://github.com/Legrandin/pycryptodome) for encryption
- [Pygame](https://www.pygame.org/) for graphical display
