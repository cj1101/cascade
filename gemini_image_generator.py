"""Gemini API image generation module with random prompt generation"""
import os
import random
import base64
from io import BytesIO
from PIL import Image

# Try to import the old SDK (google.generativeai)
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

import config

# Expanded Actions
ACTIONS = [
    "punching", "stomping", "tackling", "scoring against",
    "celebrating victory over", "dominating", "overpowering",
    "defeating in battle", "overwhelming", "triumphing over",
    "crushing", "outmatching", "vanquishing", "conquering",
    "slam dunking over", "blocking", "intercepting from",
    "charging at", "speeding past", "dodging", "leaping over",
    "charging headfirst", "throwing down", "throwing punches",
    "breaking through defenses", "counterattacking", "knocking down",
    "launching a counterstrike", "feinting", "sliding tackle",
    "making a game-winning move", "celebrating triumphantly",
    "outrunning opponents", "delivering a knockout blow",
    "marking tightly", "diving to save", "sprinting to goal",
    "throwing a decisive pass", "making a clutch play",
    "locking down defense", "setting a trap", "making a steal",
    "charging the net", "dribbling past defenders",
    "executing a perfect block", "racing to intercept",
    "performing a skillful maneuver"
]

# Expanded Art Styles
ART_STYLES = [
    "watercolor painting", "3D animation", "comic book illustration",
    "pixel art", "oil painting", "digital art", "anime style",
    "cyberpunk aesthetic", "vintage poster", "film noir",
    "impressionist", "surrealist", "abstract", "realistic photo",
    "sketch style", "neon art", "minimalist", "baroque",
    "pop art", "street art", "manga style",
    "art deco", "glitch art", "psychedelic art", "steampunk style",
    "vaporwave aesthetic", "ink drip abstract", "dreamcore visual style",
    "expressionist", "cubist (Picasso-style)", "claymation/stop-motion",
    "lowbrow art", "fantasy art", "conceptual art", "mixed media",
    "digital surrealism", "pixelated vintage", "cyber goth",
    "vector art", "neural abstract", "chromatic aberration effect",
    "black and white photo", "electron microscope style",
    "underwater photography style", "flat design minimalist"
]

# Expanded Scenarios
SCENARIOS = [
    "in a dramatic showdown", "in an epic battle scene",
    "in a high-stakes match", "in a championship moment",
    "in a cinematic action sequence", "in a dramatic confrontation",
    "with intense energy and motion", "in a dynamic sports moment",
    "in a climactic final scene", "in a heroic victory moment",
    "amidst a chaotic urban backdrop", "underneath neon city lights",
    "in a surreal dreamscape", "in a futuristic arena",
    "during a sudden power surge", "in a suspenseful duel",
    "under stormy skies", "at the break of dawn",
    "against a backdrop of swirling mist", "in a crowded coliseum",
    "under dazzling stadium spotlights", "amid swirling autumn leaves",
    "in a post-apocalyptic wasteland", "inside a vibrant graffiti alley",
    "in a quiet moment before the storm", "on a rain-soaked battlefield",
    "surrounded by glowing runes", "amidst exploding fireworks"
]


def load_gemini_api_key():
    """Load Gemini API key from .env file"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        return api_key
    except ImportError:
        # Fallback to manual .env parsing if python-dotenv not available
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        
        if not os.path.exists(env_path):
            raise FileNotFoundError(
                ".env file not found. Please create a .env file with GEMINI_API_KEY=your_api_key"
            )
        
        api_key = None
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    # Remove quotes if present
                    if api_key.startswith('"') and api_key.endswith('"'):
                        api_key = api_key[1:-1]
                    elif api_key.startswith("'") and api_key.endswith("'"):
                        api_key = api_key[1:-1]
                    break
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in .env file. "
                "Please add: GEMINI_API_KEY=your_api_key"
            )
        
        return api_key


def generate_random_prompt(winner_team_name, loser_team_name):
    """
    Generate a random prompt with varying actions, styles, and compositions.
    
    Args:
        winner_team_name: Name of the winning team
        loser_team_name: Name of the losing team
    
    Returns:
        A tuple of (prompt_string, action, style, scenario) for use in enhanced prompts
    """
    action = random.choice(ACTIONS)
    style = random.choice(ART_STYLES)
    scenario = random.choice(SCENARIOS)
    
    prompt = (
        f"Show the team from logo 1 {action} the team from logo 2, "
        f"{scenario}, rendered in {style}. "
        f"Make this scene completely unique and original with dramatic composition. "
        f"The winning team should be clearly victorious and the scene should be dynamic and engaging."
    )
    
    return prompt, action, style, scenario


def load_logo_image(team, logos_directory=None):
    """Load a team's logo image"""
    if logos_directory is None:
        logos_directory = config.LOGOS_DIRECTORY
    
    logo_path = os.path.join(logos_directory, team.get_logo_filename())
    
    # Try different filename variations
    for logo_file in [logo_path, logo_path.replace("'", "'"), logo_path.replace("'", "'")]:
        try:
            if os.path.exists(logo_file):
                return Image.open(logo_file).convert('RGBA')
        except Exception as e:
            continue
    
    return None


