"""Main parking automation bot orchestration."""

import logging
import time

import structlog

from amsterdam_parking.browser import BrowserDriver, LoginPage, NewSessionPage
from amsterdam_parking.config import AppConfig
from amsterdam_parking.models import BookingResult, BookingSummary, ParkingSession

logger = structlog.get_logger()


class ParkingBot:
    """Orchestrates the parking booking automation workflow."""

    def __init__(self, config: AppConfig):
        """Initialize parking bot.

        Args:
            config: Application configuration
        """
        self.config = config
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure structured logging."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(message)s",
        )

        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, self.config.log_level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=False,
        )

    def book_sessions(
        self, sessions: list[ParkingSession], use_tomorrow: bool = False
    ) -> BookingSummary | None:
        """Book multiple parking sessions.

        Args:
            sessions: List of sessions to book
            use_tomorrow: If True, book for tomorrow

        Returns:
            BookingSummary with results, or None if critical failure
        """
        summary = BookingSummary(total_sessions=len(sessions))
        results: list[BookingResult] = []

        try:
            with BrowserDriver(self.config) as driver:
                # Login
                logger.info("logging_in")
                login_page = LoginPage(driver, self.config)
                login_page.navigate()

                if not login_page.login():
                    logger.error("login_failed")
                    return None

                logger.info("login_successful")

                # Book each session
                for i, session in enumerate(sessions, 1):
                    logger.info(
                        "booking_session",
                        session=str(session),
                        number=i,
                        total=len(sessions),
                    )

                    result = self._book_single_session(
                        driver, session, use_tomorrow
                    )
                    results.append(result)

                    if result.success:
                        summary.successful_sessions += 1
                        logger.info("booking_successful", session=str(session))
                    else:
                        summary.failed_sessions += 1
                        logger.error(
                            "booking_failed",
                            session=str(session),
                            error=result.error_message,
                        )

                    # Rate limiting
                    if i < len(sessions):
                        delay = min(2 + (i * 0.5), 5)
                        time.sleep(delay)

                summary.results = results
                return summary

        except Exception as e:
            logger.error("critical_error", error=str(e))
            return None

    def _book_single_session(
        self,
        driver: BrowserDriver,
        session: ParkingSession,
        use_tomorrow: bool,
    ) -> BookingResult:
        """Book a single parking session with retry logic.

        Args:
            driver: Browser driver instance
            session: Session to book
            use_tomorrow: If True, select tomorrow

        Returns:
            BookingResult with outcome
        """
        for attempt in range(1, self.config.max_retries + 1):
            try:
                page = NewSessionPage(driver, self.config)
                page.navigate()

                # Set date
                if not page.set_date(use_tomorrow):
                    raise Exception("Failed to set date")

                # Set times
                if not page.set_times(session):
                    raise Exception("Failed to set times")

                # Proceed to license plate selection
                if not page.click_kenteken_button():
                    raise Exception("Failed to proceed to license plate selection")

                # Select license plate
                if not page.select_license_plate(self.config.license_plate):
                    raise Exception(f"Failed to select license plate: {self.config.license_plate}")

                # Confirm booking
                if not page.confirm_booking():
                    raise Exception("Failed to confirm booking")

                # Wait for confirmation
                if not page.wait_for_confirmation():
                    raise Exception("Booking confirmation not received")

                return BookingResult(
                    session=session,
                    success=True,
                    attempt_count=attempt,
                )

            except Exception as e:
                error_msg = str(e)

                if attempt < self.config.max_retries:
                    wait_time = 2 * (2 ** (attempt - 1))
                    logger.warning(
                        "retry_booking",
                        session=str(session),
                        attempt=attempt,
                        wait_seconds=wait_time,
                        error=error_msg,
                    )
                    time.sleep(wait_time)
                else:
                    return BookingResult(
                        session=session,
                        success=False,
                        error_message=error_msg,
                        attempt_count=attempt,
                    )

        # Should never reach here, but satisfy type checker
        return BookingResult(
            session=session,
            success=False,
            error_message="Max retries exceeded",
            attempt_count=self.config.max_retries,
        )
