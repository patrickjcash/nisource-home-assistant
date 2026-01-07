#!/usr/bin/env python3
"""Standalone test for NiSource API client - diagnose integration issues without HA dependencies."""

import os
import sys
import csv
import requests
from io import StringIO
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed, using environment variables directly")

# Provider configurations
PROVIDERS = {
    "OH": {
        "name": "Columbia Gas of Ohio",
        "base_url": "https://myaccount.columbiagasohio.com",
        "state_code": "OH",
    },
}

class StandaloneNiSourceAPI:
    """Standalone API client for testing."""

    def __init__(self, base_url: str, username: str, password: str, state_code: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.state_code = state_code
        self.session = requests.Session()
        self._authenticated = False

    def authenticate(self) -> None:
        """Authenticate with NiSource portal."""
        response = self.session.post(
            f"{self.base_url}/login",
            data={
                "ReturnUrl": "",
                "Username": self.username,
                "Password": self.password,
                "rememberme": "true",
            },
            allow_redirects=True,
            timeout=30,
        )

        if "LoginSuccess" in response.url or response.status_code == 200:
            self._authenticated = True
        else:
            raise Exception(f"Authentication failed: {response.status_code}")

    def get_usage_history_csv(self) -> list[dict]:
        """Get usage history as CSV."""
        if not self._authenticated:
            raise Exception("Not authenticated")

        response = self.session.get(
            f"{self.base_url}/UsageHistoryAllCsv/0",
            timeout=30,
        )
        response.raise_for_status()

        csv_file = StringIO(response.text)
        reader = csv.DictReader(csv_file)
        return list(reader)

    def get_account_summary(self) -> dict:
        """Get account summary JSON."""
        if not self._authenticated:
            raise Exception("Not authenticated")

        response = self.session.get(
            f"{self.base_url}/api/LinkedAccounts/1.0",
            params={
                "query": "",
                "limit": "10",
                "ascending": "1",
                "page": "1",
                "byColumn": "0",
                "diagId": "",
            },
            headers={
                "x-nis-ldc": self.state_code,
                "adrum": "isAjax:true",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def parse_date(self, date_str: str) -> datetime:
        """Parse MM/DD/YYYY format."""
        return datetime.strptime(date_str, "%m/%d/%Y")

    def parse_currency(self, currency_str: str) -> float:
        """Parse currency string like '$123.45'."""
        return float(currency_str.replace("$", "").replace(",", ""))

    @staticmethod
    def get_csv_value(row: dict, field_name: str):
        """Get value from CSV row, handling column names with or without leading spaces."""
        # Try exact match first
        value = row.get(field_name)
        if value is not None:
            return value
        # Try with leading space
        value = row.get(f" {field_name}")
        if value is not None:
            return value
        return None


def test_api_client():
    """Test the API client with real credentials."""
    username = os.getenv("NISOURCE_USERNAME")
    password = os.getenv("NISOURCE_PASSWORD")

    if not username or not password:
        print("ERROR: NISOURCE_USERNAME and NISOURCE_PASSWORD must be set in .env file")
        return False

    # Test with Ohio provider (default)
    provider_code = "OH"
    provider_info = PROVIDERS[provider_code]

    print(f"Testing NiSource API client...")
    print(f"Provider: {provider_info['name']}")
    print(f"Base URL: {provider_info['base_url']}")
    print(f"Username: {username}")

    api = StandaloneNiSourceAPI(
        base_url=provider_info["base_url"],
        username=username,
        password=password,
        state_code=provider_info["state_code"]
    )

    # Test authentication
    print("\n" + "="*80)
    print("1. TESTING AUTHENTICATION")
    print("="*80)
    try:
        api.authenticate()
        print("✓ Authentication successful!")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False

    # Test usage history CSV with detailed analysis
    print("\n" + "="*80)
    print("2. TESTING USAGE HISTORY CSV (Detailed Analysis)")
    print("="*80)
    try:
        usage_csv = api.get_usage_history_csv()
        print(f"✓ Retrieved {len(usage_csv)} usage history records")

        if usage_csv:
            # Show CSV structure (column names)
            print(f"\n  CSV Columns: {list(usage_csv[0].keys())}")

            # Check for critical fields
            print(f"\n  Checking for required fields:")
            first_row = usage_csv[0]
            print(f"    - 'Date' field: {'✓ Present' if 'Date' in first_row else '✗ MISSING'}")
            print(f"    - 'Units Used' field: {'✓ Present' if 'Units Used' in first_row else '✗ MISSING'}")
            print(f"    - 'Bill Amount' field: {'✓ Present' if 'Bill Amount' in first_row else '✗ MISSING'}")

            # Show first record (newest)
            print(f"\n  First record (newest): {usage_csv[0]}")

            # Show last record (oldest)
            print(f"\n  Last record (oldest): {usage_csv[-1]}")

            # Test date parsing
            print(f"\n  Testing date parsing:")
            date_str = first_row.get("Date")
            if date_str:
                try:
                    parsed_date = api.parse_date(date_str)
                    print(f"    Date string: '{date_str}'")
                    print(f"    Parsed date: {parsed_date}")
                    print(f"    ✓ Date parsing successful")
                except Exception as e:
                    print(f"    ✗ Date parsing failed: {e}")

            # Test Units Used parsing
            print(f"\n  Testing 'Units Used' parsing:")
            units_str = first_row.get("Units Used")
            if units_str:
                try:
                    units_float = float(units_str)
                    print(f"    Units Used string: '{units_str}'")
                    print(f"    Parsed value: {units_float} CCF")
                    print(f"    ✓ Units parsing successful")
                except Exception as e:
                    print(f"    ✗ Units parsing failed: {e}")
            else:
                print(f"    ✗ 'Units Used' field is empty or missing")

            # Test Bill Amount parsing using helper
            print(f"\n  Testing 'Bill Amount' parsing (using get_csv_value helper):")
            bill_str = api.get_csv_value(first_row, "Bill Amount")
            if bill_str:
                try:
                    bill_float = api.parse_currency(bill_str)
                    print(f"    Bill Amount string: '{bill_str}'")
                    print(f"    Parsed value: ${bill_float}")
                    print(f"    ✓ Bill amount parsing successful")
                except Exception as e:
                    print(f"    ✗ Bill amount parsing failed: {e}")
            else:
                print(f"    ✗ 'Bill Amount' field is empty or missing")

            # Simulate statistics calculation
            print(f"\n  Simulating consumption statistics calculation:")
            consumption_sum = 0.0
            consumption_count = 0
            print(f"    Processing records in reversed (chronological) order:")
            for i, row in enumerate(reversed(usage_csv)):
                date_str = row.get("Date")
                units_str = row.get("Units Used")
                if date_str and units_str:
                    try:
                        parsed_date = api.parse_date(date_str).replace(
                            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                        )
                        ccf = float(units_str)
                        consumption_sum += ccf
                        consumption_count += 1

                        if i < 3:  # Show first 3 records
                            print(f"      Record {i+1}: Date={parsed_date}, CCF={ccf}, Cumulative={consumption_sum:.2f}")
                    except Exception as e:
                        print(f"      ✗ Failed to process record {i+1}: {e}")

            print(f"    Total records processed: {consumption_count}/{len(usage_csv)}")
            print(f"    Final cumulative sum: {consumption_sum:.2f} CCF")
            if consumption_sum < 0:
                print(f"    ✗ WARNING: Negative cumulative sum detected!")
            else:
                print(f"    ✓ Cumulative sum is positive")

            # Simulate cost statistics calculation
            print(f"\n  Simulating cost statistics calculation:")
            cost_sum = 0.0
            cost_count = 0
            print(f"    Processing records in reversed (chronological) order:")
            for i, row in enumerate(reversed(usage_csv)):
                date_str = row.get("Date")
                bill_str = api.get_csv_value(row, "Bill Amount")
                if date_str and bill_str:
                    try:
                        parsed_date = api.parse_date(date_str).replace(
                            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                        )
                        cost = api.parse_currency(bill_str)
                        cost_sum += cost
                        cost_count += 1

                        if i < 3:  # Show first 3 records
                            print(f"      Record {i+1}: Date={parsed_date}, Cost=${cost:.2f}, Cumulative=${cost_sum:.2f}")
                    except Exception as e:
                        print(f"      ✗ Failed to process record {i+1}: {e}")

            print(f"    Total cost records processed: {cost_count}/{len(usage_csv)}")
            print(f"    Final cumulative cost: ${cost_sum:.2f}")
            if cost_count == 0:
                print(f"    ✗ WARNING: No cost records were processed!")
            else:
                print(f"    ✓ Cost statistics would be created")

    except Exception as e:
        print(f"✗ Failed to get usage history: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test account summary with Due Date check
    print("\n" + "="*80)
    print("3. TESTING ACCOUNT SUMMARY (Due Date Analysis)")
    print("="*80)
    try:
        account = api.get_account_summary()
        print(f"✓ Retrieved account summary")

        if account.get("linkedAccounts"):
            account_info = account["linkedAccounts"][0]
            print(f"\n  Account Details:")
            print(f"    Account ID: {account_info.get('customerAccountId')}")
            print(f"    Customer Number: {account_info.get('customerNumber')}")
            print(f"    Status: {account_info.get('status')}")

            balance = account_info.get("customerAccountBalance", {})
            print(f"\n  Balance Information:")
            print(f"    Balance Amount: ${balance.get('balanceAmount', 0)}")
            print(f"    Current Amount Due: ${balance.get('currentAmountDue', 0)}")
            print(f"    Past Due Amount: ${balance.get('pastDueAmount', 0)}")

            # Check Due Date
            due_date = balance.get("dueDate")
            print(f"\n  Due Date Check:")
            print(f"    dueDate field: '{due_date}'")
            if due_date:
                try:
                    parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    print(f"    Parsed due date: {parsed_due_date}")
                    print(f"    ✓ Due Date is valid and should be visible")
                except Exception as e:
                    print(f"    ✗ Due Date parsing failed: {e}")
                    print(f"    This explains why Due Date sensor is hidden")
            else:
                print(f"    ✗ Due Date field is empty or missing")
                print(f"    This explains why Due Date sensor is hidden")

    except Exception as e:
        print(f"✗ Failed to get account summary: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test sensor value extraction
    print("\n" + "="*80)
    print("4. TESTING SENSOR VALUE EXTRACTION")
    print("="*80)

    print(f"\n  Testing Gas Usage sensor (should use usage_csv[0]):")
    if usage_csv:
        latest = usage_csv[0]  # CSV is newest-to-oldest
        units_used = latest.get("Units Used")
        if units_used:
            try:
                gas_usage = float(units_used)
                print(f"    ✓ Gas Usage: {gas_usage} CCF")
            except Exception as e:
                print(f"    ✗ Failed to parse: {e}")
        else:
            print(f"    ✗ 'Units Used' field is missing from latest record")

    print(f"\n  Testing Total Bill sensor (should use usage_csv[0]):")
    if usage_csv:
        latest = usage_csv[0]
        bill_amount = api.get_csv_value(latest, "Bill Amount")
        if bill_amount:
            try:
                total_bill = api.parse_currency(bill_amount)
                print(f"    ✓ Total Bill: ${total_bill}")
            except Exception as e:
                print(f"    ✗ Failed to parse: {e}")
        else:
            print(f"    ✗ 'Bill Amount' field is missing from latest record")
            print(f"    Recommendation: Remove Total Bill sensor if this field is not available")

    print("\n" + "="*80)
    print("✓ ALL DIAGNOSTIC TESTS COMPLETED")
    print("="*80)
    return True

if __name__ == "__main__":
    success = test_api_client()
    sys.exit(0 if success else 1)
