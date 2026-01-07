"""API client for NiSource gas utilities."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from io import StringIO
import logging
from typing import Any

import requests

from .const import (
    ENDPOINT_ACCOUNT_SUMMARY,
    ENDPOINT_BILLING_HISTORY_CSV,
    ENDPOINT_LOGIN,
    ENDPOINT_PAYMENT_HISTORY_CSV,
    ENDPOINT_USAGE_HISTORY_CSV,
)

_LOGGER = logging.getLogger(__name__)


class NiSourceAPI:
    """API client for NiSource gas utilities."""

    def __init__(self, base_url: str, username: str, password: str, state_code: str) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for the provider (e.g., https://myaccount.columbiagasohio.com)
            username: User's email address
            password: User's password
            state_code: State code for the provider (e.g., OH, KY, PA, MD, VA, IN)
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.state_code = state_code
        self.session = requests.Session()
        self._authenticated = False

    def authenticate(self) -> None:
        """Authenticate with form-based login."""
        try:
            # Perform login POST request
            response = self.session.post(
                f"{self.base_url}{ENDPOINT_LOGIN}",
                data={
                    "ReturnUrl": "",
                    "Username": self.username,
                    "Password": self.password,
                    "rememberme": "true",
                },
                allow_redirects=True,
                timeout=30,
            )

            # Check if login was successful
            # Successful login redirects to /dashboard/{account_id}/{state}?dlp=LoginSuccess
            if "LoginSuccess" in response.url or response.status_code == 200:
                self._authenticated = True
                _LOGGER.debug("Successfully authenticated with NiSource portal")
            else:
                _LOGGER.error("Login failed: unexpected response %s", response.url)
                raise ValueError("Login failed - check credentials")

        except Exception as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise

    def _ensure_authenticated(self) -> None:
        """Ensure the session is authenticated."""
        if not self._authenticated:
            self.authenticate()

    def get_usage_history_csv(self) -> list[dict[str, str]]:
        """Get usage history from CSV endpoint.

        Returns:
            List of dictionaries with usage data:
            - Date: MM/DD/YYYY
            - Type of Read: ACTUAL READING or CALC BY DATA CENTER
            - Avg Temp: Average temperature in °F
            - Number of Days: Billing period length
            - Units Used: CCF (hundred cubic feet)
            - Yearly Usage: Percentage change (e.g., "20%")
            - Bill Amount: Dollar amount (e.g., "$232.00")
            - Cost per Day: Dollar amount (e.g., "$7.03")
        """
        self._ensure_authenticated()

        try:
            response = self.session.get(
                f"{self.base_url}{ENDPOINT_USAGE_HISTORY_CSV}",
                timeout=30,
            )
            response.raise_for_status()

            # Parse CSV
            csv_file = StringIO(response.text)
            reader = csv.DictReader(csv_file)
            data = list(reader)

            _LOGGER.debug("Retrieved %d usage history records", len(data))
            return data

        except Exception as err:
            _LOGGER.error("Failed to get usage history: %s", err)
            raise

    def get_billing_history_csv(self) -> list[dict[str, str]]:
        """Get billing history from CSV endpoint.

        Returns:
            List of dictionaries with billing data
        """
        self._ensure_authenticated()

        try:
            response = self.session.get(
                f"{self.base_url}{ENDPOINT_BILLING_HISTORY_CSV}",
                timeout=30,
            )
            response.raise_for_status()

            # Parse CSV
            csv_file = StringIO(response.text)
            reader = csv.DictReader(csv_file)
            data = list(reader)

            _LOGGER.debug("Retrieved %d billing history records", len(data))
            return data

        except Exception as err:
            _LOGGER.error("Failed to get billing history: %s", err)
            raise

    def get_payment_history_csv(self) -> list[dict[str, str]]:
        """Get payment history from CSV endpoint.

        Returns:
            List of dictionaries with payment data
        """
        self._ensure_authenticated()

        try:
            response = self.session.get(
                f"{self.base_url}{ENDPOINT_PAYMENT_HISTORY_CSV}",
                timeout=30,
            )
            response.raise_for_status()

            # Parse CSV
            csv_file = StringIO(response.text)
            reader = csv.DictReader(csv_file)
            data = list(reader)

            _LOGGER.debug("Retrieved %d payment history records", len(data))
            return data

        except Exception as err:
            _LOGGER.error("Failed to get payment history: %s", err)
            raise

    def get_account_summary(self) -> dict[str, Any]:
        """Get account summary from JSON API.

        Returns:
            Account summary with linked accounts and balance information:
            {
                "linkedAccounts": [{
                    "customerAccountId": "XXXXXXXXXXXX",
                    "customerNumber": "XXXXXXXX",
                    "serviceAddress": {...},
                    "customerAccountBalance": {
                        "balanceAmount": 0.00,
                        "dueDate": "2025-12-29",
                        "pastDueAmount": 0.00,
                        "currentAmountDue": 0.00
                    },
                    "status": "Active",
                    "ldc": "OH"
                }],
                "count": 1
            }
        """
        self._ensure_authenticated()

        try:
            # Note: diagId appears to be a timestamp or random ID
            # Using current timestamp
            diag_id = int(datetime.now().timestamp() * 1000)

            response = self.session.get(
                f"{self.base_url}{ENDPOINT_ACCOUNT_SUMMARY}",
                params={
                    "query": "",
                    "limit": 10,
                    "ascending": 1,
                    "page": 1,
                    "byColumn": 0,
                    "diagId": diag_id,
                },
                headers={
                    "x-nis-ldc": self.state_code,
                    "adrum": "isAjax:true",
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            _LOGGER.debug("Retrieved account summary for %d accounts", data.get("count", 0))
            return data

        except Exception as err:
            _LOGGER.error("Failed to get account summary: %s", err)
            raise

    @staticmethod
    def parse_currency(value: str) -> float:
        """Parse currency string to float.

        Args:
            value: Currency string like "$232.00" or "$7.03"

        Returns:
            Float value
        """
        if not value:
            return 0.0
        # Remove $ and commas, then convert to float
        return float(value.replace("$", "").replace(",", "").strip())

    @staticmethod
    def parse_percentage(value: str) -> float:
        """Parse percentage string to float.

        Args:
            value: Percentage string like "20%" or "-5%"

        Returns:
            Float value (20.0 for "20%")
        """
        if not value:
            return 0.0
        # Remove % and convert to float
        return float(value.replace("%", "").strip())

    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """Parse date string from CSV.

        Args:
            date_str: Date string in MM/DD/YYYY format

        Returns:
            datetime object
        """
        return datetime.strptime(date_str, "%m/%d/%Y")

    @staticmethod
    def get_csv_value(row: dict[str, str], field_name: str) -> str | None:
        """Get value from CSV row, handling column names with or without leading spaces.

        NiSource's CSV format has inconsistent column naming - some columns have
        leading spaces (e.g., ' Bill Amount' instead of 'Bill Amount'). This method
        tries both variants to ensure compatibility if they fix their CSV format.

        Args:
            row: Dictionary representing a CSV row
            field_name: The field name to retrieve (without leading space)

        Returns:
            The field value, or None if not found
        """
        # Try exact match first
        value = row.get(field_name)
        if value is not None:
            return value

        # Try with leading space
        value = row.get(f" {field_name}")
        if value is not None:
            return value

        # Not found
        return None
