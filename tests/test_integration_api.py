#!/usr/bin/env python3
"""Test NiSource integration API client."""

import os
import sys
from pathlib import Path

# Add parent directory to path to import the integration
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.nisource.api import NiSourceAPI
from custom_components.nisource.const import PROVIDERS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed, using environment variables directly")

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

    api = NiSourceAPI(
        base_url=provider_info["base_url"],
        username=username,
        password=password,
        state_code=provider_info["state_code"]
    )

    # Test authentication
    print("\n1. Testing authentication...")
    try:
        api.authenticate()
        print("✓ Authentication successful!")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False

    # Test usage history CSV
    print("\n2. Testing usage history CSV...")
    try:
        usage_csv = api.get_usage_history_csv()
        print(f"✓ Retrieved {len(usage_csv)} usage history records")
        if usage_csv:
            print(f"  Latest record: {usage_csv[-1]}")
    except Exception as e:
        print(f"✗ Failed to get usage history: {e}")
        return False

    # Test account summary
    print("\n3. Testing account summary...")
    try:
        account = api.get_account_summary()
        print(f"✓ Retrieved account summary")
        if account.get("linkedAccounts"):
            account_info = account["linkedAccounts"][0]
            print(f"  Account ID: {account_info.get('customerAccountId')}")
            print(f"  Status: {account_info.get('status')}")
            balance = account_info.get("customerAccountBalance", {})
            print(f"  Balance: ${balance.get('balanceAmount', 0)}")
    except Exception as e:
        print(f"✗ Failed to get account summary: {e}")
        return False

    # Test billing history CSV
    print("\n4. Testing billing history CSV...")
    try:
        billing_csv = api.get_billing_history_csv()
        print(f"✓ Retrieved {len(billing_csv)} billing history records")
    except Exception as e:
        print(f"✗ Failed to get billing history: {e}")
        return False

    print("\n✓ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_api_client()
    sys.exit(0 if success else 1)
