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
    1. Onetap page "Plus tard" (Later) button at instagram.com/accounts/onetap/
    2. "Enregister vos infos" / "Save your login info" prompt
    3. Big OK button popup that appears after saving login info
    
    These prompts appear after successful login and must be handled before
    proceeding with other actions like clicking the + button.
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        print("Handling post-login prompts...")
        time.sleep(2)  # Wait for prompts to appear
        
        # Step 0: Check if we're on the onetap page and click "Plus tard" (Later)
        current_url = driver.current_url.lower()
        if "onetap" in current_url:
            print("Detected onetap page, clicking 'Plus tard' (Later)...")
            plus_tard_clicked = False
            
            # Try exact selector first: div with role="button" and text "Plus tard"
            plus_tard_selectors = [
                "//div[@role='button' and contains(text(), 'Plus tard')]",
                "//div[@role='button' and text()='Plus tard']",
                "//button[contains(text(), 'Plus tard')]",
                # English version
                "//div[@role='button' and contains(text(), 'Later')]",
                "//div[@role='button' and text()='Later']",
                "//button[contains(text(), 'Later')]",
            ]
            
            for selector in plus_tard_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        if button.is_displayed():
                            try:
                                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                time.sleep(0.5)
                                button.click()
                                print("  ✓ Clicked 'Plus tard' (Later) button")
                                plus_tard_clicked = True
                                time.sleep(2)  # Wait for navigation
                                break
                            except Exception as e:
                                continue
                    if plus_tard_clicked:
                        break
                except:
                    continue
            
            if not plus_tard_clicked:
                print("  ⚠ Could not find 'Plus tard' button on onetap page")
            
            # Wait a bit more after clicking to ensure navigation completes
            time.sleep(2)
        
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


