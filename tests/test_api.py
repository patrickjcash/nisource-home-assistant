"""Test NiSource API endpoints."""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("NISOURCE_USERNAME")
password = os.getenv("NISOURCE_PASSWORD")

# Login
session = requests.Session()
login_response = session.post(
    "https://myaccount.columbiagasohio.com/login",
    data={
        "ReturnUrl": "",
        "Username": username,
        "Password": password,
        "rememberme": "true"
    }
)

print(f"Login successful: {login_response.status_code == 302}")

# Extract account ID from redirect
redirect_url = login_response.headers.get('Location', '')
print(f"Redirect: {redirect_url}")

# Try to find API endpoints by checking common patterns
base_url = "https://myaccount.columbiagasohio.com"

# Test potential API endpoints
endpoints_to_test = [
    "/api/account",
    "/api/usage",
    "/api/billing",
    "/api/dashboard",
    "/dashboard/api/account",
    "/dashboard/api/usage",
]

print("\nTesting API endpoints:")
for endpoint in endpoints_to_test:
    try:
        response = session.get(f"{base_url}{endpoint}")
        print(f"  {endpoint}: {response.status_code}")
        if response.status_code == 200:
            print(f"    Content-Type: {response.headers.get('content-type')}")
            if 'json' in response.headers.get('content-type', ''):
                print(f"    Sample data: {json.dumps(response.json(), indent=2)[:500]}")
    except Exception as e:
        print(f"  {endpoint}: Error - {e}")
