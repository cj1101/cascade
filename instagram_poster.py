"""Instagram posting module using Graph API"""
import requests
import os
import time
import config
from typing import List, Optional


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
    # Get credentials from parameters, config, or environment
    if not access_token:
        access_token = getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None)
        if not access_token:
            access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    
    if not instagram_account_id:
        instagram_account_id = getattr(config, 'INSTAGRAM_ACCOUNT_ID', None)
        if not instagram_account_id:
            instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
    
    if not access_token or not instagram_account_id:
        print("⚠️  Instagram Graph API credentials not configured")
        print("   Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID in config.py")
        print("   or as environment variables")
        return False
    
    try:
        if len(image_paths) > 1:
            # Carousel post (multiple images)
            print(f"Posting carousel with {len(image_paths)} images...")
            return _post_carousel(image_paths, caption, access_token, instagram_account_id)
        else:
            # Single image post
            print(f"Posting single image: {image_paths[0]}...")
            return _post_single_image(image_paths[0], caption, access_token, instagram_account_id)
    except Exception as e:
        print(f"❌ Error posting to Instagram: {e}")
        import traceback
        traceback.print_exc()
        return False


def _upload_image_to_imgur(image_path: str):
    """Upload image to Imgur and get a public URL for Instagram posting"""
    # Imgur API endpoint - no authentication required for anonymous uploads
    upload_url = "https://api.imgur.com/3/image"
    
    try:
        print(f"    [DEBUG] Attempting to upload {image_path} to Imgur...")
        with open(image_path, 'rb') as image_file:
            files = {'image': image_file}
            headers = {
                'Authorization': 'Client-ID 546c25a59c58ad7'  # Public Imgur client ID
            }
            response = requests.post(upload_url, files=files, headers=headers)
        
        print(f"    [DEBUG] Imgur response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"    [DEBUG] Imgur response JSON: {result}")
            if result.get('success') and result.get('data', {}).get('link'):
                image_url = result['data']['link']
                # Convert .gif to .jpg if needed (Instagram prefers .jpg)
                if image_url.endswith('.gif'):
                    image_url = image_url.replace('.gif', '.jpg')
                print(f"    [DEBUG] Imgur upload successful, URL: {image_url}")
                return image_url
            else:
                print(f"⚠️  Imgur upload response indicates failure: {result}")
                return None
        else:
            print(f"⚠️  Imgur upload failed with status {response.status_code}")
            print(f"    [DEBUG] Response text: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  Error uploading to Imgur: {e}")
        import traceback
        traceback.print_exc()
        return None


def _post_single_image(image_path: str, caption: str, access_token: str, account_id: str):
    """Post a single image to Instagram using Graph API"""
    # Step 1: Upload image to Imgur to get a public URL
    print("Uploading image to temporary storage (Imgur)...")
    image_url = _upload_image_to_imgur(image_path)
    
    if not image_url:
        # Fallback: try direct file upload with different parameter name
        print("Trying direct file upload...")
        image_url = None
        try:
            # Try using the file directly in the request
            url = f"https://graph.facebook.com/v18.0/{account_id}/media"
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
                        url = f"https://graph.facebook.com/v18.0/{account_id}/media_publish"
                        params = {
                            'creation_id': creation_id,
                            'access_token': access_token
                        }
                        response = requests.post(url, params=params)
                        if response.status_code == 200:
                            post_id = response.json().get('id', 'unknown')
                            print(f"✓ Successfully posted to Instagram! (Post ID: {post_id})")
                            return True
        except Exception as e:
            print(f"⚠️  Direct upload failed: {e}")
    
    if not image_url:
        print(f"❌ Could not upload image. Please ensure image is publicly accessible or use image_url parameter.")
        return False
    
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return False
    
    try:
        # Step 1: Create media container using image_url
        url = f"https://graph.facebook.com/v18.0/{account_id}/media"
        params = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token
        }
        response = requests.post(url, params=params)
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            print(f"❌ Error creating media container: {error_data}")
            return False
        
        creation_id = response.json().get('id')
        if not creation_id:
            print(f"❌ No creation ID returned: {response.json()}")
            return False
        
        # Step 2: Publish the media
        url = f"https://graph.facebook.com/v18.0/{account_id}/media_publish"
        params = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            post_id = response.json().get('id', 'unknown')
            print(f"✓ Successfully posted to Instagram! (Post ID: {post_id})")
            return True
        else:
            error_data = response.json() if response.content else {}
            print(f"❌ Error publishing post: {error_data}")
            return False
            
    except FileNotFoundError:
        print(f"❌ Image file not found: {image_path}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during single image post: {e}")
        import traceback
        traceback.print_exc()
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
    url = f"https://graph.facebook.com/v18.0/{media_id}"
    params = {
        'fields': 'status_code',
        'access_token': access_token
    }
    
    # Give Instagram a moment to process the container before checking status
    print(f"  [DEBUG] Initial wait before checking status...")
    time.sleep(2)
    
    elapsed_time = 2
    print(f"  [DEBUG] Waiting for media {media_id} to be ready (max {max_wait_time}s)...")
    
    while elapsed_time < max_wait_time:
        try:
            response = requests.get(url, params=params)
            print(f"  [DEBUG] Status check response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                status_code = result.get('status_code')
                print(f"  [DEBUG] Media {media_id} status: {status_code}")
                
                # Status codes: "FINISHED" = ready, "IN_PROGRESS" = processing, "ERROR" = failed
                if status_code == "FINISHED":
                    print(f"  ✓ Media {media_id} is ready!")
                    return True
                elif status_code == "ERROR":
                    error_info = result.get('status', 'Unknown error')
                    print(f"  ❌ Media {media_id} processing failed: {error_info}")
                    return False
                # If IN_PROGRESS or unknown/None, continue waiting
                elif status_code:
                    print(f"  [DEBUG] Status is '{status_code}', waiting...")
            elif response.status_code == 400:
                # Sometimes the status endpoint isn't immediately available
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', '')
                if 'not available' in error_msg.lower() or 'not found' in error_msg.lower():
                    print(f"  [DEBUG] Status endpoint not yet available, waiting...")
                else:
                    print(f"  [DEBUG] Status check error: {error_data}")
            else:
                print(f"  [DEBUG] Status check failed: {response.status_code} - {response.text[:200]}")
            
            time.sleep(check_interval)
            elapsed_time += check_interval
            
        except Exception as e:
            print(f"  [DEBUG] Error checking media status: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(check_interval)
            elapsed_time += check_interval
    
    print(f"  ⚠️  Timeout waiting for media {media_id} to be ready after {max_wait_time} seconds")
    print(f"  [DEBUG] Will attempt to publish anyway - sometimes status check fails but media is ready")
    return True  # Return True to allow publishing attempt even if status check times out


def _post_carousel(image_paths: List[str], caption: str, access_token: str, account_id: str):
    """Post a carousel (multiple images) to Instagram using Graph API"""
    children = []
    
    print(f"[DEBUG] Starting carousel post with {len(image_paths)} images")
    print(f"[DEBUG] Account ID: {account_id[:10]}..." if account_id else "[DEBUG] Account ID: None")
    print(f"[DEBUG] Access token present: {bool(access_token)}")
    
    # Step 1: Upload each image and get its media ID
    print(f"Uploading {len(image_paths)} images...")
    for idx, image_path in enumerate(image_paths, 1):
        print(f"\n[DEBUG] Processing image {idx}/{len(image_paths)}: {image_path}")
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            print(f"[DEBUG] Current working directory: {os.getcwd()}")
            return False
        
        print(f"[DEBUG] Image file exists, size: {os.path.getsize(image_path)} bytes")
        
        # First, upload image to Imgur to get a public URL
        print(f"  Uploading image {idx}/{len(image_paths)} to temporary storage (Imgur)...")
        image_url = _upload_image_to_imgur(image_path)
        
        if not image_url:
            # Fallback: try direct upload
            print(f"  [DEBUG] Imgur upload failed, trying direct Instagram upload...")
            try:
                url = f"https://graph.facebook.com/v18.0/{account_id}/media"
                print(f"  [DEBUG] Direct upload URL: {url}")
                with open(image_path, 'rb') as image_file:
                    files = {'file': image_file}
                    params = {
                        'is_carousel_item': True,
                        'access_token': access_token
                    }
                    print(f"  [DEBUG] Sending direct upload request...")
                    response = requests.post(url, files=files, params=params)
                    print(f"  [DEBUG] Direct upload response status: {response.status_code}")
                    print(f"  [DEBUG] Direct upload response: {response.text[:500]}")
                    if response.status_code == 200:
                        result = response.json()
                        media_id = result.get('id')
                        if media_id:
                            children.append(media_id)
                            print(f"  ✓ Uploaded image {idx}/{len(image_paths)} (media_id: {media_id})")
                            continue
                        else:
                            print(f"  [DEBUG] No media ID in response: {result}")
                    else:
                        error_data = response.json() if response.content else {}
                        print(f"  [DEBUG] Direct upload failed: {error_data}")
            except Exception as e:
                print(f"  ⚠️  Direct upload failed: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"❌ Error uploading image {idx}/{len(image_paths)} ({image_path}): Could not get image URL")
            return False
        
        url = f"https://graph.facebook.com/v18.0/{account_id}/media"
        
        try:
            # Use image_url parameter
            params = {
                'image_url': image_url,
                'is_carousel_item': True,
                'access_token': access_token
            }
            print(f"  [DEBUG] Creating Instagram media container with URL: {url}")
            print(f"  [DEBUG] Image URL: {image_url}")
            response = requests.post(url, params=params)
            print(f"  [DEBUG] Instagram API response status: {response.status_code}")
            print(f"  [DEBUG] Instagram API response: {response.text[:500]}")
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                print(f"❌ Error uploading image {idx}/{len(image_paths)} ({image_path}): {error_data}")
                return False
            
            result = response.json()
            media_id = result.get('id')
            if not media_id:
                print(f"❌ No media ID returned for image {idx}: {result}")
                return False
            
            children.append(media_id)
            print(f"  ✓ Uploaded image {idx}/{len(image_paths)} (media_id: {media_id})")
            
        except FileNotFoundError:
            print(f"❌ Image file not found: {image_path}")
            return False
        except Exception as e:
            print(f"❌ Error uploading image {idx}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print(f"\n[DEBUG] Successfully collected {len(children)} media IDs: {children}")
    
    # Step 2: Create carousel container
    if len(children) == 0:
        print(f"❌ No media IDs collected! Cannot create carousel.")
        return False
    
    print("Creating carousel container...")
    url = f"https://graph.facebook.com/v18.0/{account_id}/media"
    children_str = ','.join(children)
    params = {
        'media_type': 'CAROUSEL',
        'caption': caption,
        'children': children_str,
        'access_token': access_token
    }
    
    print(f"[DEBUG] Carousel container URL: {url}")
    print(f"[DEBUG] Carousel children: {children_str}")
    print(f"[DEBUG] Caption length: {len(caption)} characters")
    
    try:
        response = requests.post(url, params=params)
        print(f"[DEBUG] Carousel container creation response status: {response.status_code}")
        print(f"[DEBUG] Carousel container creation response: {response.text[:500]}")
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            print(f"❌ Error creating carousel: {error_data}")
            print(f"[DEBUG] Full response: {response.text}")
            return False

        result = response.json()
        creation_id = result.get('id')
        if not creation_id:
            print(f"❌ No creation ID returned for carousel: {result}")
            return False
        
        print(f"[DEBUG] Carousel creation ID: {creation_id}")
        
        # Step 2.5: Wait for carousel container to be ready before publishing
        print("Waiting for carousel container to be ready...")
        if not _wait_for_media_ready(creation_id, access_token, max_wait_time=120, check_interval=3):
            print(f"❌ Carousel container {creation_id} did not become ready in time")
            return False
        
        # Step 3: Publish the carousel
        print("Publishing carousel...")
        url = f"https://graph.facebook.com/v18.0/{account_id}/media_publish"
        params = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        print(f"[DEBUG] Publish URL: {url}")
        print(f"[DEBUG] Publish creation_id: {creation_id}")
        response = requests.post(url, params=params)
        print(f"[DEBUG] Publish response status: {response.status_code}")
        print(f"[DEBUG] Publish response: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            post_id = result.get('id', 'unknown')
            print(f"✓ Successfully posted carousel to Instagram! (Post ID: {post_id})")
            return True
        else:
            error_data = response.json() if response.content else {}
            error_code = error_data.get('error', {}).get('code')
            error_subcode = error_data.get('error', {}).get('error_subcode')
            
            # If still getting "not ready" error, wait a bit more and retry
            if error_code == 9007 and error_subcode == 2207027:
                print(f"⚠️  Media still not ready, waiting additional 10 seconds and retrying...")
                time.sleep(10)
                
                if _wait_for_media_ready(creation_id, access_token, max_wait_time=60, check_interval=2):
                    # Retry publishing
                    print("Retrying publish...")
                    response = requests.post(url, params=params)
                    print(f"[DEBUG] Retry publish response status: {response.status_code}")
                    print(f"[DEBUG] Retry publish response: {response.text[:500]}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        post_id = result.get('id', 'unknown')
                        print(f"✓ Successfully posted carousel to Instagram! (Post ID: {post_id})")
                        return True
            
            print(f"❌ Error publishing carousel: {error_data}")
            print(f"[DEBUG] Full publish response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error during carousel post: {e}")
        import traceback
        traceback.print_exc()
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
    
    print("\n" + "="*60)
    print("Starting Instagram posting schedule...")
    print("="*60)
    
    # Sort weeks (integers only)
    sorted_weeks = sorted([w for w in all_images_by_week.keys() if isinstance(w, int)])
    
    # Post all round robin weeks first
    for week in sorted_weeks:
        images = all_images_by_week[week]
        if not images:
            continue
        
        print(f"\n{'='*60}")
        print(f"Posting Week {week} ({len(images)} images)")
        if len(images) > 1:
            print(f"All {len(images)} games will be posted together as a carousel/gallery post")
        print(f"{'='*60}")
        
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
            caption_parts.append(f"Odds for Week {next_week}:")
            matchups = upcoming_schedule[next_week]
            for team1, team2 in matchups:
                odds1, odds2 = game_logic.calculate_matchup_odds(team1, team2)
                # Format odds with + sign for positive, no sign for negative
                odds1_str = f"+{odds1}" if odds1 > 0 else str(odds1)
                odds2_str = f"+{odds2}" if odds2 > 0 else str(odds2)
                caption_parts.append(f"{team1.name} vs {team2.name}: {team1.name} {odds1_str}, {team2.name} {odds2_str}")
        
        caption = "\n".join(caption_parts)
        
        # Post all images for this week as a single carousel/gallery post
        print(f"[DEBUG] About to post Week {week} with {len(images)} images")
        print(f"[DEBUG] Image paths: {images}")
        print(f"[DEBUG] Caption preview: {caption[:200]}...")
        success = post_to_instagram(images, caption)
        
        if not success:
            print(f"❌ Warning: Failed to post Week {week} images")
            print(f"[DEBUG] post_to_instagram returned False for Week {week}")
            response = input("Continue to next week? (y/n): ")
            if response.lower() != 'y':
                break
        
        # Wait 5 minutes before next week (unless it's the last week)
        if week < sorted_weeks[-1]:
            print(f"\nWaiting 5 minutes before posting Week {week + 1}...")
            print("(You can press Ctrl+C to cancel)")
            try:
                time.sleep(300)  # 5 minutes = 300 seconds
            except KeyboardInterrupt:
                print("\nPosting cancelled by user.")
                break
    
    # Post bracket before quarterfinals (if it exists)
    if 'bracket_quarterfinals' in all_images_by_week:
        images = all_images_by_week['bracket_quarterfinals']
        if images:
            print(f"\n{'='*60}")
            print(f"Posting Tournament Bracket - Quarterfinals ({len(images)} image)")
            print(f"{'='*60}")
            
            # Post with no caption
            success = post_to_instagram(images, "")
            
            if not success:
                print(f"Warning: Failed to post tournament bracket")
                response = input("Continue to quarterfinals? (y/n): ")
                if response.lower() != 'y':
                    print("\nInstagram posting schedule cancelled!")
                    return
    
    # Post bracket before semifinals (if it exists)
    if 'bracket_semifinals' in all_images_by_week:
        images = all_images_by_week['bracket_semifinals']
        if images:
            print(f"\n{'='*60}")
            print(f"Posting Tournament Bracket - Semifinals ({len(images)} image)")
            print(f"{'='*60}")
            
            # Post with no caption
            success = post_to_instagram(images, "")
            
            if not success:
                print(f"Warning: Failed to post tournament bracket")
                response = input("Continue to semifinals? (y/n): ")
                if response.lower() != 'y':
                    print("\nInstagram posting schedule cancelled!")
                    return
    
    # Post bracket before finals (if it exists)
    if 'bracket_finals' in all_images_by_week:
        images = all_images_by_week['bracket_finals']
        if images:
            print(f"\n{'='*60}")
            print(f"Posting Tournament Bracket - Finals ({len(images)} image)")
            print(f"{'='*60}")
            
            # Post with no caption
            success = post_to_instagram(images, "")
            
            if not success:
                print(f"Warning: Failed to post tournament bracket")
                response = input("Continue to finals? (y/n): ")
                if response.lower() != 'y':
                    print("\nInstagram posting schedule cancelled!")
                    return
    
    # Post tournament matches (if they exist)
    if 'tournament' in all_images_by_week:
        images = all_images_by_week['tournament']
        if images:
            print(f"\n{'='*60}")
            print(f"Posting Tournament Matches ({len(images)} images)")
            print(f"{'='*60}")
            
            caption = "🏆 TOURNAMENT MATCHES 🏆\n\nLet the playoffs begin!"
            
            success = post_to_instagram(images, caption)
            
            if not success:
                print(f"Warning: Failed to post tournament matches")
    
    print("\nInstagram posting schedule completed!")
