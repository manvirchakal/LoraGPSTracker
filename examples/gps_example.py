#!/usr/bin/env python3
"""
Simple GPS Example

This script demonstrates how to use the GPS module from the lora-gps-tracker project.
It initializes the GPS module, waits for a position fix, and then displays 
the GPS data continuously.
"""

import os
import sys
import time
import logging

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Now import can work
from beacon.gps import GPSModule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to demonstrate GPS module usage."""
    logger.info("Starting GPS example")
    
    # Initialize GPS module
    # You can override default settings from config here if needed
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
    
    logger.info("GPS module started, waiting for fix...")
    
    # Wait for a valid GPS fix (timeout after 60 seconds)
    if not gps.wait_for_fix(timeout=60.0):
        logger.warning("No GPS fix obtained within timeout")
        logger.info("Continuing anyway to show available data")
    else:
        logger.info("GPS fix obtained!")
    
    try:
        # Display GPS data every 2 seconds
        while True:
            # Get current position
            lat, lon, alt = gps.get_position()
            
            # Get other GPS data
            speed = gps.get_speed()
            course = gps.get_course()
            satellites = gps.get_satellites()
            fix_quality = gps.get_fix_quality()
            
            # Get UTC time
            utc_time = gps.get_datetime()
            
            # Display GPS data
            logger.info("GPS Data:")
            logger.info(f"  Position: {lat}, {lon}, Alt: {alt}m")
            logger.info(f"  Speed: {speed} km/h, Course: {course}°")
            logger.info(f"  Satellites: {satellites}, Fix Quality: {fix_quality}")
            logger.info(f"  UTC Time: {utc_time}")
            logger.info(f"  Has Fix: {gps.has_fix()}")
            
            # Get all GPS data as dictionary (alternative approach)
            all_data = gps.get_all_data()
            logger.info(f"  HDOP: {all_data['hdop']}")
            logger.info("-" * 40)
            
            # Wait before next update
            time.sleep(2)
            
    except KeyboardInterrupt:
        logger.info("Exiting...")
    finally:
        # Clean up
        gps.stop()
        gps.disconnect()
        logger.info("GPS module stopped and disconnected")

if __name__ == "__main__":
    main() 