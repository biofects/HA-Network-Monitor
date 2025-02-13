# 🌐 UniFi Network Monitor for Home Assistant

## 🔍 About
This is essentially a security tool that can alert you if any of your home devices are trying to communicate with known malicious servers, which could indicate a compromised device or malware infection.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release][releases-shield]][releases]
![Project Maintenance][maintenance-shield]

## 💸 Donations Welcome!

If you find this integration useful, please consider donating. Your support is greatly appreciated!

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=TWRQVYJWC77E6)

---

## ✨ Features
    - **Live Network Monitoring**: Detects outbound traffic to **malicious IPs**.
    - **Beaconing Detection**: Identifies repeated small requests to the same IP.
    - **Whitelist**: Exclude trusted devices.
    - **Home Assistant UI Configuration**.

## 🚀 Installation

### HACS Installation (Recommended)

    1. Open HACS in your Home Assistant instance
    2. Click on "Integrations"
    3. Click the three dots in the top right corner
    4. Select "Custom repositories"
    5. Add this repository URL
    6. Select "Integration" as the category
    7. Click "Add"
    8. Find "HA Network Monitor" in the integration list
    9. Click "Download"
    10. Restart Home Assistant

### Manual Installation

    1. Download the latest release
    2. Copy the `custom_components/ha_network_monitor` directory to your Home Assistant's `custom_components` directory
    3. Restart Home Assistant

## ⚙️ Configuration

    1. Go to Configuration > Integrations
    2. Click "+" to add a new integration
    3. Search for "HA Network Monitor"
    4. Enter the following details:


## 🤝 Contributing

Feel free to contribute to this project. Please read the contributing guidelines before making a pull request.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.


[releases-shield]: https://img.shields.io/github/release/tfam/ha_network_monitor.svg
[releases]: https://github.com/tfam/ha_network_monitorreleases
[maintenance-shield]: https://img.shields.io/maintenance/yes/2024.svg
