"""Test NiSource authentication flow."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("NISOURCE_USERNAME")
password = os.getenv("NISOURCE_PASSWORD")

print(f"Testing login for: {username}")

# Test login
url = "https://myaccount.columbiagasohio.com/login"
data = {
    "ReturnUrl": "",
    "Username": username,
    "Password": password,
    "rememberme": "true"
}

session = requests.Session()
response = session.post(url, data=data, allow_redirects=False)

print(f"\nStatus: {response.status_code}")
print(f"Redirect Location: {response.headers.get('Location', 'No redirect')}")
print(f"\nCookies after login:")
for cookie_name, cookie_value in session.cookies.items():
    print(f"  {cookie_name}: {cookie_value[:50]}...")

# Follow redirect if present
if response.status_code in (301, 302, 303, 307, 308):
    redirect_url = response.headers.get('Location')
    if redirect_url:
        if not redirect_url.startswith('http'):
            redirect_url = 'https://myaccount.columbiagasohio.com' + redirect_url
        print(f"\nFollowing redirect to: {redirect_url}")
        response2 = session.get(redirect_url)
        print(f"Redirect response status: {response2.status_code}")
        print(f"Final URL: {response2.url}")
