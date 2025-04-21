#!/usr/bin/env python3
"""
GPS-Only Example for LoRa GPS Tracker

This script demonstrates how to use only the GPS module without requiring the LoRa module.
It initializes the GPS module, waits for a position fix, and displays the GPS data.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import only the GPS module
from beacon.gps import GPSModule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to demonstrate GPS functionality without LoRa."""
    logger.info("Starting GPS-Only Example")
    
    # Initialize just the GPS module
    gps = GPSModule()
    
    # Connect to GPS hardware
    if not gps.connect():
        logger.error("Failed to connect to GPS module")
        return
    
    logger.info("Connected to GPS module")
    
    # Start GPS data collection thread
    if not gps.start():
        logger.error("Failed to start GPS module")
        gps.disconnect()
        return
    
    logger.info("GPS module started successfully")
    
    try:
        # Wait for a GPS fix
        logger.info("Waiting for GPS fix (up to 60 seconds)...")
        if not gps.wait_for_fix(timeout=60.0):
            logger.warning("No GPS fix obtained within timeout")
            logger.info("Will continue to display available data")
        else:
            logger.info("GPS fix obtained!")
        
        # Display GPS data continuously every 5 seconds
        while True:
            # Get all GPS data
            gps_data = gps.get_all_data()
            
            # Display summary
            logger.info("GPS Data:")
            if gps.has_fix():
                logger.info(f"  Position: {gps_data['latitude']}, {gps_data['longitude']}, Alt: {gps_data['altitude']}m")
                logger.info(f"  Speed: {gps_data['speed']} km/h, Course: {gps_data['course']}°")
            logger.info(f"  Satellites: {gps_data['satellites']}, Fix Quality: {gps_data['fix_quality']}")
            logger.info(f"  HDOP: {gps_data['hdop']}")
            logger.info(f"  Has Fix: {gps.has_fix()}")
            
            # Wait before next update
            logger.info("Waiting 5 seconds before next update...")
            logger.info("-" * 40)
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("Exiting...")
    finally:
        # Clean up
        logger.info("Shutting down GPS module...")
        gps.stop()
        gps.disconnect()
        logger.info("GPS module stopped and disconnected")

if __name__ == "__main__":
    main() 