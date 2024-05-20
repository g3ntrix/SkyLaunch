# SkyLaunch

SkyLaunch is an interactive script for creating instances in Oracle Cloud Infrastructure (OCI). With SkyLaunch, you can easily configure and deploy virtual machines (VMs) while benefiting from automatic retries across multiple availability domains. This script is particularly advantageous for free-tier users who cannot use capacity reservations, ensuring that you can secure available capacity as soon as it becomes free.

## Features

- **Interactive Setup**: User-friendly prompts guide you through the initial configuration.
- **Configuration Management**: Easily update and view your configuration settings.
- **SSH Key Support**: Option to deploy instances with or without SSH public keys.
- **Automated Retries**: Automatically retries instance creation across multiple availability domains if capacity is unavailable.
- **Dynamic Resource Fetching**: Automatically fetches available shapes and images based on selected criteria.

## Advantages

- **Maximize Free-Tier Benefits**: Free-tier users can't use capacity reservations. SkyLaunch ensures you can secure capacity as soon as it becomes available.
- **Time-Saving**: Automates the process of checking and retrying instance creation, saving you from manual intervention.
- **Flexibility**: Supports various shapes and images, allowing you to choose the best configuration for your needs.
- **Ease of Use**: The script’s interactive nature makes it accessible even for those who are not familiar with OCI.

## Requirements

- Python 3.x
- `oci` and `colorama` Python packages

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/SkyLaunch.git
   cd SkyLaunch
