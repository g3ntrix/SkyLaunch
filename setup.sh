#!/bin/bash

# Define repository URL and directory
REPO_URL="https://github.com/g3ntrix/SkyLaunch.git"
REPO_DIR="SkyLaunch"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Git
if ! command_exists git; then
    echo "Git is not installed. Please install Git and try again."
    exit 1
fi

# Check for Python
if ! command_exists python3; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check for Pip
if ! command_exists pip3; then
    echo "Pip for Python 3 is not installed. Please install Pip and try again."
    exit 1
fi

# Clone the repository
echo "Cloning the SkyLaunch repository..."
git clone $REPO_URL

# Navigate into the repository directory
cd $REPO_DIR

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Run the Python script
echo "Running SkyLaunch..."
python3 main.py
