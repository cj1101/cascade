"""Instagram posting module for Cascade game simulation"""
import os
import time
import traceback
import config


def _dismiss_instagram_popups(driver):
    """
    Dismiss any Instagram pop-ups/modals that appear after login.
    These can include welcome messages, notifications, etc.
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        print("Checking for Instagram pop-ups to dismiss...")
        time.sleep(2)  # Wait for pop-ups to appear
        
        # Try multiple times as pop-ups may appear sequentially
        max_attempts = 5
        for attempt in range(max_attempts):
            popup_dismissed = False
            
            # Common pop-up dismissal selectors
            dismiss_selectors = [
                # OK buttons
                "//button[contains(text(), 'OK')]",
                "//button[contains(text(), 'Ok')]",
                "//div[@role='button' and contains(text(), 'OK')]",
                "//div[@role='button' and contains(text(), 'Ok')]",
                # French
                "//button[contains(text(), 'D\'accord')]",
                "//div[@role='button' and contains(text(), 'D\'accord')]",
                # Got it / Continue
                "//button[contains(text(), 'Got it')]",
                "//button[contains(text(), 'Continue')]",
                "//div[@role='button' and contains(text(), 'Got it')]",
                "//div[@role='button' and contains(text(), 'Continue')]",
                # French
                "//button[contains(text(), 'Compris')]",
                "//button[contains(text(), 'Continuer')]",
                "//div[@role='button' and contains(text(), 'Compris')]",
                "//div[@role='button' and contains(text(), 'Continuer')]",
                # Not now / Close
                "//button[contains(text(), 'Not Now')]",
                "//div[@role='button' and contains(text(), 'Not Now')]",
                "//button[@aria-label='Close']",
                "//button[@aria-label='Fermer']",
                # Generic button in modal/dialog
                "//div[@role='dialog']//button[contains(@class, '_acan')]",
                "//div[@role='dialog']//div[@role='button']",
            ]
            
            for selector in dismiss_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        if button.is_displayed():
                            try:
                                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                time.sleep(0.5)
                                button.click()
                                print(f"  âœ“ Dismissed pop-up (attempt {attempt + 1})")
                                popup_dismissed = True
                                time.sleep(1)
                                break
                            except:
                                continue
                    if popup_dismissed:
                        break
                except:
                    continue
            
            # If no pop-up found, try pressing Escape key
            if not popup_dismissed:
                try:
                    from selenium.webdriver.common.keys import Keys
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                except:
                    pass
            
            # If no pop-up was dismissed in this attempt, we're done
            if not popup_dismissed:
                if attempt == 0:
                    print("  No pop-ups found to dismiss")
                break
            
            # Wait a bit before next attempt in case more pop-ups appear
            time.sleep(1)
        
        print("Finished checking for pop-ups")
        time.sleep(1)  # Final wait after dismissing pop-ups
        
    except Exception as e:
        # Silently fail - pop-ups might not be present
        pass


def _handle_post_login_prompts(driver):
    """
    Handle Instagram-specific post-login prompts:
    1. "Enregister vos infos" / "Save your login info" prompt
    2. Big OK button popup that appears after saving login info
    
    These prompts appear after successful login and must be handled before
    proceeding with other actions like clicking the + button.
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        print("Handling post-login prompts...")
        time.sleep(2)  # Wait for prompts to appear
        
        # Step 1: Handle "Enregister vos infos" / "Save your login info" prompt
        save_login_selectors = [
            # French: "Enregister vos infos"
            "//button[contains(text(), 'Enregister vos infos')]",
            "//button[contains(text(), 'Enregistrer vos infos')]",  # Alternative spelling
            "//div[@role='button' and contains(text(), 'Enregister vos infos')]",
            "//div[@role='button' and contains(text(), 'Enregistrer vos infos')]",
            # English: "Save your login info" or variations
            "//button[contains(text(), 'Save your login info')]",
            "//button[contains(text(), 'Save Login Info')]",
            "//button[contains(text(), 'Save Info')]",
            "//div[@role='button' and contains(text(), 'Save your login info')]",
            "//div[@role='button' and contains(text(), 'Save Login Info')]",
            # More generic selectors
            "//button[contains(text(), 'Enregistrer')]",
            "//button[contains(text(), 'Save')]",
            # By aria-label
            "//button[@aria-label='Enregister vos infos']",
            "//button[@aria-label='Save your login info']",
        ]
        
        save_button_clicked = False
        for selector in save_login_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                for button in buttons:
                    if button.is_displayed():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(0.5)
                            button.click()
                            print("  âœ“ Clicked 'Save your login info' button")
                            save_button_clicked = True
                            time.sleep(2)  # Wait for OK button to appear
                            break
                        except Exception as e:
                            continue
                if save_button_clicked:
                    break
            except:
                continue
        
        if not save_button_clicked:
            print("  No 'Save login info' prompt found (may not appear)")
        
        # Step 2: Handle the big OK button popup
        # Wait a bit longer for the OK button to appear after saving login info
        time.sleep(2)
        
        ok_button_selectors = [
            # French: "D'accord", "OK"
            "//button[contains(text(), \"D'accord\")]",
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Ok')]",
            "//div[@role='button' and contains(text(), \"D'accord\")]",
            "//div[@role='button' and contains(text(), 'OK')]",
            "//div[@role='button' and contains(text(), 'Ok')]",
            # English: "OK", "Got it", "Continue"
            "//button[contains(text(), 'Got it')]",
            "//button[contains(text(), 'Continue')]",
            "//div[@role='button' and contains(text(), 'Got it')]",
            "//div[@role='button' and contains(text(), 'Continue')]",
            # Large/prominent OK buttons (big button)
            "//div[@role='dialog']//button[contains(text(), 'OK')]",
            "//div[@role='dialog']//button[contains(text(), \"D'accord\")]",
            "//div[@role='dialog']//div[@role='button' and contains(text(), 'OK')]",
            "//div[@role='dialog']//div[@role='button' and contains(text(), \"D'accord\")]",
            # By aria-label
            "//button[@aria-label='OK']",
            "//button[@aria-label=\"D'accord\"]",
        ]
        
        # Try multiple times as the OK button might take a moment to appear
        max_attempts = 5
        ok_button_clicked = False
        for attempt in range(max_attempts):
            for selector in ok_button_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        if button.is_displayed():
                            try:
                                # Check if it's a "big" button (larger size indicates it's the prominent OK)
                                size = button.size
                                if size['height'] > 30 or size['width'] > 100:  # Large button
                                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                    time.sleep(0.5)
                                    button.click()
                                    print("  âœ“ Clicked big OK button popup")
                                    ok_button_clicked = True
                                    time.sleep(2)
                                    break
                            except Exception as e:
                                continue
                    if ok_button_clicked:
                        break
                except:
                    continue
            if ok_button_clicked:
                break
            
            # If not found, wait a bit and try again
            if attempt < max_attempts - 1:
                time.sleep(1)
        
        if not ok_button_clicked:
            print("  No OK button popup found (may not appear)")
        
        print("Finished handling post-login prompts")
        time.sleep(1)  # Final wait after handling prompts
        
    except Exception as e:
        # Silently fail - prompts might not be present
        print(f"  Note: Could not handle post-login prompts: {e}")


