#!/bin/bash
#
# Setup script for SX1262 LoRaWAN/GNSS HAT on Raspberry Pi 5
#

set -e

echo "Installing required packages for SX1262 LoRaWAN/GNSS HAT..."

# Update package lists
sudo apt-get update

# Install Python dependencies
sudo apt-get install -y python3-pip python3-dev

# Install SPI and GPIO libraries
sudo apt-get install -y python3-spidev python3-lgpio

# Optional: install PyCryptodome for encryption
sudo pip3 install pycryptodome

# Enable SPI interface if not already enabled
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo "Enabling SPI interface..."
    sudo sed -i '$ a\dtparam=spi=on' /boot/config.txt
    echo "SPI interface has been enabled. You will need to reboot for this to take effect."
    REBOOT_NEEDED=1
fi

# Apply the patch to fix SX126x module for Raspberry Pi 5
echo "Applying patch to SX126x module for Raspberry Pi 5 compatibility..."
python3 sx126x_patch.py

# Make test script executable
chmod +x sx126x_test.py

echo "Setup complete!"

if [ "$REBOOT_NEEDED" == "1" ]; then
    echo "Please reboot your Raspberry Pi for changes to take effect."
    echo "After rebooting, run: python3 sx126x_test.py"
else
    echo "You can now run the test script: python3 sx126x_test.py"
fi 