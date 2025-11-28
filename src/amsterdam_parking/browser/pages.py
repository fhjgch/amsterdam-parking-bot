"""Page Object Model for Amsterdam parking website pages."""


from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

from amsterdam_parking.browser.driver import BrowserDriver
from amsterdam_parking.config import AppConfig
from amsterdam_parking.models import ParkingSession


class LoginPage:
    """Login page automation."""

    # Element selectors with fallbacks
    USERNAME_SELECTORS = [
        (By.CSS_SELECTOR, "input[placeholder*='meldcode' i]"),
        (By.CSS_SELECTOR, "input[type='text']"),
        (By.NAME, "username"),
    ]

    PASSWORD_SELECTORS = [
        (By.CSS_SELECTOR, "input[placeholder*='pincode' i]"),
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.NAME, "password"),
    ]

    LOGIN_BUTTON_SELECTORS = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(text(), 'Inloggen')]"),
    ]

    def __init__(self, driver: BrowserDriver, config: AppConfig):
        """Initialize login page.

        Args:
            driver: Browser driver instance
            config: Application configuration
        """
        self.driver = driver
        self.config = config

    def navigate(self) -> None:
        """Navigate to login page."""
        self.driver.navigate(self.config.login_url)

    def login(self) -> bool:
        """Perform login.

        Returns:
            True if login successful, False otherwise
        """
        # Find username field
        username_field = self.driver.find_with_fallback(self.USERNAME_SELECTORS)
        if not username_field:
            return False

        username_field.clear()
        username_field.send_keys(self.config.username)

        # Find password field
        password_field = self.driver.find_with_fallback(self.PASSWORD_SELECTORS)
        if not password_field:
            return False

        password_field.clear()
        password_field.send_keys(self.config.password)

        # Find and click login button
        login_button = self.driver.find_with_fallback(self.LOGIN_BUTTON_SELECTORS)
        if not login_button or not self.driver.safe_click(login_button):
            return False

        # Wait for successful login
        return self.driver.wait_for_any(
            [
                EC.url_contains("dashboard"),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'saldo')]")),
            ],
            timeout=30,
        )


class NewSessionPage:
    """New parking session booking page."""

    # Page selectors
    DATE_SELECT = (By.CSS_SELECTOR, "select[name='startDay']")
    START_TIME_INPUT = (By.CSS_SELECTOR, "input[name='startTimeRaw']")
    END_TIME_INPUT = (By.CSS_SELECTOR, "input[name='endTimeRaw']")

    KENTEKEN_BUTTON_SELECTORS = [
        (By.XPATH, "//button[contains(text(), 'Kenteken')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ]

    CONFIRM_BUTTON_SELECTORS = [
        (By.XPATH, "//button[contains(text(), 'Bevestig parkeersessie')]"),
        (By.XPATH, "//button[contains(text(), 'Bevestig')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ]

    def __init__(self, driver: BrowserDriver, config: AppConfig):
        """Initialize new session page.

        Args:
            driver: Browser driver instance
            config: Application configuration
        """
        self.driver = driver
        self.config = config

    def navigate(self) -> None:
        """Navigate to new session page."""
        self.driver.navigate(self.config.new_session_url)
        # Wait for page to load
        self.driver.find_element(By.CSS_SELECTOR, "input[type='time'], select")

    def set_date(self, use_tomorrow: bool = False) -> bool:
        """Set session date.

        Args:
            use_tomorrow: If True, select tomorrow; otherwise today

        Returns:
            True if successful, False otherwise
        """
        if not use_tomorrow:
            return True  # "Vandaag" (today) is default

        try:
            date_element = self.driver.find_element(*self.DATE_SELECT)
            Select(date_element).select_by_visible_text("Morgen")
            return True
        except Exception:
            return False

    def set_times(self, session: ParkingSession) -> bool:
        """Set start and end times.

        Args:
            session: Parking session with times

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to 12-hour format for the website
            start_time_12h = session.start_time.strftime("%I:%M%p")
            end_time_12h = session.end_time.strftime("%I:%M%p")

            # Set start time
            start_input = self.driver.find_element(*self.START_TIME_INPUT)
            start_input.clear()
            start_input.send_keys(start_time_12h)

            # Set end time
            end_input = self.driver.find_element(*self.END_TIME_INPUT)
            end_input.clear()
            end_input.send_keys(end_time_12h)

            return True
        except Exception:
            return False

    def click_kenteken_button(self) -> bool:
        """Click button to proceed to license plate selection.

        Returns:
            True if successful, False otherwise
        """
        for by, selector in self.KENTEKEN_BUTTON_SELECTORS:
            try:
                button = self.driver.find_element_clickable(by, selector)
                if self.driver.safe_click(button):
                    # Wait for license plate page
                    self.driver.find_element(By.XPATH, "//input[@type='radio']", timeout=10)
                    return True
            except Exception:
                continue
        return False

    def select_license_plate(self, plate_name: str) -> bool:
        """Select license plate radio button.

        Args:
            plate_name: Name/identifier for the license plate

        Returns:
            True if successful, False otherwise
        """
        # Try various selectors
        selectors = [
            (By.XPATH, f"//label[.//span[contains(text(), '{plate_name}')]]"),
            (By.XPATH, f"//span[contains(text(), '{plate_name}')]//ancestor::label"),
            (By.XPATH, f"//label[contains(., '{plate_name}')]"),
        ]

        for by, selector in selectors:
            try:
                element = self.driver.find_element_clickable(by, selector, timeout=5)
                if self.driver.safe_click(element):
                    return True
            except Exception:
                continue

        # Fallback: search through all buttons
        try:
            if self.driver.driver:
                buttons = self.driver.driver.find_elements(By.CSS_SELECTOR, "button")
                for button in buttons:
                    inner_html = button.get_attribute("innerHTML") or ""
                    if plate_name.lower() in inner_html.lower():
                        if self.driver.safe_click(button):
                            return True
        except Exception:
            pass

        return False

    def confirm_booking(self) -> bool:
        """Click confirm booking button.

        Returns:
            True if successful, False otherwise
        """
        for by, selector in self.CONFIRM_BUTTON_SELECTORS:
            try:
                button = self.driver.find_element_clickable(by, selector)
                if self.driver.safe_click(button):
                    return True
            except Exception:
                continue
        return False

    def wait_for_confirmation(self) -> bool:
        """Wait for booking confirmation.

        Returns:
            True if confirmation received, False otherwise
        """
        return self.driver.wait_for_any(
            [
                EC.url_contains("success"),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'bevestigd')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'gepland')]")),
            ],
            timeout=15,
        )
