"""Test script to verify Instagram access token health and refresh configuration"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    import instagram_poster
    import config
    import scheduler
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running this from the project directory.")
    sys.exit(1)

def main():
    print("=" * 60)
    print("Instagram Access Token Health Check")
    print("=" * 60)
    print()
    
    # Get token from config/env
    access_token = getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None)
    if not access_token:
        access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN') or os.getenv('CASCADIA_ACCESS_TOKEN') or os.getenv('META_ACCESS_TOKEN')
    
    if not access_token:
        print("❌ No access token configured!")
        print()
        print("Please set one of these environment variables in your .env file:")
        print("  - INSTAGRAM_ACCESS_TOKEN")
        print("  - CASCADIA_ACCESS_TOKEN")
        print("  - META_ACCESS_TOKEN")
        print()
        return False
    
    # Run token health test
    print("Testing token health...")
    print()
    result = instagram_poster.test_token_health(access_token)
    
    # Display results
    print("Results:")
    print("-" * 60)
    print(f"Token Configured: {'✓ Yes' if result['token_configured'] else '✗ No'}")
    print(f"Token Valid: {'✓ Yes' if result['token_valid'] else '✗ No'}")
    
    if result['expiration_date']:
        print(f"Expiration Date: {result['expiration_date']}")
    
    if result['days_until_expiration'] is not None:
        days = result['days_until_expiration']
        if days > 15:
            status = "✓ Good"
        elif days > 0:
            status = "⚠️  Expiring Soon"
        else:
            status = "❌ Expired"
        print(f"Days Until Expiration: {days} ({status})")
    
    print(f"Refresh Configured: {'✓ Yes' if result['refresh_configured'] else '✗ No'}")
    print(f"Can Auto-Refresh: {'✓ Yes' if result['can_refresh'] else '✗ No'}")
    print()
    print("Status Message:")
    print(f"  {result['message']}")
    print()
    
    # Provide recommendations
    print("-" * 60)
    print("Recommendations:")
    print()
    
    if not result['token_configured']:
        print("❌ Configure an access token in your .env file")
    elif not result['token_valid']:
        print("❌ Token is invalid or expired. Generate a new token from Meta Developer Portal")
        print("   See SETUP_INSTAGRAM_GRAPH_API_PROMPT.md for instructions")
    elif result['days_until_expiration'] and result['days_until_expiration'] <= 0:
        print("❌ Token has expired. Generate a new long-lived token immediately")
        print("   See SETUP_INSTAGRAM_GRAPH_API_PROMPT.md for instructions")
    elif result['days_until_expiration'] and result['days_until_expiration'] <= 15:
        if result['refresh_configured']:
            print("⚠️  Token expires soon. Auto-refresh will attempt, but ensure META_APP_ID")
            print("   and META_APP_SECRET are correctly configured in .env")
        else:
            print("⚠️  Token expires soon. Set META_APP_ID and META_APP_SECRET in .env")
            print("   to enable automatic token refresh")
    elif not result['refresh_configured']:
        print("💡 Consider setting META_APP_ID and META_APP_SECRET in .env file")
        print("   This enables automatic token refresh before expiration")
    else:
        print("✓ Token is healthy and auto-refresh is configured!")
        print("   Your token will be automatically refreshed before expiration")
    
    print()
    print("=" * 60)
    
    # Return success/failure
    return result['token_valid'] and (result['days_until_expiration'] is None or result['days_until_expiration'] > 0)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
