#!/bin/bash

echo "Starting Coincine..."

# Start Backend
echo "Starting Backend Server..."
# Run uvicorn in the background
python3 -m uvicorn backend.app.main:app --reload &
BACKEND_PID=$!

# Wait for server to initialize
sleep 3

# Open Frontend
echo "Launching Frontend..."
# Check OS for the correct open command
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "http://localhost:8000/"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:8000/"
else
    echo "Could not detect OS to open browser automatically."
    echo "Please open http://localhost:8000/ manually."
fi

echo "App is up and running!"

# Keep the script alive if needed or wait for background process
# If you want the script to end and leave the backend running:
# disown $BACKEND_PID
# exit 0

# If you want the script to stay open to manage the process:
wait $BACKEND_PID
