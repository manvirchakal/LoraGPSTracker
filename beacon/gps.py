"""
GPS Module - Handles communication with GPS hardware

This module provides a class to manage GPS communication using serial interface,
including reading and parsing NMEA sentences, extracting GPS data such as
position, speed, altitude, and time.
"""

import time
import serial
import logging
import threading
import math
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from beacon.config import (
    GPS_PORT, GPS_BAUD_RATE, GPS_TIMEOUT, GPS_UPDATE_INTERVAL,
    GPS_MIN_SATELLITES, GPS_MIN_HDOP, GPS_REQUIRE_3D_FIX
)

# Configure logger
logger = logging.getLogger(__name__)

class GPSModule:
    """
    Class for managing communication with GPS hardware via serial interface.
    
    Provides methods for initializing GPS, reading and parsing NMEA sentences,
    and retrieving GPS data such as position, speed, altitude, and time.
    """
    
    def __init__(self, 
                 port: str = GPS_PORT, 
                 baud_rate: int = GPS_BAUD_RATE, 
                 timeout: float = GPS_TIMEOUT):
        """
        Initialize the GPS module with communication parameters.
        
        Args:
            port (str): Serial port for GPS module
            baud_rate (int): Serial baud rate
            timeout (float): Serial read timeout in seconds
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial = None
        self.is_connected = False
        self.is_running = False
        
        # GPS data
        self.gps_data = {
            'latitude': None,
            'longitude': None,
            'altitude': None,
            'speed': None,  # Speed in km/h
            'course': None,  # Course over ground in degrees
            'satellites': 0,
            'fix_quality': 0,  # 0=no fix, 1=GPS fix, 2=DGPS fix, 3=PPS fix
            'hdop': 99.9,      # Horizontal dilution of precision
            'pdop': 99.9,      # Position dilution of precision
            'time': None,      # UTC time
            'date': None,      # UTC date
            'fix_type': 1,     # 1=no fix, 2=2D fix, 3=3D fix
            'last_update': 0,  # Timestamp of last update
            'valid': False     # Indicates if GPS data is valid
        }
        
        # Requirements for valid fix
        self.min_satellites = GPS_MIN_SATELLITES
        self.min_hdop = GPS_MIN_HDOP
        self.require_3d_fix = GPS_REQUIRE_3D_FIX
        self.update_interval = GPS_UPDATE_INTERVAL
        
        # Thread for reading GPS data
        self.gps_thread = None
        self.stop_event = threading.Event()
        
        # Lock for thread safety
        self.data_lock = threading.Lock()
        self.serial_lock = threading.Lock()
        
        logger.info(f"GPS module initialized on port {port}")
    
    def connect(self) -> bool:
        """
        Connect to the GPS module via serial port.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to GPS module at {self.port}")
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )
            self.is_connected = True
            logger.info("Connected to GPS module")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to GPS module: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the GPS module."""
        if self.is_running:
            self.stop()
        
        if self.serial and self.serial.is_open:
            with self.serial_lock:
                self.serial.close()
            logger.info("Disconnected from GPS module")
        
        self.is_connected = False
    
    def start(self) -> bool:
        """
        Start the GPS reading thread.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if not self.is_connected:
            logger.error("Cannot start: GPS module not connected")
            return False
            
        if self.is_running:
            logger.warning("GPS module already running")
            return True
            
        try:
            # Reset stop event
            self.stop_event.clear()
            
            # Start GPS reading thread
            self.gps_thread = threading.Thread(target=self._read_gps_data, daemon=True)
            self.gps_thread.start()
            
            self.is_running = True
            logger.info("GPS thread started")
            return True
        except Exception as e:
            logger.error(f"Error starting GPS thread: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the GPS reading thread."""
        if not self.is_running:
            return
            
        # Signal thread to stop
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.gps_thread and self.gps_thread.is_alive():
            self.gps_thread.join(timeout=2.0)
            
        self.is_running = False
        logger.info("GPS thread stopped")
    
    def get_position(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Get the current GPS position.
        
        Returns:
            Tuple[Optional[float], Optional[float], Optional[float]]: 
                (latitude, longitude, altitude) or (None, None, None) if no fix
        """
        with self.data_lock:
            return (
                self.gps_data['latitude'],
                self.gps_data['longitude'],
                self.gps_data['altitude']
            )
    
    def get_altitude(self) -> Optional[float]:
        """
        Get the current GPS altitude in meters.
        
        Returns:
            Optional[float]: Altitude in meters or None if not available
        """
        with self.data_lock:
            return self.gps_data['altitude']
    
    def get_speed(self) -> Optional[float]:
        """
        Get the current GPS speed in km/h.
        
        Returns:
            Optional[float]: Speed in km/h or None if not available
        """
        with self.data_lock:
            return self.gps_data['speed']
    
    def get_course(self) -> Optional[float]:
        """
        Get the current GPS course (heading) in degrees.
        
        Returns:
            Optional[float]: Course in degrees or None if not available
        """
        with self.data_lock:
            return self.gps_data['course']
    
    def get_satellites(self) -> int:
        """
        Get the number of satellites in view.
        
        Returns:
            int: Number of satellites
        """
        with self.data_lock:
            return self.gps_data['satellites']
    
    def get_fix_quality(self) -> int:
        """
        Get the GPS fix quality.
        
        Returns:
            int: Fix quality (0=no fix, 1=GPS fix, 2=DGPS fix, 3=PPS fix)
        """
        with self.data_lock:
            return self.gps_data['fix_quality']
    
    def get_datetime(self) -> Optional[datetime]:
        """
        Get the current GPS date and time in UTC.
        
        Returns:
            Optional[datetime]: Date and time or None if not available
        """
        with self.data_lock:
            if self.gps_data['time'] and self.gps_data['date']:
                try:
                    # Combine date and time strings (format: DDMMYY HHMMSS.SSS)
                    dt_str = f"{self.gps_data['date']} {self.gps_data['time']}"
                    dt = datetime.strptime(dt_str, "%d%m%y %H%M%S.%f")
                    return dt.replace(tzinfo=timezone.utc)
                except Exception as e:
                    logger.error(f"Error parsing GPS datetime: {e}")
                    return None
            return None
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all GPS data.
        
        Returns:
            Dict[str, Any]: Dictionary containing all GPS data
        """
        with self.data_lock:
            return self.gps_data.copy()
    
    def get_location(self) -> Optional[Dict[str, Any]]:
        """
        Get the current location data if a valid fix is available.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing location data or None if no valid fix
        """
        if not self.has_fix():
            return None
            
        # Get the GPS data and add timestamp
        location_data = self.get_all_data()
        location_data["timestamp"] = time.time()
        
        return location_data
    
    def has_fix(self) -> bool:
        """
        Check if the GPS has a valid position fix.
        
        Returns:
            bool: True if valid position fix, False otherwise
        """
        with self.data_lock:
            # Check if basic position data is available
            if (self.gps_data['latitude'] is None or 
                self.gps_data['longitude'] is None):
                return False
            
            # Check minimum requirements for a valid fix
            if self.gps_data['satellites'] < self.min_satellites:
                return False
                
            if self.gps_data['hdop'] > self.min_hdop:
                return False
                
            if self.require_3d_fix and self.gps_data['fix_type'] < 3:
                return False
                
            return True
    
    def wait_for_fix(self, timeout: float = 60.0) -> bool:
        """
        Wait for a valid GPS fix.
        
        Args:
            timeout (float): Maximum time to wait in seconds
            
        Returns:
            bool: True if fix obtained within timeout, False otherwise
        """
        if not self.is_running:
            if not self.start():
                return False
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self.has_fix():
                return True
            time.sleep(0.5)
            
        return False
    
    def _read_gps_data(self) -> None:
        """Worker thread for reading and parsing GPS data."""
        logger.info("GPS reading thread started")
        
        # Buffer for NMEA sentences
        nmea_buffer = ""
        
        while not self.stop_event.is_set():
            try:
                # Read data from serial port
                with self.serial_lock:
                    if self.serial.in_waiting:
                        data = self.serial.read(self.serial.in_waiting).decode('ascii', errors='ignore')
                        nmea_buffer += data
                
                # Process complete NMEA sentences in buffer
                if '\n' in nmea_buffer:
                    lines = nmea_buffer.split('\n')
                    # Last line might be incomplete, keep it for the next iteration
                    nmea_buffer = lines.pop()
                    
                    for line in lines:
                        line = line.strip()
                        if line and self._is_valid_nmea(line):
                            self._parse_nmea(line)
                
                # Check if it's time to update GPS status
                current_time = time.time()
                with self.data_lock:
                    if (current_time - self.gps_data['last_update']) >= self.update_interval:
                        self._update_gps_status()
                        self.gps_data['last_update'] = current_time
                
                # Brief delay to avoid consuming too much CPU
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error reading GPS data: {e}")
                time.sleep(1.0)  # Delay to avoid rapid error loops
        
        logger.info("GPS reading thread stopped")
    
    def _is_valid_nmea(self, sentence: str) -> bool:
        """
        Check if a NMEA sentence is valid.
        
        Args:
            sentence (str): NMEA sentence to check
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check if sentence starts with '$'
        if not sentence.startswith('$'):
            return False
            
        # Check if sentence has enough characters
        if len(sentence) < 5:
            return False
            
        # Check checksum if present
        if '*' in sentence:
            try:
                # Split sentence into data and checksum
                data, checksum = sentence.split('*')
                data = data[1:]  # Remove the leading '$'
                
                # Calculate checksum
                calculated_checksum = 0
                for char in data:
                    calculated_checksum ^= ord(char)
                
                # Compare with provided checksum
                return int(checksum, 16) == calculated_checksum
            except Exception:
                return False
        
        return True
    
    def _parse_nmea(self, sentence: str) -> None:
        """
        Parse NMEA sentence and update GPS data.
        
        Args:
            sentence (str): NMEA sentence to parse
        """
        try:
            # Remove '$' prefix and checksum
            if '*' in sentence:
                sentence = sentence.split('*')[0]
            sentence = sentence.lstrip('$')
            
            # Split into parts
            parts = sentence.split(',')
            sentence_type = parts[0]
            
            # Parse different NMEA sentence types
            if sentence_type == "GPGGA":
                self._parse_gpgga(parts)
            elif sentence_type == "GPRMC":
                self._parse_gprmc(parts)
            elif sentence_type == "GPGSV":
                self._parse_gpgsv(parts)
            elif sentence_type == "GPGSA":
                self._parse_gpgsa(parts)
            
        except Exception as e:
            logger.error(f"Error parsing NMEA sentence: {e}")
    
    def _parse_gpgga(self, parts: List[str]) -> None:
        """
        Parse GPGGA sentence (Global Positioning System Fix Data).
        
        Args:
            parts (List[str]): Parts of the NMEA sentence
        """
        # GPGGA format:
        # $GPGGA,time,latitude,N/S,longitude,E/W,fix,satellites,hdop,altitude,M,geoid,M,age,ref*checksum
        
        if len(parts) < 15:
            return
            
        with self.data_lock:
            # Time (HHMMSS.SSS)
            if parts[1]:
                self.gps_data['time'] = parts[1]
                
            # Latitude (DDMM.MMMM)
            if parts[2] and parts[3]:
                try:
                    lat_deg = float(parts[2][:2])
                    lat_min = float(parts[2][2:])
                    latitude = lat_deg + (lat_min / 60.0)
                    if parts[3] == 'S':
                        latitude = -latitude
                    self.gps_data['latitude'] = latitude
                except ValueError:
                    pass
                    
            # Longitude (DDDMM.MMMM)
            if parts[4] and parts[5]:
                try:
                    lon_deg = float(parts[4][:3])
                    lon_min = float(parts[4][3:])
                    longitude = lon_deg + (lon_min / 60.0)
                    if parts[5] == 'W':
                        longitude = -longitude
                    self.gps_data['longitude'] = longitude
                except ValueError:
                    pass
                    
            # Fix quality
            if parts[6]:
                try:
                    self.gps_data['fix_quality'] = int(parts[6])
                except ValueError:
                    pass
                    
            # Number of satellites
            if parts[7]:
                try:
                    self.gps_data['satellites'] = int(parts[7])
                except ValueError:
                    pass
                    
            # HDOP
            if parts[8]:
                try:
                    self.gps_data['hdop'] = float(parts[8])
                except ValueError:
                    pass
                    
            # Altitude
            if parts[9] and parts[10] == 'M':
                try:
                    self.gps_data['altitude'] = float(parts[9])
                except ValueError:
                    pass
    
    def _parse_gprmc(self, parts: List[str]) -> None:
        """
        Parse GPRMC sentence (Recommended Minimum Navigation Information).
        
        Args:
            parts (List[str]): Parts of the NMEA sentence
        """
        # GPRMC format:
        # $GPRMC,time,status,latitude,N/S,longitude,E/W,speed,course,date,magnetic,E/W,mode*checksum
        
        if len(parts) < 12:
            return
            
        with self.data_lock:
            # Time (HHMMSS.SSS)
            if parts[1]:
                self.gps_data['time'] = parts[1]
                
            # Status (A=active, V=void)
            status = parts[2] == 'A'
            
            # Date (DDMMYY)
            if parts[9]:
                self.gps_data['date'] = parts[9]
                
            # Only update position if status is active
            if status:
                # Latitude (DDMM.MMMM)
                if parts[3] and parts[4]:
                    try:
                        lat_deg = float(parts[3][:2])
                        lat_min = float(parts[3][2:])
                        latitude = lat_deg + (lat_min / 60.0)
                        if parts[4] == 'S':
                            latitude = -latitude
                        self.gps_data['latitude'] = latitude
                    except ValueError:
                        pass
                        
                # Longitude (DDDMM.MMMM)
                if parts[5] and parts[6]:
                    try:
                        lon_deg = float(parts[5][:3])
                        lon_min = float(parts[5][3:])
                        longitude = lon_deg + (lon_min / 60.0)
                        if parts[6] == 'W':
                            longitude = -longitude
                        self.gps_data['longitude'] = longitude
                    except ValueError:
                        pass
                        
                # Speed (knots)
                if parts[7]:
                    try:
                        # Convert knots to km/h (1 knot = 1.852 km/h)
                        self.gps_data['speed'] = float(parts[7]) * 1.852
                    except ValueError:
                        pass
                        
                # Course (degrees)
                if parts[8]:
                    try:
                        self.gps_data['course'] = float(parts[8])
                    except ValueError:
                        pass
    
    def _parse_gpgsv(self, parts: List[str]) -> None:
        """
        Parse GPGSV sentence (Satellites in View).
        
        Args:
            parts (List[str]): Parts of the NMEA sentence
        """
        # GPGSV format:
        # $GPGSV,total_msgs,msg_num,total_sats,[sat_id,elevation,azimuth,snr,...]*checksum
        
        if len(parts) < 4:
            return
            
        # We only care about the total number of satellites in view
        # This is better provided by GPGGA, but this is a backup
        try:
            with self.data_lock:
                total_sats = int(parts[3])
                if self.gps_data['satellites'] == 0:  # Only update if not set by GPGGA
                    self.gps_data['satellites'] = total_sats
        except ValueError:
            pass
    
    def _parse_gpgsa(self, parts: List[str]) -> None:
        """
        Parse GPGSA sentence (GPS DOP and Active Satellites).
        
        Args:
            parts (List[str]): Parts of the NMEA sentence
        """
        # GPGSA format:
        # $GPGSA,mode,fix_type,[sat_id,...],pdop,hdop,vdop*checksum
        
        if len(parts) < 18:
            return
            
        with self.data_lock:
            # Fix type (1=no fix, 2=2D fix, 3=3D fix)
            if parts[2]:
                try:
                    self.gps_data['fix_type'] = int(parts[2])
                except ValueError:
                    pass
                    
            # PDOP (Position Dilution of Precision)
            if parts[15]:
                try:
                    self.gps_data['pdop'] = float(parts[15])
                except ValueError:
                    pass
                    
            # HDOP (Horizontal Dilution of Precision)
            if parts[16]:
                try:
                    self.gps_data['hdop'] = float(parts[16])
                except ValueError:
                    pass
    
    def _update_gps_status(self) -> None:
        """Update GPS status based on current data."""
        with self.data_lock:
            # Update validity status
            self.gps_data['valid'] = self.has_fix()
            
            # Log status updates
            if self.gps_data['valid']:
                logger.debug(
                    f"Valid GPS fix: Lat: {self.gps_data['latitude']:.6f}, "
                    f"Lon: {self.gps_data['longitude']:.6f}, "
                    f"Alt: {self.gps_data['altitude']:.1f}m, "
                    f"Sats: {self.gps_data['satellites']}, "
                    f"HDOP: {self.gps_data['hdop']:.1f}"
                )
            else:
                reason = "Unknown"
                if self.gps_data['latitude'] is None:
                    reason = "No position data"
                elif self.gps_data['satellites'] < self.min_satellites:
                    reason = f"Too few satellites ({self.gps_data['satellites']}/{self.min_satellites})"
                elif self.gps_data['hdop'] > self.min_hdop:
                    reason = f"HDOP too high ({self.gps_data['hdop']:.1f}/{self.min_hdop})"
                elif self.require_3d_fix and self.gps_data['fix_type'] < 3:
                    reason = "No 3D fix"
                    
                logger.debug(f"No valid GPS fix: {reason}")
                
    def set_requirements(self, 
                         min_satellites: Optional[int] = None,
                         min_hdop: Optional[float] = None,
                         require_3d_fix: Optional[bool] = None,
                         update_interval: Optional[float] = None) -> None:
        """
        Set requirements for a valid GPS fix.
        
        Args:
            min_satellites (Optional[int]): Minimum number of satellites required
            min_hdop (Optional[float]): Maximum acceptable HDOP value
            require_3d_fix (Optional[bool]): Whether a 3D fix is required
            update_interval (Optional[float]): How often to update GPS status
        """
        if min_satellites is not None:
            self.min_satellites = min_satellites
            
        if min_hdop is not None:
            self.min_hdop = min_hdop
            
        if require_3d_fix is not None:
            self.require_3d_fix = require_3d_fix
            
        if update_interval is not None:
            self.update_interval = update_interval
            
        logger.info(
            f"GPS requirements updated: min_satellites={self.min_satellites}, "
            f"min_hdop={self.min_hdop}, require_3d_fix={self.require_3d_fix}, "
            f"update_interval={self.update_interval}"
        )
    
    def calculate_distance(self, 
                          lat1: float, 
                          lon1: float, 
                          lat2: float, 
                          lon2: float) -> float:
        """
        Calculate distance between two points in meters using Haversine formula.
        
        Args:
            lat1 (float): Latitude of point 1 in degrees
            lon1 (float): Longitude of point 1 in degrees
            lat2 (float): Latitude of point 2 in degrees
            lon2 (float): Longitude of point 2 in degrees
            
        Returns:
            float: Distance in meters
        """
        # Earth radius in meters
        R = 6371000.0
        
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
