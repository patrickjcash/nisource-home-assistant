"""Thoroughly search for API endpoints."""
import os
import requests
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

print(f"Login status: {login_response.status_code}")
print(f"Session cookies: {list(session.cookies.keys())}")

# The account ID from the redirect was: 216014150010009
# State: OH
# Let's try various API endpoint patterns

base_url = "https://myaccount.columbiagasohio.com"
account_id = "216014150010009"

# Common API patterns to test
endpoints_to_test = [
    # NiSource API patterns (we saw /nisource-api/ldc/)
    f"/nisource-api/ldc/account/{account_id}",
    f"/nisource-api/ldc/accounts/{account_id}",
    "/nisource-api/ldc/account",
    "/nisource-api/ldc/accounts",
    f"/nisource-api/ldc/usage/{account_id}",
    "/nisource-api/ldc/usage",
    f"/nisource-api/ldc/billing/{account_id}",
    "/nisource-api/ldc/billing",
    f"/nisource-api/ldc/bills/{account_id}",
    "/nisource-api/ldc/bills",
    f"/nisource-api/ldc/balance/{account_id}",
    "/nisource-api/ldc/balance",
    f"/nisource-api/ldc/history/{account_id}",
    "/nisource-api/ldc/history",

    # Direct API patterns
    "/api/account",
    f"/api/account/{account_id}",
    "/api/usage",
    f"/api/usage/{account_id}",
    "/api/billing",
    "/api/bills",

    # Vue/Ajax patterns
    "/ajax/account",
    "/ajax/usage",
    "/ajax/billing",

    # Data endpoints
    "/data/account",
    "/data/usage",
    "/data/billing",
]

print(f"\n=== Testing {len(endpoints_to_test)} potential API endpoints ===\n")

found_endpoints = []

for endpoint in endpoints_to_test:
    try:
        # Try GET first
        response = session.get(f"{base_url}{endpoint}", timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'json' in content_type:
                print(f"✓ GET {endpoint}")
                print(f"  Status: {response.status_code}")
                print(f"  Content-Type: {content_type}")
                print(f"  Response preview: {response.text[:200]}")
                found_endpoints.append(('GET', endpoint, response))
                continue

        # Try POST if GET didn't work
        response_post = session.post(f"{base_url}{endpoint}", json={}, timeout=5)
        if response_post.status_code in (200, 201):
            content_type = response_post.headers.get('content-type', '')
            if 'json' in content_type:
                print(f"✓ POST {endpoint}")
                print(f"  Status: {response_post.status_code}")
                print(f"  Content-Type: {content_type}")
                print(f"  Response preview: {response_post.text[:200]}")
                found_endpoints.append(('POST', endpoint, response_post))

    except Exception as e:
        pass  # Silently skip errors

if found_endpoints:
    print(f"\n=== Found {len(found_endpoints)} working JSON endpoints ===")
    for method, endpoint, response in found_endpoints:
        print(f"\n{method} {endpoint}")
        print(f"Full response:\n{response.text[:1000]}")
else:
    print("\n❌ No JSON API endpoints found")
    print("\nLet's check what the browser's Network tab shows...")
    print("Please manually check the Network tab for XHR/Fetch requests after navigating to:")
    print("  - https://myaccount.columbiagasohio.com/dashboard")
    print("  - https://myaccount.columbiagasohio.com/usage")
    print("  - https://myaccount.columbiagasohio.com/billing")
