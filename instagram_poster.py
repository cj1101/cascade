"""Instagram posting module using Graph API"""
import requests
import os
import time
import config
import json
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

# Try to import scheduler for logger, fallback to basic logging
try:
    import scheduler
    logger = scheduler.logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Token cache file to store token and expiration info
TOKEN_CACHE_FILE = os.path.join(os.path.dirname(__file__), '.instagram_token_cache.json')


def _refresh_access_token(current_token: str) -> Optional[str]:
    """
    Refresh a long-lived Instagram access token by exchanging it for a new one.
    
    Args:
        current_token: The current long-lived access token
        
    Returns:
        New access token if successful, None otherwise
    """
    # Get app credentials from config or environment
    app_id = getattr(config, 'META_APP_ID', None) or os.getenv('META_APP_ID') or os.getenv('INSTAGRAM_APP_ID')
    app_secret = getattr(config, 'META_APP_SECRET', None) or os.getenv('META_APP_SECRET') or os.getenv('INSTAGRAM_APP_SECRET')
    
    if not app_id or not app_secret:
        logger.warning("⚠️  META_APP_ID and META_APP_SECRET not configured. Cannot auto-refresh token.")
        logger.warning("   Set META_APP_ID and META_APP_SECRET in .env file for automatic token refresh.")
        return None
    
    try:
        url = "https://graph.facebook.com/v21.0/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': app_id,
            'client_secret': app_secret,
            'fb_exchange_token': current_token
        }
        
        logger.info("Refreshing Instagram access token...")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            new_token = result.get('access_token')
            expires_in = result.get('expires_in', 5184000)  # Default to 60 days if not provided
            
            if new_token:
                # Calculate expiration date (expires_in is in seconds)
                expiration_date = datetime.now() + timedelta(seconds=expires_in)
                
                # Save token info to cache
                _save_token_cache(new_token, expiration_date)
                
                logger.info(f"✓ Token refreshed successfully! Expires: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
                return new_token
            else:
                logger.error(f"❌ No access_token in refresh response: {result}")
                return None
        else:
            error_data = response.json() if response.content else {}
            logger.error(f"❌ Token refresh failed: {error_data}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error refreshing token: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def _load_token_cache() -> Optional[Tuple[str, datetime]]:
    """Load token and expiration from cache file"""
    if not os.path.exists(TOKEN_CACHE_FILE):
        return None
    
    try:
        with open(TOKEN_CACHE_FILE, 'r') as f:
            data = json.load(f)
            token = data.get('token')
            expiration_str = data.get('expiration')
            if token and expiration_str:
                expiration = datetime.fromisoformat(expiration_str)
                return (token, expiration)
    except Exception as e:
        logger.debug(f"Error loading token cache: {e}")
    
    return None


def _save_token_cache(token: str, expiration: datetime):
    """Save token and expiration to cache file"""
    try:
        data = {
            'token': token,
            'expiration': expiration.isoformat()
        }
        with open(TOKEN_CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"⚠️  Could not save token cache: {e}")


def _get_token_expiration(access_token: str) -> Optional[datetime]:
    """
    Get the actual expiration time of an access token using Facebook's debug endpoint.
    
    Args:
        access_token: The access token to check
        
    Returns:
        datetime of expiration if successful, None otherwise
    """
    try:
        url = "https://graph.facebook.com/v21.0/debug_token"
        params = {
            'input_token': access_token,
            'access_token': access_token
        }
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            expires_at = data.get('expires_at')
            if expires_at:
                # expires_at is a Unix timestamp (seconds since epoch)
                expiration = datetime.fromtimestamp(expires_at)
                return expiration
    except Exception as e:
        logger.debug(f"Could not get token expiration: {e}")
    
    return None


def _get_valid_token(access_token: Optional[str] = None) -> Optional[str]:
    """
    Get a valid access token, refreshing if necessary.
    Now refreshes proactively 15 days before expiration to prevent expiration issues.
    
    Args:
        access_token: Optional token to use (if None, loads from config/env)
        
    Returns:
        Valid access token, or None if unable to get/refresh
    """
    # Get token from parameter, config, or environment
    if not access_token:
        access_token = getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None)
        if not access_token:
            access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN') or os.getenv('CASCADIA_ACCESS_TOKEN') or os.getenv('META_ACCESS_TOKEN')
    
    if not access_token:
        return None
    
    # Check cache first
    cached = _load_token_cache()
    if cached:
        cached_token, expiration = cached
        # If cached token is still valid and not expiring soon (within 15 days), use it
        days_until_expiration = (expiration - datetime.now()).days
        if days_until_expiration > 15:
            logger.debug(f"Using cached token (expires in {days_until_expiration} days)")
            return cached_token
        # If cached token matches current token and is expiring soon (within 15 days), refresh it proactively
        if cached_token == access_token and days_until_expiration <= 15:
            logger.info(f"⚠️  Token expiring in {days_until_expiration} days, refreshing proactively...")
            new_token = _refresh_access_token(access_token)
            if new_token:
                logger.info("✓ Token refreshed successfully before expiration!")
                return new_token
            else:
                logger.warning(f"⚠️  Could not refresh token automatically. Token expires in {days_until_expiration} days.")
                # Return the current token anyway - might still work for now
                return cached_token
    
    # Validate current token by making a test API call and getting actual expiration
    try:
        url = "https://graph.facebook.com/v21.0/me"
        params = {'access_token': access_token, 'fields': 'id'}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            # Token is valid - try to get actual expiration time
            expiration = _get_token_expiration(access_token)
            
            if expiration:
                days_until_expiration = (expiration - datetime.now()).days
                logger.debug(f"Token valid, expires in {days_until_expiration} days")
                
                # If expiring within 15 days, refresh proactively
                if days_until_expiration <= 15:
                    logger.info(f"⚠️  Token expires in {days_until_expiration} days. Refreshing proactively...")
                    new_token = _refresh_access_token(access_token)
                    if new_token:
                        logger.info("✓ Token refreshed successfully before expiration!")
                        return new_token
                    else:
                        logger.warning(f"⚠️  Could not refresh token automatically. It expires in {days_until_expiration} days.")
                        logger.warning("   Please ensure META_APP_ID and META_APP_SECRET are set in .env file.")
                
                # Cache with actual expiration
                _save_token_cache(access_token, expiration)
            else:
                # Couldn't get expiration, assume 60 days and cache
                expiration = datetime.now() + timedelta(days=60)
                _save_token_cache(access_token, expiration)
            
            return access_token
        else:
            # Token might be expired, try to refresh
            error_data = response.json() if response.content else {}
            error_code = error_data.get('error', {}).get('code')
            error_subcode = error_data.get('error', {}).get('error_subcode')
            
            if error_code == 190:  # OAuthException - invalid/expired token
                if error_subcode == 463:
                    # Session expired - can't refresh, need manual update
                    logger.error("❌ Token session has expired and cannot be automatically refreshed.")
                    logger.error("   Once a token is fully expired, it cannot be refreshed using the exchange method.")
                    logger.error("   Please generate a new long-lived token from Meta Developer Portal and update your .env file.")
                    logger.error("   See SETUP_INSTAGRAM_GRAPH_API_PROMPT.md for instructions.")
                else:
                    logger.warning("⚠️  Access token appears to be expired, attempting refresh...")
                    new_token = _refresh_access_token(access_token)
                    if new_token:
                        return new_token
                    else:
                        logger.error("❌ Could not refresh expired token.")
                        logger.error("   If token is fully expired, you must generate a new one manually.")
                        logger.error("   Otherwise, ensure META_APP_ID and META_APP_SECRET are set in .env file.")
                return None
            else:
                logger.warning(f"⚠️  Token validation returned error: {error_data}")
                return access_token  # Return anyway, might work for posting
                
    except Exception as e:
        logger.warning(f"⚠️  Error validating token: {e}")
        return access_token  # Return anyway, might work


def check_and_refresh_token(access_token: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Proactively check token health and refresh if needed.
    Call this function regularly (e.g., at startup or before posting) to prevent expiration.
    
    Args:
        access_token: Optional token to check (if None, loads from config/env)
        
    Returns:
        Tuple of (is_valid, token, message):
        - is_valid: True if token is valid and ready to use
        - token: The valid token to use (None if invalid)
        - message: Status message describing the token state
    """
    token = _get_valid_token(access_token)
    
    if not token:
        return False, None, "No access token configured. Set INSTAGRAM_ACCESS_TOKEN or CASCADIA_ACCESS_TOKEN in .env file."
    
    # Check expiration from cache
    cached = _load_token_cache()
    if cached:
        cached_token, expiration = cached
        if cached_token == token:
            days_until_expiration = (expiration - datetime.now()).days
            if days_until_expiration <= 0:
                return False, None, f"Token expired {abs(days_until_expiration)} days ago. Please generate a new token."
            elif days_until_expiration <= 15:
                return True, token, f"Token expires in {days_until_expiration} days. Auto-refresh attempted."
            else:
                return True, token, f"Token is valid and expires in {days_until_expiration} days."
    
    # Try to get actual expiration
    expiration = _get_token_expiration(token)
    if expiration:
        days_until_expiration = (expiration - datetime.now()).days
        if days_until_expiration <= 0:
            return False, None, f"Token expired {abs(days_until_expiration)} days ago. Please generate a new token."
        elif days_until_expiration <= 15:
            return True, token, f"Token expires in {days_until_expiration} days. Auto-refresh attempted."
        else:
            return True, token, f"Token is valid and expires in {days_until_expiration} days."
    
    # Can't determine expiration, but token seems valid
    return True, token, "Token appears valid (could not determine exact expiration)."


def test_token_health(access_token: Optional[str] = None) -> dict:
    """
    Test token health and refresh capability.
    Use this function to verify your token setup and refresh configuration.
    
    Args:
        access_token: Optional token to test (if None, loads from config/env)
        
    Returns:
        Dictionary with test results:
        {
            'token_configured': bool,
            'token_valid': bool,
            'expiration_date': str or None,
            'days_until_expiration': int or None,
            'can_refresh': bool,
            'refresh_configured': bool,
            'message': str
        }
    """
    result = {
        'token_configured': False,
        'token_valid': False,
        'expiration_date': None,
        'days_until_expiration': None,
        'can_refresh': False,
        'refresh_configured': False,
        'message': ''
    }
    
    # Check if token is configured
    if not access_token:
        access_token = getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None)
        if not access_token:
            access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN') or os.getenv('CASCADIA_ACCESS_TOKEN') or os.getenv('META_ACCESS_TOKEN')
    
    if not access_token:
        result['message'] = "No access token configured. Set INSTAGRAM_ACCESS_TOKEN or CASCADIA_ACCESS_TOKEN in .env file."
        return result
    
    result['token_configured'] = True
    
    # Check if refresh is configured
    app_id = getattr(config, 'META_APP_ID', None) or os.getenv('META_APP_ID') or os.getenv('INSTAGRAM_APP_ID')
    app_secret = getattr(config, 'META_APP_SECRET', None) or os.getenv('META_APP_SECRET') or os.getenv('INSTAGRAM_APP_SECRET')
    result['refresh_configured'] = bool(app_id and app_secret)
    
    # Test token validity
    try:
        url = "https://graph.facebook.com/v21.0/me"
        params = {'access_token': access_token, 'fields': 'id'}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result['token_valid'] = True
            result['can_refresh'] = result['refresh_configured']
            
            # Get expiration
            expiration = _get_token_expiration(access_token)
            if expiration:
                result['expiration_date'] = expiration.strftime('%Y-%m-%d %H:%M:%S')
                days_until = (expiration - datetime.now()).days
                result['days_until_expiration'] = days_until
                
                if days_until <= 0:
                    result['message'] = f"❌ Token expired {abs(days_until)} days ago. Generate a new token."
                    result['can_refresh'] = False
                elif days_until <= 15:
                    result['message'] = f"⚠️  Token expires in {days_until} days. Auto-refresh will attempt soon."
                else:
                    result['message'] = f"✓ Token valid, expires in {days_until} days. Auto-refresh configured: {result['refresh_configured']}"
            else:
                result['message'] = "✓ Token appears valid (could not determine exact expiration)"
        else:
            error_data = response.json() if response.content else {}
            error_code = error_data.get('error', {}).get('code')
            error_subcode = error_data.get('error', {}).get('error_subcode')
            
            if error_code == 190:
                if error_subcode == 463:
                    result['message'] = "❌ Token session has expired. Cannot refresh - must generate new token manually."
                else:
                    result['message'] = "❌ Token is invalid or expired. Auto-refresh may work if configured."
                    result['can_refresh'] = result['refresh_configured']
            else:
                result['message'] = f"❌ Token validation failed: {error_data.get('error', {}).get('message', 'Unknown error')}"
    except Exception as e:
        result['message'] = f"❌ Error testing token: {e}"
    
    return result


def post_to_instagram(image_paths: List[str], caption: str = "", 
                      access_token: Optional[str] = None, 
                      instagram_account_id: Optional[str] = None):
    """
    Post images to Instagram using Graph API.
    
    Args:
        image_paths: List of image file paths (single or carousel)
        caption: Caption text for the post
        access_token: Instagram Graph API access token (uses config if not provided)
        instagram_account_id: Your Instagram Business Account ID (uses config if not provided)
        
    Returns:
        bool: True if posting successful, False otherwise
    """
    # Get account ID from parameters, config, or environment
    if not instagram_account_id:
        instagram_account_id = getattr(config, 'INSTAGRAM_ACCOUNT_ID', None)
        if not instagram_account_id:
            instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID') or os.getenv('CASCADIA_ACCOUNT_ID')
    
    if not instagram_account_id:
        logger.warning("⚠️  Instagram Graph API account ID not configured")
        logger.warning("   Please set INSTAGRAM_ACCOUNT_ID or CASCADIA_ACCOUNT_ID in .env file")
        return False
    
    # Get and validate/refresh access token
    access_token = _get_valid_token(access_token)
    
    if not access_token:
        logger.warning("⚠️  Instagram Graph API access token not configured or invalid")
        logger.warning("   Please set INSTAGRAM_ACCESS_TOKEN or CASCADIA_ACCESS_TOKEN in .env file")
        return False
    
    try:
        if len(image_paths) > 1:
            # Carousel post (multiple images)
            logger.info(f"Posting carousel with {len(image_paths)} images...")
            return _post_carousel(image_paths, caption, access_token, instagram_account_id)
        else:
            # Single image post
            logger.info(f"Posting single image: {image_paths[0]}...")
            return _post_single_image(image_paths[0], caption, access_token, instagram_account_id)
    except Exception as e:
        logger.error(f"❌ Error posting to Instagram: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def _upload_image_to_imgur(image_path: str):
    """Upload image to Imgur and get a public URL for Instagram posting"""
    # Imgur API endpoint - no authentication required for anonymous uploads
    upload_url = "https://api.imgur.com/3/image"
    
    try:
        logger.debug(f"Attempting to upload {image_path} to Imgur...")
        with open(image_path, 'rb') as image_file:
            files = {'image': image_file}
            headers = {
                'Authorization': 'Client-ID 546c25a59c58ad7'  # Public Imgur client ID
            }
            response = requests.post(upload_url, files=files, headers=headers)
        
        logger.debug(f"Imgur response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.debug(f"Imgur response JSON: {result}")
            if result.get('success') and result.get('data', {}).get('link'):
                image_url = result['data']['link']
                # Convert .gif to .jpg if needed (Instagram prefers .jpg)
                if image_url.endswith('.gif'):
                    image_url = image_url.replace('.gif', '.jpg')
                logger.debug(f"Imgur upload successful, URL: {image_url}")
                return image_url
            else:
                logger.warning(f"⚠️  Imgur upload response indicates failure: {result}")
                return None
        else:
            logger.warning(f"⚠️  Imgur upload failed with status {response.status_code}")
            logger.debug(f"Response text: {response.text}")
            return None
    except Exception as e:
        logger.warning(f"⚠️  Error uploading to Imgur: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def _post_single_image(image_path: str, caption: str, access_token: str, account_id: str):
    """Post a single image to Instagram using Graph API"""
    # Check if file exists before attempting any upload
    if not os.path.exists(image_path):
        logger.error(f"❌ Image file not found: {image_path}")
        return False
    
    # Step 1: Upload image to Imgur to get a public URL
    logger.info("Uploading image to temporary storage (Imgur)...")
    image_url = _upload_image_to_imgur(image_path)
    
    if not image_url:
        # Fallback: try direct file upload with different parameter name
        logger.info("Trying direct file upload...")
        image_url = None
        try:
            # Try using the file directly in the request
            url = f"https://graph.facebook.com/v21.0/{account_id}/media"
            with open(image_path, 'rb') as image_file:
                # Try using 'file' parameter instead of 'image'
                files = {'file': image_file}
                params = {
                    'caption': caption,
                    'access_token': access_token
                }
                response = requests.post(url, files=files, params=params)
                if response.status_code == 200:
                    creation_id = response.json().get('id')
                    if creation_id:
                        # Step 2: Publish
                        url = f"https://graph.facebook.com/v21.0/{account_id}/media_publish"
                        params = {
                            'creation_id': creation_id,
                            'access_token': access_token
                        }
                        response = requests.post(url, params=params)
                        if response.status_code == 200:
                            post_id = response.json().get('id', 'unknown')
                            logger.info(f"✓ Successfully posted to Instagram! (Post ID: {post_id})")
                            return True
        except Exception as e:
            logger.warning(f"⚠️  Direct upload failed: {e}")
    
    if not image_url:
        logger.error(f"❌ Could not upload image. Please ensure image is publicly accessible or use image_url parameter.")
        return False
    
    try:
        # Step 1: Create media container using image_url
        url = f"https://graph.facebook.com/v21.0/{account_id}/media"
        params = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token
        }
        response = requests.post(url, params=params)
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            logger.error(f"❌ Error creating media container: {error_data}")
            return False
        
        creation_id = response.json().get('id')
        if not creation_id:
            logger.error(f"❌ No creation ID returned: {response.json()}")
            return False
        
        # Step 2: Publish the media
        url = f"https://graph.facebook.com/v21.0/{account_id}/media_publish"
        params = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            post_id = response.json().get('id', 'unknown')
            logger.info(f"✓ Successfully posted to Instagram! (Post ID: {post_id})")
            return True
        else:
            error_data = response.json() if response.content else {}
            logger.error(f"❌ Error publishing post: {error_data}")
            return False
            
    except FileNotFoundError:
        logger.error(f"❌ Image file not found: {image_path}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during single image post: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def _wait_for_media_ready(media_id: str, access_token: str, max_wait_time: int = 60, check_interval: int = 2):
    """
    Wait for a media container to be ready for publishing.
    
    Args:
        media_id: The media container ID to check
        access_token: Instagram Graph API access token
        max_wait_time: Maximum time to wait in seconds (default: 60)
        check_interval: Time between status checks in seconds (default: 2)
    
    Returns:
        bool: True if media is ready, False if timeout or error
    """
    url = f"https://graph.facebook.com/v21.0/{media_id}"
    params = {
        'fields': 'status_code',
        'access_token': access_token
    }
    
    # Give Instagram a moment to process the container before checking status
    logger.debug("Initial wait before checking status...")
    time.sleep(2)
    
    elapsed_time = 2
    logger.debug(f"Waiting for media {media_id} to be ready (max {max_wait_time}s)...")
    
    while elapsed_time < max_wait_time:
        try:
            response = requests.get(url, params=params)
            logger.debug(f"Status check response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                status_code = result.get('status_code')
                logger.debug(f"Media {media_id} status: {status_code}")
                
                # Status codes: "FINISHED" = ready, "IN_PROGRESS" = processing, "ERROR" = failed
                if status_code == "FINISHED":
                    logger.info(f"✓ Media {media_id} is ready!")
                    return True
                elif status_code == "ERROR":
                    error_info = result.get('status', 'Unknown error')
                    logger.error(f"❌ Media {media_id} processing failed: {error_info}")
                    return False
                # If IN_PROGRESS or unknown/None, continue waiting
                elif status_code:
                    logger.debug(f"Status is '{status_code}', waiting...")
            elif response.status_code == 400:
                # Sometimes the status endpoint isn't immediately available
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', '')
                if 'not available' in error_msg.lower() or 'not found' in error_msg.lower():
                    logger.debug("Status endpoint not yet available, waiting...")
                else:
                    logger.debug(f"Status check error: {error_data}")
            else:
                logger.debug(f"Status check failed: {response.status_code} - {response.text[:200]}")
            
            time.sleep(check_interval)
            elapsed_time += check_interval
            
        except Exception as e:
            logger.debug(f"Error checking media status: {e}")
            import traceback
            logger.error(traceback.format_exc())
            time.sleep(check_interval)
            elapsed_time += check_interval
    
    logger.warning(f"⚠️  Timeout waiting for media {media_id} to be ready after {max_wait_time} seconds")
    logger.debug("Will attempt to publish anyway - sometimes status check fails but media is ready")
    return True  # Return True to allow publishing attempt even if status check times out


def _post_carousel(image_paths: List[str], caption: str, access_token: str, account_id: str):
    """Post a carousel (multiple images) to Instagram using Graph API"""
    children = []
    
    logger.debug(f"Starting carousel post with {len(image_paths)} images")
    logger.debug(f"Account ID: {account_id[:10]}..." if account_id else "Account ID: None")
    logger.debug(f"Access token present: {bool(access_token)}")
    
    # Step 1: Upload each image and get its media ID
    logger.info(f"Uploading {len(image_paths)} images...")
    for idx, image_path in enumerate(image_paths, 1):
        logger.debug(f"Processing image {idx}/{len(image_paths)}: {image_path}")
        if not os.path.exists(image_path):
            logger.error(f"❌ Image file not found: {image_path}")
            logger.debug(f"Current working directory: {os.getcwd()}")
            return False
        
        logger.debug(f"Image file exists, size: {os.path.getsize(image_path)} bytes")
        
        # First, upload image to Imgur to get a public URL
        logger.info(f"Uploading image {idx}/{len(image_paths)} to temporary storage (Imgur)...")
        image_url = _upload_image_to_imgur(image_path)
        
        if not image_url:
            # Fallback: try direct upload
            logger.debug("Imgur upload failed, trying direct Instagram upload...")
            try:
                url = f"https://graph.facebook.com/v21.0/{account_id}/media"
                logger.debug(f"Direct upload URL: {url}")
                with open(image_path, 'rb') as image_file:
                    files = {'file': image_file}
                    params = {
                        'is_carousel_item': True,
                        'access_token': access_token
                    }
                    logger.debug("Sending direct upload request...")
                    response = requests.post(url, files=files, params=params)
                    logger.debug(f"Direct upload response status: {response.status_code}")
                    logger.debug(f"Direct upload response: {response.text[:500]}")
                    if response.status_code == 200:
                        result = response.json()
                        media_id = result.get('id')
                        if media_id:
                            children.append(media_id)
                            logger.info(f"✓ Uploaded image {idx}/{len(image_paths)} (media_id: {media_id})")
                            continue
                        else:
                            logger.debug(f"No media ID in response: {result}")
                    else:
                        error_data = response.json() if response.content else {}
                        logger.debug(f"Direct upload failed: {error_data}")
            except Exception as e:
                logger.warning(f"⚠️  Direct upload failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            logger.error(f"❌ Error uploading image {idx}/{len(image_paths)} ({image_path}): Could not get image URL")
            return False
        
        url = f"https://graph.facebook.com/v21.0/{account_id}/media"
        
        try:
            # Use image_url parameter
            params = {
                'image_url': image_url,
                'is_carousel_item': True,
                'access_token': access_token
            }
            logger.debug(f"Creating Instagram media container with URL: {url}")
            logger.debug(f"Image URL: {image_url}")
            response = requests.post(url, params=params)
            logger.debug(f"Instagram API response status: {response.status_code}")
            logger.debug(f"Instagram API response: {response.text[:500]}")
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                logger.error(f"❌ Error uploading image {idx}/{len(image_paths)} ({image_path}): {error_data}")
                return False
            
            result = response.json()
            media_id = result.get('id')
            if not media_id:
                logger.error(f"❌ No media ID returned for image {idx}: {result}")
                return False
            
            children.append(media_id)
            logger.info(f"✓ Uploaded image {idx}/{len(image_paths)} (media_id: {media_id})")
            
        except FileNotFoundError:
            logger.error(f"❌ Image file not found: {image_path}")
            return False
        except Exception as e:
            logger.error(f"❌ Error uploading image {idx}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    logger.debug(f"Successfully collected {len(children)} media IDs: {children}")
    
    # Step 2: Create carousel container
    if len(children) == 0:
        logger.error(f"❌ No media IDs collected! Cannot create carousel.")
        return False
    
    logger.info("Creating carousel container...")
    url = f"https://graph.facebook.com/v21.0/{account_id}/media"
    children_str = ','.join(children)
    params = {
        'media_type': 'CAROUSEL',
        'caption': caption,
        'children': children_str,
        'access_token': access_token
    }
    
    logger.debug(f"Carousel container URL: {url}")
    logger.debug(f"Carousel children: {children_str}")
    logger.debug(f"Caption length: {len(caption)} characters")
    
    try:
        response = requests.post(url, params=params)
        logger.debug(f"Carousel container creation response status: {response.status_code}")
        logger.debug(f"Carousel container creation response: {response.text[:500]}")
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            logger.error(f"❌ Error creating carousel: {error_data}")
            logger.debug(f"Full response: {response.text}")
            return False

        result = response.json()
        creation_id = result.get('id')
        if not creation_id:
            logger.error(f"❌ No creation ID returned for carousel: {result}")
            return False
        
        logger.debug(f"Carousel creation ID: {creation_id}")
        
        # Step 2.5: Wait for carousel container to be ready before publishing
        logger.info("Waiting for carousel container to be ready...")
        if not _wait_for_media_ready(creation_id, access_token, max_wait_time=120, check_interval=3):
            logger.error(f"❌ Carousel container {creation_id} did not become ready in time")
            return False
        
        # Step 3: Publish the carousel
        logger.info("Publishing carousel...")
        url = f"https://graph.facebook.com/v21.0/{account_id}/media_publish"
        params = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        logger.debug(f"Publish URL: {url}")
        logger.debug(f"Publish creation_id: {creation_id}")
        response = requests.post(url, params=params)
        logger.debug(f"Publish response status: {response.status_code}")
        logger.debug(f"Publish response: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            post_id = result.get('id', 'unknown')
            logger.info(f"✓ Successfully posted carousel to Instagram! (Post ID: {post_id})")
            return True
        else:
            error_data = response.json() if response.content else {}
            error_code = error_data.get('error', {}).get('code')
            error_subcode = error_data.get('error', {}).get('error_subcode')
            
            # If still getting "not ready" error, wait a bit more and retry
            if error_code == 9007 and error_subcode == 2207027:
                logger.warning(f"⚠️  Media still not ready, waiting additional 10 seconds and retrying...")
                time.sleep(10)
                
                if _wait_for_media_ready(creation_id, access_token, max_wait_time=60, check_interval=2):
                    # Retry publishing
                    logger.info("Retrying publish...")
                    response = requests.post(url, params=params)
                    logger.debug(f"Retry publish response status: {response.status_code}")
                    logger.debug(f"Retry publish response: {response.text[:500]}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        post_id = result.get('id', 'unknown')
                        logger.info(f"✓ Successfully posted carousel to Instagram! (Post ID: {post_id})")
                        return True
            
            logger.error(f"❌ Error publishing carousel: {error_data}")
            logger.debug(f"Full publish response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Unexpected error during carousel post: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def post_images_hourly(all_images_by_week, teams=None, upcoming_schedule=None, 
                       initial_teams=None, game_results_by_week=None, driver=None):
    """
    Post images to Instagram with 5 minute intervals between weeks (testing mode).
    Note: driver parameter is kept for compatibility but not used with Graph API.
    
    Args:
        all_images_by_week: Dictionary mapping week numbers to lists of image filenames
        teams: List of Team objects (for standings and odds calculation)
        upcoming_schedule: Dictionary mapping week numbers to lists of (team1, team2) tuples
        initial_teams: List of Team objects in their initial state (before any games)
        game_results_by_week: Dictionary mapping week numbers to lists of game_result tuples
        driver: (Deprecated - kept for compatibility, not used with Graph API)
    """
    import game_logic
    
    logger.info("\n" + "="*60)
    logger.info("Starting Instagram posting schedule...")
    logger.info("="*60)
    
    # Sort weeks (integers only)
    sorted_weeks = sorted([w for w in all_images_by_week.keys() if isinstance(w, int)])
    
    # Post all round robin weeks first
    for week in sorted_weeks:
        images = all_images_by_week[week]
        if not images:
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Posting Week {week} ({len(images)} images)")
        if len(images) > 1:
            logger.info(f"All {len(images)} games will be posted together as a carousel/gallery post")
        logger.info(f"{'='*60}")
        
        # Generate caption with standings and next week odds
        caption_parts = [f"Week {week} Game Results"]
        
        # Add current standings (only up to current week)
        if initial_teams and game_results_by_week:
            caption_parts.append("")
            caption_parts.append("Current Standings:")
            standings = game_logic.calculate_standings_up_to_week(initial_teams, game_results_by_week, week)
            caption_parts.append(standings)
        elif teams:
            # Fallback to old method if new parameters not provided
            caption_parts.append("")
            caption_parts.append("Current Standings:")
            standings = game_logic.format_standings_for_caption(teams)
            caption_parts.append(standings)
        
        # Add odds for next week's matchups
        next_week = week + 1
        if upcoming_schedule and next_week in upcoming_schedule and teams:
            caption_parts.append("")
            # Use the new detailed betting lines
            betting_lines = game_logic.format_betting_slip(upcoming_schedule[next_week])
            caption_parts.append(betting_lines)
        
        caption = "\n".join(caption_parts)
        
        # Post all images for this week as a single carousel/gallery post
        logger.debug(f"About to post Week {week} with {len(images)} images")
        logger.debug(f"Image paths: {images}")
        logger.debug(f"Caption preview: {caption[:200]}...")
        success = post_to_instagram(images, caption)
        
        if not success:
            logger.warning(f"❌ Warning: Failed to post Week {week} images")
            logger.debug(f"post_to_instagram returned False for Week {week}")
            response = input("Continue to next week? (y/n): ")
            if response.lower() != 'y':
                break
        
        # Wait 5 minutes before next week (unless it's the last week)
        if week < sorted_weeks[-1]:
            logger.info(f"\nWaiting 5 minutes before posting Week {week + 1}...")
            logger.info("(You can press Ctrl+C to cancel)")
            try:
                time.sleep(300)  # 5 minutes = 300 seconds
            except KeyboardInterrupt:
                logger.info("\nPosting cancelled by user.")
                break
    
    # Post bracket before quarterfinals (if it exists)
    if 'bracket_quarterfinals' in all_images_by_week:
        images = all_images_by_week['bracket_quarterfinals']
        if images:
            logger.info(f"\n{'='*60}")
            logger.info(f"Posting Tournament Bracket - Quarterfinals ({len(images)} image)")
            logger.info(f"{'='*60}")
            
            # Post with no caption
            success = post_to_instagram(images, "")
            
            if not success:
                logger.warning(f"Warning: Failed to post tournament bracket")
                response = input("Continue to quarterfinals? (y/n): ")
                if response.lower() != 'y':
                    logger.info("\nInstagram posting schedule cancelled!")
                    return
    
    # Post bracket before semifinals (if it exists)
    if 'bracket_semifinals' in all_images_by_week:
        images = all_images_by_week['bracket_semifinals']
        if images:
            logger.info(f"\n{'='*60}")
            logger.info(f"Posting Tournament Bracket - Semifinals ({len(images)} image)")
            logger.info(f"{'='*60}")
            
            # Post with no caption
            success = post_to_instagram(images, "")
            
            if not success:
                logger.warning(f"Warning: Failed to post tournament bracket")
                response = input("Continue to semifinals? (y/n): ")
                if response.lower() != 'y':
                    logger.info("\nInstagram posting schedule cancelled!")
                    return
    
    # Post bracket before finals (if it exists)
    if 'bracket_finals' in all_images_by_week:
        images = all_images_by_week['bracket_finals']
        if images:
            logger.info(f"\n{'='*60}")
            logger.info(f"Posting Tournament Bracket - Finals ({len(images)} image)")
            logger.info(f"{'='*60}")
            
            # Post with no caption
            success = post_to_instagram(images, "")
            
            if not success:
                logger.warning(f"Warning: Failed to post tournament bracket")
                response = input("Continue to finals? (y/n): ")
                if response.lower() != 'y':
                    logger.info("\nInstagram posting schedule cancelled!")
                    return
    
    # Post tournament matches (if they exist)
    if 'tournament' in all_images_by_week:
        images = all_images_by_week['tournament']
        if images:
            logger.info(f"\n{'='*60}")
            logger.info(f"Posting Tournament Matches ({len(images)} images)")
            logger.info(f"{'='*60}")
            
            caption = "🏆 TOURNAMENT MATCHES 🏆\n\nLet the playoffs begin!"
            
            success = post_to_instagram(images, caption)
            
            if not success:
                logger.warning(f"Warning: Failed to post tournament matches")
    
    logger.info("\nInstagram posting schedule completed!")
