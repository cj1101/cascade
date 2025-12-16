"""Google Drive Uploader for Podcast Audio Files"""
import os
import logging
from pathlib import Path

# Try to import scheduler for logger, fallback to basic logging
try:
    import scheduler
    logger = scheduler.logger
except ImportError:
    logger = logging.getLogger(__name__)

# Try to import Google Drive API libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    import pickle
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    logger.warning("Google Drive API libraries not available. Install google-api-python-client, google-auth-httplib2, and google-auth-oauthlib.")


# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def load_credentials():
    """
    Load Google Drive credentials from environment variables and authenticate.
    
    Returns:
        google.oauth2.credentials.Credentials: Authenticated credentials, or None on failure
    """
    if not GOOGLE_DRIVE_AVAILABLE:
        logger.error("Google Drive API libraries not available")
        return None
    
    try:
        # Load credentials path from environment
        from dotenv import load_dotenv
        load_dotenv()
        
        # Try GOOGLE_DRIVE_CREDENTIALS_JSON first
        credentials_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON')
        
        # If not found or empty, try gdriveCredentials.json as fallback
        if not credentials_path or credentials_path.strip() == '' or not os.path.exists(credentials_path):
            fallback_path = os.path.join(os.path.dirname(__file__), 'gdriveCredentials.json')
            if os.path.exists(fallback_path):
                credentials_path = fallback_path
                logger.info(f"Using fallback credentials path: {credentials_path}")
            else:
                logger.error("Google Drive credentials file not found. Set GOOGLE_DRIVE_CREDENTIALS_JSON in .env or place gdriveCredentials.json in the project root")
                return None
        
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
        
        # Try to load existing token
        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logger.warning(f"Could not load existing token: {e}")
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Could not refresh token: {e}. Re-authenticating...")
                    creds = None
            
            if not creds:
                # Start OAuth flow
                if not os.path.exists(credentials_path):
                    logger.error(f"Credentials file not found: {credentials_path}")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next time
            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logger.warning(f"Could not save token: {e}")
        
        return creds
        
    except Exception as e:
        logger.error(f"Error loading Google Drive credentials: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def get_or_create_folder(service, folder_name="Cascade Podcast Folder"):
    """
    Get or create a folder in Google Drive.
    
    Args:
        service: Google Drive API service object
        folder_name: Name of the folder to find or create
        
    Returns:
        str: Folder ID, or None on failure
    """
    try:
        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            folder_id = items[0]['id']
            logger.info(f"Found existing folder '{folder_name}' with ID: {folder_id}")
            return folder_id
        
        # Create folder if it doesn't exist
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
        return folder_id
        
    except HttpError as e:
        logger.error(f"Error getting/creating folder: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting/creating folder: {e}")
        return None


def upload_file_to_drive(service, file_path, folder_id=None, file_name=None):
    """
    Upload a file to Google Drive.
    
    Args:
        service: Google Drive API service object
        file_path: Path to the file to upload
        folder_id: Optional folder ID to upload to
        file_name: Optional custom name for the file in Drive
        
    Returns:
        str: File ID of uploaded file, or None on failure
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    try:
        file_name = file_name or os.path.basename(file_path)
        
        # Prepare file metadata
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # Upload file
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        
        file_id = file.get('id')
        logger.info(f"Uploaded '{file_name}' to Google Drive (ID: {file_id})")
        return file_id
        
    except HttpError as e:
        logger.error(f"Error uploading file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading file {file_path}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def upload_podcast_to_drive(podcast_file_path, week=None):
    """
    Upload a podcast file to Google Drive in the "Cascade Podcast Folder".
    
    Args:
        podcast_file_path: Path to the podcast audio file
        week: Optional week number for logging
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not GOOGLE_DRIVE_AVAILABLE:
        logger.warning("Google Drive API not available. Skipping upload.")
        return False
    
    if not os.path.exists(podcast_file_path):
        logger.error(f"Podcast file not found: {podcast_file_path}")
        return False
    
    try:
        # Load credentials
        creds = load_credentials()
        if not creds:
            logger.error("Failed to load Google Drive credentials")
            return False
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        
        # Get or create folder
        folder_id = get_or_create_folder(service, "Cascade Podcast Folder")
        if not folder_id:
            logger.error("Failed to get or create Cascade Podcast Folder")
            return False
        
        # Upload file
        file_id = upload_file_to_drive(service, podcast_file_path, folder_id=folder_id)
        if file_id:
            week_str = f" Week {week}" if week else ""
            logger.info(f"Successfully uploaded podcast{week_str} to Google Drive")
            return True
        else:
            logger.error(f"Failed to upload podcast{week_str} to Google Drive")
            return False
            
    except Exception as e:
        logger.error(f"Error uploading podcast to Google Drive: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def upload_all_podcast_files(week, output_dir="podcasts"):
    """
    Upload all podcast audio files for a week to Google Drive.
    This includes individual game files and the combined podcast.
    
    Args:
        week: Week number
        output_dir: Directory containing podcast files
        
    Returns:
        bool: True if all uploads successful, False otherwise
    """
    if not GOOGLE_DRIVE_AVAILABLE:
        logger.warning("Google Drive API not available. Skipping uploads.")
        return False
    
    try:
        # Load credentials
        creds = load_credentials()
        if not creds:
            logger.error("Failed to load Google Drive credentials")
            return False
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        
        # Get or create folder
        folder_id = get_or_create_folder(service, "Cascade Podcast Folder")
        if not folder_id:
            logger.error("Failed to get or create Cascade Podcast Folder")
            return False
        
        # Find all podcast audio files for this week
        podcast_files = []
        
        # Combined podcast
        combined_podcast = os.path.join(output_dir, f"week_{week}_podcast.mp3")
        if os.path.exists(combined_podcast):
            podcast_files.append(combined_podcast)
        
        # Individual game files
        for game_num in range(1, 5):  # Typically 4 games per week
            game_file = os.path.join(output_dir, f"week_{week}_game_{game_num}.mp3")
            if os.path.exists(game_file):
                podcast_files.append(game_file)
        
        if not podcast_files:
            logger.warning(f"No podcast files found for Week {week}")
            return False
        
        # Upload all files
        success_count = 0
        for file_path in podcast_files:
            file_id = upload_file_to_drive(service, file_path, folder_id=folder_id)
            if file_id:
                success_count += 1
        
        if success_count == len(podcast_files):
            logger.info(f"Successfully uploaded all {success_count} podcast files for Week {week} to Google Drive")
            return True
        else:
            logger.warning(f"Uploaded {success_count}/{len(podcast_files)} podcast files for Week {week}")
            return success_count > 0
            
    except Exception as e:
        logger.error(f"Error uploading podcast files to Google Drive: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False
