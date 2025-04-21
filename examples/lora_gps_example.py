#!/usr/bin/env python3
"""
LoRa GPS Example

This script demonstrates how to use both the GPS and LoRa modules together.
It initializes both modules, waits for a GPS fix, and sends the location data via LoRa.
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

# Import the modules
from beacon.gps import GPSModule
from beacon.lora import LoRaModule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to demonstrate GPS and LoRa integration."""
    logger.info("Starting LoRa GPS Example")
    
    # Initialize modules
    gps = GPSModule()
    lora = LoRaModule()
    
    # Connect to hardware
    gps_connected = gps.connect()
    if not gps_connected:
        logger.error("Failed to connect to GPS module")
        return
    
    lora_connected = lora.connect()
    if not lora_connected:
        logger.error("Failed to connect to LoRa module")
        gps.disconnect()
        return
    
    logger.info("Connected to both GPS and LoRa modules")
    
    # Start modules
    if not gps.start():
        logger.error("Failed to start GPS module")
        gps.disconnect()
        lora.disconnect()
        return
        
    if not lora.start():
        logger.error("Failed to start LoRa module")
        gps.stop()
        gps.disconnect()
        lora.disconnect()
        return
    
    logger.info("Both modules started")
    
    try:
        # Wait for a GPS fix
        logger.info("Waiting for GPS fix (up to 60 seconds)...")
        if not gps.wait_for_fix(timeout=60.0):
            logger.warning("No GPS fix obtained within timeout")
        else:
            logger.info("GPS fix obtained!")
        
        # Send location updates every 10 seconds
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
            
            # Send location update via LoRa if we have a fix
            if gps.has_fix():
                logger.info("Sending location via LoRa...")
                
                # Prepare the message data
                message_data = {
                    "latitude": gps_data["latitude"],
                    "longitude": gps_data["longitude"],
                    "altitude": gps_data["altitude"],
                    "speed": gps_data["speed"],
                    "course": gps_data["course"],
                    "satellites": gps_data["satellites"],
                    "fix_quality": gps_data["fix_quality"],
                    "hdop": gps_data["hdop"],
                    "timestamp": datetime.now().isoformat()
                }
                
                # Send the message
                message_id = lora.send_message(
                    message_type="position",
                    data=message_data,
                    require_ack=True
                )
                
                if message_id:
                    logger.info(f"Message sent with ID: {message_id}")
                    
                    # Wait for acknowledgment
                    if lora.wait_for_ack(message_id, timeout=5.0):
                        logger.info("Message acknowledged")
                    else:
                        logger.warning("Message not acknowledged")
                else:
                    logger.error("Failed to send message")
            else:
                logger.warning("No GPS fix available, not sending location")
                
            # Wait before next update
            logger.info("Waiting 10 seconds before next update...")
            logger.info("-" * 40)
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Exiting...")
    finally:
        # Clean up
        logger.info("Shutting down modules...")
        gps.stop()
        gps.disconnect()
        lora.stop()
        lora.disconnect()
        logger.info("Modules stopped and disconnected")

if __name__ == "__main__":
    main() 