#!/usr/bin/env python3
"""
Example Runner

This script allows running examples from the project root with proper path configuration.
Usage: python run_example.py <example_name>
Example: python run_example.py simple_gps_example
"""

import os
import sys
import importlib
import argparse

def main():
    """Parse arguments and run the selected example."""
    parser = argparse.ArgumentParser(description="Run LoRa GPS Tracker examples")
    parser.add_argument("example", 
                       choices=["simple_gps_example", "gps_example", "lora_gps_example", "gps_only_example"], 
                       help="Name of the example to run (without .py extension)")
    args = parser.parse_args()
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Add the project root to the Python path
    sys.path.insert(0, project_root)
    
    # Add the examples directory to the Python path
    examples_dir = os.path.join(project_root, "examples")
    sys.path.insert(0, examples_dir)
    
    # Import and run the selected example's main function
    try:
        # Import the module
        example_module = importlib.import_module(args.example)
        
        # Run the main function
        if hasattr(example_module, "main"):
            example_module.main()
        else:
            print(f"Error: No main() function found in {args.example}.py")
    except ImportError:
        print(f"Error: Could not import example '{args.example}'")
        print(f"Make sure '{args.example}.py' exists in the examples directory")
    except Exception as e:
        print(f"Error running example: {e}")

if __name__ == "__main__":
    main() 