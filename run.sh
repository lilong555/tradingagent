#!/bin/bash

# Navigate to the script's directory to ensure correct relative paths
cd "$(dirname "$0")"

# Add the project root to the PYTHONPATH
export PYTHONPATH=$(pwd)

# Run the automated analysis script
echo "Starting automated analysis..."
python autorun.py
