#!/usr/bin/env python3
"""
Minimal GPS Example

A simple script that demonstrates the basic usage of the GPS module.
"""

import os
import sys
import logging

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Now import can work
from beacon.gps import GPSModule

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Initialize the GPS module
gps = GPSModule()

# Connect to GPS hardware
if gps.connect():
    logger.info("Connected to GPS module")
    
    # Start GPS data collection
    if gps.start():
        logger.info("Waiting for GPS fix (up to 30 seconds)...")
        
        # Wait for GPS fix with a timeout of 30 seconds
        if gps.wait_for_fix(timeout=30.0):
            logger.info("GPS fix obtained!")
            
            # Get current position
            lat, lon, alt = gps.get_position()
            logger.info(f"Position: {lat:.6f}, {lon:.6f}, Altitude: {alt}m")
            
            # Get additional data
            all_data = gps.get_all_data()
            logger.info(f"Satellites: {all_data['satellites']}")
            logger.info(f"Speed: {all_data['speed']} km/h")
            logger.info(f"HDOP: {all_data['hdop']}")
        else:
            logger.info("No GPS fix obtained within timeout")
        
        # Clean up
        gps.stop()
    else:
        logger.error("Failed to start GPS module")
    
    # Disconnect from GPS hardware
    gps.disconnect()
else:
    logger.error("Failed to connect to GPS module") 