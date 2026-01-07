"""Extract and parse usage data from NiSource portal."""
import os
import requests
from bs4 import BeautifulSoup
import json
import re
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

# Get usage page
usage_response = session.get("https://myaccount.columbiagasohio.com/usage")

# Find the script tags with usage data
soup = BeautifulSoup(usage_response.text, 'html.parser')
scripts = soup.find_all('script')

usage_bar_data = None
usage_data = None

for script in scripts:
    if script.string:
        # Extract usageBarData
        if 'window.VueTables.usageBarData' in script.string:
            match = re.search(r'window\.VueTables\.usageBarData\s*=\s*(\[.*?\]);', script.string, re.DOTALL)
            if match:
                usage_bar_data = json.loads(match.group(1))

        # Extract usageData
        if 'window.VueTables.usageData' in script.string:
            match = re.search(r'window\.VueTables\.usageData\s*=\s*(\[.*?\]);', script.string, re.DOTALL)
            if match:
                usage_data = json.loads(match.group(1))

if usage_bar_data:
    print("=== Usage Bar Data (Chart Data) ===")
    print(json.dumps(usage_bar_data[:3], indent=2))  # Show first 3 entries
    print(f"\nTotal entries: {len(usage_bar_data)}")

if usage_data:
    print("\n=== Usage Data (Detailed) ===")
    print(json.dumps(usage_data[:3], indent=2))  # Show first 3 entries
    print(f"\nTotal entries: {len(usage_data)}")

# Now check dashboard for account/billing info
dashboard_response = session.get("https://myaccount.columbiagasohio.com/dashboard")
soup_dashboard = BeautifulSoup(dashboard_response.text, 'html.parser')

print("\n=== Looking for account/billing data on dashboard ===")
scripts_dashboard = soup_dashboard.find_all('script')
for script in scripts_dashboard:
    if script.string and 'VueTables' in script.string and 'window.VueTables' in script.string:
        # Look for any Vue data
        if 'account' in script.string.lower() or 'bill' in script.string.lower() or 'balance' in script.string.lower():
            print(f"\nFound potential account data:")
            print(script.string[:1000])
