#!/usr/bin/env python3
"""
Amsterdam Parking Session Automation Script - Production Version

Automates the booking of multiple short parking sessions to optimize costs.
Splits long sessions into shorter ones with configurable breaks.

Usage:
    python park.py "13:00-14:00"
    python park.py "13:10-14:00" --session=15 --max-break=3
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional, Union
import calendar

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager


class InsufficientBalanceError(Exception):
    """Raised when account balance is too low for booking."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class ParkingSession:
    """Represents a single parking session with start/end times."""
    
    def __init__(self, start_time: datetime, end_time: datetime):
        self.start_time = start_time
        self.end_time = end_time
        self.duration_minutes = int((end_time - start_time).total_seconds() / 60)
    
    def __str__(self) -> str:
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"


class RobustElementFinder:
    """Utility class for finding elements with multiple fallback strategies."""
    
    def __init__(self, driver: webdriver.Chrome, wait: WebDriverWait):
        self.driver = driver
        self.wait = wait
    
    def find_login_username(self):
        """Find username field with multiple strategies."""
        strategies = [
            (By.CSS_SELECTOR, "input[placeholder*='meldcode' i]"),
            (By.CSS_SELECTOR, "input[name*='username' i]"),
            (By.CSS_SELECTOR, "input[name*='login' i]"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.XPATH, "//input[contains(@placeholder, 'meld')]"),
        ]
        return self._try_strategies(strategies, "username field")
    
    def find_login_password(self):
        """Find password field with multiple strategies."""
        strategies = [
            (By.CSS_SELECTOR, "input[placeholder*='pincode' i]"),
            (By.CSS_SELECTOR, "input[name*='password' i]"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[contains(@placeholder, 'pin')]"),
        ]
        return self._try_strategies(strategies, "password field")
    
    def find_login_button(self):
        """Find login button with multiple strategies."""
        strategies = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, ".btn-primary"),
            (By.XPATH, "//button[contains(text(), 'Inloggen')]"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//input[@type='submit']"),
        ]
        return self._try_strategies(strategies, "login button")
    
    def find_new_session_button(self):
        """Find new parking session button."""
        strategies = [
            (By.XPATH, "//button[contains(text(), 'Nieuwe parkeersessie')]"),
            (By.CSS_SELECTOR, "button[href*='new']"),
            (By.XPATH, "//a[contains(@href, 'new')]"),
            (By.CSS_SELECTOR, ".btn[href*='parking-session']"),
        ]
        return self._try_strategies(strategies, "new session button")
    
    def find_balance_element(self):
        """Find balance display element."""
        strategies = [
            (By.XPATH, "//*[contains(text(), 'saldo')]/following-sibling::*[contains(text(), '€')]"),
            (By.XPATH, "//*[contains(text(), '€')]"),
            (By.CSS_SELECTOR, "[class*='balance'] [class*='amount']"),
            (By.CSS_SELECTOR, "[class*='saldo']"),
        ]
        return self._try_strategies(strategies, "balance element", required=False)
    
    def find_time_budget_element(self):
        """Find time budget display element."""
        strategies = [
            (By.XPATH, "//*[contains(text(), 'uur') and (contains(text(), 'min') or contains(text(), 'tijd'))]"),
            (By.XPATH, "//*[contains(text(), 'Tijd')]/following-sibling::*"),
            (By.CSS_SELECTOR, "[class*='time'] [class*='budget']"),
        ]
        return self._try_strategies(strategies, "time budget element", required=False)
    
    def _try_strategies(self, strategies: List[Tuple], element_name: str, required: bool = True):
        """Try multiple element finding strategies."""
        for by_method, selector in strategies:
            try:
                element = self.wait.until(EC.presence_of_element_located((by_method, selector)))
                logging.debug(f"Found {element_name} using: {by_method}='{selector}'")
                return element
            except TimeoutException:
                continue
        
        if required:
            raise NoSuchElementException(f"Could not find {element_name} using any strategy")
        return None


