# Amsterdam Parking Bot

Automates split parking sessions on [parkeervergunningen.amsterdam.nl](https://parkeervergunningen.amsterdam.nl) to minimise cost.

Amsterdam's visitor parking permit charges per minute. By booking several short sessions with small breaks instead of one long block, you pay only for the minutes the car is actively parked rather than a continuous stretch.

**Example** — covering 13:00–16:00 with 10-minute sessions and 5-minute breaks:

```
13:00–13:10  13:15–13:25  13:30–13:40  13:45–13:55
14:00–14:10  14:15–14:25  14:30–14:40  14:45–14:55
15:00–15:10  15:15–15:25  15:30–15:40  15:45–15:55
```

---

## Requirements

- Python 3.10+
- Google Chrome
- ChromeDriver matching your Chrome version (placed at `/usr/bin/chromedriver` or update the path in `park.py`)

---

## Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd amsterdam-parking-bot

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your config file
cp config.example.json config.json
# Then open config.json and fill in your credentials
```

---

## Configuration

`config.json` is gitignored and never committed. Copy the example and edit it:

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

| Field | Description | Default |
|---|---|---|
| `username` | Your meldcode | required |
| `password` | Your pincode | required |
| `license_plate` | Default license plate | required to book |
| `meter_number` | Parking meter number (the number on the physical machine) | required to book |
| `session_duration_minutes` | Length of each parking session | 10 |
| `break_duration_minutes` | Break between sessions | 5 |
| `headless` | Run Chrome in the background | false |
| `timeout` | Selenium element wait timeout (seconds) | 15 |

All fields except `username` and `password` can be overridden with CLI flags.

---

## Usage

```bash
# Book sessions for today
python park.py "13:00-16:00"

# Book for tomorrow
python park.py "13:00-16:00" --tomorrow

# Preview sessions without booking anything
python park.py "13:00-16:00" --dry-run

# Check your time and money balance
python park.py --status

# Override session length and break
python park.py "13:00-16:00" --session=15 --break=3

# Override plate and meter on the fly
python park.py "13:00-16:00" --plate=ABC123 --meter=19850

# Use a different config file
python park.py "13:00-16:00" --config=work.json

# Verbose output for debugging
python park.py "13:00-16:00" -v
```

---

## Sample output

```
09:32:00  INFO     Planned 12 session(s) for 25 Mar 2026  [10 min on / 5 min off]
09:32:00  INFO       1. 13:00–13:10  (10 min)
09:32:00  INFO       2. 13:15–13:25  (10 min)
           ...
09:32:01  INFO     ✓ Logged in
09:32:02  INFO     [before] Tijdsaldo : 14 uur 55 minuten
09:32:02  INFO     [before] Geldsaldo : €61.06
09:32:04  INFO     Session 1/12: 13:00–13:10
09:32:07  INFO       ✓ 13:00–13:10  (10 min)
           ...
09:34:10  INFO     [after] Tijdsaldo : 12 uur 55 minuten
09:34:10  INFO     [after] Geldsaldo : €44.15
09:34:10  INFO     Done: 12/12 booked  |  cost: €16.91
```

---

## Troubleshooting

**Login fails** — double-check meldcode and pincode in `config.json`. Set `"headless": false` to watch the browser.

**Sessions fail after login** — run with `-v` to see exactly which step breaks. The meter number must be valid for your permit area; you can find it by looking at the physical machine or the [Amsterdam parking map](https://www.amsterdam.nl/parkeren/parkeertarieven/).

**ChromeDriver version mismatch** — install the driver that matches your Chrome version:
```bash
# Ubuntu/Debian
sudo apt install chromium-driver

# Or download from https://googlechromelabs.github.io/chrome-for-testing/
```
Then update the path in `park.py` if it is not at `/usr/bin/chromedriver`.

---

## Security

- `config.json` is listed in `.gitignore` and will never be committed.
- Credentials stay on your machine; the script only talks to `parkeervergunningen.amsterdam.nl`.
