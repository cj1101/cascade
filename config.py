# Configuration Settings
# Number of rounds to play in each round-robin cycle (None = play all rounds)
# Can be overridden via environment variable ROUNDS_PER_ROUND_ROBIN

# Auto-detect OS and set logos directory accordingly
import os

ROUNDS_PER_ROUND_ROBIN = int(os.getenv('ROUNDS_PER_ROUND_ROBIN')) if os.getenv('ROUNDS_PER_ROUND_ROBIN') else None

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, environment variables must be set manually
    pass

if os.name == 'nt':  # Windows
    LOGOS_DIRECTORY = r"C:\Users\charl\CodingProjets\logos"
else:  # Linux (AWS EC2)
    LOGOS_DIRECTORY = "/home/ubuntu/cascade/logos"

# AWS Scheduled Automation Settings
ROUND_ROBIN_REPETITIONS = 2  # Always 2 round robins
USE_GEMINI = True  # Always use Gemini image generation
STATE_FILE_PATH = "game_state.json"  # Path to game state persistence file

# Scheduling Times (in EST/EDT, 24-hour format)
ROUND_ROBIN_1_START_HOUR = 13  # 1pm EST Friday
ROUND_ROBIN_1_START_MINUTE = 0  # Minute for round robin 1 start
ROUND_ROBIN_2_START_HOUR = 13  # 1pm EST Saturday
TOURNAMENT_QUARTERFINALS_HOUR = 18  # 6pm EST Sunday
TOURNAMENT_SEMIFINALS_HOUR = 19  # 7pm EST Sunday
TOURNAMENT_FINALS_HOUR = 20  # 8pm EST Sunday

# Instagram Graph API Credentials
# These should be set via environment variables in .env file:
#   CASCADIA_ACCESS_TOKEN or META_ACCESS_TOKEN or INSTAGRAM_ACCESS_TOKEN - Your Instagram Graph API access token
#   CASCADIA_ACCOUNT_ID or INSTAGRAM_ACCOUNT_ID - Your Instagram Business Account ID
#
# Load from environment variables (supports multiple naming conventions)
INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN') or os.getenv('CASCADIA_ACCESS_TOKEN') or os.getenv('META_ACCESS_TOKEN')
INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ACCOUNT_ID') or os.getenv('CASCADIA_ACCOUNT_ID')

# Instagram Stories Settings
ENABLE_INSTAGRAM_STORIES = os.getenv('ENABLE_INSTAGRAM_STORIES', 'False').lower() == 'true'

