"""
Shared modules for the LoRa GPS tracker.

This package contains modules shared between the transmitter (beacon) and receiver (tracker).
"""

from .packet_parser import PacketParser
from .utils import (
    setup_logging,
    calculate_distance,
    calculate_bearing,
    format_coordinates,
    get_timestamp_str,
    save_location_to_file,
    load_location_from_file
)

__all__ = [
    'PacketParser',
    'setup_logging',
    'calculate_distance',
    'calculate_bearing',
    'format_coordinates',
    'get_timestamp_str',
    'save_location_to_file',
    'load_location_from_file'
] 