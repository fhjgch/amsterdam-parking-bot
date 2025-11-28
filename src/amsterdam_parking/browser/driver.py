"""WebDriver setup and management."""

import time
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from amsterdam_parking.config import AppConfig


class BrowserDriver:
    """Manages Chrome WebDriver lifecycle and element interactions."""

    def __init__(self, config: AppConfig):
        """Initialize browser driver.

        Args:
            config: Application configuration
        """
        self.config = config
        self.driver: WebDriver | None = None
        self.wait: WebDriverWait | None = None

    def __enter__(self) -> "BrowserDriver":
        """Context manager entry - setup driver."""
        self.setup()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - cleanup driver."""
        self.quit()

    def setup(self) -> None:
        """Initialize and configure Chrome WebDriver."""
        options = Options()

        # Standard Chrome options for stability
        chrome_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--disable-blink-features=AutomationControlled",
        ]

        if self.config.headless:
            chrome_args.append("--headless=new")

        for arg in chrome_args:
            options.add_argument(arg)

        # Additional preferences
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(self.config.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(5)

        self.wait = WebDriverWait(self.driver, self.config.timeout_seconds)

    def quit(self) -> None:
        """Close browser and cleanup resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
                self.wait = None

    def navigate(self, url: str) -> None:
        """Navigate to URL.

        Args:
            url: Target URL

        Raises:
            RuntimeError: If driver not initialized
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Call setup() first.")
        self.driver.get(url)

    def find_element(
        self, by: By, selector: str, timeout: int | None = None
    ) -> WebElement:
        """Find element with explicit wait.

        Args:
            by: Selenium By strategy
            selector: Element selector
            timeout: Optional custom timeout

        Returns:
            WebElement if found

        Raises:
            TimeoutException: If element not found within timeout
            RuntimeError: If driver not initialized
        """
        if not self.wait:
            raise RuntimeError("Driver not initialized. Call setup() first.")

        wait = (
            WebDriverWait(self.driver, timeout) if timeout else self.wait  # type: ignore
        )
        return wait.until(EC.presence_of_element_located((by, selector)))

    def find_element_clickable(
        self, by: By, selector: str, timeout: int | None = None
    ) -> WebElement:
        """Find clickable element with explicit wait.

        Args:
            by: Selenium By strategy
            selector: Element selector
            timeout: Optional custom timeout

        Returns:
            Clickable WebElement

        Raises:
            TimeoutException: If element not found or not clickable
            RuntimeError: If driver not initialized
        """
        if not self.wait:
            raise RuntimeError("Driver not initialized. Call setup() first.")

        wait = (
            WebDriverWait(self.driver, timeout) if timeout else self.wait  # type: ignore
        )
        return wait.until(EC.element_to_be_clickable((by, selector)))

    def find_with_fallback(self, selectors: list[tuple[By, str]]) -> WebElement | None:
        """Try multiple selectors until one succeeds.

        Args:
            selectors: List of (By, selector) tuples to try

        Returns:
            First matching WebElement, or None if all fail
        """
        for by, selector in selectors:
            try:
                return self.find_element(by, selector)
            except TimeoutException:
                continue
        return None

    def safe_click(self, element: WebElement) -> bool:
        """Click element with fallback strategies.

        Args:
            element: Element to click

        Returns:
            True if click succeeded, False otherwise
        """
        if not self.driver:
            return False

        # Strategy 1: Normal click
        try:
            element.click()
            return True
        except Exception:
            pass

        # Strategy 2: JavaScript click with delay
        try:
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            pass

        # Strategy 3: Dispatch click event
        try:
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));",
                element,
            )
            return True
        except Exception:
            return False

    def wait_for_any(self, conditions: list[Any], timeout: int = 15) -> bool:
        """Wait for any of multiple conditions.

        Args:
            conditions: List of expected_conditions
            timeout: Timeout in seconds

        Returns:
            True if any condition met, False otherwise
        """
        if not self.driver:
            return False

        try:
            WebDriverWait(self.driver, timeout).until(EC.any_of(*conditions))
            return True
        except TimeoutException:
            return False