def _find_login_button_robust(driver):
    """
    Find the login button on Instagram login page using multiple strategies.
    Handles both English and French variants, with robust fallback logic.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        WebElement or None: The login button element if found, None otherwise
    """
    from selenium.webdriver.common.by import By
    
    # Comprehensive list of selectors, ordered by specificity
    login_selectors = [
        # Generic submit button (highest priority - most reliable)
        "button[type='submit']",
        
        # English text variants
        "//button[contains(text(), 'Log in')]",
        "//button[contains(text(), 'Log In')]",
        "//div[@role='button' and contains(text(), 'Log in')]",
        "//div[@role='button' and contains(text(), 'Log In')]",
        # Divs containing nested spans with English login text (for Instagram's div-based buttons)
        "//div[.//span[contains(text(), 'Log in')]]",
        "//div[.//span[contains(text(), 'Log In')]]",
        # More specific: find span with login text, then get its ancestor div with x1ja2u2z class
        "//span[contains(text(), 'Log in')]/ancestor::div[contains(@class, 'x1ja2u2z')][1]",
        "//span[contains(text(), 'Log In')]/ancestor::div[contains(@class, 'x1ja2u2z')][1]",
        
        # French text variants
        "//button[contains(text(), 'Se connecter')]",
        "//button[contains(text(), 'Se Connecter')]",
        "//button[contains(text(), 'Connexion')]",
        "//div[@role='button' and contains(text(), 'Se connecter')]",
        "//div[@role='button' and contains(text(), 'Se Connecter')]",
        "//div[@role='button' and contains(text(), 'Connexion')]",
        # Divs containing nested spans with French login text (for Instagram's div-based buttons)
        "//div[.//span[contains(text(), 'Se connecter')]]",
        "//div[.//span[contains(text(), 'Se Connecter')]]",
        "//div[.//span[contains(text(), 'Connexion')]]",
        # More specific: find span with login text, then get its outermost ancestor div with x1ja2u2z class
        "//span[contains(text(), 'Se connecter')]/ancestor::div[contains(@class, 'x1ja2u2z')][1]",
        "//span[contains(text(), 'Se Connecter')]/ancestor::div[contains(@class, 'x1ja2u2z')][1]",
        "//span[contains(text(), 'Connexion')]/ancestor::div[contains(@class, 'x1ja2u2z')][1]",
        
        # Aria-label based selectors (case insensitive matching via contains)
        "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]",
        "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'connecter')]",
        "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'connexion')]",
        "//div[@role='button' and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]",
        "//div[@role='button' and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'connecter')]",
        
        # Form context-based selectors (find submit button within login form)
        "//form//button[@type='submit']",
        "//form//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]",
        "//form//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'connecter')]",
        "//form//div[@role='button' and @type='submit']",
    ]
    
    # Try each selector
    for selector in login_selectors:
        try:
            if selector.startswith("//"):
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            # Check each element to see if it's displayed and enabled
            for element in elements:
                try:
                    # Check if displayed
                    if not element.is_displayed():
                        continue
                    
                    # For buttons, check if enabled; for divs, just check if they're visible
                    try:
                        if element.tag_name.lower() == 'button':
                            if not element.is_enabled():
                                continue
                        # For divs, check if they're not disabled via attribute
                        elif element.tag_name.lower() == 'div':
                            if element.get_attribute('disabled') is not None or element.get_attribute('aria-disabled') == 'true':
                                continue
                    except:
                        # If is_enabled() doesn't exist (for divs), continue anyway if displayed
                        pass
                    
                    return element
                except:
                    continue
        except:
            continue
    
    # Fallback: Use JavaScript to find submit button in forms with password fields
    try:
        login_button_js = driver.execute_script("""
            // Strategy 1: Look for divs containing "Se connecter" or "Log in" text in nested spans
            var loginTexts = ['Se connecter', 'Se Connecter', 'Log in', 'Log In'];
            for (var t = 0; t < loginTexts.length; t++) {
                var text = loginTexts[t];
                // Find all spans containing the login text
                var spans = Array.from(document.querySelectorAll('span'));
                for (var s = 0; s < spans.length; s++) {
                    var span = spans[s];
                    if (span.textContent && span.textContent.trim() === text) {
                        // Find the outermost clickable div ancestor
                        var parent = span.parentElement;
                        var depth = 0;
                        while (parent && depth < 10) {
                            // Look for divs that might be clickable (have pointer cursor, or contain class x1ja2u2z)
                            if (parent.tagName === 'DIV' && 
                                (parent.classList.contains('x1ja2u2z') || 
                                 window.getComputedStyle(parent).cursor === 'pointer' ||
                                 parent.onclick !== null ||
                                 parent.getAttribute('role') === 'button')) {
                                // Check if it's visible
                                if (parent.offsetParent !== null && parent.offsetWidth > 0 && parent.offsetHeight > 0) {
                                    return parent;
                                }
                            }
                            parent = parent.parentElement;
                            depth++;
                        }
                    }
                }
            }
            
            // Strategy 2: Find all password input fields and look for nearby submit buttons
            var passwordInputs = document.querySelectorAll('input[type="password"]');
            if (passwordInputs.length > 0) {
                for (var i = 0; i < passwordInputs.length; i++) {
                    var passwordInput = passwordInputs[i];
                    var form = passwordInput.closest('form');
                    
                    if (form) {
                        // Look for submit button in the form
                        var submitButton = form.querySelector('button[type="submit"]');
                        if (submitButton && submitButton.offsetParent !== null) {
                            if (!submitButton.hasAttribute('disabled') && !submitButton.disabled) {
                                return submitButton;
                            }
                        }
                    }
                    
                    // Look for buttons in parent containers
                    var parent = passwordInput.parentElement;
                    var depth = 0;
                    while (parent && depth < 5) {
                        var buttons = parent.querySelectorAll('button[type="submit"], button:not([type]), div[role="button"]');
                        for (var j = 0; j < buttons.length; j++) {
                            var btn = buttons[j];
                            // Check if button is visible and enabled
                            if (btn.offsetParent !== null && btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                // Check if disabled attribute is not present
                                if (!btn.hasAttribute('disabled') && !btn.disabled) {
                                    return btn;
                                }
                            }
                        }
                        parent = parent.parentElement;
                        depth++;
                    }
                }
            }
            
            // Strategy 3: Last resort - find any submit button on the page
            var allSubmitButtons = document.querySelectorAll('button[type="submit"]');
            for (var k = 0; k < allSubmitButtons.length; k++) {
                var btn = allSubmitButtons[k];
                if (btn.offsetParent !== null && btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                    if (!btn.hasAttribute('disabled') && !btn.disabled) {
                        return btn;
                    }
                }
            }
            
            return null;
        """)
        
        if login_button_js:
            return login_button_js
    except:
        pass
    
    return None


