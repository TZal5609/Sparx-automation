# Sparx Maths Automation Tool

# Sparx Maths Automation Tool

A Python script that automatically completes tasks on Sparx Maths platform.

## Features

### Core Automation
- ✅ Auto-login with saved credentials
- 🔍 Intelligent task detection (skips completed tasks)
- 📚 Handles both normal and Bookwork questions
- ⚡ Automatic answer submission
- 📊 Progress tracking

### Technical Implementation
- **Precise Element Location**:
  - 🎯 XPath-based DOM navigation
  - 🛡️ CSS selector fallbacks
  - ⏳ Dynamic waiting system
- **Error Recovery**:
  - 🌐 Network interruption handling
  - 💀 Stale element protection
  - 🔄 Auto-retry failed operations
- **Browser Control**:
  - 🖱️ Smooth scrolling simulation
  - ⏱️ Human-like interaction timing
  - 👻 Headless mode support

## Requirements
- Python 3.8+
- Chrome/Firefox browser
- Required packages:
  ```plaintext
  selenium
  pyautogui
  cryptography
Installation
Clone repository:

bash
Copy
git clone https://github.com/yourusername/sparx-automation.git
cd sparx-automation
Install dependencies:

bash
Copy
pip install -r requirements.txt
Configure credentials in config.ini

Usage
bash
Copy
python main.py [--headless] [--bookwork]
Options:
Flag	Description
--headless	Run without browser GUI
--bookwork	Prioritize Bookwork questions
Logging
📝 Detailed activity logs in /logs

📸 Screenshots on error (in /errors)

📈 Runtime metrics recording

Disclaimer
⚠️ Note: This tool is for educational purposes only. Use responsibly and in compliance with Sparx Maths' terms of service.



