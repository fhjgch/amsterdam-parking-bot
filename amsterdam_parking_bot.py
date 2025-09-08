#!/usr/bin/env python3
"""
Amsterdam Parking Session Automation Script - Compact Version

Automates booking of multiple short parking sessions to optimize costs.
Usage: python park.py "13:00-14:00" [--tomorrow] [--session=15] [--max-break=3]
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional
import calendar

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

class InsufficientBalanceError(Exception):
    pass

class ConfigurationError(Exception):
    pass

class ParkingSession:
    def __init__(self, start_time: datetime, end_time: datetime):
        self.start_time = start_time
        self.end_time = end_time
        self.duration_minutes = int((end_time - start_time).total_seconds() / 60)
    
    def __str__(self) -> str:
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

class AmsterdamParkingBot:
    """Compact parking automation bot."""
    
    # Centralized selectors
    SELECTORS = {
        'login_username': [(By.CSS_SELECTOR, "input[placeholder*='meldcode' i]"), (By.CSS_SELECTOR, "input[type='text']")],
        'login_password': [(By.CSS_SELECTOR, "input[placeholder*='pincode' i]"), (By.CSS_SELECTOR, "input[type='password']")],
        'login_button': [(By.CSS_SELECTOR, "button[type='submit']"), (By.XPATH, "//button[contains(text(), 'Inloggen')]")],
        'time_inputs': ["input[type='time']", "input[placeholder*='tijd']", "input[name*='start']"],
        'date_dropdown': [(By.CSS_SELECTOR, "select[name*='date' i]"), (By.CSS_SELECTOR, "select")],
        'balance': [(By.XPATH, "//*[contains(text(), '€')]"), (By.CSS_SELECTOR, "[class*='saldo']")],
        'time_budget': [(By.XPATH, "//*[contains(text(), 'uur')]"), (By.CSS_SELECTOR, "[class*='time']")]
    }
    
    BUTTONS = {
        'kenteken': ["//button[contains(text(), 'Kenteken')]", "button[type='submit']"],
        'confirm': [
            "//button[contains(text(), 'Bevestig parkeersessie')]",  # Exact text match
            "//button[contains(text(), 'Bevestig')]",                # Partial match fallback
            "//button[contains(@class, 'sc-907d1856-1')]",           # Class-based selector
            "button[type='submit']"                                   # Generic fallback
        ]
    }
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.wait = None
        self._setup_logging()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration with defaults."""
        defaults = {
            "username": "", "password": "", "license_plate": "MQR108",
            "session_duration_minutes": 10, "max_break_minutes": 5,
            "balance_warning_threshold": 30.0, "monthly_time_budget": 150,
            "max_retries": 3, "headless": False, "timeout_seconds": 15
        }
        
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                defaults.update(json.load(f))
        else:
            with open(config_file, 'w') as f:
                json.dump(defaults, f, indent=2)
            logging.warning(f"Created config file: {config_path} - Please update credentials")
        
        # Validate required fields
        if not defaults.get('username') or not defaults.get('password'):
            raise ConfigurationError("Username and password required in config.json")
        
        return defaults
    
    def _setup_logging(self):
        """Configure logging."""
        level = logging.DEBUG if not self.config.get('headless') else logging.INFO
        logging.basicConfig(level=level, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')

        logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    
    def _setup_driver(self):
        """Initialize WebDriver."""
        options = Options()
        for arg in ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--window-size=1920,1080']:
            options.add_argument(arg)
        if self.config['headless']:
            options.add_argument('--headless')
        
        self.driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(5)
        self.wait = WebDriverWait(self.driver, self.config['timeout_seconds'])
    
    def _find_element(self, selector_key: str, required: bool = True):
        """Find element using predefined selectors."""
        selectors = self.SELECTORS.get(selector_key, [])
        for by_method, selector in selectors:
            try:
                return self.wait.until(EC.presence_of_element_located((by_method, selector)))
            except TimeoutException:
                continue
        if required:
            raise NoSuchElementException(f"Could not find {selector_key}")
        return None
    
    def _click_button(self, button_key: str) -> bool:
        """Find and click button using predefined selectors."""
        selectors = self.BUTTONS.get(button_key, [])
        for selector in selectors:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                # Wait for element to be clickable, not just present
                button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((by, selector))
                )
                return self._safe_click(button)
            except TimeoutException:
                continue
            except Exception:
                continue
        return False
    
    def _safe_click(self, element) -> bool:
        """Click element with fallback strategies."""
        try:
            element.click()
            return True
        except:
            try:
                # Wait a moment for any overlays to disappear
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                try:
                    # Force click with JavaScript event dispatch
                    self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", element)
                    return True
                except:
                    return False
    
    def _parse_time_range(self, time_range: str, target_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """Parse time range string into datetime objects."""
        if '-' not in time_range:
            raise ValueError("Time range must contain '-' (e.g., '13:00-14:00')")
        
        start_str, end_str = [t.strip() for t in time_range.split('-')]
        base_date = target_date.date() if target_date else datetime.now().date()
        
        start_time = datetime.strptime(f"{base_date} {start_str}", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{base_date} {end_str}", "%Y-%m-%d %H:%M")
        
        if end_time <= start_time:
            if target_date is None:
                end_time += timedelta(days=1)
            else:
                raise ValueError("End time must be after start time")
        
        return start_time, end_time
    
    def _calculate_sessions(self, start_time: datetime, end_time: datetime, session_minutes: int, max_break_minutes: int) -> List[ParkingSession]:
        """Calculate session splits."""
        total_minutes = int((end_time - start_time).total_seconds() / 60)
        sessions = []
        current_time = start_time
        
        while current_time < end_time:
            session_end = min(current_time + timedelta(minutes=session_minutes), end_time)
            sessions.append(ParkingSession(current_time, session_end))
            
            if session_end >= end_time:
                break
            
            # Smart break calculation
            remaining = int((end_time - session_end).total_seconds() / 60)
            if remaining <= session_minutes:
                break  # Avoid tiny final session
            
            current_time = session_end + timedelta(minutes=max_break_minutes)
        
        return sessions
    
    def _login(self):
        """Login to parking portal."""
        logging.info("Logging in...")
        self.driver.get("https://aanmeldenparkeren.amsterdam.nl/login")
        
        # Enter credentials
        username_field = self._find_element('login_username')
        username_field.clear()
        username_field.send_keys(self.config['username'])
        
        password_field = self._find_element('login_password')
        password_field.clear()
        password_field.send_keys(self.config['password'])
        
        # Click login
        login_button = self._find_element('login_button')
        if not self._safe_click(login_button):
            raise Exception("Could not click login button")
        
        # Wait for success
        try:
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.url_contains("dashboard"),
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'saldo')]"))
                )
            )
            logging.info("✓ Logged in successfully")
        except TimeoutException:
            raise Exception("Login failed - check credentials")
    
    def _get_account_status(self) -> Tuple[float, str]:
        """Get balance and time budget."""
        try:
            # Extract balance
            balance = 0.0
            balance_element = self._find_element('balance', required=False)
            if balance_element:
                balance_text = balance_element.text
                balance_match = re.search(r'€\s*([\d,]+\.?\d*)', balance_text)
                if balance_match:
                    balance_str = balance_match.group(1).replace(',', '')
                    balance = float(balance_str)
            
            # Extract time budget
            time_budget = "Unknown"
            time_element = self._find_element('time_budget', required=False)
            if time_element:
                time_budget = time_element.text.strip()
            
            return balance, time_budget
        except:
            return 0.0, "Unknown"
    
    def _book_single_session(self, session: ParkingSession, target_date: Optional[datetime] = None) -> bool:
        """Book a single session with improved form handling."""
        try:
            logging.info(f"Booking: {session}")
            
            # Navigate to booking form
            self.driver.get("https://aanmeldenparkeren.amsterdam.nl/parking-sessions/new")
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='time'], select")))
            
            # PAGE 1: Set date, times, and proceed to license plate
            
            def convert_to_12hour_format(time_24h: datetime) -> str:
                """Convert 24-hour time to 12-hour format for the website."""
                return time_24h.strftime("%I:%M%p")

            # 1. Select date (Vandaag/Morgen)
            if target_date == 'tomorrow':
                # Select "Morgen" from dropdown
                try:
                    date_select = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "select[name='startDay']")))
                    Select(date_select).select_by_visible_text("Morgen")
                    logging.debug("Selected tomorrow (Morgen) from dropdown")
                except Exception as e:
                    logging.debug(f"Could not select tomorrow date: {e}")
            # If no --tomorrow flag, "Vandaag" remains selected by default

            # 2. Set start time (Starttijd) in 12-hour format
            try:
                start_time_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='startTimeRaw']")))
                
                # Convert 24-hour to 12-hour format
                start_time_12h = convert_to_12hour_format(session.start_time)
                logging.debug(f"Converting {session.start_time.strftime('%H:%M')} to {start_time_12h}")
                
                start_time_input.clear()
                start_time_input.send_keys(start_time_12h)
                logging.debug(f"Set start time: {start_time_12h}")
            except Exception as e:
                raise Exception(f"Could not set start time: {e}")

            # 3. Set end time (Eindtijd) in 12-hour format
            try:
                end_time_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='endTimeRaw']")))
                
                # Convert 24-hour to 12-hour format
                end_time_12h = convert_to_12hour_format(session.end_time)
                logging.debug(f"Converting {session.end_time.strftime('%H:%M')} to {end_time_12h}")
                
                end_time_input.clear()
                end_time_input.send_keys(end_time_12h)
                logging.debug(f"Set end time: {end_time_12h}")
            except Exception as e:
                raise Exception(f"Could not set end time: {e}")
            
            # 4. Click "Kenteken" button
            try:
                kenteken_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Kenteken')]")))
                if not self._safe_click(kenteken_button):
                    raise Exception("Could not click Kenteken button")
                logging.debug("Clicked Kenteken button")
            except:
                raise Exception("Could not proceed to license plate selection")
            
            # PAGE 2: Select license plate and confirm booking
            
            # Wait for license plate selection page to load
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='radio'][@value='MQR108']")))
            
            # 5. Select MQR108 radio button
            # Find license plate radio button/label - search for labels containing "Ganesh"
            plate_name = self.config['license_plate']  # "Ganesh"

            plate_selectors = [
                f"//label[.//span[contains(text(), '{plate_name}')]]",
                f"//span[contains(text(), '{plate_name}')]//ancestor::label",
                f"//label[contains(., '{plate_name}')]"
            ]

            plate_clicked = False
            for selector in plate_selectors:
                try:
                    label_element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if self._safe_click(label_element):
                        plate_clicked = True
                        logging.debug(f"Selected license plate using: {selector}")
                        break
                except:
                    continue
            
            if not plate_clicked:
                # Enhanced fallback: search in button innerHTML and nested spans
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
                    for button in buttons:
                        # Check button's innerHTML for the plate name
                        innerHTML = button.get_attribute('innerHTML')
                        if plate_name.lower() in innerHTML.lower():
                            # Scroll into view and click
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(0.5)
                            if self._safe_click(button):
                                plate_clicked = True
                                break
                        
                        # Also check if button contains spans with our text
                        try:
                            spans = button.find_elements(By.TAG_NAME, "span")
                            for span in spans:
                                if plate_name.lower() in span.text.lower():
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                    time.sleep(0.5)
                                    if self._safe_click(button):
                                        plate_clicked = True
                                        break
                            if plate_clicked:
                                break
                        except:
                            continue
                except Exception as e:
                    logging.debug(f"Fallback license plate search failed: {e}")
            
            if not plate_clicked:
                raise Exception(f"Could not select license plate: {plate_name}")
            
            # 6. Click "Bevestig parkeersessie" button
            try:
                confirm_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Bevestig parkeersessie')]")))
                if not self._safe_click(confirm_button):
                    raise Exception("Could not click confirmation button")
                logging.debug("Clicked Bevestig parkeersessie button")
            except:
                raise Exception("Could not confirm booking")
            
            # 7. Wait for success confirmation
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.url_contains("success"),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'bevestigd')]")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'gepland')]"))
                    )
                )
                logging.info(f"✓ Successfully booked: {session}")
                return True
            except TimeoutException:
                raise Exception("Booking confirmation not received")
                    
        except Exception as e:
            logging.error(f"✗ Failed to book {session}: {e}")
            return False
    
    def book_parking_sessions(self, time_range: str, session_minutes: int = None, max_break_minutes: int = None, target_date: Optional[str] = None):
        """Main booking method."""
        try:
            # Parse target date
            booking_date = None
            if target_date:
                if target_date.lower() == 'tomorrow':
                    booking_date = datetime.now() + timedelta(days=1)
                elif target_date.lower() != 'today':
                    booking_date = datetime.strptime(target_date, "%Y-%m-%d")
            
            # Use config defaults
            session_minutes = session_minutes or self.config['session_duration_minutes']
            max_break_minutes = max_break_minutes or self.config['max_break_minutes']
            
            # Calculate sessions
            start_time, end_time = self._parse_time_range(time_range, booking_date)
            sessions = self._calculate_sessions(start_time, end_time, session_minutes, max_break_minutes)
            
            date_str = "today" if booking_date is None else booking_date.strftime("%A, %B %d")
            logging.info(f"Booking {len(sessions)} sessions for {time_range} on {date_str}")
            
            # Setup and login
            self._setup_driver()
            self._login()
            
            # Check account status
            balance, time_budget = self._get_account_status()
            logging.info(f"Balance: €{balance:.2f}, Time Budget: {time_budget}")
            
            if balance < self.config['balance_warning_threshold']:
                logging.warning(f"⚠️ Low balance: €{balance:.2f}")
            
            # Book sessions
            successful = []
            failed = []
            
            for i, session in enumerate(sessions, 1):
                logging.info(f"Processing session {i}/{len(sessions)}")
                
                # Retry logic
                success = False
                for attempt in range(self.config['max_retries']):
                    try:
                        if self._book_single_session(session, booking_date):
                            success = True
                            break
                    except InsufficientBalanceError:
                        failed.extend(sessions[i-1:])  # Mark rest as failed
                        raise
                    except Exception as e:
                        if attempt < self.config['max_retries'] - 1:
                            wait_time = 2 * (2 ** attempt)
                            logging.warning(f"Retry {attempt + 1} in {wait_time}s: {e}")
                            time.sleep(wait_time)
                
                if success:
                    successful.append(session)
                else:
                    failed.append(session)
                
                # Delay between bookings
                if i < len(sessions):
                    time.sleep(min(2 + (i * 0.5), 5))
            
            # Summary
            logging.info("=" * 50)
            logging.info(f"SUMMARY - {date_str}")
            logging.info(f"Successful: {len(successful)}/{len(sessions)}")
            if failed:
                logging.info(f"Failed: {', '.join(str(s) for s in failed)}")
            
            # Final balance
            final_balance, _ = self._get_account_status()
            cost = balance - final_balance
            if cost > 0:
                logging.info(f"Cost: €{cost:.2f}")
            
            return {
                'total_sessions': len(sessions),
                'successful_sessions': len(successful),
                'failed_sessions': len(failed),
                'cost': cost
            }
            
        except Exception as e:
            logging.error(f"Critical error: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(description="Amsterdam Parking Automation")
    parser.add_argument("time_range", help="Time range 'HH:MM-HH:MM'")
    parser.add_argument("--session", type=int, help="Session duration (minutes)")
    parser.add_argument("--max-break", type=int, help="Max break duration (minutes)")
    parser.add_argument("--tomorrow", action="store_const", const="tomorrow", dest="target_date")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--dry-run", action="store_true", help="Calculate only")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    try:
        bot = AmsterdamParkingBot(args.config)

        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
        
        if args.dry_run:
            # Calculate sessions only
            start_time, end_time = bot._parse_time_range(args.time_range)
            sessions = bot._calculate_sessions(
                start_time, end_time,
                args.session or bot.config['session_duration_minutes'],
                args.max_break or bot.config['max_break_minutes']
            )
            print(f"Calculated {len(sessions)} sessions:")
            for i, session in enumerate(sessions, 1):
                print(f"  {i}. {session}")
            return
        
        # Normal operation
        result = bot.book_parking_sessions(
            args.time_range, args.session, args.max_break, args.target_date
        )
        
        if result is None:
            sys.exit(1)
        elif result['failed_sessions'] > 0:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
