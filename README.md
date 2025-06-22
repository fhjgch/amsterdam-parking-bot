# 🚗 Amsterdam Parking Automation Bot

> **Save money on Amsterdam parking by automatically splitting long sessions into cheaper short intervals**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Selenium](https://img.shields.io/badge/selenium-4.15.0-green.svg)](https://selenium-python.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What This Does

Amsterdam parking costs can be significantly reduced by booking multiple short sessions with breaks instead of one long session. This bot automates that process:

**Instead of:** 1 hour session (13:00-14:00)  
**Books:** 4 sessions of 10 minutes each with 5-minute breaks  
→ `13:00-13:10`, `13:15-13:25`, `13:30-13:40`, `13:45-13:55`

## ✨ Key Features

- 🎛️ **Flexible Timing** - Configurable session duration and break times
- 🧠 **Smart Scheduling** - Never exceeds your maximum break limit  
- 💰 **Budget Tracking** - Monitors monthly parking allowance (150h default)
- 🔄 **Robust Retry Logic** - Individual session retries, books what it can
- 📊 **Detailed Reporting** - Shows exactly what succeeded/failed
- 🛡️ **Production Ready** - Multi-strategy element finding, handles website changes
- 🔍 **Debug Mode** - Test mode and verbose logging for troubleshooting

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/yourusername/amsterdam-parking-bot.git
cd amsterdam-parking-bot
pip install -r requirements.txt
```

### 2. Configure
```bash
cp config.example.json config.json
# Edit config.json with your meldcode and pincode
```

### 3. Test & Run
```bash
# Test configuration (no actual booking)
python park.py "13:00-14:00" --dry-run

# Book your first session
python park.py "13:00-14:00"
```

## 📊 Sample Output

```
[13:45:01] INFO: Starting parking automation for 13:00-14:00 (60 minutes)
[13:45:02] INFO: Calculated 4 sessions: 13:00-13:10, 13:15-13:25, 13:30-13:40, 13:45-13:55
[13:45:06] INFO: ✓ Successfully logged in
[13:45:07] INFO: ACCOUNT STATUS:
[13:45:07] INFO:            Balance: €45.20
[13:45:07] INFO:            Time Budget: 87h 23min remaining
[13:45:08] INFO: TIME BUDGET ANALYSIS (June 2025):
[13:45:08] INFO:            Days elapsed: 15/30 
[13:45:08] INFO:            Hours used: 62h 37min (4.2h/day average)
[13:45:08] INFO:            Status: 12h 23min below schedule ✓
[13:45:08] INFO:            Projected month-end: 125h total usage

[13:45:30] INFO: ============================================================
[13:45:30] INFO: BOOKING SUMMARY:
[13:45:30] INFO: Requested: 4 sessions
[13:45:30] INFO: Successful: 4
[13:45:30] INFO: Failed: 0
[13:45:31] INFO: FINAL ACCOUNT STATUS:
[13:45:31] INFO:            Balance: €37.96 (spent: €7.24)
[13:45:31] INFO:            Time Budget: 86h 23min
```

## 🎛️ Usage Examples

```bash
# Basic: 1-hour split into optimal sessions (today)
python park.py "13:00-14:00"

# Book for tomorrow
python park.py "13:00-14:00" --tomorrow

# Perfect timing for non-hour intervals
python park.py "13:10-14:00"
# → 13:10-13:20, 13:25-13:35, 13:40-13:50, 13:55-14:00

# Custom session duration for tomorrow
python park.py "09:00-17:00" --tomorrow --session=15

# Shorter breaks (max 5min still enforced)
python park.py "15:00-16:30" --max-break=3

# Test mode - calculate without booking
python park.py "13:00-14:00" --tomorrow --dry-run

# Debug mode with detailed logs
python park.py "13:00-14:00" --verbose
```

## ⚙️ Configuration

Key settings in `config.json`:

| Setting | Description | Default |
|---------|-------------|---------|
| `username` | Your meldcode | **Required** |
| `password` | Your pincode | **Required** |
| `session_duration_minutes` | Length per session | 10 |
| `max_break_minutes` | Max break between sessions | 5 |
| `balance_warning_threshold` | Warn below this amount (€) | 30.00 |
| `monthly_time_budget` | Hours per month | 150 |
| `headless` | Run browser in background | false |

## 🎯 Smart Features

### Intelligent Session Splitting
The bot automatically calculates optimal session timing:
- **Respects your max break limit** (never exceeds 5 minutes by default)
- **Fits exact end times** - no wasted time or missed periods
- **Handles edge cases** - works with any duration and timing

### Monthly Budget Tracking
Tracks your 150-hour monthly allowance:
```
TIME BUDGET ANALYSIS (June 2025):
           Days elapsed: 15/30 
           Hours used: 62h 37min (4.2h/day average)
           Status: 12h 23min below schedule ✓
           Projected month-end: 125h total usage
```

### Robust Error Handling
- **Individual session retries** - if session 2 fails, still books sessions 1, 3, 4
- **Balance monitoring** - stops before insufficient funds
- **Website changes** - multiple fallback strategies for finding elements
- **Detailed reporting** - know exactly what needs manual booking

## 🛡️ Safety & Reliability

### Production Features
- ✅ **Multi-strategy element finding** - adapts to website changes
- ✅ **Auto ChromeDriver management** - no manual driver installation
- ✅ **Rate limiting protection** - progressive delays between bookings
- ✅ **Comprehensive logging** - debug any issues easily
- ✅ **Configuration validation** - catches setup errors early

### Security
- 🔒 **Local credential storage** - config.json (not committed to git)
- 🔒 **No data transmission** - runs entirely on your machine
- 🔒 **Read-only account access** - only books parking, doesn't modify account

## 🐛 Troubleshooting

### Common Issues

**Configuration Error: "Username required"**
```bash
# Fix: Update config.json with your credentials
cp config.example.json config.json
nano config.json  # Add your meldcode and pincode
```

**Login Failed**
```bash
# Debug with visible browser
# Set in config.json: "headless": false
python park.py "13:00-14:00" --verbose
```

**Insufficient Balance**
```bash
# Top up your account manually, then run:
python park.py "13:00-14:00"
```

**Website Changes**
```bash
# The bot has multiple fallback strategies, but if it fails:
python park.py "13:00-14:00" --verbose
# Check the logs and open an issue with the error details
```

## 📚 Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed installation and configuration
- **[Code Explanation](docs/EXPLANATION.md)** - How the automation works
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## 🤝 Contributing

Contributions welcome! The Amsterdam parking website changes occasionally, so updates to element selectors may be needed.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Test your changes thoroughly
4. Commit your changes (`git commit -am 'Add new feature'`)
5. Push to the branch (`git push origin feature/improvement`)
6. Open a Pull Request

## ⚠️ Disclaimer

- **Personal use only** - This tool is for individual parking management
- **No warranty** - Use at your own risk, always verify bookings manually for critical sessions
- **Rate limiting** - Don't run excessively to avoid being blocked by the website
- **Terms compliance** - Ensure your usage complies with the Amsterdam parking website's terms of service

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for Amsterdam residents dealing with expensive parking costs
- Uses Selenium WebDriver for reliable automation
- Inspired by the need to optimize municipal parking systems

---

**💡 Pro Tip:** Start with `--dry-run` mode to test your timing strategy before booking real sessions!

**⭐ Found this useful?** Give it a star and share with fellow Amsterdam drivers!