"""Test scraping usage page for embedded data."""
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

print(f"Login status: {login_response.status_code}")

# Get usage page
usage_response = session.get("https://myaccount.columbiagasohio.com/usage")
print(f"\nUsage page status: {usage_response.status_code}")

# Parse HTML
soup = BeautifulSoup(usage_response.text, 'html.parser')

# Look for embedded JSON data in script tags
scripts = soup.find_all('script')
print(f"\nFound {len(scripts)} script tags")

for i, script in enumerate(scripts):
    if script.string:
        # Look for common patterns of embedded data
        if 'window.' in script.string or 'var ' in script.string:
            # Check for JSON-like structures
            if '{' in script.string and ':' in script.string:
                print(f"\n--- Script {i} (potential data) ---")
                print(script.string[:500])

# Also check for data attributes
elements_with_data = soup.find_all(attrs={'data-usage': True})
if elements_with_data:
    print("\n\nFound elements with data-usage attributes:")
    for elem in elements_with_data:
        print(elem)
