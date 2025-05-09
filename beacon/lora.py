"""
LoRa Module for GPS Tracker

This module provides functionality for LoRa communication, handling transmit and receive
operations, message queuing, and interfacing with the LoRa hardware.
"""

import threading
import queue
import time
import logging
import json
import base64
from typing import Dict, Any, Optional, List, Tuple, Callable
import os
import sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from beacon.config import (
    LORA_CONFIG, LORA_ENCRYPTION_KEY, LORA_MESSAGE_QUEUE_SIZE, 
    LORA_TX_INTERVAL, LORA_ACK_TIMEOUT, LORA_RETRIES, 
    TRACKER_ID, SERVER_ID, LORA_USING_SPI, 
    LORA_SPI_BUS, LORA_SPI_CS, LORA_RESET_PIN, 
    LORA_BUSY_PIN, LORA_IRQ_PIN, LORA_TXEN_PIN, LORA_RXEN_PIN,
    LORA_USE_POLLING
)

# Add the necessary module path for LoRaRF
sx126x_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sx126x_lorawan_hat_code/python/lora'))
if sx126x_path not in sys.path:
    sys.path.insert(0, sx126x_path)

# Set up logging
logger = logging.getLogger(__name__)

class LoRaModule:
    """
    Class for interfacing with a LoRa module via SPI connection.
    
    This class provides an interface to a LoRa radio module connected via SPI.
    It handles initialization, configuration, message transmission and reception,
    as well as basic encryption for secure communication.
    """

    def __init__(self):
        """Initialize the LoRa module."""
        # Configuration values
        self.config = LORA_CONFIG
        self.encryption_key = LORA_ENCRYPTION_KEY
        
        # SPI module
        self.lora = None
        self.connected = False
        
        # Message handling
        self.tx_queue = queue.Queue(maxsize=LORA_MESSAGE_QUEUE_SIZE)
        self.rx_queue = queue.Queue(maxsize=LORA_MESSAGE_QUEUE_SIZE)
        self.message_callbacks = {}
        self.ack_events = {}
        self.message_id_counter = 0
        
        # Threads
        self.rx_thread = None
        self.tx_thread = None
        self.stop_event = threading.Event()
        
        # Stats
        self.stats = {
            "tx_packets": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "rx_bytes": 0,
            "tx_errors": 0,
            "rx_errors": 0,
            "last_rssi": 0,
            "last_snr": 0
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
            logger.info(f"Initializing LoRa module using SPI")
            
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
                logger.info("LoRa module connected and configured via SPI")
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
            try:
                if self.lora:
                    self.lora.sleep()
            except Exception as e:
                logger.error(f"Error during LoRa disconnect: {e}")
            self.lora = None
            self.connected = False
            logger.info("LoRa module disconnected")
            
    def start(self) -> bool:
        """
        Start LoRa communication threads.
        
        Returns:
            bool: True if successfully started, False otherwise.
        """
        if not self.connected:
            logger.error("Cannot start LoRa threads: not connected")
            return False
            
        if self.rx_thread is not None and self.rx_thread.is_alive():
            logger.warning("LoRa threads already running")
            return True
            
        self.stop_event.clear()
        
        # Start receiver thread
        self.rx_thread = threading.Thread(target=self._receive_worker, daemon=True)
        self.rx_thread.start()
        
        # Start transmitter thread
        self.tx_thread = threading.Thread(target=self._tx_worker, daemon=True)
        self.tx_thread.start()
        
        logger.info("LoRa communication threads started")
        return True
        
    def stop(self) -> None:
        """Stop LoRa communication threads."""
        self.stop_event.set()
        
        # Set module to sleep mode before stopping threads
        if self.connected and self.lora:
            try:
                self.lora.sleep()
            except Exception as e:
                logger.error(f"Error putting LoRa module to sleep: {e}")
        
        if self.rx_thread:
            self.rx_thread.join(timeout=2.0)
            
        if self.tx_thread:
            self.tx_thread.join(timeout=2.0)
            
        logger.info("LoRa communication threads stopped")
        
    def send_message(self, message_type: str, data: Dict[str, Any], 
                    destination: str = SERVER_ID, require_ack: bool = True) -> Optional[str]:
        """
        Queue a message for transmission.
        
        Args:
            message_type: Type of message (e.g., 'position', 'heartbeat', 'alert')
            data: Message payload as a dictionary
            destination: Destination device ID
            require_ack: Whether to require an acknowledgment
            
        Returns:
            str: Message ID if successfully queued, None otherwise
        """
        if not self.connected:
            logger.error("Cannot send message: not connected")
            return None
            
        # Generate message ID
        message_id = f"{TRACKER_ID}_{int(time.time())}_{self.message_id_counter}"
        self.message_id_counter = (self.message_id_counter + 1) % 10000
        
        # Prepare message
        message = {
            "id": message_id,
            "src": TRACKER_ID,
            "dst": destination,
            "type": message_type,
            "time": time.time(),
            "ack_req": require_ack,
            "data": data
        }
        
        # Set up ACK event if needed
        if require_ack:
            self.ack_events[message_id] = threading.Event()
        
        try:
            self.tx_queue.put(message, block=False)
            logger.debug(f"Message {message_id} queued for transmission")
            return message_id
        except queue.Full:
            logger.error("TX queue full, message not sent")
            return None
            
    def wait_for_ack(self, message_id: str, timeout: float = LORA_ACK_TIMEOUT) -> bool:
        """
        Wait for acknowledgment of a sent message.
        
        Args:
            message_id: Message ID to wait for acknowledgment
            timeout: Timeout in seconds
            
        Returns:
            bool: True if ACK received, False otherwise
        """
        if message_id not in self.ack_events:
            logger.warning(f"No ACK event found for message {message_id}")
            return False
            
        return self.ack_events[message_id].wait(timeout)
        
    def register_callback(self, message_type: str, callback: Callable) -> None:
        """
        Register a callback function for a specific message type.
        
        Args:
            message_type: Type of message to register callback for
            callback: Function to call when message is received
        """
        self.message_callbacks[message_type] = callback
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get communication statistics.
        
        Returns:
            Dict: Dictionary containing communication statistics
        """
        return self.stats.copy()
        
    def _configure_module(self) -> bool:
        """
        Configure the LoRa module with the specified parameters.
        
        Returns:
            bool: True if configuration successful, False otherwise
        """
        try:
            # Set frequency
            self.lora.setFrequency(self.config['frequency'])
            
            # Set spreading factor, bandwidth, and coding rate
            self.lora.setLoRaModulation(
                self.config['spreading_factor'],
                self.config['bandwidth'],
                self.config['coding_rate']
            )
            
            # Set packet parameters
            self.lora.setLoRaPacket(
                self.lora.HEADER_EXPLICIT,
                self.config['preamble_length'],
                255,  # max payload length
                self.config['crc']
            )
            
            # Set sync word
            self.lora.setSyncWord(self.config['sync_word'])
            
            # Set TX power
            self.lora.setTxPower(self.config['power'], self.lora.TX_POWER_SX1262)
            
            return True
                
        except Exception as e:
            logger.error(f"Error configuring LoRa module: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def _receive_worker(self) -> None:
        """Worker thread for receiving messages."""
        logger.info("LoRa RX worker started")
        
        while not self.stop_event.is_set():
            try:
                if LORA_USE_POLLING:
                    # Use polling mode for receiving
                    if self.lora.getStatus() == self.lora.STATUS_RX_DONE:
                        # Read the received data
                        data = self.lora.read()
                        if data:
                            # Process the received data
                            self._process_received_data(data)
                    else:
                        # Start receiving if not already in RX mode
                        self.lora.setRx(0)  # 0 means continuous receive mode
                        time.sleep(0.001)  # Small delay to prevent busy waiting
                else:
                    # Use interrupt mode for receiving
                    self.lora.setRx(0)  # 0 means continuous receive mode
                    self.lora.wait()
                    
            except Exception as e:
                logger.error(f"Error in receive worker: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(1)  # Wait before retrying
                
        logger.info("LoRa RX worker stopped")
                
    def _tx_worker(self) -> None:
        """Worker thread for transmitting messages."""
        logger.info("LoRa TX worker started")
        
        while not self.stop_event.is_set():
            try:
                # Get next message from queue with timeout
                try:
                    message = self.tx_queue.get(block=True, timeout=0.5)
                except queue.Empty:
                    continue
                    
                # Try to send the message
                success = False
                retries = 0
                
                while retries < LORA_RETRIES and not success and not self.stop_event.is_set():
                    # Transmit the message
                    if self._transmit_message(message):
                        success = True
                        
                        # If ACK required, wait for it
                        if message.get("ack_req", False):
                            message_id = message["id"]
                            if message_id in self.ack_events:
                                # Wait for ACK using polling
                                start_time = time.time()
                                while (time.time() - start_time) < LORA_ACK_TIMEOUT:
                                    if self.lora.available():
                                        ack_data = ""
                                        while self.lora.available():
                                            ack_data += chr(self.lora.read())
                                        try:
                                            ack_msg = json.loads(ack_data)
                                            if ack_msg.get("type") == "ack" and ack_msg.get("ack_id") == message_id:
                                                self.ack_events[message_id].set()
                                                break
                                        except json.JSONDecodeError:
                                            pass
                                    time.sleep(0.01)
                                    
                                if not self.ack_events[message_id].is_set():
                                    logger.warning(f"No ACK received for message {message_id}, retry {retries+1}")
                                    success = False
                                    
                    if not success:
                        retries += 1
                        # Exponential backoff
                        backoff_time = 0.1 * (2 ** retries)
                        time.sleep(backoff_time)
                        
                # Log result
                if success:
                    logger.debug(f"Message {message['id']} transmitted successfully")
                    self.stats["tx_packets"] += 1
                else:
                    logger.error(f"Failed to transmit message {message['id']} after {retries} retries")
                    self.stats["tx_errors"] += 1
                    
                # Mark as done in the queue
                self.tx_queue.task_done()
                
                # Rate limiting
                time.sleep(LORA_TX_INTERVAL / 1000.0)  # Convert ms to seconds
                
            except Exception as e:
                logger.error(f"Error in TX worker: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(1.0)  # Avoid tight loop on error
                
        logger.info("LoRa TX worker stopped")
                
    def _transmit_message(self, message: Dict[str, Any]) -> bool:
        """
        Transmit a message via the LoRa module.
        
        Args:
            message: Message to transmit
            
        Returns:
            bool: True if transmission successful, False otherwise
        """
        try:
            # Serialize the message to JSON
            json_data = json.dumps(message)
            
            # Encrypt if needed
            if self.encryption_key:
                encrypted_data = self._encrypt(json_data)
                # Base64 encode
                payload = base64.b64encode(encrypted_data).decode('ascii')
            else:
                payload = json_data
                
            # Convert payload to a list of bytes for LoRaRF
            data_list = list(payload)
            for i in range(len(data_list)):
                data_list[i] = ord(data_list[i])
                
            # Begin packet transmission
            self.lora.beginPacket()
            self.lora.write(data_list, len(data_list))
            
            # Use polling mode instead of interrupts
            if LORA_USE_POLLING:
                self.lora.setTx(0)  # 0 means transmit until complete
                # Wait for transmission to complete using polling
                while self.lora.getStatus() != self.lora.STATUS_TX_DONE:
                    time.sleep(0.001)  # Small delay to prevent busy waiting
            else:
                self.lora.setTx(0)  # 0 means transmit until complete
                self.lora.wait()
            
            # Update stats
            self.stats["tx_bytes"] += len(payload)
            
            return True
            
        except Exception as e:
            logger.error(f"Error transmitting message: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def _process_packet(self, payload: str) -> None:
        """
        Process a received packet.
        
        Args:
            payload: Received packet data as string
        """
        try:
            # Check if the payload is encrypted
            if self.encryption_key:
                # Assume the payload is base64 encoded
                try:
                    encrypted_data = base64.b64decode(payload)
                    decrypted_data = self._decrypt(encrypted_data)
                    payload = decrypted_data
                except Exception as e:
                    logger.error(f"Failed to decrypt payload: {e}")
                    # Continue with the raw payload
            
            # Parse the JSON data
            message = json.loads(payload)
            
            # Check message destination
            if message.get('dst') not in [TRACKER_ID, 'broadcast']:
                logger.debug(f"Ignoring message for {message.get('dst')}")
                return
                
            # Handle acknowledgment
            if message.get('type') == 'ack':
                ack_id = message.get('ack_id')
                if ack_id in self.ack_events:
                    self.ack_events[ack_id].set()
                    logger.debug(f"Received ACK for message {ack_id}")
                return
                
            # Handle other message types
            message_type = message.get('type')
            if message_type in self.message_callbacks:
                # Process in a separate thread to avoid blocking
                threading.Thread(
                    target=self.message_callbacks[message_type],
                    args=(message,),
                    daemon=True
                ).start()
                
            # Send acknowledgment if requested
            if message.get('ack_req', False):
                self._send_ack(message)
                
            # Add to RX queue
            try:
                self.rx_queue.put(message, block=False)
            except queue.Full:
                logger.warning("RX queue full, message dropped")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message as JSON: {payload}")
        except Exception as e:
            logger.error(f"Error processing packet: {e}")
            
    def _send_ack(self, message: Dict[str, Any]) -> None:
        """
        Send an acknowledgment for a received message.
        
        Args:
            message: Message to acknowledge
        """
        ack_message = {
            "id": f"ack_{TRACKER_ID}_{int(time.time())}",
            "src": TRACKER_ID,
            "dst": message.get('src', 'unknown'),
            "type": "ack",
            "time": time.time(),
            "ack_req": False,
            "ack_id": message.get('id'),
            "data": {}
        }
        
        # Queue for transmission with high priority
        try:
            self.tx_queue.put(ack_message, block=False)
            logger.debug(f"ACK for message {message.get('id')} queued")
        except queue.Full:
            logger.error("TX queue full, ACK not sent")
            
    def _encrypt(self, data: str) -> bytes:
        """
        Encrypt a string using AES encryption.
        
        Args:
            data: Plain text data
            
        Returns:
            bytes: Encrypted data
        """
        try:
            key = self.encryption_key.encode('utf-8')
            # Use AES-128 if key is 16 bytes, AES-192 if 24 bytes, AES-256 if 32 bytes
            if len(key) not in [16, 24, 32]:
                # Truncate or pad to 16 bytes
                key = key[:16].ljust(16, b'\0')
                
            # Create cipher
            cipher = AES.new(key, AES.MODE_CBC)
            
            # Pad data
            data_bytes = data.encode('utf-8')
            padded_data = pad(data_bytes, AES.block_size)
            
            # Encrypt
            encrypted_data = cipher.encrypt(padded_data)
            
            # Return IV + encrypted data
            return cipher.iv + encrypted_data
            
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            # Return raw data on error
            return data.encode('utf-8')
            
    def _decrypt(self, data: bytes) -> str:
        """
        Decrypt data using AES decryption.
        
        Args:
            data: Encrypted data
            
        Returns:
            str: Decrypted text
        """
        try:
            key = self.encryption_key.encode('utf-8')
            # Use AES-128 if key is 16 bytes, AES-192 if 24 bytes, AES-256 if 32 bytes
            if len(key) not in [16, 24, 32]:
                # Truncate or pad to 16 bytes
                key = key[:16].ljust(16, b'\0')
                
            # Extract IV
            iv = data[:16]
            encrypted_data = data[16:]
            
            # Create cipher
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Decrypt
            decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            
            # Return as string
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            # Return raw data on error
            return data.decode('utf-8', errors='ignore')

    def _process_received_data(self, data: bytes) -> None:
        """
        Process received data from the LoRa module.
        
        Args:
            data: Received data as bytes
        """
        try:
            # Update stats
            self.stats["rx_packets"] += 1
            self.stats["rx_bytes"] += len(data)
            self.stats["last_rssi"] = self.lora.packetRssi()
            self.stats["last_snr"] = self.lora.snr()
            
            logger.debug(f"Received packet, RSSI: {self.stats['last_rssi']} dBm, SNR: {self.stats['last_snr']} dB")
            
            # Process the received data
            self._process_packet(data.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error processing received data: {e}")
            self.stats["rx_errors"] += 1
            time.sleep(1.0)  # Wait before retrying
