# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based automation bot for Amsterdam parking that optimizes parking costs by splitting long sessions into shorter intervals with breaks. The bot uses Selenium WebDriver to automate the Amsterdam parking website.

## Key Commands

### Running the Bot
```bash
# Basic usage - book parking for today
python amsterdam_parking_bot.py "13:00-14:00"

# Book for tomorrow
python amsterdam_parking_bot.py "13:00-14:00" --tomorrow

# Test mode (calculate sessions without booking)
python amsterdam_parking_bot.py "13:00-14:00" --dry-run

# Custom session duration and break time
python amsterdam_parking_bot.py "13:00-14:00" --session=15 --max-break=3

# Debug mode with verbose logging
python amsterdam_parking_bot.py "13:00-14:00" --verbose
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
The bot requires a `config.json` file with Amsterdam parking credentials:
```json
{
  "username": "your_meldcode",
  "password": "your_pincode",
  "license_plate": "your_plate",
  "session_duration_minutes": 10,
  "max_break_minutes": 5,
  "headless": false
}
```

## Architecture

### Core Components

1. **AmsterdamParkingBot class** (`amsterdam_parking_bot.py`):
   - Main automation engine with centralized selectors for web elements
   - Handles login, session calculation, and booking workflow
   - Implements retry logic and error handling

2. **ParkingSession class**:
   - Represents individual parking sessions with start/end times
   - Used for session splitting calculations

3. **Selector Strategy**:
   - Uses multi-fallback element finding with predefined selectors
   - Adapts to website changes through multiple CSS/XPath strategies
   - Centralized in `SELECTORS` and `BUTTONS` dictionaries

### Key Features

- **Session Splitting Algorithm**: Calculates optimal short sessions with breaks to minimize cost
- **Robust Element Finding**: Multiple fallback strategies for web elements that change
- **12-Hour Time Conversion**: Handles Amsterdam parking website's 12-hour time format
- **Account Status Monitoring**: Tracks balance and monthly time budget
- **Retry Logic**: Individual session retries with exponential backoff

### Web Automation Flow

1. Login to Amsterdam parking portal
2. Navigate to new parking session form
3. For each calculated session:
   - Set date (today/tomorrow)
   - Set start/end times (converted to 12-hour format)
   - Select license plate
   - Confirm booking
   - Wait for confirmation

### Configuration Management

- Default config created automatically if missing
- Required fields: username, password
- Optional fields have sensible defaults
- Config validation on startup

## Development Notes

### WebDriver Setup
- Uses Chrome WebDriver at `/usr/bin/chromedriver`
- Headless mode configurable via config.json
- Includes standard Chrome options for stability

### Error Handling
- Custom exceptions: `InsufficientBalanceError`, `ConfigurationError`
- Graceful degradation: books what it can, reports failures
- Comprehensive logging with different levels

### Element Selection Strategy
The bot uses a multi-strategy approach for finding web elements:
1. Primary CSS selectors
2. XPath fallbacks
3. Generic type-based selectors
4. JavaScript click fallbacks for interaction issues

### Time Handling
- All times parsed to datetime objects
- Smart session calculation prevents tiny final sessions
- Handles edge cases like overnight parking
- Converts to 12-hour format for website compatibility

## Testing

Use `--dry-run` flag to test session calculations without actual booking:
```bash
python amsterdam_parking_bot.py "13:00-16:00" --dry-run
```

## Security Considerations

- Credentials stored in local config.json (not committed to git)
- No external data transmission beyond parking website
- Read-only account access (only books parking)
- Rate limiting to avoid being blocked by website