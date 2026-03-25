#!/usr/bin/env python3
"""
Amsterdam Parking Bot
Automates booking of split parking sessions on parkeervergunningen.amsterdam.nl.

Usage:
  park.py "13:00-16:00"                    # book sessions for today
  park.py "13:00-16:00" --tomorrow         # book for tomorrow
  park.py "13:00-16:00" --dry-run          # preview sessions without booking
  park.py --status                         # check balance and time remaining
  park.py "13:00-16:00" --session=15       # 15-minute sessions (default: 10)
  park.py "13:00-16:00" --break=3          # 3-minute breaks between sessions (default: 5)
  park.py "13:00-16:00" --plate=ABC123     # override license plate
  park.py "13:00-16:00" --meter=19850      # override parking meter number
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ── URLs ──────────────────────────────────────────────────────────────────────

BASE_URL = "https://parkeervergunningen.amsterdam.nl"
LOGIN_URL = f"{BASE_URL}/login-ssp"
PERMITS_URL = f"{BASE_URL}/permits"

# ── Default config ────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "username": "",
    "password": "",
    "license_plate": "",
    "meter_number": "",
    "session_duration_minutes": 10,
    "break_duration_minutes": 5,
    "headless": False,
    "timeout": 15,
}


# ── Data model ────────────────────────────────────────────────────────────────

class ParkingSession:
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

    def __str__(self):
        return f"{self.start.strftime('%H:%M')}–{self.end.strftime('%H:%M')}"

    @property
    def minutes(self):
        return int((self.end - self.start).total_seconds() / 60)


# ── Bot ───────────────────────────────────────────────────────────────────────

class ParkingBot:

    def __init__(self, config_path: str = "config.json", verbose: bool = False):
        self.cfg = self._load_config(config_path)
        self.driver = None
        self.wait = None
        self._setup_logging(verbose)

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self, path: str) -> dict:
        p = Path(path)
        if p.exists():
            with open(p) as f:
                user_cfg = json.load(f)
            cfg = {**DEFAULT_CONFIG, **user_cfg}
            if not cfg["username"] or not cfg["password"]:
                raise SystemExit(f"Error: 'username' and 'password' must be set in {path}")
            return cfg
        else:
            with open(p, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            raise SystemExit(
                f"Config file created at '{path}'. "
                "Please fill in your credentials and re-run."
            )

    # ── Logging ───────────────────────────────────────────────────────────────

    def _setup_logging(self, verbose: bool):
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format="%(asctime)s  %(levelname)-7s  %(message)s",
            datefmt="%H:%M:%S",
        )
        for noisy in [
            "selenium.webdriver.remote.remote_connection",
            "urllib3.connectionpool",
        ]:
            logging.getLogger(noisy).setLevel(logging.WARNING)

    # ── Driver ────────────────────────────────────────────────────────────────

    def _setup_driver(self):
        opts = Options()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1280,900")
        if self.cfg["headless"]:
            opts.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=opts)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, self.cfg["timeout"])

    # ── Low-level helpers ─────────────────────────────────────────────────────

    def _find(self, by, selector, timeout: int = None):
        """Wait for and return an element."""
        w = WebDriverWait(self.driver, timeout or self.cfg["timeout"])
        return w.until(EC.presence_of_element_located((by, selector)))

    def _click(self, element):
        """Click with a JavaScript fallback for stubborn elements."""
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

    def _set_datetime_input(self, element, dt: datetime):
        """
        Set a datetime-local input reliably by going through React's native
        value setter and firing input/change events so the framework picks it up.
        """
        value = dt.strftime("%Y-%m-%dT%H:%M")
        self.driver.execute_script(
            """
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
            """,
            element,
            value,
        )
        logging.debug(f"Set datetime input → {value}")

    def _fill_combobox(self, element, value: str):
        """Clear a combobox text input, type a value, and dismiss any dropdown."""
        element.click()
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)
        time.sleep(0.15)
        element.send_keys(str(value))
        time.sleep(0.25)
        # Dismiss autocomplete dropdown if one appeared
        element.send_keys(Keys.ESCAPE)
        logging.debug(f"Filled combobox → {value}")

    # ── Authentication ────────────────────────────────────────────────────────

    def _login(self):
        logging.info("Logging in …")
        self.driver.get(LOGIN_URL)

        self._find(By.CSS_SELECTOR, "input[type='text']").send_keys(
            self.cfg["username"]
        )
        self._find(By.CSS_SELECTOR, "input[type='password']").send_keys(
            self.cfg["password"]
        )
        self._click(
            self._find(By.XPATH, "//button[contains(text(), 'Inloggen')]")
        )

        try:
            WebDriverWait(self.driver, 20).until(EC.url_contains("/permits"))
            logging.info("✓ Logged in")
        except TimeoutException:
            raise RuntimeError(
                "Login failed – check username and password in config.json"
            )

    # ── Permit ────────────────────────────────────────────────────────────────

    def _get_permit_id(self) -> str:
        """Return the first active permit ID found on the /permits page."""
        self.driver.get(PERMITS_URL)
        # Wait for the permit table to render (React SPA), then click the permit button
        btn = self._find(By.CSS_SELECTOR, "button[data-cy='linkTable']")
        self._click(btn)
        # Wait for URL to change to the permit detail page
        WebDriverWait(self.driver, 15).until(
            lambda d: re.search(r"/permit/\d+", d.current_url)
        )
        match = re.search(r"/permit/(\d+)", self.driver.current_url)
        if not match:
            raise RuntimeError(
                f"Could not extract permit ID from URL: {self.driver.current_url}. "
                "Check that you have an active Bezoekersparkeervergunning."
            )
        permit_id = match.group(1)
        logging.debug(f"Permit ID: {permit_id}  (URL: {self.driver.current_url})")
        return permit_id

    # ── Account status ────────────────────────────────────────────────────────

    def _get_status(self, permit_id: str) -> dict:
        """Scrape Tijdsaldo and Geldsaldo from the permit detail page."""
        self.driver.get(f"{BASE_URL}/permit/{permit_id}")
        body = self._find(By.TAG_NAME, "body").text
        logging.debug(f"Status page body:\n{body}")

        time_match = re.search(r"Tijdsaldo\s+([^\n]+)", body)
        money_match = re.search(r"Geldsaldo\s+€\s*([\d,\.]+)", body)

        return {
            "time_balance": time_match.group(1).strip() if time_match else "Unknown",
            "balance": (
                float(money_match.group(1).replace(",", "."))
                if money_match
                else 0.0
            ),
        }

    def _print_status(self, status: dict, label: str = ""):
        prefix = f"[{label}] " if label else ""
        logging.info(f"{prefix}Tijdsaldo : {status['time_balance']}")
        logging.info(f"{prefix}Geldsaldo : €{status['balance']:.2f}")

    # ── Session calculation ───────────────────────────────────────────────────

    def _parse_range(
        self, time_range: str, base_date: datetime = None
    ) -> tuple[datetime, datetime]:
        date = (base_date or datetime.now()).date()
        parts = [t.strip() for t in time_range.split("-", 1)]
        if len(parts) != 2:
            raise ValueError(
                f"Invalid time range '{time_range}'. Expected format: HH:MM-HH:MM"
            )
        start = datetime.strptime(f"{date} {parts[0]}", "%Y-%m-%d %H:%M")
        end = datetime.strptime(f"{date} {parts[1]}", "%Y-%m-%d %H:%M")
        if end <= start:
            raise ValueError("End time must be after start time")
        return start, end

    def _calculate_sessions(
        self,
        start: datetime,
        end: datetime,
        session_min: int,
        break_min: int,
    ) -> list[ParkingSession]:
        sessions = []
        cur = start
        while cur < end:
            s_end = min(cur + timedelta(minutes=session_min), end)
            sessions.append(ParkingSession(cur, s_end))
            if s_end >= end:
                break
            # Skip tiny leftover sessions that would be shorter than break time
            remaining_min = (end - s_end).total_seconds() / 60
            if remaining_min <= break_min:
                break
            cur = s_end + timedelta(minutes=break_min)
        return sessions

    # ── Booking ───────────────────────────────────────────────────────────────

    def _book_session(
        self,
        session: ParkingSession,
        permit_id: str,
        plate: str,
        meter: str,
    ) -> bool:
        try:
            self.driver.get(
                f"{BASE_URL}/permit/{permit_id}/start-parking-session"
            )

            # 1. Reveal custom end-time input first (clicking it resets the start time)
            custom_end_link = self._find(
                By.XPATH,
                "//*[contains(text(), 'Voer mijn eigen eindtijd in')]",
            )
            self._click(custom_end_link)
            time.sleep(0.4)

            dt_inputs = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='datetime-local']"
            )
            if len(dt_inputs) < 2:
                raise RuntimeError(
                    "End-time input did not appear after clicking custom end link"
                )

            # 2. Set start time (must be after revealing end-time input)
            self._set_datetime_input(dt_inputs[0], session.start)

            # 3. Set end time
            self._set_datetime_input(dt_inputs[1], session.end)

            # 4. Parking meter number
            #    First text input after the 'parkeerautomaat' label
            meter_input = self._find(
                By.XPATH,
                "//*[contains(text(), 'parkeerautomaat')]"
                "/following::input[@type='text'][1]",
            )
            self._fill_combobox(meter_input, meter)

            # 5. License plate
            #    First text input after the 'kenteken' hint text
            plate_input = self._find(
                By.XPATH,
                "//*[contains(text(), 'kenteken')]"
                "/following::input[@type='text'][1]",
            )
            self._fill_combobox(plate_input, plate)

            # 6. Submit
            submit_btn = self._find(
                By.XPATH,
                "//button[contains(text(), 'Parkeersessie starten')]",
            )
            self._click(submit_btn)

            # 6. Confirm: wait for redirect back to permit page
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.any_of(
                        EC.url_matches(
                            rf"{re.escape(BASE_URL)}/permit/{permit_id}$"
                        ),
                        EC.presence_of_element_located(
                            (By.XPATH, "//*[contains(text(), 'Actief')]")
                        ),
                    )
                )
            except TimeoutException:
                # If we're no longer on the booking form, treat as success
                if "start-parking-session" not in self.driver.current_url:
                    logging.debug("Redirect detected; assuming booking succeeded")
                else:
                    raise RuntimeError(
                        "Timed out waiting for booking confirmation"
                    )

            logging.info(f"  ✓ {session}  ({session.minutes} min)")
            return True

        except Exception as exc:
            logging.error(f"  ✗ {session} failed: {exc}")
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    def check_status(self):
        """Log in, print Tijdsaldo and Geldsaldo, then exit."""
        self._setup_driver()
        try:
            self._login()
            permit_id = self._get_permit_id()
            status = self._get_status(permit_id)
            print()
            self._print_status(status)
            print()
        finally:
            self.driver.quit()

    def book(
        self,
        time_range: str,
        *,
        session_min: int = None,
        break_min: int = None,
        tomorrow: bool = False,
        dry_run: bool = False,
        plate: str = None,
        meter: str = None,
    ):
        """Calculate and (optionally) book split parking sessions."""
        session_min = session_min or self.cfg["session_duration_minutes"]
        break_min   = break_min   or self.cfg["break_duration_minutes"]
        plate       = plate       or self.cfg["license_plate"]
        meter       = meter       or self.cfg["meter_number"]

        base_date = datetime.now() + timedelta(days=1) if tomorrow else None
        start, end = self._parse_range(time_range, base_date)
        sessions   = self._calculate_sessions(start, end, session_min, break_min)

        date_label = (base_date or datetime.now()).strftime("%d %b %Y")
        logging.info(
            f"Planned {len(sessions)} session(s) for {date_label}  "
            f"[{session_min} min on / {break_min} min off]"
        )
        for i, s in enumerate(sessions, 1):
            logging.info(f"  {i}. {s}  ({s.minutes} min)")

        if dry_run:
            logging.info("Dry run – no bookings made.")
            return 0, 0

        if not plate:
            raise SystemExit(
                "License plate required. Set 'license_plate' in config or use --plate."
            )
        if not meter:
            raise SystemExit(
                "Meter number required. Set 'meter_number' in config or use --meter."
            )

        self._setup_driver()
        try:
            self._login()
            permit_id = self._get_permit_id()

            status_before = self._get_status(permit_id)
            self._print_status(status_before, label="before")

            ok, fail = 0, 0
            for i, session in enumerate(sessions, 1):
                logging.info(f"Session {i}/{len(sessions)}: {session}")
                if self._book_session(session, permit_id, plate, meter):
                    ok += 1
                else:
                    fail += 1
                if i < len(sessions):
                    time.sleep(2)

            status_after = self._get_status(permit_id)
            self._print_status(status_after, label="after")

            cost = status_before["balance"] - status_after["balance"]
            logging.info(
                f"Done: {ok}/{len(sessions)} booked"
                + (f"  |  cost: €{cost:.2f}" if cost > 0 else "")
            )
            return ok, fail

        finally:
            self.driver.quit()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="park.py",
        description="Amsterdam Parking Bot – books split sessions automatically.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "time_range",
        nargs="?",
        help="Parking window as HH:MM-HH:MM, e.g. '13:00-16:00'",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show time and money balance, then exit",
    )
    parser.add_argument(
        "--tomorrow",
        action="store_true",
        help="Book sessions for tomorrow instead of today",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate and print sessions without making any bookings",
    )
    parser.add_argument(
        "--session",
        type=int,
        metavar="MIN",
        help="Parking session length in minutes (default from config)",
    )
    parser.add_argument(
        "--break",
        type=int,
        metavar="MIN",
        dest="break_min",
        help="Break length between sessions in minutes (default from config)",
    )
    parser.add_argument(
        "--plate",
        metavar="PLATE",
        help="License plate, e.g. ABC123 (overrides config)",
    )
    parser.add_argument(
        "--meter",
        metavar="NUM",
        help="Parking meter number, e.g. 19850 (overrides config)",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        metavar="FILE",
        help="Path to config file (default: config.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug-level logging",
    )

    args = parser.parse_args()

    if not args.status and not args.time_range:
        parser.error("time_range is required unless --status is used")

    bot = ParkingBot(config_path=args.config, verbose=args.verbose)

    if args.status:
        bot.check_status()
        sys.exit(0)

    ok, fail = bot.book(
        args.time_range,
        session_min=args.session,
        break_min=args.break_min,
        tomorrow=args.tomorrow,
        dry_run=args.dry_run,
        plate=args.plate,
        meter=args.meter,
    )
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
