"""
Packet Parser Module

This module handles the formatting and parsing of GPS data packets for LoRa transmission.
It provides a consistent format for both the transmitter and receiver components.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple

class PacketParser:
    """Parser for LoRa GPS packets."""
    
    @staticmethod
    def format_gps_packet(latitude: float, longitude: float, altitude: float = 0.0, 
                         satellites: int = 0, hdop: float = 0.0, 
                         speed: float = 0.0, course: float = 0.0,
                         fix_quality: int = 0, metadata: Dict[str, Any] = None) -> bytes:
        """
        Format GPS data into a JSON packet for transmission.
        
        Args:
            latitude: GPS latitude in decimal degrees
            longitude: GPS longitude in decimal degrees
            altitude: Altitude in meters
            satellites: Number of satellites used for the fix
            hdop: Horizontal dilution of precision
            speed: Ground speed in km/h
            course: Course over ground in degrees
            fix_quality: GPS fix quality (0: no fix, 1: GPS fix, 2: DGPS fix)
            metadata: Additional metadata to include in the packet
            
        Returns:
            Bytes containing the formatted packet
        """
        if metadata is None:
            metadata = {}
            
        packet = {
            "lat": round(latitude, 6),
            "lon": round(longitude, 6),
            "alt": round(altitude, 1),
            "sat": satellites,
            "hdop": round(hdop, 1),
            "spd": round(speed, 1),
            "crs": round(course, 1),
            "fix": fix_quality,
            "ts": int(time.time()),  # Unix timestamp
            "meta": metadata
        }
        
        # Convert to JSON string and then to bytes
        return json.dumps(packet).encode('utf-8')
    
    @staticmethod
    def parse_gps_packet(packet_bytes: bytes) -> Dict[str, Any]:
        """
        Parse a received GPS packet into a dictionary.
        
        Args:
            packet_bytes: The raw packet bytes received via LoRa
            
        Returns:
            Dictionary containing the parsed GPS data
            
        Raises:
            ValueError: If the packet cannot be parsed
        """
        try:
            packet_str = packet_bytes.decode('utf-8')
            packet_data = json.loads(packet_str)
            
            # Validate required fields
            required_fields = ['lat', 'lon', 'ts']
            for field in required_fields:
                if field not in packet_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            return packet_data
            
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse GPS packet: {e}")
            
    @staticmethod
    def encode_minimal_packet(latitude: float, longitude: float, timestamp: int = None) -> bytes:
        """
        Create a minimal binary packet format for scenarios where bandwidth conservation is critical.
        
        Format:
        - 4 bytes: Latitude (encoded as int32, multiplied by 1,000,000)
        - 4 bytes: Longitude (encoded as int32, multiplied by 1,000,000)
        - 4 bytes: Timestamp (Unix timestamp as uint32)
        
        Args:
            latitude: GPS latitude in decimal degrees
            longitude: GPS longitude in decimal degrees
            timestamp: Unix timestamp (seconds since epoch), or current time if None
            
        Returns:
            Binary packet as bytes
        """
        import struct
        
        if timestamp is None:
            timestamp = int(time.time())
            
        # Convert to integers with 6 decimal precision
        lat_int = int(latitude * 1000000)
        lon_int = int(longitude * 1000000)
        
        # Pack into binary format (12 bytes total)
        return struct.pack('<iii', lat_int, lon_int, timestamp)
        
    @staticmethod
    def decode_minimal_packet(packet_bytes: bytes) -> Tuple[float, float, int]:
        """
        Decode a minimal binary packet.
        
        Args:
            packet_bytes: Binary packet data (12 bytes)
            
        Returns:
            Tuple of (latitude, longitude, timestamp)
            
        Raises:
            ValueError: If the packet is invalid
        """
        import struct
        
        if len(packet_bytes) != 12:
            raise ValueError(f"Invalid packet length: {len(packet_bytes)}, expected 12 bytes")
            
        try:
            lat_int, lon_int, timestamp = struct.unpack('<iii', packet_bytes)
            
            # Convert back to floating point
            latitude = lat_int / 1000000.0
            longitude = lon_int / 1000000.0
            
            return latitude, longitude, timestamp
            
        except struct.error as e:
            raise ValueError(f"Failed to decode packet: {e}") 