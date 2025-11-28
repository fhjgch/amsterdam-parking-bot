# Migration Guide: v1.x → v2.0

This guide helps you migrate from the old monolithic `amsterdam_parking_bot.py` to the new modular v2.0 architecture.

## Breaking Changes

### 1. Command Line Interface

**OLD (v1.x):**
```bash
python amsterdam_parking_bot.py "13:00-14:00" --tomorrow
```

**NEW (v2.0):**
```bash
amsterdam-parking book "13:00-14:00" --tomorrow
```

### 2. Configuration

**OLD:** Optional parameters with defaults
```python
bot = AmsterdamParkingBot("config.json")
```

**NEW:** Validated Pydantic configuration
```python
config = AppConfig.from_json("config.json")
bot = ParkingBot(config)
```

### 3. Dry Run

**OLD:**
```bash
python amsterdam_parking_bot.py "13:00-14:00" --dry-run
```

**NEW:**
```bash
amsterdam-parking book "13:00-14:00" --dry-run
# OR use calculate command
amsterdam-parking calculate "13:00-14:00"
```

## Step-by-Step Migration

### 1. Backup Your Config

```bash
cp config.json config.json.backup
```

### 2. Install New Version

```bash
# Create fresh virtual environment
python -m venv venv
source venv/bin/activate

# Install new version
pip install -e ".[dev]"
```

### 3. Initialize New Config

```bash
# Generate new config structure
amsterdam-parking init

# Or manually update your config.json
# The new format is backward compatible with most fields
```

### 4. Update Scripts/Automation

**OLD script:**
```python
from amsterdam_parking_bot import AmsterdamParkingBot

bot = AmsterdamParkingBot()
bot.book_parking_sessions("13:00-14:00")
```

**NEW script:**
```python
from amsterdam_parking.bot import ParkingBot
from amsterdam_parking.config import AppConfig
from amsterdam_parking.session_calculator import SessionCalculator

config = AppConfig.from_json("config.json")
calculator = SessionCalculator(
    config.session_duration_minutes,
    config.max_break_minutes
)

start, end = calculator.parse_time_range("13:00-14:00")
sessions = calculator.calculate_sessions(start, end)

bot = ParkingBot(config)
result = bot.book_sessions(sessions)
```

### 5. Update Cron Jobs

**OLD crontab:**
```cron
0 8 * * * cd /path/to/bot && python amsterdam_parking_bot.py "09:00-17:00"
```

**NEW crontab:**
```cron
0 8 * * * cd /path/to/bot && venv/bin/amsterdam-parking book "09:00-17:00"
```

## Feature Mapping

| Old Feature | New Equivalent |
|-------------|---------------|
| `--dry-run` | `--dry-run` or `calculate` command |
| `--tomorrow` | `--tomorrow` |
| `--session=N` | `--session N` |
| `--max-break=N` | `--max-break N` |
| `--verbose` | `--verbose` |
| `--config=path` | `--config path` |

## New Features in v2.0

### 1. Modular Architecture

```python
# Import only what you need
from amsterdam_parking.session_calculator import SessionCalculator
from amsterdam_parking.models import ParkingSession
```

### 2. Type Safety

```python
# Full type hints throughout
from amsterdam_parking.config import AppConfig

config: AppConfig = AppConfig(
    username="user",
    password="pass"
)
```

### 3. Rich CLI

```bash
# Beautiful table output
amsterdam-parking book "13:00-14:00" --dry-run

┏━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ # ┃ Session Time ┃ Duration ┃
┡━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1 │ 13:00-13:10  │  10 min  │
└───┴──────────────┴──────────┘
```

### 4. Better Error Handling

```python
try:
    config = AppConfig.from_json("config.json")
except FileNotFoundError:
    print("Config not found")
except ValueError as e:
    print(f"Invalid config: {e}")
```

### 5. Structured Logging

```python
# Structured JSON logs for production
logger.info("booking_session", session="13:00-13:10", attempt=1)
```

## Configuration Changes

### Old Config Fields → New Config Fields

| Old | New | Notes |
|-----|-----|-------|
| `username` | `username` | ✅ No change |
| `password` | `password` | ✅ No change |
| `license_plate` | `license_plate` | ✅ No change |
| `session_duration_minutes` | `session_duration_minutes` | ✅ Now validated (5-60) |
| `max_break_minutes` | `max_break_minutes` | ✅ Now validated (1-15) |
| `headless` | `headless` | ✅ No change |
| `timeout_seconds` | `timeout_seconds` | ✅ No change |
| N/A | `chromedriver_path` | ⭐ New: explicit path |
| N/A | `login_url` | ⭐ New: configurable URL |
| N/A | `new_session_url` | ⭐ New: configurable URL |
| N/A | `log_level` | ⭐ New: DEBUG/INFO/WARNING/ERROR |

### Example New Config

```json
{
  "username": "your_meldcode",
  "password": "your_pincode",
  "license_plate": "MQR108",
  "session_duration_minutes": 10,
  "max_break_minutes": 5,
  "headless": false,
  "timeout_seconds": 15,
  "chromedriver_path": "/usr/bin/chromedriver",
  "log_level": "INFO"
}
```

## Testing Migration

### 1. Verify Installation

```bash
amsterdam-parking --version
# Should output: amsterdam-parking, version 2.0.0
```

### 2. Test Configuration

```bash
# Validate config
python -c "from amsterdam_parking.config import AppConfig; AppConfig.from_json('config.json')"
```

### 3. Test Session Calculation

```bash
amsterdam-parking calculate "13:00-14:00"
```

### 4. Test Booking (Dry Run)

```bash
amsterdam-parking book "13:00-14:00" --dry-run
```

## Troubleshooting Migration

### Issue: "Module not found"

**Solution:**
```bash
pip install -e ".[dev]"
```

### Issue: "Invalid config"

**Solution:**
```bash
# Regenerate config
amsterdam-parking init
# Then copy your credentials
```

### Issue: "Command not found"

**Solution:**
```bash
# Use venv directly
venv/bin/amsterdam-parking book "13:00-14:00"

# Or activate venv
source venv/bin/activate
amsterdam-parking book "13:00-14:00"
```

### Issue: "Tests fail"

**Solution:**
```bash
# Reinstall dependencies
pip install -e ".[dev]"
pytest
```

## Rollback Plan

If you need to rollback to v1.x:

```bash
# Restore old script
git checkout main -- amsterdam_parking_bot.py

# Use old method
python amsterdam_parking_bot.py "13:00-14:00"
```

## Support

- **Issues**: Open a GitHub issue
- **Questions**: Check README.md
- **Contributing**: See CONTRIBUTING.md

## Next Steps

1. Read README.md for full documentation
2. Run tests: `pytest`
3. Try new CLI: `amsterdam-parking book --help`
4. Explore new modules in `src/amsterdam_parking/`

Happy parking! 🚗
