#!/bin/bash

# Navigate to the script's directory to ensure correct relative paths
cd "$(dirname "$0")"

# Run the automated analysis script
echo "Starting automated analysis..."
python autorun.py
