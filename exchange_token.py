"""Helper script to exchange short-lived Instagram token for long-lived token"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Short-lived token obtained from Meta Developer Console
# Note: Token was extracted on 2025-12-04 - update if expired
# Get the latest token from: https://developers.facebook.com/tools/accesstoken/
# Look for "Cascade Game Simulator" app and copy the User Token
SHORT_LIVED_TOKEN = "EAARZAG8x3iPIBQDOipkEcG0Pkt1qtFxJpNZBVvfTNnOXC2bKIppnQ4fQoHMgKAYrfNr7yVbPjNgcPGdcnyyi5Lh23fUNWA8E8cZBCZB4tQdz91JEZCMC uYXXgZAvUmNXlbeBH7dNmEeopGMzilSMTBezEtyS0GZCG3z8bMRhr7mZAohDH8aZCGt4SbjZC Xyuu95kw".replace(" ", "")

# App credentials
APP_ID = os.getenv('META_APP_ID') or "1223875836217586"  # Cascade Game Simulator App ID
APP_SECRET = os.getenv('META_APP_SECRET')

if not APP_SECRET:
    print("⚠️  META_APP_SECRET not found in environment variables.")
    print("Please set META_APP_SECRET in your .env file to exchange for a long-lived token.")
    print("\nTo get your App Secret:")
    print("1. Go to https://developers.facebook.com/apps/1223875836217586/settings/basic/")
    print("2. Click 'Show' next to App Secret (you may need to enter your password)")
    print("3. Copy the App Secret and add it to your .env file:")
    print("   META_APP_SECRET=your_app_secret_here")
    print("\nFor now, you can use this short-lived token directly in your .env file:")
    print(f"CASCADIA_ACCESS_TOKEN={SHORT_LIVED_TOKEN}")
    exit(1)

print("Exchanging short-lived token for long-lived token...")
print(f"App ID: {APP_ID}")

url = "https://graph.facebook.com/v21.0/oauth/access_token"
params = {
    'grant_type': 'fb_exchange_token',
    'client_id': APP_ID,
    'client_secret': APP_SECRET,
    'fb_exchange_token': SHORT_LIVED_TOKEN
}

try:
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        result = response.json()
        long_lived_token = result.get('access_token')
        expires_in = result.get('expires_in', 5184000)  # Default to 60 days
        
        if long_lived_token:
            print("\n✅ Success! Long-lived token obtained:")
            print(f"Token: {long_lived_token}")
            print(f"Expires in: {expires_in} seconds ({expires_in / 86400:.1f} days)")
            print("\nAdd this to your .env file:")
            print(f"CASCADIA_ACCESS_TOKEN={long_lived_token}")
        else:
            print(f"❌ No access_token in response: {result}")
    else:
        error_data = response.json() if response.content else {}
        print(f"❌ Token exchange failed: {error_data}")
        print(f"Status code: {response.status_code}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
