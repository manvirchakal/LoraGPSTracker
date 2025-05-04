"""
GPS Module for Tracker

This module handles reading the GPS data from the tracker's own GPS module (if available).
"""

import threading
import time
import logging
import os
import sys
import queue
from typing import Dict, Any, Optional, Tuple

from tracker.config import (
    GPS_ENABLED, GPS_PORT, GPS_BAUD_RATE, GPS_TIMEOUT
)

# Set up logging
logger = logging.getLogger(__name__)

class GPSReceiver:
    """
    Class for interfacing with a GPS module on the tracker.
    
    This class provides an interface to a GPS module connected via serial port.
    It's used to get the tracker's own position, which can be used to calculate
    distance and bearing to the beacon.
    """
    
    def __init__(self):
        """Initialize the GPS receiver."""
        self.enabled = GPS_ENABLED
        self.port = GPS_PORT
        self.baud_rate = GPS_BAUD_RATE
        self.timeout = GPS_TIMEOUT
        
        self.gps = None
        self.serial = None
        self.connected = False
        
        self.position = None  # (latitude, longitude)
        self.altitude = 0.0
        self.speed = 0.0
        self.course = 0.0
        self.satellites = 0
        self.fix_quality = 0
        self.hdop = 0.0
        self.last_update = 0
        
        # Thread control
        self.thread = None
        self.stop_event = threading.Event()
        
    def connect(self) -> bool:
        """
        Connect to the GPS module.
        
        Returns:
            bool: True if successfully connected, False otherwise.
        """
        if not self.enabled:
            logger.info("GPS is disabled in configuration")
            return False
            
        try:
            # Import the required modules
            import serial
            import pynmea2
            
            # Initialize the serial connection
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )
            
            self.connected = True
            logger.info(f"Connected to GPS module at {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to GPS module: {e}")
            self.connected = False
            return False
            
    def disconnect(self) -> None:
        """Disconnect from the GPS module."""
        if self.connected and self.serial:
            self.stop()
            
            try:
                self.serial.close()
            except Exception as e:
                logger.error(f"Error closing GPS serial port: {e}")
                
            self.serial = None
            self.connected = False
            logger.info("Disconnected from GPS module")
            
    def start(self) -> bool:
        """
        Start the GPS reading thread.
        
        Returns:
            bool: True if successfully started, False otherwise.
        """
        if not self.enabled or not self.connected:
            logger.error("Cannot start GPS: not enabled or not connected")
            return False
            
        if self.thread is not None and self.thread.is_alive():
            logger.warning("GPS thread already running")
            return True
            
        self.stop_event.clear()
        
        # Start GPS thread
        self.thread = threading.Thread(target=self._gps_worker, daemon=True)
        self.thread.start()
        
        logger.info("GPS thread started")
        return True
        
    def stop(self) -> None:
        """Stop the GPS reading thread."""
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=2.0)
            
        logger.info("GPS thread stopped")
        
    def get_position(self) -> Optional[Tuple[float, float]]:
        """
        Get the current GPS position.
        
        Returns:
            Tuple of (latitude, longitude), or None if no position is available
        """
        return self.position
        
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all available GPS data.
        
        Returns:
            Dictionary containing all GPS data
        """
        return {
            "latitude": self.position[0] if self.position else None,
            "longitude": self.position[1] if self.position else None,
            "altitude": self.altitude,
            "speed": self.speed,
            "course": self.course,
            "satellites": self.satellites,
            "fix_quality": self.fix_quality,
            "hdop": self.hdop,
            "timestamp": self.last_update
        }
        
    def has_fix(self) -> bool:
        """
        Check if the GPS has a valid fix.
        
        Returns:
            bool: True if a valid fix is available, False otherwise
        """
        return (self.position is not None and 
                self.fix_quality > 0 and 
                self.satellites >= 3)
        
    def _gps_worker(self) -> None:
        """
        Worker thread function for reading GPS data.
        """
        logger.info("GPS worker thread started")
        
        import pynmea2
        
        while not self.stop_event.is_set():
            try:
                if self.serial and self.serial.in_waiting > 0:
                    # Read a line from the GPS module
                    line = self.serial.readline().decode('ascii', errors='replace').strip()
                    
                    # Process the NMEA sentence
                    if line.startswith('$'):
                        try:
                            msg = pynmea2.parse(line)
                            
                            # Process different types of NMEA messages
                            if isinstance(msg, pynmea2.GGA):
                                # Global Positioning System Fix Data
                                if msg.latitude and msg.longitude:
                                    self.position = (msg.latitude, msg.longitude)
                                    self.altitude = float(msg.altitude) if msg.altitude else 0.0
                                    self.satellites = int(msg.num_sats) if msg.num_sats else 0
                                    self.fix_quality = int(msg.gps_qual) if msg.gps_qual else 0
                                    self.hdop = float(msg.horizontal_dil) if msg.horizontal_dil else 0.0
                                    self.last_update = time.time()
                                    
                            elif isinstance(msg, pynmea2.RMC):
                                # Recommended Minimum Navigation Information
                                if msg.latitude and msg.longitude:
                                    self.position = (msg.latitude, msg.longitude)
                                    self.speed = float(msg.spd_over_grnd) if msg.spd_over_grnd else 0.0
                                    self.course = float(msg.true_course) if msg.true_course else 0.0
                                    self.last_update = time.time()
                                    
                            elif isinstance(msg, pynmea2.GSA):
                                # GPS DOP and active satellites
                                self.fix_quality = int(msg.mode_fix_type) if msg.mode_fix_type else 0
                                self.hdop = float(msg.hdop) if msg.hdop else 0.0
                                
                        except pynmea2.ParseError:
                            pass  # Ignore parse errors for invalid NMEA sentences
                else:
                    # Small delay to prevent CPU hogging when no data
                    time.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Error reading GPS data: {e}")
                time.sleep(1.0)  # Pause on error to prevent log flooding
                
        logger.info("GPS worker thread stopped")
