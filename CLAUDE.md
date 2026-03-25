# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python bot that reduces Amsterdam parking costs by splitting long sessions into shorter intervals with breaks. Uses Selenium WebDriver to automate `parkeervergunningen.amsterdam.nl`.

## Key Commands

### Running the Bot
```bash
# Book sessions for today
python park.py "13:00-14:00"

# Book for tomorrow
python park.py "13:00-14:00" --tomorrow

# Preview sessions without booking
python park.py "13:00-14:00" --dry-run

# Check balance and time remaining
python park.py --status

# Custom session duration and break time
python park.py "13:00-14:00" --session=15 --break=3

# Override plate and meter
python park.py "13:00-14:00" --plate=ABC123 --meter=19850

# Debug mode
python park.py "13:00-14:00" --verbose
```

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
# edit config.json with your credentials
```

### Configuration (`config.json`)
```json
{
  "username": "your_meldcode",
  "password": "your_pincode",
  "license_plate": "ABC123",
  "meter_number": "19850",
  "session_duration_minutes": 10,
  "break_duration_minutes": 5,
  "headless": false,
  "timeout": 15
}
```

## Architecture

### Core Classes

- **`ParkingBot`** (`park.py`): main automation engine — login, permit detection, session booking
- **`ParkingSession`**: start/end datetime pair with computed `minutes` property

### Web Automation Flow

1. Login at `/login-ssp`
2. Navigate to `/permits`, click `button[data-cy='linkTable']`, extract permit ID from resulting URL
3. For each session:
   - Navigate to `/permit/{id}/start-parking-session`
   - Click "Voer mijn eigen eindtijd in" **first** (reveals end-time input; also resets start time to now)
   - Set start time **after** the above click
   - Set end time
   - Fill meter number and license plate
   - Submit and wait for redirect

### Key Implementation Notes

- **Start time ordering**: the "custom end time" link triggers a React re-render that resets the start field to now. Always reveal the end-time input before setting the start time.
- **Permit detection**: the permits list renders as a React table with no `<a>` tags. Use `button[data-cy='linkTable']` and extract the ID from the URL after navigation.
- **ChromeDriver**: managed automatically by Selenium (no hardcoded path needed).
- **Datetime inputs**: set via React's native HTMLInputElement value setter + dispatched `input`/`change` events.

## Testing

```bash
python park.py "13:00-16:00" --dry-run
```
