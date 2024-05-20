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

# Check for Pip and install if not present
if ! command_exists pip3; then
    echo "Pip for Python 3 is not installed. Attempting to install Pip..."
    
    # Determine the OS and install pip accordingly
    if [ -f /etc/debian_version ]; then
        # Debian-based system
        sudo apt update
        sudo apt install -y python3-pip
    elif [ -f /etc/redhat-release ]; then
        # Red Hat-based system
        sudo yum install -y python3-pip
    else
        echo "Unsupported OS. Please install Pip manually and try again."
        exit 1
    fi
    
    # Verify pip installation
    if ! command_exists pip3; then
        echo "Pip installation failed. Please install Pip manually and try again."
        exit 1
    fi
fi

# Clone the repository if it doesn't already exist
if [ ! -d "$REPO_DIR" ]; then
    echo "Cloning the SkyLaunch repository..."
    git clone $REPO_URL
else
    echo "SkyLaunch directory already exists. Skipping clone."
fi

# Navigate into the repository directory
cd $REPO_DIR

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Run the Python script
echo "Running SkyLaunch..."
python3 main.py
