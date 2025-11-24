#!/bin/bash

# Start the Python backend API server
echo "Starting Trade Surveillance Backend API..."

# Navigate to the backend directory
cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start the Flask server
echo "Starting Flask server on http://localhost:5001"
python surveillance_api.py