def _handle_second_login_at_home(driver, username, password):
    """
    Handle the second login at https://www.instagram.com/ after first login.
    This function fills in credentials using exact selectors provided for the second login form.
    
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
        
        print("Handling second login at instagram.com/...")
        time.sleep(2)  # Wait for page to stabilize
        
        # Find username input using exact selector
        username_input = None
        try:
            # Exact selector: input[aria-label="Num. téléphone, nom de profil ou e-mail"][name="username"]
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[aria-label="Num. téléphone, nom de profil ou e-mail"][name="username"]'))
            )
            if not username_input.is_displayed() or not username_input.is_enabled():
                username_input = None
        except:
            pass
        
        # Fallback selectors if exact one doesn't work
        if not username_input:
            fallback_selectors = [
                "input[name='username']",
                "input[type='text'][name='username']",
                "//input[@name='username']",
            ]
            for selector in fallback_selectors:
                try:
                    if selector.startswith("//"):
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                username_input = elem
                                break
                    else:
                        username_input = driver.find_element(By.CSS_SELECTOR, selector)
                    if username_input:
                        break
                except:
                    continue
        
        if not username_input:
            print("⚠️  Could not find username input field on second login page")
            return False
        
        # Find password input using exact selector
        password_input = None
        try:
            # Exact selector: input[aria-label="Mot de passe"][type="password"][name="password"]
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[aria-label="Mot de passe"][type="password"][name="password"]'))
            )
            if not password_input.is_displayed() or not password_input.is_enabled():
                password_input = None
        except:
            pass
        
        # Fallback selectors if exact one doesn't work
        if not password_input:
            fallback_selectors = [
                "input[name='password']",
                "input[type='password'][name='password']",
                "//input[@type='password' and @name='password']",
            ]
            for selector in fallback_selectors:
                try:
                    if selector.startswith("//"):
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                password_input = elem
                                break
                    else:
                        password_input = driver.find_element(By.CSS_SELECTOR, selector)
                    if password_input:
                        break
                except:
                    continue
        
        if not password_input:
            print("⚠️  Could not find password input field on second login page")
            return False
        
        # Fill in credentials
        print(f"Entering username on second login: {username}")
        username_input.clear()
        username_input.send_keys(username)
        time.sleep(1)
        
        print("Entering password on second login...")
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1)
        
        # Find login button using exact selector
        login_button = None
        try:
            # Try to find div with class containing key classes and text "Se connecter"
            # The div has class="html-div xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b..."
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[contains(@class, "html-div") and contains(@class, "xdj266r") and contains(@class, "x14z9mp") and contains(@class, "xat24cr") and contains(@class, "x1lziwak") and contains(text(), "Se connecter")]'))
            )
        except:
            # Fallback: try simpler XPath with just text "Se connecter"
            try:
                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Se connecter")]'))
                )
            except:
                # Try using the robust helper as last resort
                login_button = _find_login_button_robust(driver)
        
        if not login_button:
            print("⚠️  Could not find login button on second login page")
            return False
        
        print("Clicking login button on second login page...")
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(0.5)
        login_button.click()
        
        # Wait 5 seconds after second login as specified
        print("Waiting 5 seconds after second login...")
        time.sleep(5)
        
        # Check if login was successful
        current_url = driver.current_url.lower()
        if "login" not in current_url and "accounts/login" not in current_url:
            print("✓ Successfully completed second login!")
            return True
        else:
            print("⚠️  Still on login page after second login attempt")
            return False
            
    except Exception as e:
        print(f"⚠️  Error during second login: {e}")
        traceback.print_exc()
        return False


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
        
        # Also check for login form elements on the page (in case URL doesn't indicate login)
        # This helps catch login pages that appear after initial login
        is_login_page = False
        if "login" in current_url or "accounts/login" in current_url:
            is_login_page = True
        else:
            # Check if login form elements are present (detect login page even if URL doesn't show it)
            try:
                # Look for password input field (indicates login form)
                password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                # Look for login button text
                page_text = driver.page_source.lower()
                if password_inputs and ("se connecter" in page_text or "log in" in page_text or "connexion" in page_text):
                    is_login_page = True
            except:
                pass
        
        if not is_login_page:
            # Not on login page, no action needed
            return True
        
        print("⚠️  Still on login page - Instagram may be asking to login again")
        print("Attempting to login again...")
        
        # Define selectors for login form elements (including French labels)
        username_selectors = [
            "input[name='username']",
            "input[type='text']",
            # English aria-labels
            "input[aria-label='Phone number, username, or email']",
            "input[aria-label*='Phone number']",
            "input[aria-label*='username']",
            "input[aria-label*='email']",
            # French aria-labels
            "input[aria-label*='Num. téléphone']",
            "input[aria-label*='nom de profil']",
            "input[aria-label*='téléphone, nom de profil ou e-mail']",
            # XPath with contains for French labels
            "//input[@type='text' and contains(@aria-label, 'téléphone')]",
            "//input[@type='text' and contains(@aria-label, 'nom de profil')]",
            "//input[@type='text' and contains(@aria-label, 'e-mail')]",
            # Placeholder selectors
            "input[placeholder*='username']",
            "input[placeholder*='Phone number']",
            "input[placeholder*='téléphone']",
            "input[placeholder*='profil']",
        ]
        
        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            # English aria-labels
            "input[aria-label='Password']",
            "input[aria-label*='Password']",
            # French aria-labels
            "input[aria-label='Mot de passe']",
            "input[aria-label*='Mot de passe']",
            # XPath with contains for French labels
            "//input[@type='password' and contains(@aria-label, 'Mot de passe')]",
            "//input[@type='password' and contains(@aria-label, 'password')]",
            # Placeholder selectors
            "input[placeholder*='Password']",
            "input[placeholder*='Mot de passe']",
            "input[placeholder*='passe']",
        ]
        
        # Wait a moment for the page to stabilize
        time.sleep(2)
        
        # Try to find username and password fields again
        username_input_retry = None
        for selector in username_selectors:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    elements = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.XPATH, selector))
                    )
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            username_input_retry = elem
                            break
                else:
                    # CSS selector
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
                if selector.startswith("//"):
                    # XPath selector
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            password_input_retry = elem
                            break
                else:
                    # CSS selector
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
        
        # Find and click login button again using robust helper
        login_button_retry = _find_login_button_robust(driver)
        
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
            # English aria-labels
            "input[aria-label='Phone number, username, or email']",
            "input[aria-label*='Phone number']",
            "input[aria-label*='username']",
            "input[aria-label*='email']",
            # French aria-labels
            "input[aria-label*='Num. téléphone']",
            "input[aria-label*='nom de profil']",
            "input[aria-label*='téléphone, nom de profil ou e-mail']",
            # XPath with contains for French labels
            "//input[@type='text' and contains(@aria-label, 'téléphone')]",
            "//input[@type='text' and contains(@aria-label, 'nom de profil')]",
            "//input[@type='text' and contains(@aria-label, 'e-mail')]",
            # Placeholder selectors
            "input[placeholder*='username']",
            "input[placeholder*='Phone number']",
            "input[placeholder*='téléphone']",
            "input[placeholder*='profil']",
        ]
        
        username_input = None
        for selector in username_selectors:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    elements = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.XPATH, selector))
                    )
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            username_input = elem
                            break
                else:
                    # CSS selector
                    username_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                if username_input:
                    break
            except:
                continue
        
        if not username_input:
            print("âš  Could not find username input field")
            return False

        # Find password input field
        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            # English aria-labels
            "input[aria-label='Password']",
            "input[aria-label*='Password']",
            # French aria-labels
            "input[aria-label='Mot de passe']",
            "input[aria-label*='Mot de passe']",
            # XPath with contains for French labels
            "//input[@type='password' and contains(@aria-label, 'Mot de passe')]",
            "//input[@type='password' and contains(@aria-label, 'password')]",
            # Placeholder selectors
            "input[placeholder*='Password']",
            "input[placeholder*='Mot de passe']",
            "input[placeholder*='passe']",
        ]

        password_input = None
        for selector in password_selectors:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            password_input = elem
                            break
                else:
                    # CSS selector
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
        
        # Find and click login button using robust helper
        login_button = _find_login_button_robust(driver)
        
        if login_button:
            print("Clicking first login button...")
            login_button.click()
            print("Waiting 5 seconds after first login...")
            time.sleep(5)  # Wait 5 seconds after first login as specified
            
            # Check current URL and detect if we need second login
            current_url = driver.current_url.lower()
            
            # Check if we're on instagram.com/ and need second login
            needs_second_login = False
            
            # Check if we're on instagram.com/ (not /accounts/login/)
            if "instagram.com" in current_url and "accounts/login" not in current_url:
                # Check if login form is present on the page
                try:
                    # Look for password input field (indicates login form)
                    password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                    # Check for login button text
                    page_text = driver.page_source.lower()
                    if password_inputs and ("se connecter" in page_text or "log in" in page_text or "connexion" in page_text):
                        needs_second_login = True
                        print("Detected second login form at instagram.com/")
                except:
                    pass
            
            # Handle second login if needed
            if needs_second_login:
                print("Performing second login at instagram.com/...")
                second_login_success = _handle_second_login_at_home(driver, username, password)
                if not second_login_success:
                    print("⚠️  Second login failed")
                    return False
                # Second login completed successfully (already waited 5 seconds in the function)
            else:
                # Check if we're already logged in (no second login needed)
                if "instagram.com" in current_url and "login" not in current_url and "accounts/login" not in current_url:
                    # Verify we're actually logged in by navigating to home
                    driver.get("https://www.instagram.com")
                    time.sleep(3)
                    
                    current_url = driver.current_url.lower()
                    if "login" not in current_url and "accounts/login" not in current_url:
                        print("✓ Successfully logged in to Instagram (only one login required)!")
                    else:
                        # Still on login page - might need second login
                        print("Detected login form after navigation, attempting second login...")
                        second_login_success = _handle_second_login_at_home(driver, username, password)
                        if not second_login_success:
                            print("⚠️  Second login failed")
                            return False
            
            # Verify final login status
            time.sleep(2)
            driver.get("https://www.instagram.com")
            time.sleep(3)
            
            current_url = driver.current_url.lower()
            if "login" not in current_url and "accounts/login" not in current_url:
                print("✓ Successfully logged in to Instagram after two-step login!")
                # Handle post-login prompts (save login info, OK button)
                _handle_post_login_prompts(driver)
                return True
            else:
                print("âš  Login verification failed - still on login page after two-step login")
                return False
        else:
            print("âš  Could not find login button")
            return False
            
    except Exception as e:
        print(f"âš  Error during automatic login: {e}")
        traceback.print_exc()
        return False


def post_to_instagram(image_paths, caption="", username=None, password=None, driver=None):
    """
    Post images to Instagram using browser automation.
    If driver is provided, reuses existing browser session.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        
        browser_created = False
        if driver is None:
            # Create new browser if none provided
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            # Keep browser open even if there's an error
            chrome_options.add_experimental_option("detach", True)
            
            driver = webdriver.Chrome(options=chrome_options)
            browser_created = True
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Login logic here...
            login_success = login_to_instagram(driver, username, password)
            # ... rest of login handling ...
        else:
            # Reuse existing driver - check if still logged in
            print("Reusing existing browser session...")
            driver.get("https://www.instagram.com")
            time.sleep(2)
            
            # Check if we need to login again
            if "login" in driver.current_url.lower() or "accounts/login" in driver.current_url:
                print("Session expired, logging in again...")
                login_success = login_to_instagram(driver, username, password)
                # ... handle login ...
        
        # ... rest of posting logic ...
        
        # Only quit if we created the browser
        if browser_created:
            driver.quit()
        else:
            # Keep browser open for reuse
            print("Browser session kept open for next post...")
            return True
            
    except Exception as e:
        # ... error handling ...


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


def post_images_hourly(all_images_by_week, teams=None, upcoming_schedule=None, initial_teams=None, game_results_by_week=None):
    """
    Post images to Instagram with 5 minute intervals between weeks (testing mode).
    
    Args:
        all_images_by_week: Dictionary mapping week numbers to lists of image filenames
        teams: List of Team objects (for standings and odds calculation)
        upcoming_schedule: Dictionary mapping week numbers to lists of (team1, team2) tuples
                          representing upcoming matchups
        initial_teams: List of Team objects in their initial state (before any games)
        game_results_by_week: Dictionary mapping week numbers to lists of game_result tuples
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

