#!/bin/bash

# Navigate to the script's directory to ensure correct relative paths
cd "$(dirname "$0")"

# Check for and install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Skipping dependency installation."
fi

# Run the automated analysis script
echo "Starting automated analysis..."
python autorun.py
