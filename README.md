# Deezer ARL Extractor 🎧

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Powered%20by-Playwright-45ba4b.svg)](https://playwright.dev/)

A lightweight Python tool that automates the extraction of Deezer ARL cookies through browser automation using Playwright.

![Code Structure](https://img.shields.io/badge/Code%20Structure-Single%20File%20☕-brightgreen)

---

## 📌 Overview

Deezer ARL Extractor simplifies the process of retrieving valid ARL cookies from Deezer accounts by automating the login procedure in a headless (or optionally visible) Chromium session.
It is designed for developers, researchers, and technical users who need to automate session handling for integration, testing, or data retrieval.

> ⚠️ **Note**: This tool requires manual user interaction to solve CAPTCHA challenges during login (see below for an example).

---

## 🚀 Feature Checklist

- [x] Standalone script in a single file (`main.py`)
- [x] Quick installation with minimal dependencies
- [x] Easy configuration through `sessions.json`
- [x] Secure session and credential management
- [x] Automatic screenshot capture on errors
- [x] Support for multiple accounts with parallel processing
- [x] Manual CAPTCHA support during login
- [x] Detailed account-specific log generation
- [x] Automatic saving of extracted ARL cookies
- [ ] Automatic verification of ARL status
- [ ] Graphical User Interface (GUI) for easier use
- [ ] Local encryption of credentials
- [ ] Export results to CSV or HTML
- [ ] Full multiplatform compatibility
- [ ] Proxy configuration support
- [ ] Advanced configuration customization (timeouts, retries)
- [ ] Support for scheduled execution (cron job or scheduler)
- [ ] Automate CAPTCHA completion using [Anti Captcha](https://anti-captcha.com) or [2captcha](https://2captcha.com)

---

## 📦 Prerequisites

- Python **3.8 or later**
- [Playwright](https://playwright.dev/python/) (installed automatically via script)

---

## ⚙️ Installation

Follow the steps below to get started:

### 1. Clone the Repository
```bash
git clone https://github.com/tutitoos/deezer_arl_extractor.git
cd deezer_arl_extractor
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install
```

---

## 🔧 Configuration

### Step 1: Prepare the Session File
Copy the example config:
```bash
cp data/sessions.json.example data/sessions.json
```

### Step 2: Define Accounts
Edit `data/sessions.json` with your credentials:
```json
[
  {
    "email": "your_email@domain.com",
    "password": "your_password",
    "arl": null,
    "lastUpdated": null,
    "enable": true
  }
]
```

> Only accounts with `"enable": true` will be processed.

---

## 🖥️ Usage

Execute the script with:

```bash
python main.py
```

If credentials are valid and no errors occur, the `arl` field will be updated in the same JSON file.

---

## 🧩 CAPTCHA Handling (Manual Step)

Due to security measures, **Deezer may require CAPTCHA verification** during login.

When prompted, the Chromium browser will open and you must complete the CAPTCHA manually:

![Captcha Example](https://i.imgur.com/PhzNXVt.png)

> Once verified, the script will resume automatically.

---

## 📂 Output Structure

- **ARL Cookies**: stored in `data/sessions.json`
- **Logs**: located at `logs/<email>/logs.txt`
- **Screenshots**: saved in `screenshots/<email>/` with timestamped filenames

---

## 🛡️ License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This tool is intended for **educational and personal use only**.
You are solely responsible for how you use it. Respect the terms of service of any platform you interact with.
