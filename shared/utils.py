"""
Utility Functions Module

This module provides common utility functions used across the GPS tracker system.
"""

import math
import logging
import time
import os
from typing import Tuple, Optional, Dict, Any

def setup_logging(name: str, log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Name for the logger
        log_dir: Directory for log files
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    log_file = os.path.join(log_dir, f"{name.lower().replace(' ', '_')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates in meters using the Haversine formula.
    
    Args:
        lat1: Latitude of point 1 in decimal degrees
        lon1: Longitude of point 1 in decimal degrees
        lat2: Latitude of point 2 in decimal degrees
        lon2: Longitude of point 2 in decimal degrees
        
    Returns:
        Distance in meters
    """
    # Earth radius in meters
    radius = 6371000
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = radius * c
    
    return distance

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing from point 1 to point 2.
    
    Args:
        lat1: Latitude of point 1 in decimal degrees
        lon1: Longitude of point 1 in decimal degrees
        lat2: Latitude of point 2 in decimal degrees
        lon2: Longitude of point 2 in decimal degrees
        
    Returns:
        Bearing in degrees (0-360, where 0 is North)
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Calculate bearing
    y = math.sin(lon2_rad - lon1_rad) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad)
    bearing_rad = math.atan2(y, x)
    
    # Convert to degrees
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360
    bearing_normalized = (bearing_deg + 360) % 360
    
    return bearing_normalized

def format_coordinates(latitude: float, longitude: float, format_type: str = "decimal") -> str:
    """
    Format GPS coordinates as a string.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        format_type: "decimal" or "dms" (degrees, minutes, seconds)
        
    Returns:
        Formatted coordinate string
    """
    if format_type == "decimal":
        return f"{latitude:.6f}, {longitude:.6f}"
    elif format_type == "dms":
        # Convert decimal degrees to degrees, minutes, seconds
        def decimal_to_dms(coord):
            # Get absolute value of the coordinate
            coord_abs = abs(coord)
            
            # Degrees
            degrees = int(coord_abs)
            
            # Minutes
            minutes_float = (coord_abs - degrees) * 60
            minutes = int(minutes_float)
            
            # Seconds
            seconds = (minutes_float - minutes) * 60
            
            return (degrees, minutes, seconds)
        
        # Get DMS for latitude and longitude
        lat_dms = decimal_to_dms(latitude)
        lon_dms = decimal_to_dms(longitude)
        
        # Direction (N/S for latitude, E/W for longitude)
        lat_dir = "N" if latitude >= 0 else "S"
        lon_dir = "E" if longitude >= 0 else "W"
        
        # Create formatted strings
        lat_str = f"{lat_dms[0]}° {lat_dms[1]}' {lat_dms[2]:.2f}\" {lat_dir}"
        lon_str = f"{lon_dms[0]}° {lon_dms[1]}' {lon_dms[2]:.2f}\" {lon_dir}"
        
        return f"{lat_str}, {lon_str}"
    else:
        raise ValueError(f"Unknown format type: {format_type}")

def get_timestamp_str(timestamp: Optional[int] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a Unix timestamp as a human-readable string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch), or current time if None
        format_str: strftime format string
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = int(time.time())
        
    return time.strftime(format_str, time.localtime(timestamp))

def save_location_to_file(location_data: Dict[str, Any], filename: str = "last_location.json") -> None:
    """
    Save location data to a JSON file for persistence.
    
    Args:
        location_data: Dictionary containing location data
        filename: File to save the data to
    """
    import json
    
    try:
        with open(filename, 'w') as f:
            json.dump(location_data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save location data: {e}")

def load_location_from_file(filename: str = "last_location.json") -> Optional[Dict[str, Any]]:
    """
    Load location data from a JSON file.
    
    Args:
        filename: File to load data from
        
    Returns:
        Dictionary containing location data, or None if file doesn't exist or is invalid
    """
    import json
    
    try:
        if not os.path.exists(filename):
            return None
            
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load location data: {e}")
        return None 