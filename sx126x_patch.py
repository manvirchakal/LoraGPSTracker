#!/usr/bin/env python3
"""
Patch script for the SX126x module to make it compatible with Raspberry Pi 5.
This script modifies the SX126x.py file to use the lgpio library instead of
RPi.GPIO, which is not fully compatible with Raspberry Pi 5.

Usage:
    python3 sx126x_patch.py
"""

import os
import shutil
import sys

# Path to the original SX126x.py file
SX126X_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'sx126x_lorawan_hat_code/python/lora/LoRaRF/SX126x.py'
)

# Path to the backup file
BACKUP_PATH = SX126X_PATH + '.backup'

# Make a backup of the original file if it doesn't exist
if not os.path.exists(BACKUP_PATH):
    print(f"Creating backup of {SX126X_PATH} to {BACKUP_PATH}")
    shutil.copy2(SX126X_PATH, BACKUP_PATH)
else:
    print(f"Backup file {BACKUP_PATH} already exists, using it as reference")

# Read the original content
with open(BACKUP_PATH, 'r') as file:
    original_content = file.read()

# Modifications to make the file compatible with Raspberry Pi 5
# 1. Replace RPi.GPIO with lgpio
# 2. Update pin setup and GPIO control methods

# Replace imports
modified_content = original_content.replace(
    "import RPi.GPIO",
    "try:\n    import lgpio\n    gpio = lgpio\nexcept ImportError:\n    import RPi.GPIO as gpio"
)

# Remove the line that sets up GPIO
modified_content = modified_content.replace(
    "gpio = RPi.GPIO",
    "# gpio is already imported above"
)

# Remove the mode setting
modified_content = modified_content.replace(
    "gpio.setmode(RPi.GPIO.BCM)",
    "# No need to set mode with lgpio"
)

# Update the modified content to handle lgpio's different API
modified_content = modified_content.replace(
    "gpio.setup(reset, gpio.OUT)",
    "try:\n            gpio.setup(reset, gpio.OUT)  # RPi.GPIO\n        except AttributeError:\n            # lgpio uses different API\n            self._lgpio_handle = gpio.gpiochip_open(0)\n            gpio.gpio_claim_output(self._lgpio_handle, reset)\n            # Set up other pins for lgpio"
)

# Fix the input/output pin setup for lgpio
modified_content = modified_content.replace(
    "gpio.setup(busy, gpio.IN)",
    "try:\n            gpio.setup(busy, gpio.IN)  # RPi.GPIO\n        except AttributeError:\n            # Already set up lgpio above\n            gpio.gpio_claim_input(self._lgpio_handle, busy)"
)

# Fix the cleanup for lgpio
modified_content = modified_content.replace(
    "gpio.cleanup()",
    "try:\n        gpio.cleanup()  # RPi.GPIO\n    except AttributeError:\n        # lgpio uses different cleanup\n        if hasattr(self, '_lgpio_handle'):\n            gpio.gpiochip_close(self._lgpio_handle)"
)

# Fix GPIO input for lgpio
modified_content = modified_content.replace(
    "gpio.input(self._busy) == gpio.HIGH",
    "self._gpio_read(self._busy) == gpio.HIGH"
)

# Add helper method for GPIO read operations
modified_content = modified_content.replace(
    "# callback functions",
    """# Helper method for GPIO read that works with both RPi.GPIO and lgpio
    def _gpio_read(self, pin):
        try:
            return gpio.input(pin)  # RPi.GPIO
        except AttributeError:
            # lgpio uses different API
            return gpio.gpio_read(self._lgpio_handle, pin)
    
    # callback functions"""
)

# Fix GPIO output for lgpio
modified_content = modified_content.replace(
    "gpio.output(self._reset, gpio.LOW)",
    "self._gpio_write(self._reset, gpio.LOW)"
)

modified_content = modified_content.replace(
    "gpio.output(self._reset, gpio.HIGH)",
    "self._gpio_write(self._reset, gpio.HIGH)"
)

# Add helper method for GPIO write operations
modified_content = modified_content.replace(
    "# Helper method for GPIO read that works with both RPi.GPIO and lgpio",
    """# Helper method for GPIO write that works with both RPi.GPIO and lgpio
    def _gpio_write(self, pin, value):
        try:
            gpio.output(pin, value)  # RPi.GPIO
        except AttributeError:
            # lgpio uses different API
            gpio.gpio_write(self._lgpio_handle, pin, value)
            
    # Helper method for GPIO read that works with both RPi.GPIO and lgpio"""
)

# Write the modified content to the original file
with open(SX126X_PATH, 'w') as file:
    file.write(modified_content)

print(f"Successfully patched {SX126X_PATH} for Raspberry Pi 5 compatibility!")
print("You can now run your SX126x code with Raspberry Pi 5.")
print("\nIf you encounter any issues, you can restore the original file using:")
print(f"  cp {BACKUP_PATH} {SX126X_PATH}")
print("\nTo run the test script:")
print("  python3 sx126x_test.py") 