def image_to_base64(image):
    """Convert PIL Image to base64 string for API"""
    buffered = BytesIO()
    # Convert RGBA to RGB if needed
    if image.mode == 'RGBA':
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[3])
        image = rgb_image
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def generate_game_image_with_gemini(game_result, filename, game_type="game", week=None, game_number=None, is_champion=False):
    """
    Generate a game image using Gemini API with team logos as context.
    
    Args:
        game_result: Dictionary containing game result data
        filename: Output filename for the generated image
        game_type: Type of game (e.g., "game", "quarterfinal", etc.)
        week: Week number (optional)
        game_number: Game number (optional)
        is_champion: If True, generate a trophy victory image instead of action scene
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load API key
        api_key = load_gemini_api_key()
        
        # Configure old SDK if available
        if GENAI_AVAILABLE:
            genai.configure(api_key=api_key)
        
        # Get teams and determine winner
        team1 = game_result['team1']
        team2 = game_result['team2']
        team1_score = game_result['team1_score']
        team2_score = game_result['team2_score']
        
        # Determine winner and loser
        if team1_score > team2_score:
            winner_team = team1
            loser_team = team2
        elif team2_score > team1_score:
            winner_team = team2
            loser_team = team1
        else:
            # Tie - use team1 as winner by default
            winner_team = team1
            loser_team = team2
        
        # Load logos
        winner_logo = load_logo_image(winner_team)
        loser_logo = load_logo_image(loser_team)
        
        if not winner_logo or not loser_logo:
            print(f"Warning: Could not load logos for {winner_team.name} or {loser_team.name}")
            print("Falling back to text-only prompt")
            winner_logo = None
            loser_logo = None
        
        # Generate prompt - use trophy prompt for champion, otherwise random
        if is_champion:
            # For champion, use trophy victory prompt but keep random style
            style = random.choice(ART_STYLES)
            scenario = random.choice(SCENARIOS)
            action = "celebrating victory"
            prompt = (
                f"Show the team from logo 1 standing on a victory podium holding a championship trophy, "
                f"celebrating their tournament victory, {scenario}, rendered in {style}. "
                f"Make this a triumphant championship moment with confetti, spotlights, and a grand celebration atmosphere. "
                f"The winning team character should be clearly visible holding the trophy on the victory stand."
            )
        else:
            # Generate random prompt with all variations
            prompt, action, style, scenario = generate_random_prompt(winner_team.name, loser_team.name)
        
        try:
            import requests
        except ImportError:
            print("Error: 'requests' library is required for Gemini API image generation.")
            print("Please install it with: pip install requests")
            return False
        
        # Enhanced prompt with explicit instruction to transform logos into characters
        if winner_logo and loser_logo:
            # Convert images to base64 for API
            winner_logo_b64 = image_to_base64(winner_logo)
            loser_logo_b64 = image_to_base64(loser_logo)
            
            # Explicitly instruct to transform logos into characters
            if is_champion:
                # For champion trophy image, only use winner logo
                final_prompt = (
                    f"Here is the winning team logo. Logo 1 represents {winner_team.name}. "
                    f"Transform this logo into a character or figure representing the team. "
                    f"The character should be based on and inspired by the logo design - use the logo's "
                    f"colors, shapes, symbols, and visual elements to create the character. "
                    f"{prompt} "
                    f"The character should clearly represent the team and logo."
                )
            else:
                final_prompt = (
                    f"Here are two team logos. Logo 1 (winner) represents {winner_team.name}. "
                    f"Logo 2 (loser) represents {loser_team.name}. "
                    f"Transform these logos into characters or figures representing each team. "
                    f"The characters should be based on and inspired by the logo designs - use the logo's "
                    f"colors, shapes, symbols, and visual elements to create the characters. "
                    f"Create a character from logo 1 (the winner) {action} a character from logo 2 (the loser), "
                    f"{scenario}, rendered in {style}. "
                    f"The characters should clearly represent their respective teams and logos. "
                    f"Make this scene completely unique and original with dramatic composition. "
                    f"The winning team's character should be clearly victorious and the scene should be dynamic and engaging."
                )
        else:
            # Fallback if logos aren't available - still create characters but without logo context
            if is_champion:
                final_prompt = (
                    f"Create a character representing {winner_team.name} (champion). "
                    f"{prompt} "
                    f"The character should clearly represent the team."
                )
            else:
                final_prompt = (
                    f"Create characters representing {winner_team.name} (winner) and {loser_team.name} (loser). "
                    f"Show the character from {winner_team.name} {action} the character from {loser_team.name}, "
                    f"{scenario}, rendered in {style}. "
                    f"Make this scene completely unique and original with dramatic composition. "
                    f"The winning team's character should be clearly victorious and the scene should be dynamic and engaging."
                )
        
        # Use Gemini API for image generation
        # Try the new SDK approach first (google.genai), then fallback to old SDK, then REST
        try:
            # Method 1: Try new SDK (google.genai) if available
            try:
                from google import genai as new_genai
                from google.genai import types
                
                client = new_genai.Client(api_key=api_key)
                
                # Prepare content parts - convert PIL Images to proper format
                # The new SDK may need images in a specific format
                content_parts = [final_prompt]
                
                if is_champion:
                    # For champion trophy, only use winner logo
                    if winner_logo:
                        # Convert RGBA to RGB if needed
                        if winner_logo.mode == 'RGBA':
                            rgb_logo = Image.new('RGB', winner_logo.size, (255, 255, 255))
                            rgb_logo.paste(winner_logo, mask=winner_logo.split()[3])
                            content_parts.append(rgb_logo)
                        else:
                            content_parts.append(winner_logo)
                elif winner_logo and loser_logo:
                    # Convert PIL Images to RGB if needed
                    for logo in [winner_logo, loser_logo]:
                        if logo.mode == 'RGBA':
                            rgb_logo = Image.new('RGB', logo.size, (255, 255, 255))
                            rgb_logo.paste(logo, mask=logo.split()[3])
                            content_parts.append(rgb_logo)
                        else:
                            content_parts.append(logo)
                
                # Generate content with image-only response
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-image",
                        contents=content_parts,
                        config=types.GenerateContentConfig(
                            response_modalities=['Image']
                        )
                    )
                except Exception as config_error:
                    # If response_modalities config fails, try without it
                    print(f"Note: Image-only response config not supported, trying without: {config_error}")
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-image",
                        contents=content_parts
                    )
                
                # Extract image from response
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            # Skip text parts
                            if hasattr(part, 'text'):
                                continue
                            if hasattr(part, 'inline_data') and part.inline_data:
                                try:
                                    # Decode and save image
                                    image_data = part.inline_data.data
                                    if isinstance(image_data, bytes):
                                        img = Image.open(BytesIO(image_data))
                                    elif isinstance(image_data, str):
                                        # Base64 encoded string
                                        image_data = base64.b64decode(image_data)
                                        img = Image.open(BytesIO(image_data))
                                    else:
                                        continue
                                    img.save(filename)
                                    print(f"✓ Generated image with Gemini (new SDK): {filename}")
                                    print(f"  Prompt used: {final_prompt[:150]}...")
                                    return True
                                except Exception as img_error:
                                    print(f"Error processing image from new SDK: {img_error}")
                                    continue
                
            except ImportError:
                # New SDK not available, try old SDK
                pass
            except Exception as e:
                print(f"New SDK approach failed: {e}")
                # Fall through to old SDK
            
            # Method 2: Try old SDK (google.generativeai)
            if GENAI_AVAILABLE:
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash-image')
                    
                    # Prepare content parts - old SDK accepts PIL Images directly
                    # But we need to ensure they're in RGB mode
                    content_parts = [final_prompt]
                    
                    if is_champion:
                        # For champion trophy, only use winner logo
                        if winner_logo:
                            # Convert RGBA to RGB if needed
                            if winner_logo.mode == 'RGBA':
                                rgb_logo = Image.new('RGB', winner_logo.size, (255, 255, 255))
                                rgb_logo.paste(winner_logo, mask=winner_logo.split()[3])
                                content_parts.append(rgb_logo)
                            else:
                                content_parts.append(winner_logo)
                    elif winner_logo and loser_logo:
                        # Convert PIL Images to RGB if needed
                        for logo in [winner_logo, loser_logo]:
                            if logo.mode == 'RGBA':
                                rgb_logo = Image.new('RGB', logo.size, (255, 255, 255))
                                rgb_logo.paste(logo, mask=logo.split()[3])
                                content_parts.append(rgb_logo)
                            else:
                                content_parts.append(logo)
                    
                    response = model.generate_content(content_parts)
                    
                    # Check if response has image
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                # Check for inline_data with data attribute
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    if hasattr(part.inline_data, 'data'):
                                        # Decode and save image
                                        image_data = part.inline_data.data
                                        if isinstance(image_data, str):
                                            # Base64 string
                                            image_data = base64.b64decode(image_data)
                                        elif isinstance(image_data, bytes):
                                            # Already bytes
                                            pass
                                        else:
                                            continue
                                        img = Image.open(BytesIO(image_data))
                                        img.save(filename)
                                        print(f"✓ Generated image with Gemini (old SDK): {filename}")
                                        print(f"  Prompt used: {final_prompt[:150]}...")
                                        return True
                except Exception as e:
                    print(f"Old SDK approach failed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("Old SDK (google.generativeai) not available, skipping...")
            
            # Method 3: Fallback to REST API
            try:
                import requests
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"
                
                # Prepare the request payload
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": final_prompt
                        }]
                    }],
                    "generation_config": {
                        "response_modalities": ["IMAGE"]
                    }
                }
                
                # If we have logos, add them as image parts
                if is_champion:
                    # For champion trophy, only use winner logo
                    if winner_logo:
                        winner_logo_b64 = image_to_base64(winner_logo)
                        payload["contents"][0]["parts"].append({
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": winner_logo_b64
                            }
                        })
                elif winner_logo and loser_logo:
                    # Convert images to base64
                    winner_logo_b64 = image_to_base64(winner_logo)
                    loser_logo_b64 = image_to_base64(loser_logo)
                    
                    payload["contents"][0]["parts"].extend([
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": winner_logo_b64
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": loser_logo_b64
                            }
                        }
                    ])
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                response = requests.post(url, json=payload, headers=headers)
                
                # If request fails with generation_config, try without it
                if response.status_code != 200 and 'generation_config' in payload:
                    # Remove generation_config and retry
                    payload_without_config = payload.copy()
                    del payload_without_config['generation_config']
                    response = requests.post(url, json=payload_without_config, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check for image in response
                    if 'candidates' in result and len(result['candidates']) > 0:
                        candidate = result['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            for part in candidate['content']['parts']:
                                # Skip text parts, only look for images
                                if 'text' in part:
                                    continue
                                if 'inline_data' in part and 'data' in part['inline_data']:
                                    try:
                                        # Decode base64 image
                                        image_data_str = part['inline_data']['data']
                                        image_data = base64.b64decode(image_data_str)
                                        img = Image.open(BytesIO(image_data))
                                        img.save(filename)
                                        print(f"✓ Generated image with Gemini (REST API): {filename}")
                                        print(f"  Prompt used: {final_prompt[:150]}...")
                                        return True
                                    except Exception as img_error:
                                        print(f"Error decoding image from REST API: {img_error}")
                                        continue
                    
                    # If no image found, print response for debugging
                    print("Warning: Response structure unexpected - no image found in response.")
                    print("Response structure:", list(result.keys()) if isinstance(result, dict) else type(result))
                    if isinstance(result, dict) and 'candidates' in result:
                        print(f"Number of candidates: {len(result['candidates'])}")
                        if len(result['candidates']) > 0 and 'content' in result['candidates'][0]:
                            print(f"Content parts: {len(result['candidates'][0].get('content', {}).get('parts', []))}")
                            for i, part in enumerate(result['candidates'][0].get('content', {}).get('parts', [])):
                                print(f"  Part {i}: {list(part.keys())}")
                else:
                    print(f"API Error: {response.status_code}")
                    print(f"Response: {response.text[:500]}")
                    
            except Exception as e:
                print(f"REST API approach failed: {e}")
            
            print("All image generation methods failed. Please check your API key and model availability.")
            return False
                
        except Exception as e:
            print(f"Error generating image: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"Error generating image with Gemini API: {e}")
        import traceback
        traceback.print_exc()
        return False

