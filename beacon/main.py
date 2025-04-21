#!/usr/bin/env python3
"""
LoRa GPS Tracker Beacon

This module serves as the main application for the LoRa GPS Tracker Beacon.
It handles GPS data acquisition, LoRa communication, and power management.
"""

import os
import signal
import time
import threading
import logging
import json
from typing import Dict, Any, Optional

from beacon.config import (
    LOG_LEVEL, LOG_FORMAT, LOG_FILE, USE_FILE_LOGGING,
    LOCATION_UPDATE_INTERVAL, HEARTBEAT_INTERVAL,
    LOW_BATTERY_THRESHOLD, POSITION_HISTORY_SIZE,
    SHUTDOWN_TIMEOUT
)
from beacon.gps import GPSModule
from beacon.lora import LoRaModule
from beacon.power import PowerModule

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)

logger = logging.getLogger(__name__)

# Add file handler if enabled
if USE_FILE_LOGGING and LOG_FILE:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(file_handler)

# Global variables
running = True
position_history = []
lora_module = None
gps_module = None
power_module = None
last_location_update = 0
last_heartbeat = 0

def init_modules() -> bool:
    """
    Initialize all hardware modules.
    
    Returns:
        bool: True if all modules initialized successfully, False otherwise
    """
    global lora_module, gps_module, power_module
    
    logger.info("Initializing hardware modules...")
    
    # Initialize LoRa module
    logger.info("Initializing LoRa module...")
    lora_module = LoRaModule()
    if not lora_module.connect():
        logger.error("Failed to initialize LoRa module")
        return False
    
    # Initialize GPS module
    logger.info("Initializing GPS module...")
    gps_module = GPSModule()
    if not gps_module.connect():
        logger.error("Failed to initialize GPS module")
        return False
    
    # Initialize power management module
    logger.info("Initializing power management...")
    power_module = PowerModule()
    if not power_module.connect():
        logger.error("Failed to initialize power management")
        return False
    
    # Start the LoRa communication threads
    if not lora_module.start():
        logger.error("Failed to start LoRa communication")
        return False
    
    # Register message handlers
    lora_module.register_callback("command", handle_command_message)
    
    logger.info("All hardware modules initialized successfully")
    return True

def shutdown_modules() -> None:
    """Shutdown all hardware modules gracefully."""
    logger.info("Shutting down hardware modules...")
    
    if lora_module:
        lora_module.stop()
        lora_module.disconnect()
        
    if gps_module:
        gps_module.disconnect()
        
    if power_module:
        power_module.disconnect()
        
    logger.info("All hardware modules shut down")

def handle_command_message(message: Dict[str, Any]) -> None:
    """
    Handle incoming command messages from the server.
    
    Args:
        message: Command message data
    """
    try:
        command = message.get("data", {}).get("command")
        params = message.get("data", {}).get("params", {})
        
        logger.info(f"Received command: {command}")
        
        if command == "get_location":
            # Send immediate location update
            send_location_update()
            
        elif command == "set_update_interval":
            # Update the location update interval
            new_interval = params.get("interval")
            if new_interval:
                global LOCATION_UPDATE_INTERVAL
                LOCATION_UPDATE_INTERVAL = new_interval
                logger.info(f"Location update interval set to {new_interval} seconds")
                
        elif command == "reboot":
            # Reboot the device
            logger.info("Rebooting device...")
            shutdown_modules()
            os.system("sudo reboot")
            
        elif command == "power_off":
            # Power off the device
            logger.info("Powering off device...")
            shutdown_modules()
            os.system("sudo poweroff")
            
        else:
            logger.warning(f"Unknown command: {command}")
            
    except Exception as e:
        logger.error(f"Error handling command message: {e}")

def send_location_update() -> bool:
    """
    Send the current location to the server.
    
    Returns:
        bool: True if successfully sent, False otherwise
    """
    try:
        if not gps_module:
            logger.error("GPS module not initialized")
            return False
            
        # Get current location
        location = gps_module.get_location()
        if not location:
            logger.warning("No GPS fix available for location update")
            return False
            
        # Add to history
        global position_history
        position_history.append(location)
        
        # Trim history to max size
        while len(position_history) > POSITION_HISTORY_SIZE:
            position_history.pop(0)
            
        # Prepare message data
        message_data = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "altitude": location["altitude"],
            "speed": location["speed"],
            "course": location["course"],
            "satellites": location["satellites"],
            "fix_quality": location["fix_quality"],
            "hdop": location["hdop"],
            "timestamp": location["timestamp"]
        }
        
        # Send via LoRa
        message_id = lora_module.send_message(
            message_type="position",
            data=message_data,
            require_ack=True
        )
        
        if not message_id:
            logger.error("Failed to send location update")
            return False
            
        # Wait for acknowledgment
        ack_received = lora_module.wait_for_ack(message_id)
        if ack_received:
            logger.info("Location update acknowledged")
        else:
            logger.warning("Location update not acknowledged")
            
        return ack_received
        
    except Exception as e:
        logger.error(f"Error sending location update: {e}")
        return False

