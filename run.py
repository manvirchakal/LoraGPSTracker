#!/usr/bin/env python3
"""
LoRa GPS Tracker Runner

This script provides a convenient way to run either the beacon (transmitter)
or tracker (receiver) component of the LoRa GPS Tracker system.
"""

import os
import sys
import argparse
import subprocess
import logging

def setup_logging():
    """Set up basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('run')

def check_environment():
    """Check if the environment is set up correctly."""
    logger = logging.getLogger('run')
    
    # Check if virtual environment is active
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.warning("Virtual environment not activated. It's recommended to run within the virtual environment.")
        
    # Check if required directories exist
    required_dirs = ['beacon', 'tracker', 'shared']
    missing_dirs = [d for d in required_dirs if not os.path.isdir(d)]
    
    if missing_dirs:
        logger.error(f"Missing required directories: {', '.join(missing_dirs)}")
        logger.error("Please run this script from the project root directory.")
        return False
        
    return True

def run_component(component, args):
    """
    Run the specified component.
    
    Args:
        component: 'beacon' or 'tracker'
        args: Command line arguments
    """
    logger = logging.getLogger('run')
    
    if component == 'beacon':
        script_path = os.path.join('beacon', 'main.py')
        logger.info("Starting beacon (transmitter) component...")
    else:  # tracker
        script_path = os.path.join('tracker', 'main.py')
        logger.info("Starting tracker (receiver) component...")
    
    # Build command with any additional arguments
    cmd = [sys.executable, script_path]
    
    if args.debug:
        cmd.append('--debug')
        
    if component == 'tracker' and args.simulate:
        cmd.append('--simulate')
    
    try:
        # Run the component
        process = subprocess.run(cmd)
        return process.returncode
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error running {component}: {e}")
        return 1

def main():
    """Main entry point."""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='Run LoRa GPS Tracker components')
    parser.add_argument('component', choices=['beacon', 'tracker'], 
                       help='Which component to run (beacon=transmitter, tracker=receiver)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--simulate', action='store_true', help='Simulate beacon signals (tracker only)')
    
    args = parser.parse_args()
    
    if not check_environment():
        return 1
        
    return run_component(args.component, args)

if __name__ == "__main__":
    sys.exit(main()) 