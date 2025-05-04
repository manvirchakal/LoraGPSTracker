"""
Navigation Module

This module handles navigation calculations between tracker and beacon.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple

from shared.utils import (
    calculate_distance, calculate_bearing, format_coordinates, get_timestamp_str
)

# Set up logging
logger = logging.getLogger(__name__)

class NavigationCalculator:
    """
    Class for calculating navigation parameters between tracker and beacon.
    
    This class provides methods to calculate distance, bearing, and other
    navigation parameters between the tracker and the beacon.
    """
    
    def __init__(self):
        """Initialize the navigation calculator."""
        # Current positions
        self.tracker_position: Optional[Tuple[float, float]] = None
        self.beacon_position: Optional[Tuple[float, float]] = None
        
        # Calculated values
        self.distance: Optional[float] = None
        self.bearing: Optional[float] = None
        self.last_calc_time: float = 0
        
        # History for trend analysis
        self.distance_history: list = []
        self.bearing_history: list = []
        self.max_history_size: int = 20
        
    def update_tracker_position(self, latitude: float, longitude: float) -> None:
        """
        Update the tracker's position.
        
        Args:
            latitude: Tracker latitude in decimal degrees
            longitude: Tracker longitude in decimal degrees
        """
        self.tracker_position = (latitude, longitude)
        self._update_calculations()
        
    def update_beacon_position(self, latitude: float, longitude: float) -> None:
        """
        Update the beacon's position.
        
        Args:
            latitude: Beacon latitude in decimal degrees
            longitude: Beacon longitude in decimal degrees
        """
        self.beacon_position = (latitude, longitude)
        self._update_calculations()
        
    def get_navigation_data(self) -> Dict[str, Any]:
        """
        Get current navigation data.
        
        Returns:
            Dictionary containing navigation data
        """
        return {
            "tracker_position": self.tracker_position,
            "beacon_position": self.beacon_position,
            "distance": self.distance,
            "bearing": self.bearing,
            "distance_trend": self._calculate_distance_trend(),
            "bearing_trend": self._calculate_bearing_trend(),
            "last_calc_time": self.last_calc_time
        }
        
    def _update_calculations(self) -> None:
        """Update navigation calculations if both positions are available."""
        if self.tracker_position and self.beacon_position:
            # Calculate distance and bearing
            self.distance = calculate_distance(
                self.tracker_position[0], self.tracker_position[1],
                self.beacon_position[0], self.beacon_position[1]
            )
            
            self.bearing = calculate_bearing(
                self.tracker_position[0], self.tracker_position[1],
                self.beacon_position[0], self.beacon_position[1]
            )
            
            # Update history
            self.distance_history.append((time.time(), self.distance))
            self.bearing_history.append((time.time(), self.bearing))
            
            # Keep history within size limit
            if len(self.distance_history) > self.max_history_size:
                self.distance_history = self.distance_history[-self.max_history_size:]
                
            if len(self.bearing_history) > self.max_history_size:
                self.bearing_history = self.bearing_history[-self.max_history_size:]
                
            self.last_calc_time = time.time()
            
            logger.debug(f"Navigation update: Distance: {self.distance:.1f}m, "
                        f"Bearing: {self.bearing:.1f}°")
        else:
            # If either position is missing, calculations are not possible
            self.distance = None
            self.bearing = None
            
    def _calculate_distance_trend(self) -> Optional[float]:
        """
        Calculate the trend in distance over time.
        
        Returns:
            Rate of change in meters per second (negative means getting closer),
            or None if insufficient data
        """
        if len(self.distance_history) < 2:
            return None
            
        # Use last few points for trend
        points = self.distance_history[-5:] if len(self.distance_history) >= 5 else self.distance_history
        
        # Simple linear regression
        n = len(points)
        sum_x = sum(p[0] for p in points)  # Sum of times
        sum_y = sum(p[1] for p in points)  # Sum of distances
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_xx = sum(p[0] * p[0] for p in points)
        
        # Calculate slope (meters per second)
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
            return slope
        except ZeroDivisionError:
            return None
            
    def _calculate_bearing_trend(self) -> Optional[float]:
        """
        Calculate the trend in bearing over time.
        
        Returns:
            Rate of change in degrees per second (positive means turning clockwise),
            or None if insufficient data
        """
        if len(self.bearing_history) < 2:
            return None
            
        # Bearing requires special handling due to the 0-360 discontinuity
        # Convert to a continuous scale
        
        # Use last few points for trend
        raw_points = self.bearing_history[-5:] if len(self.bearing_history) >= 5 else self.bearing_history
        
        # Unwrap bearings to handle the 0-360 discontinuity
        prev_bearing = raw_points[0][1]
        points = [(raw_points[0][0], prev_bearing)]
        
        for t, b in raw_points[1:]:
            # Calculate smallest angle difference
            diff = ((b - prev_bearing + 180) % 360) - 180
            unwrapped_bearing = prev_bearing + diff
            points.append((t, unwrapped_bearing))
            prev_bearing = unwrapped_bearing
            
        # Simple linear regression on unwrapped bearings
        n = len(points)
        sum_x = sum(p[0] for p in points)  # Sum of times
        sum_y = sum(p[1] for p in points)  # Sum of unwrapped bearings
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_xx = sum(p[0] * p[0] for p in points)
        
        # Calculate slope (degrees per second)
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
            return slope
        except ZeroDivisionError:
            return None
            
    def get_formatted_distance(self) -> str:
        """
        Get a formatted string representation of the distance.
        
        Returns:
            Formatted distance string, or 'N/A' if not available
        """
        if self.distance is None:
            return "N/A"
            
        if self.distance < 1000:
            return f"{self.distance:.1f} m"
        else:
            return f"{self.distance/1000:.2f} km"
            
    def get_formatted_bearing(self) -> str:
        """
        Get a formatted string representation of the bearing.
        
        Returns:
            Formatted bearing string, or 'N/A' if not available
        """
        if self.bearing is None:
            return "N/A"
            
        # Get cardinal direction
        cardinal_directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        
        # Convert bearing to 0-15 index
        index = round(self.bearing / 22.5) % 16
        cardinal = cardinal_directions[index]
        
        return f"{self.bearing:.1f}° ({cardinal})"
