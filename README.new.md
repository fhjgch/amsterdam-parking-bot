# Amsterdam Parking Automation Bot v2.0

> **Modern, type-safe Python automation for optimized Amsterdam parking bookings**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What's New in v2.0

This is a complete rewrite using modern Python best practices (2025):

- **Modern Architecture**: Clean src/ layout with modular design
- **Type Safety**: Full type hints with mypy validation
- **Pydantic v2**: Validated configuration management
- **Rich CLI**: Beautiful command-line interface with Click
- **Fast Tooling**: Ruff for linting (10-100x faster than traditional tools)
- **Comprehensive Tests**: pytest with fixtures and mocking
- **CI/CD Ready**: GitHub Actions workflows included
- **Structured Logging**: Production-ready logging with structlog

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/amsterdam-parking-bot.git
cd amsterdam-parking-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e ".[dev]"
```

### 2. Configuration

```bash
# Initialize config file
amsterdam-parking init

# Edit config.json with your credentials
nano config.json
```

**config.json:**
```json
{
  "username": "your_meldcode",
  "password": "your_pincode",
  "license_plate": "MQR108",
  "session_duration_minutes": 10,
  "max_break_minutes": 5,
  "headless": false
}
```

### 3. Usage

```bash
# Calculate sessions (dry-run)
amsterdam-parking book "13:00-14:00" --dry-run

# Book sessions for today
amsterdam-parking book "13:00-14:00"

# Book for tomorrow
amsterdam-parking book "09:00-17:00" --tomorrow

# Custom session duration
amsterdam-parking book "13:00-16:00" --session 15 --max-break 3

# Calculate without config
amsterdam-parking calculate "13:00-16:00" --session 10
```

## Features

### Smart Session Splitting

The bot automatically calculates optimal parking sessions:

```
Input:  13:00-14:00 (60 minutes)
Output: 4 sessions → 13:00-13:10, 13:15-13:25, 13:30-13:40, 13:45-13:55
```

- Respects max break limits (default: 5 minutes)
- Avoids tiny final sessions
- Handles any time range and duration

### Modular Architecture

```
src/amsterdam_parking/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── cli.py               # Click-based CLI
├── bot.py               # Main orchestration
├── config.py            # Pydantic configuration
├── models.py            # Data models
├── session_calculator.py # Session logic
└── browser/
    ├── driver.py        # WebDriver management
    └── pages.py         # Page Object Models
```

### Type-Safe Configuration

```python
from amsterdam_parking.config import AppConfig

# Validated at runtime with Pydantic
config = AppConfig(
    username="test_user",
    password="test_pass",
    session_duration_minutes=10,  # Validated: 5-60
    max_break_minutes=5,           # Validated: 1-15
    log_level="INFO"              # Validated: DEBUG/INFO/WARNING/ERROR/CRITICAL
)
```

### Robust Browser Automation

- **Page Object Model**: Clean separation between logic and UI
- **Multi-Strategy Element Finding**: Adapts to website changes
- **Retry Logic**: Exponential backoff for failed sessions
- **Context Managers**: Automatic resource cleanup

### Rich CLI Output

```
┏━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ # ┃ Session Time ┃ Duration ┃
┡━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1 │ 13:00-13:10  │  10 min  │
│ 2 │ 13:15-13:25  │  10 min  │
│ 3 │ 13:30-13:40  │  10 min  │
│ 4 │ 13:45-13:55  │  10 min  │
└───┴──────────────┴──────────┘
```

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_session_calculator.py

# Run with verbose output
pytest -v

# Generate coverage report
pytest --cov-report=html
```

### Code Quality

```bash
# Lint with ruff (fast!)
ruff check src tests

# Auto-fix issues
ruff check src tests --fix

# Format code
ruff format src tests

# Type check with mypy
mypy src

# Run all pre-commit hooks
pre-commit run --all-files
```

### Project Structure

```
amsterdam-parking-bot/
├── src/amsterdam_parking/       # Source code
├── tests/                       # Test suite
├── .github/workflows/           # CI/CD
├── pyproject.toml              # Modern Python config
├── .pre-commit-config.yaml     # Git hooks
├── config.json                 # User configuration
└── README.md                   # This file
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `username` | str | **Required** | Amsterdam parking meldcode |
| `password` | str | **Required** | Amsterdam parking pincode |
| `license_plate` | str | MQR108 | Vehicle license plate |
| `session_duration_minutes` | int | 10 | Session duration (5-60) |
| `max_break_minutes` | int | 5 | Max break between sessions (1-15) |
| `balance_warning_threshold` | float | 30.0 | Warn below this amount (€) |
| `monthly_time_budget` | int | 150 | Monthly hours budget |
| `max_retries` | int | 3 | Retry attempts per session |
| `headless` | bool | false | Run browser in headless mode |
| `timeout_seconds` | int | 15 | WebDriver timeout |
| `log_level` | str | INFO | Logging level |

## API Usage

### Programmatic Usage

```python
from amsterdam_parking.bot import ParkingBot
from amsterdam_parking.config import AppConfig
from amsterdam_parking.session_calculator import SessionCalculator
from datetime import datetime

# Setup
config = AppConfig.from_json("config.json")
calculator = SessionCalculator(10, 5)

# Calculate sessions
start, end = calculator.parse_time_range("13:00-14:00")
sessions = calculator.calculate_sessions(start, end)

# Book sessions
bot = ParkingBot(config)
result = bot.book_sessions(sessions, use_tomorrow=False)

print(f"Booked: {result.successful_sessions}/{result.total_sessions}")
```

## Troubleshooting

### Installation Issues

```bash
# If using system Python on Arch Linux
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### ChromeDriver Path

Update `chromedriver_path` in config.json:

```json
{
  "chromedriver_path": "/usr/bin/chromedriver"  # Linux
  "chromedriver_path": "/usr/local/bin/chromedriver"  # macOS
  "chromedriver_path": "C:\\chromedriver.exe"  # Windows
}
```

### Website Changes

The bot uses multiple fallback selectors. If website changes break automation:

1. Run with `--verbose` flag
2. Check logs for specific failures
3. Update selectors in `src/amsterdam_parking/browser/pages.py`

### Debug Mode

```bash
# Visible browser + verbose logging
amsterdam-parking book "13:00-14:00" --verbose

# Update config.json:
{
  "headless": false,
  "log_level": "DEBUG"
}
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest`
4. Run linting: `ruff check src tests --fix`
5. Run type checking: `mypy src`
6. Submit a pull request

## Testing

```bash
# Quick test
pytest

# With coverage
pytest --cov

# Specific tests
pytest tests/test_session_calculator.py::TestSessionCalculator::test_calculate_sessions
```

## Security

- Credentials stored locally in `config.json` (git-ignored)
- No external data transmission beyond parking website
- Read-only account access
- Rate limiting to avoid blocking

## License

MIT License - see LICENSE file

## Acknowledgments

- Built for Amsterdam residents optimizing parking costs
- Uses modern Python tooling (Ruff, Pydantic, Click, Rich)
- Inspired by need for cost-effective parking solutions

---

**Pro Tip:** Start with `amsterdam-parking calculate` to test your strategy!

**Need Help?** Open an issue with `--verbose` output attached.
