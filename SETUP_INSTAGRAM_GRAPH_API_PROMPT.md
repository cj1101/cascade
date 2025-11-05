# Instagram Graph API Setup Prompt for Web Agent

Use this prompt to guide a web agent through setting up Instagram Graph API credentials for the Cascade game simulation program.

---

## Prompt for Web Agent

You are helping set up Instagram Graph API credentials for an automated Instagram posting system. The goal is to get the program running with the bare minimum steps needed.

### Your Mission:
1. Navigate to Facebook/Meta for Developers
2. Create or find a Facebook App
3. Get an Instagram Business Account ID
4. Generate a long-lived access token
5. Update the config.py file with these credentials

### Step-by-Step Instructions:

#### Step 1: Verify Instagram Account Type
- Go to https://www.instagram.com/accounts/edit/
- Verify the account (@real_cascadia) is a **Business** or **Creator** account
- If it's a Personal account, convert it:
  - Go to Settings → Account → Switch to Professional Account
  - Choose Business or Creator (Business recommended)

#### Step 2: Create Facebook Page (if needed)
- Go to https://www.facebook.com/pages/create
- Create a new Facebook Page (or use existing one)
- **IMPORTANT**: Link this Facebook Page to the Instagram Business account
  - Go to Instagram Settings → Linked Accounts → Facebook
  - Link the Facebook Page to Instagram

#### Step 3: Access Meta for Developers
- Navigate to https://developers.facebook.com/
- Log in with the Facebook account that manages the Instagram Business account

#### Step 4: Create or Find Facebook App
- Go to "My Apps" → "Create App" (or use existing app)
- Choose "Business" as the app type
- Fill in app details:
  - App Name: "Cascade Game Simulator" (or similar)
  - Contact Email: Your email
  - Click "Create App"

#### Step 5: Add Instagram Graph API Product
- In the app dashboard, go to "Add Products"
- Find "Instagram Graph API" and click "Set Up"
- This will add the Instagram Graph API product to your app

#### Step 6: Get Instagram Business Account ID
- In the app dashboard, go to "Instagram Graph API" → "Basic Display"
- Or go directly to: https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_ACCESS_TOKEN
- You'll need a temporary access token first:
  - Go to "Tools" → "Graph API Explorer"
  - Select your app from the dropdown
  - Click "Generate Access Token"
  - Grant permissions: `instagram_basic`, `pages_show_list`, `pages_read_engagement`
  - Copy this temporary token

#### Step 7: Find Instagram Account ID
- Use Graph API Explorer or make this API call:
  ```
  GET https://graph.facebook.com/v18.0/me/accounts?access_token=TEMP_TOKEN
  ```
- Find the Facebook Page connected to Instagram
- Get the Page ID, then:
  ```
  GET https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token=TEMP_TOKEN
  ```
- The `instagram_business_account.id` is your **INSTAGRAM_ACCOUNT_ID** - copy this value

#### Step 8: Generate Long-Lived Access Token
- Go to "Tools" → "Access Token Generator"
- Select your app and the Instagram Graph API
- Select permissions:
  - `instagram_basic`
  - `instagram_content_publish`
  - `pages_show_list`
  - `pages_read_engagement`
- Generate token
- **Exchange for long-lived token** (60 days):
  ```
  GET https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN
  ```
- Copy the long-lived access token - this is your **INSTAGRAM_ACCESS_TOKEN**

#### Step 9: Update config.py
- Open the file `config.py` in the project
- Find these lines:
  ```python
  INSTAGRAM_ACCESS_TOKEN = None  # Set this to your access token
  INSTAGRAM_ACCOUNT_ID = None  # Set this to your Instagram Business Account ID
  ```
- Replace `None` with the actual values:
  ```python
  INSTAGRAM_ACCESS_TOKEN = "your_long_lived_access_token_here"
  INSTAGRAM_ACCOUNT_ID = "your_instagram_account_id_here"
  ```
- Save the file

#### Step 10: Test the Setup
- Run a quick test by posting a single image:
  - Create a test image file
  - Run: `python -c "import instagram_poster; instagram_poster.post_to_instagram(['test_image.png'], 'Test post')"`
- If successful, you should see: "✓ Successfully posted to Instagram!"

### Troubleshooting:

**If you get "Invalid OAuth Access Token" error:**
- Token may have expired - regenerate it
- Ensure token has correct permissions

**If you get "User not authorized" error:**
- Verify Instagram account is Business/Creator type
- Check that Facebook Page is linked to Instagram account

**If you get "Media upload failed" error:**
- Check image file exists and is valid
- Ensure image meets Instagram requirements (JPG, PNG, max size)

### Quick Reference:
- **INSTAGRAM_ACCOUNT_ID**: Found via `GET /me/accounts` → Page ID → `instagram_business_account.id`
- **INSTAGRAM_ACCESS_TOKEN**: Generated via Access Token Generator, then exchanged for long-lived token

### Success Criteria:
✅ Instagram account is Business/Creator type  
✅ Facebook Page is linked to Instagram  
✅ Facebook App created with Instagram Graph API  
✅ Long-lived access token generated  
✅ config.py updated with both credentials  
✅ Test post successful  

---

**Once complete, the program is ready to run!**

