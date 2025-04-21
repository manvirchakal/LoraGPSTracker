"""
Beacon Controller Module

This module provides the main controller for the LoRa GPS Tracker beacon,
coordinating the GPS and LoRa modules and implementing the tracking logic.
"""

import time
import threading
import logging
import json
import os
from typing import Dict, Any, Optional, Tuple, List

from beacon.config import (
    TRACKER_ID, SERVER_ID, POSITION_UPDATE_INTERVAL, 
    HEARTBEAT_INTERVAL, POSITION_CHANGE_THRESHOLD,
    GEOFENCE_RADIUS, GEOFENCE_CENTER, LOW_POWER_MODE,
    LOW_BATTERY_THRESHOLD, DATA_LOGGING, LOG_DIRECTORY,
    DEBUG_MODE
)
from beacon.gps import GPSModule
from beacon.lora import LoRaModule

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIRECTORY, 'beacon.log'))
    ]
)
logger = logging.getLogger(__name__)

class BeaconController:
    """
    Main controller for the LoRa GPS Tracker beacon.
    
    This class coordinates between the GPS and LoRa modules, implements
    the tracking logic, and handles device state and communication.
    """
    
    def __init__(self):
        """Initialize the beacon controller."""
        self.gps = GPSModule()
        self.lora = LoRaModule()
        
        # Make sure log directory exists
        os.makedirs(LOG_DIRECTORY, exist_ok=True)
        
        # State variables
        self.running = False
        self.last_position: Optional[Tuple[float, float]] = None
        self.last_position_time = 0
        self.last_heartbeat_time = 0
        self.battery_level = 100  # Mock battery level, replace with actual sensor reading
        self.inside_geofence = None  # None means unknown, True/False once determined
        self.waypoints: List[Dict[str, Any]] = []
        self.waypoint_radius = 100  # Default radius in meters
        
        # Command handlers
        self.command_handlers = {
            "set_config": self._handle_set_config,
            "request_position": self._handle_request_position,
            "add_waypoint": self._handle_add_waypoint,
            "clear_waypoints": self._handle_clear_waypoints,
            "reboot": self._handle_reboot,
            "power_save": self._handle_power_save,
        }
        
        # Control threads
        self.main_thread = None
        self.stop_event = threading.Event()
        
        # Data logging
        self.data_log_file = None
        if DATA_LOGGING:
            self._setup_data_logging()
            
        logger.info(f"Beacon controller initialized with ID: {TRACKER_ID}")
        
    def start(self) -> bool:
        """
        Start the beacon controller and all modules.
        
        Returns:
            bool: True if successfully started, False otherwise
        """
        logger.info("Starting beacon controller...")
        
        # Connect to GPS module
        if not self.gps.connect():
            logger.error("Failed to connect to GPS module")
            return False
            
        # Connect to LoRa module
        if not self.lora.connect():
            logger.error("Failed to connect to LoRa module")
            self.gps.disconnect()
            return False
            
        # Start GPS module
        if not self.gps.start():
            logger.error("Failed to start GPS module")
            self.gps.disconnect()
            self.lora.disconnect()
            return False
            
        # Start LoRa module and register command callback
        if not self.lora.start():
            logger.error("Failed to start LoRa module")
            self.gps.stop()
            self.gps.disconnect()
            self.lora.disconnect()
            return False
            
        # Register message handlers
        self.lora.register_callback("command", self._handle_command_message)
        
        # Start main controller thread
        self.stop_event.clear()
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        
        self.running = True
        logger.info("Beacon controller started successfully")
        
        # Send initial status message
        self._send_status_message()
        
        return True
        
    def stop(self) -> None:
        """Stop the beacon controller and all modules."""
        if not self.running:
            return
            
        logger.info("Stopping beacon controller...")
        
        # Signal threads to stop
        self.stop_event.set()
        
        # Wait for main thread to stop
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5.0)
            
        # Stop modules
        self.gps.stop()
        self.lora.stop()
        
        # Disconnect modules
        self.gps.disconnect()
        self.lora.disconnect()
        
        # Close data log if open
        if self.data_log_file:
            self.data_log_file.close()
            self.data_log_file = None
            
        self.running = False
        logger.info("Beacon controller stopped")
        
    def _main_loop(self) -> None:
        """Main control loop for beacon operation."""
        logger.info("Main controller loop started")
        
        while not self.stop_event.is_set():
            try:
                # Check if we have a GPS fix
                if self.gps.has_fix():
                    # Get current position
                    lat, lon = self.gps.get_position()
                    altitude = self.gps.get_altitude()
                    speed = self.gps.get_speed()
                    course = self.gps.get_course()
                    fix_quality = self.gps.get_fix_quality()
                    satellites = self.gps.get_satellites()
                    
                    current_position = (lat, lon)
                    current_time = time.time()
                    
                    # Log data point if enabled
                    if DATA_LOGGING and self.data_log_file:
                        self._log_data_point(lat, lon, altitude, speed, course, satellites)
                    
                    # Check if position has changed significantly or it's time for an update
                    position_changed = False
                    if self.last_position:
                        distance = self.gps.calculate_distance(
                            self.last_position[0], self.last_position[1], 
                            current_position[0], current_position[1]
                        )
                        position_changed = distance > POSITION_CHANGE_THRESHOLD
                    
                    time_for_update = (
                        self.last_position_time == 0 or 
                        (current_time - self.last_position_time) >= POSITION_UPDATE_INTERVAL
                    )
                    
                    # Send position update if needed
                    if position_changed or time_for_update:
                        self._send_position_message(
                            lat, lon, altitude, speed, course, 
                            fix_quality, satellites
                        )
                        self.last_position = current_position
                        self.last_position_time = current_time
                    
                    # Check geofence if configured
                    if GEOFENCE_RADIUS > 0 and GEOFENCE_CENTER != (0.0, 0.0):
                        inside_geofence = self._check_geofence(lat, lon)
                        # If geofence status changed, send alert
                        if self.inside_geofence is not None and inside_geofence != self.inside_geofence:
                            self._send_geofence_alert(inside_geofence, lat, lon)
                        self.inside_geofence = inside_geofence
                    
                    # Check waypoints
                    self._check_waypoints(lat, lon)
                
                # Send heartbeat if needed
                current_time = time.time()
                if (current_time - self.last_heartbeat_time) >= HEARTBEAT_INTERVAL:
                    self._send_heartbeat()
                    self.last_heartbeat_time = current_time
                
                # Check battery level (mock implementation, replace with actual sensor)
                self._update_battery_level()
                if self.battery_level <= LOW_BATTERY_THRESHOLD:
                    self._send_low_battery_alert()
                
                # Sleep to conserve power
                sleep_time = 1.0
                if LOW_POWER_MODE and not self.gps.has_fix():
                    sleep_time = 5.0  # Longer sleep when no GPS fix
                
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5.0)  # Longer sleep on error
        
        logger.info("Main controller loop stopped")
    
    def _send_position_message(self, lat: float, lon: float, altitude: float, 
                              speed: float, course: float, fix_quality: int, 
                              satellites: int) -> None:
        """
        Send a position update message.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            altitude: Altitude in meters
            speed: Speed in km/h
            course: Course in degrees
            fix_quality: GPS fix quality
            satellites: Number of satellites used for fix
        """
        data = {
            "lat": lat,
            "lon": lon,
            "alt": altitude,
            "spd": speed,
            "crs": course,
            "fix": fix_quality,
            "sat": satellites,
            "bat": self.battery_level
        }
        
        message_id = self.lora.send_message("position", data)
        logger.debug(f"Position update sent: {lat}, {lon} (ID: {message_id})")
    
    def _send_heartbeat(self) -> None:
        """Send a heartbeat message with basic status information."""
        has_fix = self.gps.has_fix()
        
        data = {
            "bat": self.battery_level,
            "fix": has_fix,
            "mode": "low_power" if LOW_POWER_MODE else "normal"
        }
        
        if has_fix:
            lat, lon = self.gps.get_position()
            data["lat"] = lat
            data["lon"] = lon
        
        message_id = self.lora.send_message("heartbeat", data, require_ack=False)
        logger.debug(f"Heartbeat sent (ID: {message_id})")
    
    def _send_status_message(self) -> None:
        """Send a detailed status message."""
        gps_status = "active" if self.gps.is_active else "inactive"
        if self.gps.is_active:
            gps_status = "fixed" if self.gps.has_fix() else "no_fix"
            
        data = {
            "id": TRACKER_ID,
            "gps": gps_status,
            "bat": self.battery_level,
            "mode": "low_power" if LOW_POWER_MODE else "normal",
            "uptime": int(time.time()),  # Simplified, not real uptime
            "lora_stats": self.lora.get_stats()
        }
        
        message_id = self.lora.send_message("status", data)
        logger.info(f"Status message sent (ID: {message_id})")
    
    def _send_geofence_alert(self, inside: bool, lat: float, lon: float) -> None:
        """
        Send a geofence alert when crossing the boundary.
        
        Args:
            inside: True if entering geofence, False if exiting
            lat: Current latitude
            lon: Current longitude
        """
        data = {
            "alert": "geofence",
            "status": "enter" if inside else "exit",
            "lat": lat,
            "lon": lon,
            "fence_id": "main"  # Support for multiple geofences could be added
        }
        
        message_id = self.lora.send_message("alert", data)
        logger.info(f"Geofence {'entry' if inside else 'exit'} alert sent (ID: {message_id})")
    
    def _send_low_battery_alert(self) -> None:
        """Send a low battery alert."""
        data = {
            "alert": "battery",
            "level": self.battery_level
        }
        
        message_id = self.lora.send_message("alert", data)
        logger.warning(f"Low battery alert sent: {self.battery_level}% (ID: {message_id})")
    
    def _check_geofence(self, lat: float, lon: float) -> bool:
        """
        Check if position is inside the configured geofence.
        
        Args:
            lat: Current latitude
            lon: Current longitude
            
        Returns:
            bool: True if inside geofence, False otherwise
        """
        distance = self.gps.calculate_distance(
            GEOFENCE_CENTER[0], GEOFENCE_CENTER[1], lat, lon
        )
        
        return distance <= GEOFENCE_RADIUS
    
    def _check_waypoints(self, lat: float, lon: float) -> None:
        """
        Check if position is near any waypoints and handle accordingly.
        
        Args:
            lat: Current latitude
            lon: Current longitude
        """
        for waypoint in self.waypoints:
            wp_lat = waypoint.get("lat", 0)
            wp_lon = waypoint.get("lon", 0)
            wp_radius = waypoint.get("radius", self.waypoint_radius)
            wp_id = waypoint.get("id", "unknown")
            
            # Skip if already visited
            if waypoint.get("visited", False):
                continue
                
            distance = self.gps.calculate_distance(wp_lat, wp_lon, lat, lon)
            
            if distance <= wp_radius:
                # Mark as visited
                waypoint["visited"] = True
                waypoint["visited_time"] = time.time()
                
                # Send waypoint reached alert
                data = {
                    "alert": "waypoint",
                    "wp_id": wp_id,
                    "lat": lat,
                    "lon": lon,
                    "distance": distance
                }
                
                message_id = self.lora.send_message("alert", data)
                logger.info(f"Waypoint {wp_id} reached (ID: {message_id})")
    
    def _update_battery_level(self) -> None:
        """
        Update battery level from sensor.
        
        This is a mock implementation - replace with actual battery sensor reading.
        """
        # Mock battery discharge at 0.01% per cycle (very slow for testing)
        self.battery_level = max(0, self.battery_level - 0.01)
    
    def _setup_data_logging(self) -> None:
        """Set up data logging to file."""
        try:
            log_filename = os.path.join(
                LOG_DIRECTORY, 
                f"tracker_data_{TRACKER_ID}_{int(time.time())}.csv"
            )
            
            self.data_log_file = open(log_filename, 'w')
            # Write CSV header
            self.data_log_file.write(
                "timestamp,latitude,longitude,altitude,speed,course,satellites\n"
            )
            self.data_log_file.flush()
            
            logger.info(f"Data logging enabled to {log_filename}")
        except Exception as e:
            logger.error(f"Failed to set up data logging: {e}")
            self.data_log_file = None
    
    def _log_data_point(self, lat: float, lon: float, altitude: float, 
                       speed: float, course: float, satellites: int) -> None:
        """
        Log a data point to the CSV file.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            altitude: Altitude in meters
            speed: Speed in km/h
            course: Course in degrees
            satellites: Number of satellites
        """
        if not self.data_log_file:
            return
            
        try:
            timestamp = time.time()
            line = f"{timestamp},{lat},{lon},{altitude},{speed},{course},{satellites}\n"
            self.data_log_file.write(line)
            self.data_log_file.flush()
        except Exception as e:
            logger.error(f"Error logging data point: {e}")
    
    def _handle_command_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming command messages.
        
        Args:
            message: Parsed message from LoRa module
        """
        try:
            data = message.get("data", {})
            command = data.get("command")
            
            if not command:
                logger.warning(f"Received command message without command field: {message}")
                return
                
            if command in self.command_handlers:
                # Call appropriate handler
                self.command_handlers[command](data, message.get("id"))
            else:
                logger.warning(f"Unknown command received: {command}")
                
        except Exception as e:
            logger.error(f"Error handling command message: {e}")
    
    def _handle_set_config(self, data: Dict[str, Any], message_id: str) -> None:
        """
        Handle set_config command.
        
        Args:
            data: Command data
            message_id: Original message ID for response
        """
        config = data.get("config", {})
        success = False
        
        # TODO: Implement actual configuration parameter changes
        logger.info(f"Received configuration update: {config}")
        success = True
        
        # Send acknowledgement
        response = {
            "response": "config_update",
            "status": "success" if success else "failed",
            "request_id": message_id
        }
        
        self.lora.send_message("response", response)
    
    def _handle_request_position(self, data: Dict[str, Any], message_id: str) -> None:
        """
        Handle request_position command.
        
        Args:
            data: Command data
            message_id: Original message ID for response
        """
        if self.gps.has_fix():
            lat, lon = self.gps.get_position()
            altitude = self.gps.get_altitude()
            speed = self.gps.get_speed()
            course = self.gps.get_course()
            fix_quality = self.gps.get_fix_quality()
            satellites = self.gps.get_satellites()
            
            response = {
                "response": "position",
                "status": "success",
                "request_id": message_id,
                "lat": lat,
                "lon": lon,
                "alt": altitude,
                "spd": speed,
                "crs": course,
                "fix": fix_quality,
                "sat": satellites,
                "bat": self.battery_level
            }
        else:
            response = {
                "response": "position",
                "status": "no_fix",
                "request_id": message_id
            }
            
        self.lora.send_message("response", response)
    
    def _handle_add_waypoint(self, data: Dict[str, Any], message_id: str) -> None:
        """
        Handle add_waypoint command.
        
        Args:
            data: Command data
            message_id: Original message ID for response
        """
        waypoint = data.get("waypoint", {})
        success = False
        
        if "lat" in waypoint and "lon" in waypoint:
            waypoint["id"] = waypoint.get("id", f"wp_{len(self.waypoints)}")
            waypoint["radius"] = waypoint.get("radius", self.waypoint_radius)
            waypoint["visited"] = False
            
            self.waypoints.append(waypoint)
            logger.info(f"Added waypoint {waypoint['id']} at {waypoint['lat']}, {waypoint['lon']}")
            success = True
        
        response = {
            "response": "add_waypoint",
            "status": "success" if success else "failed",
            "request_id": message_id,
            "wp_id": waypoint.get("id") if success else None
        }
        
        self.lora.send_message("response", response)
    
    def _handle_clear_waypoints(self, data: Dict[str, Any], message_id: str) -> None:
        """
        Handle clear_waypoints command.
        
        Args:
            data: Command data
            message_id: Original message ID for response
        """
        self.waypoints = []
        logger.info("Cleared all waypoints")
        
        response = {
            "response": "clear_waypoints",
            "status": "success",
            "request_id": message_id
        }
        
        self.lora.send_message("response", response)
    
    def _handle_reboot(self, data: Dict[str, Any], message_id: str) -> None:
        """
        Handle reboot command.
        
        Args:
            data: Command data
            message_id: Original message ID for response
        """
        response = {
            "response": "reboot",
            "status": "success",
            "request_id": message_id
        }
        
        self.lora.send_message("response", response)
        
        # Schedule reboot after sending response
        threading.Timer(5.0, self._perform_reboot).start()
    
    def _handle_power_save(self, data: Dict[str, Any], message_id: str) -> None:
        """
        Handle power_save command.
        
        Args:
            data: Command data
            message_id: Original message ID for response
        """
        enable = data.get("enable", False)
        global LOW_POWER_MODE
        LOW_POWER_MODE = enable
        
        logger.info(f"Power save mode {'enabled' if enable else 'disabled'}")
        
        response = {
            "response": "power_save",
            "status": "success",
            "request_id": message_id,
            "mode": "low_power" if enable else "normal"
        }
        
        self.lora.send_message("response", response)
    
    def _perform_reboot(self) -> None:
        """Perform a system reboot (mock implementation)."""
        logger.info("Performing system reboot...")
        self.stop()
        # In a real implementation, this would trigger an actual system reboot
        # For simulation, just restart the controller
        time.sleep(2.0)
        self.start()
        logger.info("System rebooted") 