class AmsterdamParkingBot:
    """Main automation class for Amsterdam parking system."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._validate_config()
        self.driver = None
        self.wait = None
        self.finder = None
        self._setup_logging()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        default_config = {
            "username": "",
            "password": "",
            "license_plate": "3. Ganesh MQR108",
            "session_duration_minutes": 10,
            "break_duration_minutes": 5,
            "max_break_minutes": 5,
            "balance_warning_threshold": 30.00,
            "monthly_time_budget": 150,
            "max_retries": 3,
            "retry_delay_seconds": 2,
            "headless": False,
            "timeout_seconds": 15,
            "page_load_timeout": 30,
            "implicit_wait": 5
        }
        
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                raise ConfigurationError(f"Error reading config file {config_path}: {e}")
        else:
            # Create default config file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
            logging.warning(f"Created default config file: {config_path}")
            logging.warning("Please update username and password in config.json")
        
        return default_config
    
    def _validate_config(self):
        """Validate configuration parameters."""
        errors = []
        
        if not self.config.get('username'):
            errors.append("Username (meldcode) is required")
        if not self.config.get('password'):
            errors.append("Password (pincode) is required")
        
        # Validate numeric parameters
        numeric_params = {
            'session_duration_minutes': (1, 60),
            'max_break_minutes': (0, 30),
            'monthly_time_budget': (1, 1000),
            'max_retries': (1, 10),
            'timeout_seconds': (5, 60)
        }
        
        for param, (min_val, max_val) in numeric_params.items():
            value = self.config.get(param)
            if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                errors.append(f"{param} must be between {min_val} and {max_val}")
        
        if errors:
            raise ConfigurationError("Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))
    
    def _setup_logging(self):
        """Configure logging with timestamps."""
        log_level = logging.DEBUG if not self.config.get('headless', False) else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def _setup_driver(self):
        """Initialize Chrome WebDriver with robust options."""
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Language and locale
        chrome_options.add_argument('--lang=nl-NL')
        chrome_options.add_experimental_option('prefs', {
            'intl.accept_languages': 'nl-NL,nl,en-US,en'
        })
        
        if self.config['headless']:
            chrome_options.add_argument('--headless')
        
        try:
            # Use webdriver-manager for automatic ChromeDriver management
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.config['page_load_timeout'])
            self.driver.implicitly_wait(self.config['implicit_wait'])
            
            # Remove automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, self.config['timeout_seconds'])
            self.finder = RobustElementFinder(self.driver, self.wait)
            
            logging.info("✓ WebDriver initialized successfully")
            
        except Exception as e:
            raise WebDriverException(f"Failed to initialize WebDriver: {e}")
    
    def _parse_time_range(self, time_range: str) -> Tuple[datetime, datetime]:
        """Parse time range string like '13:00-14:00' into datetime objects."""
        try:
            # Support multiple formats
            if '-' in time_range:
                parts = time_range.split('-')
            elif ' to ' in time_range.lower():
                parts = time_range.lower().split(' to ')
            else:
                raise ValueError("Time range must contain '-' or ' to '")
            
            if len(parts) != 2:
                raise ValueError("Time range must have exactly two times")
            
            start_str, end_str = [part.strip() for part in parts]
            today = datetime.now().date()
            
            # Parse times with flexible format
            for time_str in [start_str, end_str]:
                if not re.match(r'^\d{1,2}:\d{2}$', time_str):
                    raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format")
            
            start_time = datetime.strptime(f"{today} {start_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{today} {end_str}", "%Y-%m-%d %H:%M")
            
            # Handle next day scenarios
            if end_time <= start_time:
                end_time += timedelta(days=1)
            
            # Validate reasonable duration (max 24 hours)
            duration_hours = (end_time - start_time).total_seconds() / 3600
            if duration_hours > 24:
                raise ValueError("Parking duration cannot exceed 24 hours")
            
            return start_time, end_time
            
        except ValueError as e:
            raise ValueError(f"Invalid time range format '{time_range}': {e}")
    
    def _calculate_sessions(self, start_time: datetime, end_time: datetime, 
                          session_minutes: int, max_break_minutes: int) -> List[ParkingSession]:
        """Calculate optimal session splits with break constraints."""
        total_minutes = int((end_time - start_time).total_seconds() / 60)
        
        if total_minutes <= 0:
            raise ValueError("End time must be after start time")
        
        sessions = []
        current_time = start_time
        
        while current_time < end_time:
            # Calculate session end time
            session_end = min(current_time + timedelta(minutes=session_minutes), end_time)
            sessions.append(ParkingSession(current_time, session_end))
            
            # If this was the last session, break
            if session_end >= end_time:
                break
            
            # Calculate break duration (never exceed max_break_minutes)
            remaining_time = int((end_time - session_end).total_seconds() / 60)
            if remaining_time <= session_minutes:
                # Last session - minimize break to fit exactly
                break_minutes = max(1, min(max_break_minutes, remaining_time - session_minutes))
                break_minutes = max(1, break_minutes)  # Ensure at least 1 minute break
            else:
                break_minutes = max_break_minutes
            
            current_time = session_end + timedelta(minutes=break_minutes)
        
        if not sessions:
            raise ValueError("Could not calculate any valid sessions")
        
        return sessions
    
    def _safe_click(self, element, description: str = "element") -> bool:
        """Safely click an element with multiple strategies."""
        strategies = [
            lambda: element.click(),
            lambda: self.driver.execute_script("arguments[0].click();", element),
            lambda: self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", element)
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                strategy()
                logging.debug(f"✓ Clicked {description} using strategy {i}")
                return True
            except ElementClickInterceptedException:
                if i < len(strategies):
                    logging.debug(f"Click intercepted for {description}, trying strategy {i+1}")
                    time.sleep(0.5)
                    continue
                else:
                    logging.warning(f"All click strategies failed for {description}")
                    return False
            except Exception as e:
                logging.debug(f"Click strategy {i} failed for {description}: {e}")
                if i == len(strategies):
                    return False
        
        return False
    
    def _login(self):
        """Login to the Amsterdam parking portal with robust element finding."""
        logging.info("Navigating to login page...")
        
        try:
            self.driver.get("https://aanmeldenparkeren.amsterdam.nl/login")
            
            # Wait for page load
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Find and fill username
            username_field = self.finder.find_login_username()
            username_field.clear()
            username_field.send_keys(self.config['username'])
            logging.debug("✓ Username entered")
            
            # Find and fill password
            password_field = self.finder.find_login_password()
            password_field.clear()
            password_field.send_keys(self.config['password'])
            logging.debug("✓ Password entered")
            
            # Find and click login button
            login_button = self.finder.find_login_button()
            if not self._safe_click(login_button, "login button"):
                raise Exception("Could not click login button")
            
            # Wait for successful login with multiple success indicators
            success_conditions = [
                EC.url_contains("dashboard"),
                EC.url_contains("parking-sessions"),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Welkom') or contains(text(), 'Welcome')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'saldo') or contains(text(), 'balance')]"))
            ]
            
            try:
                WebDriverWait(self.driver, 10).until(EC.any_of(*success_conditions))
                logging.info("✓ Successfully logged in")
            except TimeoutException:
                # Check for error messages
                try:
                    error_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'fout') or contains(text(), 'error') or contains(text(), 'incorrect')]")
                    raise Exception(f"Login failed: {error_element.text}")
                except NoSuchElementException:
                    raise Exception("Login failed - unknown error (check credentials)")
                    
        except Exception as e:
            raise Exception(f"Login process failed: {e}")
    
    def _get_account_status(self) -> Tuple[float, str]:
        """Extract balance and time budget from the dashboard with robust parsing."""
        try:
            # Navigate to main dashboard if not already there
            current_url = self.driver.current_url
            if not any(keyword in current_url for keyword in ["dashboard", "aanmelden", "parking-sessions"]):
                self.driver.get("https://aanmeldenparkeren.amsterdam.nl/")
                self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Extract balance with multiple strategies
            balance = 0.0
            balance_element = self.finder.find_balance_element()
            if balance_element:
                balance_text = balance_element.text
                # Try multiple number formats (European: €1.234,56 and US: €1,234.56)
                balance_patterns = [
                    r'€\s*([\d,]+\.?\d*)',  # €1,234.56 or €1234.56
                    r'€\s*([\d.]+,\d+)',    # €1.234,56
                    r'([\d,]+\.?\d*)\s*€',  # 1234.56€
                    r'([\d.]+,\d+)\s*€'     # 1.234,56€
                ]
                
                for pattern in balance_patterns:
                    balance_match = re.search(pattern, balance_text)
                    if balance_match:
                        balance_str = balance_match.group(1)
                        # Handle European format (1.234,56 -> 1234.56)
                        if ',' in balance_str and '.' in balance_str:
                            balance_str = balance_str.replace('.', '').replace(',', '.')
                        # Handle comma as decimal separator
                        elif ',' in balance_str and '.' not in balance_str:
                            balance_str = balance_str.replace(',', '.')
                        # Remove thousands separators
                        else:
                            balance_str = balance_str.replace(',', '')
                        
                        try:
                            balance = float(balance_str)
                            break
                        except ValueError:
                            continue
            
            # Extract time budget
            time_budget = "Unknown"
            time_element = self.finder.find_time_budget_element()
            if time_element:
                time_budget = time_element.text.strip()
            
            logging.debug(f"Extracted balance: €{balance:.2f}, time budget: {time_budget}")
            return balance, time_budget
            
        except Exception as e:
            logging.warning(f"Could not extract account status: {e}")
            return 0.0, "Unknown"
    
    def _analyze_monthly_budget(self, time_budget_str: str):
        """Analyze monthly parking budget usage with improved parsing."""
        try:
            # Parse time budget with multiple formats
            time_patterns = [
                r'(\d+)\s*(?:uur|hours?|h)\s*(?:(\d+)\s*(?:min|minutes?|m))?',
                r'(\d+):(\d+)',  # 87:23 format
                r'(\d+)h\s*(\d+)m?',  # 87h 23m format
            ]
            
            hours_left = 0
            minutes_left = 0
            
            for pattern in time_patterns:
                time_match = re.search(pattern, time_budget_str, re.IGNORECASE)
                if time_match:
                    hours_left = int(time_match.group(1))
                    minutes_left = int(time_match.group(2)) if time_match.group(2) else 0
                    break
            
            if hours_left == 0 and minutes_left == 0:
                logging.warning(f"Could not parse time budget format: '{time_budget_str}'")
                return
            
            total_minutes_left = hours_left * 60 + minutes_left
            
            # Calculate monthly statistics
            now = datetime.now()
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            days_elapsed = now.day
            
            # Budget calculations
            monthly_budget_minutes = self.config['monthly_time_budget'] * 60
            minutes_used = monthly_budget_minutes - total_minutes_left
            daily_average_used = minutes_used / days_elapsed if days_elapsed > 0 else 0
            daily_budget_average = monthly_budget_minutes / days_in_month
            
            # Format output
            hours_used = minutes_used // 60
            mins_used = minutes_used % 60
            daily_avg_hours = daily_average_used / 60
            
            logging.info(f"TIME BUDGET ANALYSIS ({now.strftime('%B %Y')}):")
            logging.info(f"           Days elapsed: {days_elapsed}/{days_in_month}")
            logging.info(f"           Hours used: {hours_used}h {mins_used}min ({daily_avg_hours:.1f}h/day average)")
            logging.info(f"           Hours remaining: {hours_left}h {minutes_left}min")
            
            # Status analysis
            difference_minutes = (daily_budget_average * days_elapsed) - minutes_used
            difference_hours = abs(difference_minutes) / 60
            
            if difference_minutes > 0:
                logging.info(f"           Status: {difference_hours:.1f}h below schedule ✓")
            else:
                logging.info(f"           Status: {difference_hours:.1f}h above schedule ⚠️")
            
            # Project month-end usage
            projected_total_hours = (daily_average_used * days_in_month) / 60
            logging.info(f"           Projected month-end: {projected_total_hours:.1f}h total usage")
            
            # Warnings
            if projected_total_hours > self.config['monthly_time_budget']:
                excess_hours = projected_total_hours - self.config['monthly_time_budget']
                logging.warning(f"⚠️  BUDGET RISK: Projected to exceed limit by {excess_hours:.1f}h")
            
        except Exception as e:
            logging.warning(f"Could not analyze monthly budget: {e}")
    
    def _book_single_session(self, session: ParkingSession) -> bool:
        """Book a single parking session with robust error handling."""
        try:
            logging.info(f"Booking session: {session}")
            
            # Navigate to new session page
            self.driver.get("https://aanmeldenparkeren.amsterdam.nl/parking-sessions/new?filter=undefined")
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Wait for form elements to be present
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select, input[type='time'], input[placeholder*='tijd']")))
            
            # Handle date selection
            try:
                date_dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "select")
                for dropdown in date_dropdowns:
                    if any(option.text.lower() in ['vandaag', 'today'] for option in Select(dropdown).options):
                        Select(dropdown).select_by_visible_text('Vandaag')
                        break
            except Exception as e:
                logging.debug(f"Date selection issue (may be auto-selected): {e}")
            
            # Set start time with multiple strategies
            start_time_str = session.start_time.strftime("%H:%M")
            time_selectors = [
                "input[type='time']",
                "input[placeholder*='tijd']",
                "input[placeholder*='time']",
                "input[name*='start']",
                ".time-input"
            ]
            
            start_time_set = False
            for selector in time_selectors:
                try:
                    time_fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if time_fields:
                        time_field = time_fields[0]  # Assume first is start time
                        time_field.clear()
                        time_field.send_keys(start_time_str)
                        start_time_set = True
                        logging.debug(f"✓ Start time set using: {selector}")
                        break
                except Exception as e:
                    logging.debug(f"Failed to set start time with {selector}: {e}")
            
            if not start_time_set:
                raise Exception("Could not set start time")
            
            # Set end time
            end_time_str = session.end_time.strftime("%H:%M")
            end_time_set = False
            for selector in time_selectors:
                try:
                    time_fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(time_fields) > 1:
                        time_field = time_fields[1]  # Assume second is end time
                        time_field.clear()
                        time_field.send_keys(end_time_str)
                        end_time_set = True
                        logging.debug(f"✓ End time set using: {selector}")
                        break
                except Exception as e:
                    logging.debug(f"Failed to set end time with {selector}: {e}")
            
            if not end_time_set:
                raise Exception("Could not set end time")
            
            # Continue to next step
            continue_selectors = [
                "button[type='submit']",
                ".btn-primary",
                "button.btn",
                "input[type='submit']"
            ]
            
            for selector in continue_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if self._safe_click(button, "continue button"):
                        break
                except NoSuchElementException:
                    continue
            
            # Wait for license plate selection page
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'kenteken') or contains(text(), 'license')]")))
            
            # Select configured license plate
            plate_config = self.config['license_plate']
            plate_selectors = [
                f"//button[contains(text(), '{plate_config}')]",
                f"//div[contains(text(), '{plate_config}')]//button",
                "//button[contains(@class, 'license') or contains(@class, 'plate')]"
            ]
            
            plate_selected = False
            for selector in plate_selectors:
                try:
                    plate_button = self.driver.find_element(By.XPATH, selector)
                    if self._safe_click(plate_button, "license plate"):
                        plate_selected = True
                        break
                except NoSuchElementException:
                    continue
            
            if not plate_selected:
                # Fallback: click first available plate button
                try:
                    plate_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
                    for button in plate_buttons:
                        if any(keyword in button.text.lower() for keyword in ['ganesh', 'mqr', plate_config.lower()]):
                            if self._safe_click(button, "fallback license plate"):
                                plate_selected = True
                                break
                except Exception:
                    pass
            
            if not plate_selected:
                raise Exception(f"Could not select license plate: {plate_config}")
            
            # Continue to payment step
            for selector in continue_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if self._safe_click(button, "continue to payment"):
                        break
                except NoSuchElementException:
                    continue
            
            # Check for insufficient balance warning
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'opwaarderen') or contains(text(), 'saldo')]")), timeout=3)
                balance_warning = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Geldsaldo opwaarderen') or contains(text(), 'insufficient')]")
                if balance_warning and balance_warning.is_displayed():
                    raise InsufficientBalanceError("Insufficient balance detected. Please top up manually before booking.")
            except TimeoutException:
                pass  # No balance warning found, continue
            
            # Final confirmation
            confirm_selectors = [
                "//button[contains(text(), 'Bevestig')]",
                "//button[contains(text(), 'Confirm')]", 
                "//button[contains(text(), 'parkeersessie')]",
                ".btn-confirm",
                "button[type='submit']"
            ]
            
            confirmed = False
            for selector in confirm_selectors:
                try:
                    confirm_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)), timeout=5)
                    if self._safe_click(confirm_button, "confirmation"):
                        confirmed = True
                        break
                except TimeoutException:
                    continue
            
            if not confirmed:
                raise Exception("Could not find or click confirmation button")
            
            # Wait for success confirmation
            success_indicators = [
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'bevestigd') or contains(text(), 'confirmed')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'gepland') or contains(text(), 'scheduled')]")),
                EC.url_contains("success"),
                EC.url_contains("confirmation")
            ]
            
            try:
                WebDriverWait(self.driver, 10).until(EC.any_of(*success_indicators))
                logging.info(f"✓ Successfully booked: {session}")
                return True
            except TimeoutException:
                raise Exception("Booking confirmation not received")
            
        except InsufficientBalanceError:
            raise  # Re-raise balance errors without modification
        except Exception as e:
            logging.error(f"✗ Failed to book session {session}: {e}")
            return False
    
    def _retry_session(self, session: ParkingSession, max_retries: int) -> bool:
        """Retry booking a session with exponential backoff."""
        for attempt in range(max_retries):
            try:
                if self._book_single_session(session):
                    return True
            except InsufficientBalanceError:
                raise  # Don't retry balance errors
            except Exception as e:
                wait_time = self.config['retry_delay_seconds'] * (2 ** attempt)
                logging.warning(f"Retry {attempt + 1}/{max_retries} for {session} in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        logging.error(f"✗ All retries failed for session: {session}")
        return False
    
    def book_parking_sessions(self, time_range: str, session_minutes: int = None, max_break_minutes: int = None):
        """Main method to book multiple parking sessions."""
        start_time = None
        try:
            # Parse parameters with validation
            session_minutes = session_minutes or self.config['session_duration_minutes']
            max_break_minutes = max_break_minutes or self.config['max_break_minutes']
            
            if session_minutes < 1 or session_minutes > 60:
                raise ValueError("Session duration must be between 1 and 60 minutes")
            if max_break_minutes < 0 or max_break_minutes > 30:
                raise ValueError("Max break duration must be between 0 and 30 minutes")
            
            # Parse time range and calculate sessions
            start_time, end_time = self._parse_time_range(time_range)
            sessions = self._calculate_sessions(start_time, end_time, session_minutes, max_break_minutes)
            
            total_duration = int((end_time - start_time).total_seconds() / 60)
            logging.info(f"Starting parking automation for {time_range} ({total_duration} minutes)")
            logging.info(f"Calculated {len(sessions)} sessions: {', '.join(str(s) for s in sessions)}")
            
            # Setup browser and login
            self._setup_driver()
            self._login()
            
            # Check account status before booking
            balance, time_budget = self._get_account_status()
            logging.info(f"ACCOUNT STATUS:")
            logging.info(f"           Balance: €{balance:.2f}")
            logging.info(f"           Time Budget: {time_budget}")
            
            # Balance warning
            if balance < self.config['balance_warning_threshold']:
                logging.warning(f"⚠️  LOW BALANCE: €{balance:.2f} - Consider topping up manually")
            
            # Monthly budget analysis
            self._analyze_monthly_budget(time_budget)
            
            # Estimate cost and check if sufficient
            estimated_cost_per_session = 1.81  # Rough estimate based on screenshot
            total_estimated_cost = len(sessions) * estimated_cost_per_session
            
            if balance < total_estimated_cost:
                logging.warning(f"⚠️  Estimated cost: €{total_estimated_cost:.2f}, Available: €{balance:.2f}")
                logging.warning("May encounter insufficient balance during booking")
            
            # Book sessions
            successful_sessions = []
            failed_sessions = []
            
            for i, session in enumerate(sessions, 1):
                try:
                    logging.info(f"Processing session {i}/{len(sessions)}: {session}")
                    if self._retry_session(session, self.config['max_retries']):
                        successful_sessions.append(session)
                    else:
                        failed_sessions.append(session)
                except InsufficientBalanceError as e:
                    logging.error(f"✗ Insufficient balance: {e}")
                    failed_sessions.extend(sessions[sessions.index(session):])  # Mark remaining as failed
                    break
                except KeyboardInterrupt:
                    logging.info("Booking cancelled by user")
                    failed_sessions.extend(sessions[sessions.index(session):])
                    break
                
                # Progressive delay between bookings to avoid rate limiting
                if i < len(sessions):
                    delay = min(2 + (i * 0.5), 5)  # 2s to 5s delay
                    time.sleep(delay)
            
            # Final summary
            logging.info("=" * 60)
            logging.info(f"BOOKING SUMMARY:")
            logging.info(f"Requested: {len(sessions)} sessions")
            logging.info(f"Successful: {len(successful_sessions)}")
            logging.info(f"Failed: {len(failed_sessions)}")
            
            if successful_sessions:
                logging.info(f"✓ Successfully booked:")
                for session in successful_sessions:
                    logging.info(f"  - {session}")
            
            if failed_sessions:
                logging.info(f"✗ Manual booking required:")
                for session in failed_sessions:
                    logging.info(f"  - {session}")
            
            # Check final account status
            try:
                final_balance, final_time_budget = self._get_account_status()
                cost_incurred = balance - final_balance
                logging.info(f"FINAL ACCOUNT STATUS:")
                logging.info(f"           Balance: €{final_balance:.2f} (spent: €{cost_incurred:.2f})")
                logging.info(f"           Time Budget: {final_time_budget}")
            except Exception as e:
                logging.warning(f"Could not retrieve final account status: {e}")
            
            logging.info("=" * 60)
            
            # Return summary for programmatic use
            return {
                'total_sessions': len(sessions),
                'successful_sessions': len(successful_sessions),
                'failed_sessions': len(failed_sessions),
                'successful_times': [str(s) for s in successful_sessions],
                'failed_times': [str(s) for s in failed_sessions],
                'balance_before': balance,
                'balance_after': final_balance if 'final_balance' in locals() else balance
            }
            
        except KeyboardInterrupt:
            logging.info("Script cancelled by user")
            return None
        except ConfigurationError as e:
            logging.error(f"Configuration error: {e}")
            logging.error("Please check your config.json file")
            return None
        except ValueError as e:
            logging.error(f"Input error: {e}")
            return None
        except Exception as e:
            logging.error(f"Critical error: {e}")
            if start_time:
                logging.error(f"Failed while processing request for: {time_range}")
            return None
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logging.debug("✓ WebDriver closed")
                except Exception:
                    pass


def main():
    """Command line interface with improved argument handling."""
    parser = argparse.ArgumentParser(
        description="Amsterdam Parking Session Automation - Production Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python park.py "13:00-14:00"                    # Basic 1-hour booking
  python park.py "13:10-14:00" --session=15       # Custom session length
  python park.py "15:00-16:30" --max-break=3      # Custom break duration
  python park.py "09:00-17:00" --config=work.json # Different config file
        """
    )
    
    parser.add_argument(
        "time_range", 
        help="Time range in format 'HH:MM-HH:MM' (e.g., '13:00-14:00')"
    )
    parser.add_argument(
        "--session", 
        type=int, 
        metavar="MINUTES",
        help="Session duration in minutes (default: from config, usually 10)"
    )
    parser.add_argument(
        "--max-break", 
        type=int, 
        metavar="MINUTES",
        help="Maximum break duration in minutes (default: from config, usually 5)"
    )
    parser.add_argument(
        "--config", 
        default="config.json", 
        metavar="FILE",
        help="Configuration file path (default: config.json)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Calculate sessions without booking (for testing)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        bot = AmsterdamParkingBot(args.config)
        
        if args.dry_run:
            # Test mode - just calculate and display sessions
            start_time, end_time = bot._parse_time_range(args.time_range)
            session_minutes = args.session or bot.config['session_duration_minutes']
            max_break_minutes = args.max_break or bot.config['max_break_minutes']
            
            sessions = bot._calculate_sessions(start_time, end_time, session_minutes, max_break_minutes)
            
            print(f"DRY RUN - Session calculation for {args.time_range}:")
            print(f"Total sessions: {len(sessions)}")
            for i, session in enumerate(sessions, 1):
                print(f"  {i}. {session} ({session.duration_minutes} minutes)")
            print(f"Total time: {sum(s.duration_minutes for s in sessions)} minutes")
            return
        
        # Normal operation
        result = bot.book_parking_sessions(
            time_range=args.time_range,
            session_minutes=args.session,
            max_break_minutes=args.max_break
        )
        
        if result is None:
            sys.exit(1)
        elif result['failed_sessions'] > 0:
            sys.exit(2)  # Partial success
        else:
            sys.exit(0)  # Complete success
            
    except KeyboardInterrupt:
        logging.info("Cancelled by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()