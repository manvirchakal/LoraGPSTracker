"""
Display Handler Module

This module handles displaying the tracking information on a screen.
It supports both console output and graphical display if available.
"""

import time
import logging
import os
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import math

from tracker.config import (
    DISPLAY_ENABLED, DISPLAY_UPDATE_INTERVAL, DISPLAY_WIDTH, DISPLAY_HEIGHT,
    DISPLAY_ROTATION, MAP_CENTER_ON_BEACON, MAP_SCALE, MAP_TRAIL_LENGTH,
    MAP_SHOW_COMPASS
)

from shared.utils import (
    format_coordinates, calculate_distance, calculate_bearing, get_timestamp_str
)

# Set up logging
logger = logging.getLogger(__name__)

class DisplayHandler:
    """
    Handler for displaying GPS tracking information.
    
    This class manages the display of beacon tracking information, including:
    - Current coordinates of the beacon
    - Distance and bearing to the beacon
    - Signal strength
    - Timestamp of last reception
    - History trail of previous positions
    """
    
    def __init__(self):
        """Initialize the display handler."""
        self.enabled = DISPLAY_ENABLED
        self.update_interval = DISPLAY_UPDATE_INTERVAL
        self.display = None
        self.screen = None
        self.update_thread = None
        self.stop_event = threading.Event()
        
        # Tracking data
        self.tracker_position = None  # Tuple of (lat, lon) for tracker
        self.beacon_position = None   # Tuple of (lat, lon) for beacon
        self.beacon_history = []      # List of previous beacon positions
        self.last_update_time = 0     # Unix timestamp of last update
        self.signal_strength = 0      # RSSI value in dBm
        self.signal_quality = 0       # SNR value in dB
        
        # Initialize the display if enabled
        if self.enabled:
            self._init_display()
        
    def _init_display(self) -> bool:
        """
        Initialize the display device.
        
        Returns:
            bool: True if successfully initialized, False otherwise.
        """
        try:
            # Try to import pygame for graphical display
            try:
                import pygame
                
                # Initialize pygame
                pygame.init()
                
                # Set up the screen
                self.screen = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT))
                pygame.display.set_caption("LoRa GPS Tracker")
                
                # Load fonts
                self.fonts = {
                    'small': pygame.font.Font(None, 20),
                    'medium': pygame.font.Font(None, 24),
                    'large': pygame.font.Font(None, 32),
                    'title': pygame.font.Font(None, 40)
                }
                
                # Set display type
                self.display_type = "pygame"
                logger.info("Initialized Pygame display")
                return True
                
            except ImportError:
                # If pygame isn't available, fall back to console display
                logger.warning("Pygame not available, using console display instead")
                self.display_type = "console"
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            self.enabled = False
            return False
        
    def start(self) -> bool:
        """
        Start the display update thread.
        
        Returns:
            bool: True if successfully started, False otherwise.
        """
        if not self.enabled:
            logger.warning("Display is not enabled, cannot start")
            return False
            
        if self.update_thread is not None and self.update_thread.is_alive():
            logger.warning("Display update thread already running")
            return True
            
        self.stop_event.clear()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self.update_thread.start()
        
        logger.info("Display update thread started")
        return True
        
    def stop(self) -> None:
        """Stop the display update thread."""
        self.stop_event.set()
        
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
            
        logger.info("Display update thread stopped")
        
        # Clean up display
        if self.display_type == "pygame":
            import pygame
            pygame.quit()
        
    def update_beacon_position(self, position: Tuple[float, float], 
                              timestamp: Optional[int] = None, 
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the position of the beacon.
        
        Args:
            position: Tuple of (latitude, longitude)
            timestamp: Unix timestamp of the position update, or None for current time
            metadata: Additional metadata (signal strength, etc.)
        """
        self.beacon_position = position
        
        # Add to history (limit to MAP_TRAIL_LENGTH entries)
        self.beacon_history.append({
            'position': position,
            'timestamp': timestamp or int(time.time())
        })
        
        # Keep history within size limit
        if len(self.beacon_history) > MAP_TRAIL_LENGTH:
            self.beacon_history = self.beacon_history[-MAP_TRAIL_LENGTH:]
            
        # Update signal info if provided
        if metadata:
            if 'rssi' in metadata:
                self.signal_strength = metadata['rssi']
            if 'snr' in metadata:
                self.signal_quality = metadata['snr']
                
        self.last_update_time = timestamp or int(time.time())
        
    def update_tracker_position(self, position: Tuple[float, float]) -> None:
        """
        Update the position of the tracker itself.
        
        Args:
            position: Tuple of (latitude, longitude)
        """
        self.tracker_position = position
        
    def _update_worker(self) -> None:
        """
        Worker thread function for updating the display.
        """
        logger.info("Display update worker started")
        
        while not self.stop_event.is_set():
            try:
                self._update_display()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error updating display: {e}")
                time.sleep(1.0)  # Pause on error to prevent log flooding
        
        logger.info("Display update worker stopped")
        
    def _update_display(self) -> None:
        """
        Update the display with current tracking information.
        """
        if self.display_type == "pygame":
            self._update_pygame_display()
        else:
            self._update_console_display()
            
    def _update_pygame_display(self) -> None:
        """
        Update the pygame graphical display.
        """
        import pygame
        
        # Get the screen surface
        screen = self.screen
        
        # Fill the background
        screen.fill((0, 0, 0))  # Black background
        
        # Header
        pygame.draw.rect(screen, (0, 0, 80), (0, 0, DISPLAY_WIDTH, 50))
        title = self.fonts['title'].render("LoRa GPS Tracker", True, (255, 255, 255))
        screen.blit(title, (DISPLAY_WIDTH // 2 - title.get_width() // 2, 10))
        
        # Draw map area background
        pygame.draw.rect(screen, (20, 20, 20), (10, 60, DISPLAY_WIDTH - 20, DISPLAY_HEIGHT - 120))
        
        # Draw beacon position if available
        if self.beacon_position:
            # Draw current position (large red dot)
            map_center_x = DISPLAY_WIDTH // 2
            map_center_y = (DISPLAY_HEIGHT - 60) // 2 + 60
            
            # Draw the map
            if MAP_CENTER_ON_BEACON:
                pygame.draw.circle(screen, (255, 0, 0), (map_center_x, map_center_y), 8)
                
                # Draw beacon position text
                pos_text = self.fonts['medium'].render(
                    f"Beacon: {format_coordinates(*self.beacon_position)}", 
                    True, (255, 200, 200))
                screen.blit(pos_text, (20, DISPLAY_HEIGHT - 50))
                
                # Draw tracker position if available
                if self.tracker_position:
                    # Calculate relative position to beacon
                    distance = calculate_distance(
                        self.tracker_position[0], self.tracker_position[1],
                        self.beacon_position[0], self.beacon_position[1]
                    )
                    bearing = calculate_bearing(
                        self.tracker_position[0], self.tracker_position[1],
                        self.beacon_position[0], self.beacon_position[1]
                    )
                    
                    # Convert polar (distance, bearing) to cartesian for display
                    # Note: On screen, y-axis is inverted (positive is down)
                    scale_factor = 100.0 / MAP_SCALE  # pixels per meter
                    rel_x = distance * scale_factor * math.sin(math.radians(bearing))
                    rel_y = -distance * scale_factor * math.cos(math.radians(bearing))
                    
                    # Draw tracker position (blue triangle)
                    tracker_x = map_center_x - int(rel_x)
                    tracker_y = map_center_y - int(rel_y)
                    
                    # Triangle points
                    triangle_size = 10
                    # Calculate triangle vertices based on bearing
                    tracker_angle = math.radians(bearing - 180)  # Point towards beacon
                    tx1 = tracker_x + int(triangle_size * math.sin(tracker_angle))
                    ty1 = tracker_y - int(triangle_size * math.cos(tracker_angle))
                    tx2 = tracker_x + int(triangle_size * math.sin(tracker_angle + 2.1))
                    ty2 = tracker_y - int(triangle_size * math.cos(tracker_angle + 2.1))
                    tx3 = tracker_x + int(triangle_size * math.sin(tracker_angle - 2.1))
                    ty3 = tracker_y - int(triangle_size * math.cos(tracker_angle - 2.1))
                    
                    pygame.draw.polygon(screen, (0, 100, 255), [(tx1, ty1), (tx2, ty2), (tx3, ty3)])
                    
                    # Draw distance and bearing
                    if distance < 1000:
                        dist_text = f"{distance:.1f} m"
                    else:
                        dist_text = f"{distance/1000:.2f} km"
                        
                    dist_bearing_text = self.fonts['medium'].render(
                        f"Distance: {dist_text}, Bearing: {bearing:.1f}°", 
                        True, (255, 255, 255))
                    screen.blit(dist_bearing_text, (20, DISPLAY_HEIGHT - 80))
            
            # Draw signal strength indicator
            if self.signal_strength != 0:
                signal_text = self.fonts['medium'].render(
                    f"Signal: {self.signal_strength:.1f} dBm, Quality: {self.signal_quality:.1f} dB", 
                    True, (200, 255, 200))
                screen.blit(signal_text, (DISPLAY_WIDTH - signal_text.get_width() - 20, DISPLAY_HEIGHT - 50))
                
            # Draw timestamp
            time_text = self.fonts['small'].render(
                f"Last update: {get_timestamp_str(self.last_update_time)}", 
                True, (180, 180, 180))
            screen.blit(time_text, (DISPLAY_WIDTH - time_text.get_width() - 20, DISPLAY_HEIGHT - 30))
        else:
            # No beacon position
            waiting_text = self.fonts['large'].render(
                "Waiting for beacon signal...", 
                True, (255, 255, 0))
            screen.blit(waiting_text, (DISPLAY_WIDTH // 2 - waiting_text.get_width() // 2, 
                                     DISPLAY_HEIGHT // 2 - waiting_text.get_height() // 2))
        
        # Update the display
        pygame.display.flip()
        
    def _update_console_display(self) -> None:
        """
        Update the console display (text-only).
        """
        # Clear console (cross-platform)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 50)
        print("  LoRa GPS Tracker - Console Display")
        print("=" * 50)
        
        if self.beacon_position:
            print(f"\nBeacon Position: {format_coordinates(*self.beacon_position)}")
            
            if self.tracker_position:
                distance = calculate_distance(
                    self.tracker_position[0], self.tracker_position[1],
                    self.beacon_position[0], self.beacon_position[1]
                )
                bearing = calculate_bearing(
                    self.tracker_position[0], self.tracker_position[1],
                    self.beacon_position[0], self.beacon_position[1]
                )
                
                if distance < 1000:
                    dist_text = f"{distance:.1f} m"
                else:
                    dist_text = f"{distance/1000:.2f} km"
                    
                print(f"Distance to Beacon: {dist_text}")
                print(f"Bearing to Beacon: {bearing:.1f}°")
                
            if self.signal_strength != 0:
                print(f"\nSignal Strength: {self.signal_strength:.1f} dBm")
                print(f"Signal Quality:  {self.signal_quality:.1f} dB")
                
            print(f"\nLast Update: {get_timestamp_str(self.last_update_time)}")
            
        else:
            print("\nWaiting for beacon signal...")
            
        print("\n" + "=" * 50)
        
        # History (last 5 positions)
        if self.beacon_history:
            print("\nRecent History:")
            for i, entry in enumerate(reversed(self.beacon_history[:5])):
                pos = entry['position']
                ts = entry['timestamp']
                print(f" {i+1}. {format_coordinates(*pos)} at {get_timestamp_str(ts)}")
                
        print("=" * 50)
