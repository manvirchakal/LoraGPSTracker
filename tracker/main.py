#!/usr/bin/env python3
"""
LoRa GPS Tracker: Receiver Component

This is the main module for the receiver component of the LoRa GPS tracker.
It integrates all the components to receive and display tracking information.
"""

import os
import sys
import time
import logging
import signal
import json
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tracker.config import (
    APP_NAME, SHUTDOWN_TIMEOUT, LOCATION_LOG_FILE, DATA_DIR,
    GPS_ENABLED, DISPLAY_ENABLED, DEBUG_MODE, SIMULATE_BEACON
)
from tracker.lora import LoRaReceiver
from tracker.display import DisplayHandler
from tracker.navigation import NavigationCalculator

if GPS_ENABLED:
    from tracker.gps import GPSReceiver

from shared.utils import (
    setup_logging, calculate_distance, calculate_bearing, 
    format_coordinates, get_timestamp_str, save_location_to_file
)
from shared.packet_parser import PacketParser

# Set up logging
logger = setup_logging("tracker", level=logging.DEBUG if DEBUG_MODE else logging.INFO)

class TrackerController:
    """
    Main controller for the LoRa GPS Tracker (receiver).
    
    This class integrates all the components and manages the main program flow.
    """
    
    def __init__(self):
        """Initialize the tracker controller."""
        logger.info(f"{APP_NAME} starting...")
        
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Components
        self.lora_receiver = LoRaReceiver()
        self.display = DisplayHandler() if DISPLAY_ENABLED else None
        self.navigation = NavigationCalculator()
        self.gps = GPSReceiver() if GPS_ENABLED else None
        
        # State
        self.running = True
        self.last_beacon_update = 0
        self.location_log = None
        
        # Initialize location log file
        self._init_location_log()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _init_location_log(self) -> None:
        """Initialize the location log file."""
        try:
            # Create log file if it doesn't exist
            if not os.path.exists(LOCATION_LOG_FILE):
                with open(LOCATION_LOG_FILE, 'w') as f:
                    f.write("timestamp,latitude,longitude,altitude,satellites,hdop,speed,course,distance,bearing,rssi,snr\n")
                    
            # Open log file for appending
            self.location_log = open(LOCATION_LOG_FILE, 'a')
            logger.info(f"Location log initialized at {LOCATION_LOG_FILE}")
            
        except Exception as e:
            logger.error(f"Failed to initialize location log: {e}")
            self.location_log = None
            
    def _log_location(self, data: Dict[str, Any]) -> None:
        """
        Log location data to the CSV file.
        
        Args:
            data: Location data dictionary
        """
        if not self.location_log:
            return
            
        try:
            # Extract required fields (use empty string for missing values)
            timestamp = data.get('ts', int(time.time()))
            latitude = data.get('lat', '')
            longitude = data.get('lon', '')
            altitude = data.get('alt', '')
            satellites = data.get('sat', '')
            hdop = data.get('hdop', '')
            speed = data.get('spd', '')
            course = data.get('crs', '')
            distance = self.navigation.distance if self.navigation.distance else ''
            bearing = self.navigation.bearing if self.navigation.bearing else ''
            rssi = data.get('rssi', '')
            snr = data.get('snr', '')
            
            # Format as CSV line
            line = f"{timestamp},{latitude},{longitude},{altitude},{satellites},{hdop},"
            line += f"{speed},{course},{distance},{bearing},{rssi},{snr}\n"
            
            # Write to log file
            self.location_log.write(line)
            self.location_log.flush()  # Flush to ensure data is written immediately
            
        except Exception as e:
            logger.error(f"Failed to log location data: {e}")
            
    def _process_message(self, message: Dict[str, Any]) -> None:
        """
        Process a received LoRa message.
        
        Args:
            message: Dictionary containing the message data
        """
        logger.info(f"Received beacon message: {message}")
        
        # Extract location data
        try:
            # Basic validation
            if 'lat' not in message or 'lon' not in message:
                logger.warning("Message missing required location data")
                return
                
            # Update navigation with beacon position
            self.navigation.update_beacon_position(message['lat'], message['lon'])
            
            # Update display if available
            if self.display:
                metadata = {
                    'rssi': self.lora_receiver.stats.get('last_rssi', 0),
                    'snr': self.lora_receiver.stats.get('last_snr', 0)
                }
                self.display.update_beacon_position(
                    (message['lat'], message['lon']),
                    message.get('ts', int(time.time())),
                    metadata
                )
                
            # Log the location
            message.update({
                'rssi': self.lora_receiver.stats.get('last_rssi', 0),
                'snr': self.lora_receiver.stats.get('last_snr', 0)
            })
            self._log_location(message)
            
            # Update timestamp
            self.last_beacon_update = time.time()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
    def _simulate_beacon(self) -> None:
        """Simulate a beacon signal for testing purposes."""
        from tracker.config import SIMULATE_BEACON_LOCATION
        import random
        
        # Use simulated location with small random variations
        lat = SIMULATE_BEACON_LOCATION[0] + random.uniform(-0.0001, 0.0001)
        lon = SIMULATE_BEACON_LOCATION[1] + random.uniform(-0.0001, 0.0001)
        
        # Create simulated message
        message = {
            'lat': lat,
            'lon': lon,
            'alt': 100 + random.uniform(-5, 5),
            'sat': 8,
            'hdop': 1.2,
            'ts': int(time.time()),
            'spd': random.uniform(0, 5),
            'crs': random.uniform(0, 359)
        }
        
        # Process the simulated message
        self._process_message(message)
        
        # Simulate signal strength
        self.lora_receiver.stats['last_rssi'] = -65 + random.uniform(-10, 10)
        self.lora_receiver.stats['last_snr'] = 9 + random.uniform(-2, 2)
        
    def _signal_handler(self, sig, frame) -> None:
        """
        Handle termination signals.
        
        Args:
            sig: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {sig}, shutting down")
        self.running = False
        
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            bool: True if successfully initialized, False otherwise.
        """
        logger.info("Initializing components...")
        
        # Initialize LoRa receiver
        if not SIMULATE_BEACON:
            if not self.lora_receiver.connect():
                logger.error("Failed to connect to LoRa module")
                return False
                
            if not self.lora_receiver.start():
                logger.error("Failed to start LoRa receiver")
                self.lora_receiver.disconnect()
                return False
                
            logger.info("LoRa receiver initialized")
        else:
            logger.info("Beacon simulation mode enabled, skipping LoRa initialization")
        
        # Initialize GPS if enabled
        if self.gps:
            if not self.gps.connect():
                logger.warning("Failed to connect to GPS module, continuing without GPS")
            else:
                if not self.gps.start():
                    logger.warning("Failed to start GPS receiver")
                    self.gps.disconnect()
                else:
                    logger.info("GPS receiver initialized")
        
        # Initialize display if enabled
        if self.display:
            if not self.display.start():
                logger.warning("Failed to start display, continuing without display")
            else:
                logger.info("Display initialized")
                
        logger.info("Initialization complete")
        return True
        
    def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info(f"Shutting down {APP_NAME}...")
        
        # Close location log
        if self.location_log:
            try:
                self.location_log.close()
            except Exception:
                pass
                
        # Shut down components
        if self.display:
            self.display.stop()
            
        if self.gps:
            self.gps.stop()
            self.gps.disconnect()
            
        if not SIMULATE_BEACON:
            self.lora_receiver.stop()
            self.lora_receiver.disconnect()
            
        logger.info(f"{APP_NAME} shutdown complete")
        
    def run(self) -> None:
        """Main program loop."""
        if not self.initialize():
            logger.error("Initialization failed, exiting")
            return
            
        logger.info("Starting main loop")
        
        try:
            while self.running:
                # Process LoRa messages
                if not SIMULATE_BEACON:
                    message = self.lora_receiver.get_message(timeout=0.1)
                    if message:
                        self._process_message(message)
                else:
                    # In simulation mode, generate a beacon signal every 5 seconds
                    if time.time() - self.last_beacon_update >= 5:
                        self._simulate_beacon()
                        
                # Update tracker position from GPS if available
                if self.gps and self.gps.has_fix():
                    position = self.gps.get_position()
                    if position:
                        self.navigation.update_tracker_position(*position)
                        
                        # Update display with tracker position
                        if self.display:
                            self.display.update_tracker_position(position)
                            
                # Small delay to prevent CPU hogging
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        finally:
            # Ensure clean shutdown
            self.shutdown()

def main() -> None:
    """Main entry point for the tracker."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - Receiver Component")
    parser.add_argument('--simulate', action='store_true', help='Simulate beacon signals (for testing)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Override config settings if specified
    if args.simulate:
        global SIMULATE_BEACON
        SIMULATE_BEACON = True
        
    if args.debug:
        global DEBUG_MODE
        DEBUG_MODE = True
        logger.setLevel(logging.DEBUG)
    
    # Create and run the controller
    controller = TrackerController()
    controller.run()

if __name__ == "__main__":
    main()
