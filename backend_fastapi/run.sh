#!/bin/bash
# Start the FastAPI backend server
# This script ensures the server starts from the correct directory

cd "$(dirname "$0")"
VENV_PATH="../.venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Start the server
$VENV_PATH/bin/python -m uvicorn main:app --reload --port 8000