def _check_and_handle_secondary_login(driver, username, password):
    """
    Check if we're on the login page and attempt to login again if needed.
    This handles cases where Instagram redirects to login page after initial login attempt
    or when navigating to home page.
    
    Args:
        driver: Selenium WebDriver instance
        username: Instagram username
        password: Instagram password
    
    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Check current URL to see if we're on login page
        current_url = driver.current_url.lower()
        
        if "login" not in current_url and "accounts/login" not in current_url:
            # Not on login page, no action needed
            return True
        
        print("⚠️  Still on login page - Instagram may be asking to login again")
        print("Attempting to login again...")
        
        # Define selectors for login form elements
        username_selectors = [
            "input[name='username']",
            "input[type='text']",
            "input[aria-label='Phone number, username, or email']",
            "input[placeholder*='username']",
            "input[placeholder*='Phone number']"
        ]
        
        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            "input[aria-label='Password']",
            "input[placeholder*='Password']"
        ]
        
        login_selectors = [
            "button[type='submit']",
            "//button[contains(text(), 'Log in')]",
            "//button[contains(text(), 'Log In')]",
            "//div[@role='button' and contains(text(), 'Log in')]",
            "//div[@role='button' and contains(text(), 'Log In')]"
        ]
        
        # Wait a moment for the page to stabilize
        time.sleep(2)
        
        # Try to find username and password fields again
        username_input_retry = None
        for selector in username_selectors:
            try:
                username_input_retry = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_input_retry:
                    break
            except:
                continue
        
        password_input_retry = None
        for selector in password_selectors:
            try:
                password_input_retry = driver.find_element(By.CSS_SELECTOR, selector)
                if password_input_retry:
                    break
            except:
                continue
        
        if not username_input_retry or not password_input_retry:
            print("⚠️  Could not find login form fields for retry")
            return False
        
        # Fill in credentials again
        print(f"Re-entering username: {username}")
        username_input_retry.clear()
        username_input_retry.send_keys(username)
        time.sleep(1)
        
        print("Re-entering password...")
        password_input_retry.clear()
        password_input_retry.send_keys(password)
        time.sleep(1)
        
        # Find and click login button again
        login_button_retry = None
        for selector in login_selectors:
            try:
                if selector.startswith("//"):
                    login_button_retry = driver.find_element(By.XPATH, selector)
                else:
                    login_button_retry = driver.find_element(By.CSS_SELECTOR, selector)
                if login_button_retry and login_button_retry.is_displayed():
                    break
            except:
                continue
        
        if not login_button_retry:
            print("⚠️  Could not find login button for retry")
            return False
        
        print("Clicking login button again...")
        login_button_retry.click()
        time.sleep(5)  # Wait for login to process
        
        # Check if login was successful this time
        current_url_retry = driver.current_url.lower()
        if "instagram.com" in current_url_retry and "login" not in current_url_retry and "accounts/login" not in current_url_retry:
            # Verify we're actually logged in by navigating to home
            driver.get("https://www.instagram.com")
            time.sleep(3)
            
            current_url_retry = driver.current_url.lower()
            if "login" not in current_url_retry and "accounts/login" not in current_url_retry:
                print("✓ Successfully logged in to Instagram after retry!")
                # Handle post-login prompts (save login info, OK button)
                _handle_post_login_prompts(driver)
                return True
            else:
                print("⚠️  Login retry verification failed - redirected back to login page")
                return False
        else:
            # Still on login page after retry - login failed
            print("⚠️  Login retry failed - still on login page")
            print("This might indicate incorrect credentials or a login error.")
            return False
            
    except Exception as retry_error:
        print(f"⚠️  Error during login retry: {retry_error}")
        return False


def login_to_instagram(driver, username=None, password=None):
    """
    Automatically log in to Instagram with provided credentials.
    
    Args:
        driver: Selenium WebDriver instance
        username: Instagram username (if None, tries to get from config)
        password: Instagram password (if None, tries to get from config)
    
    Returns:
        bool: True if login successful, False otherwise
    """
    # Import Selenium classes needed for login
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("âš  Selenium not available for automatic login")
        return False
    
    # Get credentials from parameters or config
    if username is None:
        username = getattr(config, 'INSTAGRAM_USERNAME', None)
    if password is None:
        password = getattr(config, 'INSTAGRAM_PASSWORD', None)
    
    # If no credentials provided, return False to use manual login
    if not username or not password:
        return False
    
    try:
        print("Attempting automatic login to Instagram...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)
        
        # Find username/email input field
        username_selectors = [
            "input[name='username']",
            "input[type='text']",
            "input[aria-label='Phone number, username, or email']",
            "input[placeholder*='username']",
            "input[placeholder*='Phone number']"
        ]
        
        username_input = None
        for selector in username_selectors:
            try:
                username_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_input:
                    break
            except:
                continue
        
        if not username_input:
            print("âš  Could not find username input field")
            return False
        
        # Find password input field
        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            "input[aria-label='Password']",
            "input[placeholder*='Password']"
        ]
        
        password_input = None
        for selector in password_selectors:
            try:
                password_input = driver.find_element(By.CSS_SELECTOR, selector)
                if password_input:
                    break
            except:
                continue
        
        if not password_input:
            print("âš  Could not find password input field")
            return False
        
        # Fill in credentials
        print(f"Entering username: {username}")
        username_input.clear()
        username_input.send_keys(username)
        time.sleep(1)
        
        print("Entering password...")
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1)
        
        # Find and click login button
        login_button = None
        login_selectors = [
            "button[type='submit']",
            "//button[contains(text(), 'Log in')]",
            "//button[contains(text(), 'Log In')]",
            "//div[@role='button' and contains(text(), 'Log in')]",
            "//div[@role='button' and contains(text(), 'Log In')]"
        ]
        
        for selector in login_selectors:
            try:
                if selector.startswith("//"):
                    login_button = driver.find_element(By.XPATH, selector)
                else:
                    login_button = driver.find_element(By.CSS_SELECTOR, selector)
                if login_button and login_button.is_displayed():
                    break
            except:
                continue
        
        if login_button:
            print("Clicking login button...")
            login_button.click()
            time.sleep(5)  # Wait for login to process
            
            # First, check if login was immediately successful (no 2FA needed)
            current_url = driver.current_url.lower()
            
            # Check if we're already logged in (redirected away from login page)
            if "instagram.com" in current_url and "login" not in current_url and "accounts/login" not in current_url:
                # Verify we're actually logged in by navigating to home
                driver.get("https://www.instagram.com")
                time.sleep(3)
                
                current_url = driver.current_url.lower()
                if "login" not in current_url and "accounts/login" not in current_url:
                    print("✓ Successfully logged in to Instagram!")
                    # Handle post-login prompts (save login info, OK button)
                    _handle_post_login_prompts(driver)
                    
                    # Check if Instagram is asking to login again (sometimes happens when no save login prompts appear)
                    current_url_check = driver.current_url.lower()
                    if "login" in current_url_check or "accounts/login" in current_url_check:
                        print("⚠️  Instagram redirected to login page after initial login")
                        print("Attempting secondary login...")
                        secondary_login_success = _check_and_handle_secondary_login(driver, username, password)
                        if not secondary_login_success:
                            print("⚠️  Secondary login failed")
                            return False
                    
                    return True
                else:
                    print("âš  Login verification failed - redirected back to login page")
                    return False
            
            # If still on login page, check for 2FA prompts
            # Wait a moment for any 2FA prompts to appear
            time.sleep(2)
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()
            
            # More specific 2FA detection - look for actual 2FA page indicators
            is_2fa_page = (
                "two-factor" in page_source or 
                "two factor" in page_source or
                ("security" in page_source and "code" in page_source and "enter" in page_source) or
                ("verify" in page_source and ("code" in page_source or "security" in page_source))
            )
            
            # Also check if URL indicates 2FA/challenge page
            is_2fa_url = (
                "challenge" in current_url or 
                "two-factor" in current_url or
                "accounts/two_factor" in current_url
            )
            
            if is_2fa_page or is_2fa_url:
                print("\n" + "="*60)
                print("âš  Two-factor authentication or security check detected.")
                print("Please complete the verification in the browser.")
                print("Press Enter once verification is complete and you're logged in...")
                print("="*60)
                input()
                
                # After 2FA completion, verify login was successful
                time.sleep(3)
                driver.get("https://www.instagram.com")
                time.sleep(3)
                
                # Verify we're actually logged in
                current_url = driver.current_url.lower()
                if "login" not in current_url and "accounts/login" not in current_url:
                    print("✓ Successfully logged in to Instagram after 2FA verification!")
                    # Handle post-login prompts (save login info, OK button)
                    _handle_post_login_prompts(driver)
                    
                    # Check if Instagram is asking to login again (sometimes happens when no save login prompts appear)
                    current_url_check = driver.current_url.lower()
                    if "login" in current_url_check or "accounts/login" in current_url_check:
                        print("⚠️  Instagram redirected to login page after 2FA login")
                        print("Attempting secondary login...")
                        secondary_login_success = _check_and_handle_secondary_login(driver, username, password)
                        if not secondary_login_success:
                            print("⚠️  Secondary login failed")
                            return False
                    
                    return True
                else:
                    print("âš  Login verification failed - still on login page")
                    print("Please check if you completed the 2FA verification correctly.")
                    return False
            
            # No 2FA detected, but still on login page - try logging in again
            if "login" in current_url or "accounts/login" in current_url:
                return _check_and_handle_secondary_login(driver, username, password)
            
            # If we got here, something unexpected happened
            print("âš  Unexpected state after login attempt")
            return False
        else:
            print("âš  Could not find login button")
            return False
            
    except Exception as e:
        print(f"âš  Error during automatic login: {e}")
        traceback.print_exc()
        return False


def post_to_instagram(image_paths, caption="", username=None, password=None):
    """
    Post images to Instagram using browser automation.
    Note: This function uses browser automation tools available via MCP.
    For automated posting, you may need to install selenium or playwright.
    """
    try:
        # Try using selenium if available
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            
            # Setup Chrome driver with options to avoid detection
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            # Keep browser open even if there's an error
            chrome_options.add_experimental_option("detach", True)
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute script to hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            try:
                # Try automatic login first
                login_success = login_to_instagram(driver, username, password)
                
                if not login_success:
                    # Fall back to manual login
                    print("\n" + "="*60)
                    print("Automatic login not available or failed.")
                    print("Please log in to Instagram in the browser window.")
                    print("IMPORTANT: Make sure you log in to the account: real_cascadia")
                    print("The browser will NOT do anything until you press Enter.")
                    print("Take your time - complete the full login process.")
                    print("Once you are fully logged in and on the Instagram home page, press Enter...")
                    print("="*60)
                    input()  # Wait here - browser stays static until Enter is pressed
                    
                    # Verify login after manual entry
                    print("\nVerifying login...")
                    time.sleep(2)
                    driver.get("https://www.instagram.com")
                    time.sleep(3)
                
                # Verify we're logged in as the correct account (real_cascadia)
                try:
                    print("Verifying account...")
                    # Try to find the username in the page - check profile link or navigation
                    # Instagram's structure varies, so we'll try multiple approaches
                    username_found = False
                    try:
                        # Method 1: Check profile link in navigation
                        profile_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/real_cascadia/']")
                        if profile_links:
                            username_found = True
                            print("âœ“ Verified: Logged in as real_cascadia")
                    except:
                        pass
                    
                    if not username_found:
                        try:
                            # Method 2: Check if we can access the profile page
                            driver.get(f"https://www.instagram.com/real_cascadia/")
                            time.sleep(2)
                            # If we're logged in as this account, we should see edit profile or similar
                            if "edit" in driver.page_source.lower() or "real_cascadia" in driver.current_url:
                                username_found = True
                                print("âœ“ Verified: Logged in as real_cascadia")
                            else:
                                print("âš  Warning: Could not verify account. Please ensure you're logged in as real_cascadia")
                        except:
                            print("âš  Warning: Could not verify account. Please ensure you're logged in as real_cascadia")
                    
                    # Navigate back to main page
                    driver.get("https://www.instagram.com")
                    time.sleep(2)
                except Exception as verify_error:
                    print(f"âš  Could not verify account automatically: {verify_error}")
                    print("Please manually verify you're logged in as real_cascadia before continuing")
                    input("Press Enter to continue...")
                
                # Navigate to home page and click create button
                print("\nNavigating to Instagram home page...")
                driver.get("https://www.instagram.com")
                time.sleep(3)
                
                # Handle post-login prompts (save login info, OK button) as safety measure
                # This ensures prompts are handled even if they appear later or weren't caught during login
                _handle_post_login_prompts(driver)
                
                # Dismiss any other pop-ups that appear after login (must be done before clicking +)
                _dismiss_instagram_popups(driver)
                
                # Click the create/new post button (+ icon) - using exact aria-label
                print("Looking for create post button (+ icon)...")
                create_button = None
                # Try exact selectors for the create button (French: "Nouvelle publication")
                create_selectors = [
                    "svg[aria-label='Nouvelle publication']",
                    "svg[aria-label*='Nouvelle publication']",
                    "svg[aria-label='New post']",
                    "svg[aria-label='Create']",
                    "//svg[@aria-label='Nouvelle publication']",
                    "//svg[contains(@aria-label, 'Nouvelle publication')]",
                    "//a[contains(@href, '/create/')]"
                ]
                
                for selector in create_selectors:
                    try:
                        if selector.startswith("//"):
                            create_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            create_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        if create_button:
                            break
                    except:
                        continue
                
                # If SVG found, try to find parent clickable element
                if create_button and create_button.tag_name == 'svg':
                    try:
                        # Find parent anchor or button
                        parent = create_button.find_element(By.XPATH, "./ancestor::a | ./ancestor::button | ./ancestor::div[@role='button']")
                        if parent:
                            create_button = parent
                    except:
                        pass
                
                if create_button:
                    driver.execute_script("arguments[0].scrollIntoView(true);", create_button)
                    time.sleep(1)
                    create_button.click()
                    print("âœ“ Clicked create post button")
                    time.sleep(3)
                else:
                    print("âš  Could not find create button automatically")
                    print("Please manually click the '+' (create) button in Instagram")
                    input("Press Enter once you've clicked the create button...")
                
                # Click "Publication" option - wait for dropdown to appear, then click the link
                print("Waiting for dropdown menu to appear...")
                time.sleep(2)
                
                # Wait for the dropdown to be visible (it should contain Publication option)
                publication_link = None
                publication_selectors = [
                    # Target the <a> tag that contains the span with "Publication" text
                    "//a[@role='link'][.//span[contains(text(), 'Publication')]]",
                    "//a[.//span[contains(text(), 'Publication')]]",
                    "//a[contains(@href, '#')][.//span[contains(text(), 'Publication')]]",
                    # Fallback: find by span and get parent <a>
                    "//span[contains(text(), 'Publication')]/ancestor::a[@role='link']",
                    "//span[contains(text(), 'Publication')]/ancestor::a",
                    # Alternative: find by SVG aria-label
                    "//a[.//svg[@aria-label='Publication']]",
                    "//svg[@aria-label='Publication']/ancestor::a[@role='link']"
                ]
                
                for selector in publication_selectors:
                    try:
                        publication_link = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if publication_link:
                            break
                    except:
                        continue
                
                if publication_link:
                    # Scroll into view and click
                    driver.execute_script("arguments[0].scrollIntoView(true);", publication_link)
                    time.sleep(0.5)
                    publication_link.click()
                    print("âœ“ Clicked Publication option")
                    time.sleep(3)
                else:
                    print("âš  Could not find Publication option automatically")
                    print("Please manually click 'Publication' option from the dropdown")
                    input("Press Enter once you've selected Publication...")
                
                # Find and click the file selector button, or use file input directly
                print("Looking for file selector...")
                time.sleep(2)
                
                # Try to find the "SÃ©lectionner sur l'ordinateur" button first
                file_selector_button = None
                try:
                    file_selector_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'SÃ©lectionner sur l')]"))
                    )
                except:
                    pass
                
                # Find file input for uploading images
                print("Looking for file upload element...")
                file_input = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                
                # Make sure the file input is visible
                driver.execute_script("arguments[0].scrollIntoView(true);", file_input)
                time.sleep(1)
                
                # Upload images - for carousel/gallery posts, upload all images together
                if len(image_paths) > 1:
                    print(f"Uploading {len(image_paths)} images for gallery post...")
                else:
                    print(f"Uploading image...")
                
                try:
                    # Instagram accepts multiple files when sent as newline-separated paths
                    # Convert all paths to absolute paths
                    absolute_paths = [os.path.abspath(img) for img in image_paths]
                    file_paths = "\n".join(absolute_paths)
                    
                    # Send all file paths at once for carousel/gallery
                    file_input.send_keys(file_paths)
                    if len(image_paths) > 1:
                        print(f"âœ“ Successfully uploaded {len(image_paths)} images for gallery post")
                    else:
                        print(f"âœ“ Successfully uploaded image")
                    time.sleep(5)  # Give Instagram time to process all images
                except Exception as upload_error:
                    print(f"Multiple file upload failed: {upload_error}")
                    print("Trying alternative method...")
                    try:
                        # Try uploading first image, then adding more
                        file_input.send_keys(os.path.abspath(image_paths[0]))
                        print(f"Uploaded first image: {image_paths[0]}")
                        time.sleep(3)
                        
                        # Try to find and click "Add" or "Select more" to add additional images
                        try:
                            add_selectors = [
                                "//button[contains(text(), 'Add')]",
                                "//button[contains(text(), 'Select more')]",
                                "//div[contains(text(), 'Add')]",
                                "//div[@role='button' and contains(text(), 'Add')]"
                            ]
                            add_button = None
                            for selector in add_selectors:
                                try:
                                    add_button = WebDriverWait(driver, 5).until(
                                        EC.element_to_be_clickable((By.XPATH, selector))
                                    )
                                    if add_button:
                                        break
                                except:
                                    continue
                            
                            if add_button:
                                add_button.click()
                                time.sleep(2)
                                
                                # Find file input again and upload remaining images
                                file_input2 = WebDriverWait(driver, 5).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                                )
                                remaining_paths = "\n".join([os.path.abspath(img) for img in image_paths[1:]])
                                file_input2.send_keys(remaining_paths)
                                print(f"âœ“ Uploaded remaining {len(image_paths) - 1} images")
                            else:
                                print(f"âš  Could not find 'Add' button")
                                print(f"   Please manually add the remaining {len(image_paths) - 1} image(s) in Instagram")
                        except Exception as add_error:
                            print(f"âš  Could not add additional images: {add_error}")
                            print(f"   Please manually add the remaining {len(image_paths) - 1} image(s) in Instagram")
                    except Exception as alt_error:
                        print(f"Alternative upload method also failed: {alt_error}")
                        print(f"âš  Please manually select all {len(image_paths)} images in Instagram")
                
                # Wait for images to load and process
                print("Waiting for images to process...")
                time.sleep(5)
                # Images are already in 1:1 square format, so no aspect ratio adjustment needed                                                                 

                # Click "Suivant" (Next) button twice
                print("Clicking Next buttons...")
                try:
                    # Find and click first "Suivant" button
                    suivant_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(text(), 'Suivant')] | //div[contains(text(), 'Suivant')]")

                    if len(suivant_buttons) > 0:
                        # Click first Suivant button
                        suivant_buttons[0].click()
                        print("âœ“ Clicked first 'Suivant' (Next) button")
                        time.sleep(2)

                        # Find and click second Suivant button (might be the same element or different)                                                         
                        suivant_buttons_2 = driver.find_elements(By.XPATH, "//div[@role='button' and contains(text(), 'Suivant')] | //div[contains(text(), 'Suivant')]")                                                                        
                        if len(suivant_buttons_2) > 0:
                            suivant_buttons_2[0].click()
                            print("Clicked second 'Suivant' (Next) button")
                            time.sleep(2)
                    else:
                        # Try English version
                        next_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(text(), 'Next')] | //div[contains(text(), 'Next')]")
                        if len(next_buttons) > 0:
                            next_buttons[0].click()
                            print("âœ“ Clicked first 'Next' button")
                            time.sleep(2)
                            next_buttons_2 = driver.find_elements(By.XPATH, "//div[@role='button' and contains(text(), 'Next')] | //div[contains(text(), 'Next')]")
                            if len(next_buttons_2) > 0:
                                next_buttons_2[0].click()
                                print("âœ“ Clicked second 'Next' button")
                                time.sleep(2)
                        else:
                            print("âš  Could not find 'Suivant' button automatically")
                            input("Please manually click 'Next' button(s), then press Enter...")

                    # Now fill caption after second Suivant button is clicked
                    # Find and fill caption
                    try:
                        print("Looking for caption input area...")
                        # Try multiple selectors for the caption area
                        caption_area = None
                        caption_selectors = [
                            # The specific element provided by user
                            "p.xdj266r.x14z9mp.xat24cr.x1lziwak[dir='auto']",
                            "//p[@class='xdj266r x14z9mp xat24cr x1lziwak' and @dir='auto']",
                            # Try finding parent with class that contains these classes
                            "//p[contains(@class, 'xdj266r') and contains(@class, 'x14z9mp')]",
                            # Fallback to textarea
                            "textarea[aria-label*='Write a caption']",
                            "textarea[aria-label*='Ã‰crire une lÃ©gende']",
                            "//textarea",
                            # Contenteditable div
                            "div[contenteditable='true']",
                            "//div[@contenteditable='true']",
                        ]

                        for selector in caption_selectors:
                            try:
                                if selector.startswith("//"):
                                    caption_area = WebDriverWait(driver, 5).until(
                                        EC.presence_of_element_located((By.XPATH, selector))
                                    )
                                else:
                                    caption_area = WebDriverWait(driver, 5).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                    )
                                if caption_area and caption_area.is_displayed():
                                    print(f"  Found caption area using selector: {selector}")
                                    break
                            except:
                                continue

                        if not caption_area:
                            # Try to find parent contenteditable element
                            try:
                                p_element = driver.find_element(By.CSS_SELECTOR, "p.xdj266r.x14z9mp.xat24cr.x1lziwak[dir='auto']")
                                # Find parent with contenteditable
                                caption_area = driver.execute_script("""
                                    var p = arguments[0];
                                    var parent = p.parentElement;
                                    while (parent) {
                                        if (parent.contentEditable === 'true' || parent.getAttribute('contenteditable') === 'true') {                               
                                            return parent;
                                        }
                                        parent = parent.parentElement;
                                    }
                                    return p;
                                """, p_element)
                                if caption_area:
                                    print("  Found parent contenteditable element") 
                            except:
                                pass

                        if caption_area:
                            # Wait for element to be clickable and scroll into view
                            print("  Waiting for caption area to be ready...")
                            try:
                                WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable(caption_area)
                                )
                            except:
                                print("  ⚠ Element might not be clickable yet, continuing anyway...")
                            
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", caption_area)
                            time.sleep(1)
                        
                            # Try multiple methods to fill the caption
                            caption_filled = False
                            
                            # Method 1: Click to focus, then use send_keys (most reliable for contenteditable)
                            try:
                                from selenium.webdriver.common.keys import Keys
                                from selenium.webdriver.common.action_chains import ActionChains
                                
                                # Multiple click strategies to ensure the element is focused
                                print("  Clicking on caption text box to focus...")
                                
                                # Strategy 1: JavaScript click (more reliable for some elements)
                                driver.execute_script("arguments[0].click();", caption_area)
                                time.sleep(0.5)
                                
                                # Strategy 2: Regular Selenium click
                                try:
                                    caption_area.click()
                                    time.sleep(0.5)
                                except:
                                    pass
                                
                                # Strategy 3: ActionChains click (moves mouse and clicks)
                                try:
                                    ActionChains(driver).move_to_element(caption_area).click().perform()
                                    time.sleep(0.5)
                                except:
                                    pass
                                
                                # Ensure element has focus using JavaScript
                                driver.execute_script("arguments[0].focus();", caption_area)
                                time.sleep(0.5)
                                
                                # Verify focus
                                focused_element = driver.execute_script("return document.activeElement;")
                                if focused_element == caption_area or driver.execute_script("return arguments[0].contains(document.activeElement) || arguments[0] === document.activeElement;", caption_area):
                                    print("  ✓ Caption box is focused")
                                else:
                                    print("  ⚠ Warning: Caption box might not be focused, continuing anyway...")
                                
                                # Clear any existing content
                                ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                                time.sleep(0.3)
                                ActionChains(driver).send_keys(Keys.DELETE).perform()
                                time.sleep(0.3)
                                
                                # Type the caption
                                print(f"  Typing caption ({len(caption)} characters)...")
                                caption_area.send_keys(caption)
                                time.sleep(1)
                                caption_filled = True
                                print("  ✓ Caption filled using send_keys")
                            except Exception as send_keys_error:
                                print(f"  send_keys failed: {send_keys_error}")
                            
                            # Method 2: JavaScript with proper event handling (if send_keys didn't work)
                            if not caption_filled:
                                try:
                                    print("  Trying JavaScript method to fill caption...")
                                    # First, click and focus the element
                                    driver.execute_script("""
                                        var element = arguments[0];
                                        element.click();
                                        element.focus();
                                        element.scrollIntoView({block: 'center', behavior: 'smooth'});
                                    """, caption_area)
                                    time.sleep(0.5)  # Wait for focus to take effect
                                    
                                    # Now set the content
                                    driver.execute_script("""
                                        var element = arguments[0];
                                        var text = arguments[1];

                                        // For contenteditable elements, we need to set the content properly
                                        // Clear existing content
                                        while (element.firstChild) {
                                            element.removeChild(element.firstChild);
                                        }
                                        
                                        // Set the text - try multiple methods
                                        element.textContent = text;
                                        element.innerText = text;
                                        
                                        // For <p> elements, also set innerHTML with proper structure
                                        if (element.tagName === 'P') {
                                            // Split by newlines and join with <br> tags
                                            var lines = text.split('\\n');
                                            element.innerHTML = lines.join('<br>');
                                        }
                                        
                                        // Move cursor to end
                                        var range = document.createRange();
                                        var selection = window.getSelection();
                                        range.selectNodeContents(element);
                                        range.collapse(false);
                                        selection.removeAllRanges();
                                        selection.addRange(range);
                                        
                                        // Trigger all relevant events that Instagram listens for
                                        var eventTypes = ['input', 'change', 'keyup', 'keydown', 'paste', 'compositionend'];
                                        eventTypes.forEach(function(eventType) {
                                            var event = new Event(eventType, { bubbles: true, cancelable: true });
                                            element.dispatchEvent(event);
                                        });
                                        
                                        // Also trigger InputEvent specifically (more realistic)
                                        try {
                                            var inputEvent = new InputEvent('input', { 
                                                bubbles: true, 
                                                cancelable: true, 
                                                data: text,
                                                inputType: 'insertText'
                                            });
                                            element.dispatchEvent(inputEvent);
                                        } catch(e) {
                                            // Fallback if InputEvent not supported
                                            var inputEvent = new Event('input', { bubbles: true, cancelable: true });
                                            element.dispatchEvent(inputEvent);
                                        }
                                    """, caption_area, caption)
                                    time.sleep(1)
                                    caption_filled = True
                                    print("✓ Caption filled using JavaScript")
                                except Exception as js_error:
                                    print(f"  JavaScript method failed: {js_error}")
                            
                            if not caption_filled:
                                print("⚠ All caption filling methods failed")
                            else:
                                # Verify the caption was actually set
                                try:
                                    actual_text = driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", caption_area)
                                    if actual_text.strip():
                                        print(f"✓ Verified caption is set (length: {len(actual_text)} characters)")
                                    else:
                                        print("⚠ Warning: Caption area appears empty after filling")
                                except:
                                    pass
                            
                                time.sleep(1)
                        else:
                            print("⚠ Could not find caption area - you may need to add caption manually")
                    except Exception as caption_error:
                        print(f"⚠ Error finding/filling caption area: {caption_error}")
                        import traceback
                        traceback.print_exc()
                        print("You may need to add caption manually")

                    # Automatically proceed to share (no user input needed)
                    print("Caption filled, proceeding to share...")

                    # Now click "Partager" (Share) button
                    # Now click "Partager" (Share) button
                    print("Looking for Share button...")
                    time.sleep(2)
                    partager_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(text(), 'Partager')] | //div[contains(text(), 'Partager')]")
                    
                    if len(partager_buttons) > 0:
                        partager_buttons[0].click()
                        print("âœ“ Clicked 'Partager' (Share) button - Post shared!")
                        time.sleep(3)
                    else:
                        # Try English version
                        share_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(text(), 'Share')] | //div[contains(text(), 'Share')] | //button[contains(text(), 'Share')]")
                        if len(share_buttons) > 0:
                            share_buttons[0].click()
                            print("âœ“ Clicked 'Share' button - Post shared!")
                            time.sleep(3)
                        else:
                            print("âš  Could not find 'Partager' button automatically")
                            input("Please manually click 'Share' button, then press Enter...")
                except Exception as share_error:
                    print(f"âš  Error clicking share button: {share_error}")
                    print("Please manually click 'Share' button")
                    input("Press Enter once posted...")
                
                driver.quit()
                return True
                
            except Exception as e:
                print(f"\nError during Instagram posting: {e}")
                print(f"Error type: {type(e).__name__}")
                print("Full error details:")
                traceback.print_exc()
                print("\nThe browser will remain open so you can try posting manually.")
                print("If you want to close it, you can do so manually.")
                print("Falling back to manual posting instructions...\n")
                # Don't quit the browser immediately - let user close it manually if needed
                # driver.quit()  # Commented out to keep browser open
                return post_to_instagram_manual(image_paths, caption)
                
        except ImportError:
            # Selenium not available, use manual method
            print("Selenium not installed. Using manual posting method.")
            return post_to_instagram_manual(image_paths, caption)
            
    except Exception as e:
        print(f"Error posting to Instagram: {e}")
        return post_to_instagram_manual(image_paths, caption)


def post_to_instagram_manual(image_paths, caption=""):
    """Manual posting method with instructions"""
    print("\n" + "="*60)
    print("MANUAL INSTAGRAM POSTING")
    print("="*60)
    print(f"Caption: {caption}")
    print(f"Images to post ({len(image_paths)}):")
    for i, img in enumerate(image_paths, 1):
        print(f"  {i}. {os.path.abspath(img)}")
    print("\nInstructions:")
    print("1. Open Instagram in your browser")
    print("2. Click the '+' button to create a new post")
    if len(image_paths) > 1:
        print(f"3. Select ALL {len(image_paths)} images listed above (hold Ctrl/Cmd to select multiple)")
        print("   This will create a carousel/gallery post with all games from this week")
    else:
        print("3. Select the image listed above")
    print(f"4. Add the caption: {caption}")
    print("5. Click 'Share'")
    print("\nPress Enter once you have posted...")
    input()
    return True


def post_images_hourly(all_images_by_week, teams=None, upcoming_schedule=None):
    """
    Post images to Instagram with 5 minute intervals between weeks (testing mode).
    
    Args:
        all_images_by_week: Dictionary mapping week numbers to lists of image filenames
        teams: List of Team objects (for standings and odds calculation)
        upcoming_schedule: Dictionary mapping week numbers to lists of (team1, team2) tuples
                          representing upcoming matchups
    """
    import game_logic
    
    print("\n" + "="*60)
    print("Starting Instagram posting schedule...")
    print("="*60)
    
    # Sort weeks
    sorted_weeks = sorted([w for w in all_images_by_week.keys() if isinstance(w, int)])
    
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
        
        # Add current standings
        if teams:
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
        success = post_to_instagram(images, caption)
        
        if not success:
            print(f"Warning: Failed to post Week {week} images")
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
    
    print("\nInstagram posting schedule completed!")

