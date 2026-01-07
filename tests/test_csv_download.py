"""Test CSV download endpoint."""
import os
import requests
import csv
from io import StringIO
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

# Download CSV
csv_response = session.get("https://myaccount.columbiagasohio.com/UsageHistoryAllCsv/0")

print(f"\nCSV download status: {csv_response.status_code}")
print(f"Content-Type: {csv_response.headers.get('content-type')}")
print(f"Content-Length: {csv_response.headers.get('content-length')}")

if csv_response.status_code == 200:
    print("\n=== CSV Content ===")
    print(csv_response.text[:1000])

    # Parse CSV
    csv_file = StringIO(csv_response.text)
    reader = csv.DictReader(csv_file)

    print("\n=== Parsed CSV Data ===")
    rows = list(reader)
    print(f"Total rows: {len(rows)}")

    if rows:
        print(f"\nColumn names: {list(rows[0].keys())}")
        print(f"\nFirst 3 rows:")
        for row in rows[:3]:
            print(row)

# Also check if there are other CSV endpoints
other_endpoints = [
    "/UsageHistoryAllCsv/1",  # Maybe different account?
    "/BillingHistoryCsv",
    "/BillingHistoryCsv/0",
    "/PaymentHistoryCsv",
    "/PaymentHistoryCsv/0",
]

print("\n=== Testing other potential CSV endpoints ===")
for endpoint in other_endpoints:
    try:
        resp = session.get(f"https://myaccount.columbiagasohio.com{endpoint}")
        if resp.status_code == 200 and 'text/csv' in resp.headers.get('content-type', ''):
            print(f"✓ Found: {endpoint}")
            print(f"  Preview: {resp.text[:200]}")
    except:
        pass
