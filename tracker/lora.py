"""
LoRa Receiver Module

This module handles receiving LoRa packets from the beacon transmitter.
"""

import threading
import queue
import time
import logging
import json
import os
import sys
from typing import Dict, Any, Optional, List, Tuple, Callable

# Add the necessary module path for LoRaRF
sx126x_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                           'sx126x_lorawan_hat_code/python/lora'))
if sx126x_path not in sys.path:
    sys.path.insert(0, sx126x_path)

from tracker.config import (
    LORA_CONFIG, LORA_ENCRYPTION_KEY, LORA_MESSAGE_QUEUE_SIZE,
    LORA_USING_SPI, LORA_SPI_BUS, LORA_SPI_CS, LORA_RESET_PIN, 
    LORA_BUSY_PIN, LORA_IRQ_PIN, LORA_TXEN_PIN, LORA_RXEN_PIN,
    LORA_RX_CONTINUOUS
)

# Set up logging
logger = logging.getLogger(__name__)

class LoRaReceiver:
    """
    Class for interfacing with a LoRa module for receiving GPS data.
    
    This class provides an interface to a LoRa radio module connected via SPI.
    It handles initialization, configuration, and receiving messages.
    """

    def __init__(self):
        """Initialize the LoRa receiver."""
        # Configuration values
        self.config = LORA_CONFIG
        self.encryption_key = LORA_ENCRYPTION_KEY
        
        # SPI module
        self.lora = None
        self.connected = False
        
        # Message handling
        self.rx_queue = queue.Queue(maxsize=LORA_MESSAGE_QUEUE_SIZE)
        self.message_callbacks = {}
        
        # Threads
        self.rx_thread = None
        self.stop_event = threading.Event()
        
        # Stats
        self.stats = {
            "rx_packets": 0,
            "rx_bytes": 0,
            "rx_errors": 0,
            "last_rssi": 0,
            "last_snr": 0,
            "last_rx_time": 0
        }
        
    def connect(self) -> bool:
        """
        Connect to the LoRa module via SPI.
        
        Returns:
            bool: True if successfully connected, False otherwise.
        """
        try:
            # Import the SX126x module from LoRaRF
            from LoRaRF import SX126x
            
            # Initialize the module
            self.lora = SX126x()
            logger.info(f"Initializing LoRa receiver using SPI")
            
            # Begin LoRa radio and set pins
            begin_result = self.lora.begin(LORA_SPI_BUS, LORA_SPI_CS, LORA_RESET_PIN, 
                                 LORA_BUSY_PIN, LORA_IRQ_PIN, LORA_TXEN_PIN, LORA_RXEN_PIN)
            if not begin_result:
                logger.error("Failed to initialize LoRa module")
                return False
                
            # Configure DIO2 as RF switch
            self.lora.setDio2RfSwitch()
            
            # Configure the module
            if self._configure_module():
                self.connected = True
                logger.info("LoRa receiver connected and configured via SPI")
                return True
            else:
                logger.error("Failed to configure LoRa module")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to LoRa module: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.connected = False
            return False
            
    def disconnect(self) -> None:
        """Disconnect from the LoRa module."""
        if self.connected:
            self.stop()
            self.lora = None
            self.connected = False
            logger.info("LoRa receiver disconnected")
            
    def start(self) -> bool:
        """
        Start LoRa receiver thread.
        
        Returns:
            bool: True if successfully started, False otherwise.
        """
        if not self.connected:
            logger.error("Cannot start LoRa receiver thread: not connected")
            return False
            
        if self.rx_thread is not None and self.rx_thread.is_alive():
            logger.warning("LoRa receiver thread already running")
            return True
            
        self.stop_event.clear()
        
        # Start receiver thread
        self.rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
        self.rx_thread.start()
        
        logger.info("LoRa receiver thread started")
        return True
        
    def stop(self) -> None:
        """Stop LoRa receiver thread."""
        self.stop_event.set()
        
        if self.rx_thread:
            self.rx_thread.join(timeout=2.0)
            
        logger.info("LoRa receiver thread stopped")
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback function for received messages.
        
        Args:
            callback: Function to call when a message is received
        """
        self.message_callbacks.append(callback)
        
    def get_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Get the next received message from the queue.
        
        Args:
            timeout: Timeout in seconds, or None to block indefinitely
            
        Returns:
            Message dictionary, or None if timeout occurs
        """
        try:
            return self.rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def get_stats(self) -> Dict[str, Any]:
        """Get receiver statistics."""
        return self.stats.copy()
        
    def _configure_module(self) -> bool:
        """
        Configure the LoRa module with the settings from the config.
        
        Returns:
            bool: True if successfully configured, False otherwise.
        """
        try:
            # Set frequency
            self.lora.setFrequency(self.config["frequency"])
            
            # Set RX gain
            self.lora.setRxGain(self.lora.RX_GAIN_BOOSTED)  # Use boosted gain for better reception
            
            # Set modulation parameters
            self.lora.setLoRaModulation(
                self.config["spreading_factor"],
                self.config["bandwidth"],
                self.config["coding_rate"]
            )
            
            # Set packet parameters
            self.lora.setLoRaPacket(
                self.lora.HEADER_EXPLICIT,
                self.config["preamble_length"],
                0,  # Variable payload length
                self.config["crc"]
            )
            
            # Set sync word
            self.lora.setSyncWord(self.config["sync_word"])
            
            # Other configuration as needed
            logger.info("LoRa module configured for reception")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure LoRa module: {e}")
            return False
            
    def _rx_worker(self) -> None:
        """
        Worker thread function for receiving LoRa packets.
        """
        logger.info("LoRa receiver worker started")
        
        while not self.stop_event.is_set():
            try:
                # Request for receiving new LoRa packet
                self.lora.request()
                
                # Wait for incoming LoRa packet (with timeout)
                result = self.lora.wait(0.1)  # 100ms timeout
                
                if result:
                    # Packet received
                    payload = bytearray()
                    
                    # Read all available data
                    while self.lora.available():
                        payload.append(self.lora.read())
                    
                    # Update stats
                    self.stats["rx_packets"] += 1
                    self.stats["rx_bytes"] += len(payload)
                    self.stats["last_rssi"] = self.lora.packetRssi()
                    self.stats["last_snr"] = self.lora.snr()
                    self.stats["last_rx_time"] = time.time()
                    
                    # Log packet reception
                    logger.info(f"Received LoRa packet, RSSI: {self.stats['last_rssi']:.1f} dBm, "
                               f"SNR: {self.stats['last_snr']:.1f} dB, Size: {len(payload)} bytes")
                    
                    # Process the packet
                    try:
                        # Try to decrypt if encryption is used
                        decrypted_payload = self._decrypt(bytes(payload))
                        
                        # Process as JSON
                        message = self._process_packet(decrypted_payload)
                        
                        # Add to queue if valid
                        if message and not self.rx_queue.full():
                            self.rx_queue.put(message)
                            
                            # Call registered callbacks
                            for callback in self.message_callbacks:
                                try:
                                    callback(message)
                                except Exception as e:
                                    logger.error(f"Error in message callback: {e}")
                    except Exception as e:
                        logger.error(f"Error processing packet: {e}")
                        self.stats["rx_errors"] += 1
                
                # Check for errors
                status = self.lora.status()
                if status == self.lora.STATUS_CRC_ERR:
                    logger.warning("CRC error in received packet")
                    self.stats["rx_errors"] += 1
                elif status == self.lora.STATUS_HEADER_ERR:
                    logger.warning("Header error in received packet")
                    self.stats["rx_errors"] += 1
                    
                # Prevent CPU hogging if in non-continuous mode
                if not LORA_RX_CONTINUOUS:
                    time.sleep(0.01)  # 10ms pause between reception attempts
                    
            except Exception as e:
                logger.error(f"Error in LoRa receive thread: {e}")
                time.sleep(1.0)  # Pause on error to prevent log flooding
        
        logger.info("LoRa receiver worker stopped")
    
    def _process_packet(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """
        Process a received packet payload.
        
        Args:
            payload: Decrypted payload bytes
            
        Returns:
            Parsed message dictionary, or None if invalid
        """
        try:
            # Try to parse as JSON first
            try:
                message = json.loads(payload.decode('utf-8'))
                logger.debug(f"Received JSON message: {message}")
                return message
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Not JSON, try binary format
                pass
                
            # Try to parse as binary packet for minimal format
            try:
                from shared.packet_parser import PacketParser
                latitude, longitude, timestamp = PacketParser.decode_minimal_packet(payload)
                
                # Convert to standard message format
                message = {
                    "lat": latitude,
                    "lon": longitude,
                    "ts": timestamp,
                    "binary_format": True
                }
                logger.debug(f"Received binary format message: {message}")
                return message
            except Exception as e:
                logger.error(f"Failed to parse binary packet: {e}")
                
            # If we get here, we couldn't parse the packet
            logger.warning(f"Unknown packet format, raw bytes: {payload.hex()}")
            return None
                
        except Exception as e:
            logger.error(f"Error processing packet: {e}")
            return None
    
    def _decrypt(self, data: bytes) -> bytes:
        """
        Decrypt packet data.
        
        Args:
            data: Encrypted data
            
        Returns:
            Decrypted data
            
        Note: This is a simple placeholder. In a real implementation, 
        you would use proper encryption like AES-128.
        """
        # Placeholder for decryption - in a real implementation
        # this would use the same encryption as the transmitter
        # such as AES-CTR mode
        try:
            # If encryption is used
            if self.encryption_key:
                from Crypto.Cipher import AES
                from Crypto.Util.Padding import unpad
                
                # For simplicity, we're using a fixed IV
                # In a real implementation, you might derive this from packet metadata
                iv = b'\x00' * 16
                
                # Create AES cipher in ECB mode (simplistic)
                key = self.encryption_key.encode('utf-8')
                if len(key) < 16:
                    key = key.ljust(16, b'\0')  # Pad key if needed
                elif len(key) > 16:
                    key = key[:16]  # Truncate if too long
                    
                cipher = AES.new(key, AES.MODE_ECB)
                
                # In a real implementation, we'd use a proper mode like CTR
                # which doesn't need padding
                
                # Decrypt the data
                try:
                    # Try with padding
                    decrypted = unpad(cipher.decrypt(data), AES.block_size)
                except Exception:
                    # Try without padding if that fails
                    decrypted = cipher.decrypt(data)
                
                return decrypted
            else:
                # No encryption
                return data
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            # If decryption fails, return the original data
            return data