def send_heartbeat() -> bool:
    """
    Send a heartbeat message to the server.
    
    Returns:
        bool: True if successfully sent, False otherwise
    """
    try:
        # Get battery status
        battery = power_module.get_battery_status() if power_module else {"level": 0, "voltage": 0, "charging": False}
        
        # Get LoRa stats
        lora_stats = lora_module.get_stats() if lora_module else {}
        
        # Get system uptime
        uptime = time.time()  # This is time since start, not true system uptime
        
        # Prepare message data
        message_data = {
            "battery": battery,
            "uptime": uptime,
            "lora_stats": {
                "tx_packets": lora_stats.get("tx_packets", 0),
                "rx_packets": lora_stats.get("rx_packets", 0),
                "tx_errors": lora_stats.get("tx_errors", 0),
                "rx_errors": lora_stats.get("rx_errors", 0),
                "last_rssi": lora_stats.get("last_rssi", 0),
                "last_snr": lora_stats.get("last_snr", 0)
            },
            "has_gps_fix": gps_module.has_fix() if gps_module else False
        }
        
        # Send via LoRa
        message_id = lora_module.send_message(
            message_type="heartbeat",
            data=message_data,
            require_ack=False  # Heartbeats don't need acknowledgment
        )
        
        if not message_id:
            logger.error("Failed to send heartbeat")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error sending heartbeat: {e}")
        return False

def check_battery() -> None:
    """Check battery level and take appropriate action if low."""
    try:
        if not power_module:
            return
            
        battery = power_module.get_battery_status()
        
        # If battery level is below threshold and not charging
        if (battery["level"] < LOW_BATTERY_THRESHOLD and 
            not battery["charging"]):
            
            logger.warning(f"Low battery ({battery['level']}%), sending alert")
            
            # Send alert message
            lora_module.send_message(
                message_type="alert",
                data={
                    "type": "low_battery",
                    "level": battery["level"],
                    "voltage": battery["voltage"]
                }
            )
            
            # If extremely low, initiate shutdown
            if battery["level"] < 5:
                logger.critical("Critical battery level, shutting down")
                
                # Send final alert
                lora_module.send_message(
                    message_type="alert",
                    data={
                        "type": "shutdown",
                        "reason": "critical_battery"
                    }
                )
                
                # Initiate shutdown
                shutdown_gracefully()
                
    except Exception as e:
        logger.error(f"Error checking battery: {e}")

def signal_handler(sig, frame) -> None:
    """Handle signals for graceful shutdown."""
    logger.info(f"Received signal {sig}, shutting down")
    shutdown_gracefully()

def shutdown_gracefully() -> None:
    """Perform a graceful shutdown."""
    global running
    running = False
    
    # Allow some time for threads to complete
    logger.info(f"Waiting up to {SHUTDOWN_TIMEOUT} seconds for graceful shutdown")
    time.sleep(SHUTDOWN_TIMEOUT)
    
    # Shutdown modules
    shutdown_modules()

def main() -> None:
    """Main application entry point."""
    global running, last_location_update, last_heartbeat
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("LoRa GPS Tracker Beacon starting...")
    
    # Initialize hardware modules
    if not init_modules():
        logger.critical("Failed to initialize hardware, exiting")
        return
    
    # Send initial heartbeat
    send_heartbeat()
    last_heartbeat = time.time()
    
    # Main loop
    logger.info("Entering main loop")
    try:
        while running:
            # Check if it's time for a location update
            current_time = time.time()
            
            if current_time - last_location_update >= LOCATION_UPDATE_INTERVAL:
                logger.debug("Sending scheduled location update")
                if send_location_update():
                    last_location_update = current_time
                
            # Check if it's time for a heartbeat
            if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
                logger.debug("Sending scheduled heartbeat")
                if send_heartbeat():
                    last_heartbeat = current_time
                
            # Check battery status
            check_battery()
            
            # Sleep to avoid busy-waiting
            time.sleep(1)
            
    except Exception as e:
        logger.critical(f"Unhandled exception in main loop: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        
    finally:
        # Ensure proper shutdown
        shutdown_modules()
        logger.info("LoRa GPS Tracker Beacon shutdown complete")

if __name__ == "__main__":
    main()
