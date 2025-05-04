"""
LoRa GPS Tracker Receiver Module

This package contains modules for the receiver component of the LoRa GPS tracker.
"""

from tracker.lora import LoRaReceiver
from tracker.display import DisplayHandler
from tracker.navigation import NavigationCalculator

# Only import GPS if it's available
try:
    from tracker.gps import GPSReceiver
    gps_available = True
except ImportError:
    gps_available = False

__all__ = [
    'LoRaReceiver',
    'DisplayHandler',
    'NavigationCalculator'
]

if gps_available:
    __all__.append('GPSReceiver')
