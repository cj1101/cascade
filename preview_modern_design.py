"""Preview script to show the new modern design"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont  # type: ignore
import config
import game_logic
import image_generator

# Setup dummy logos if they don't exist
if not os.path.exists('test_logos'):
    os.makedirs('test_logos')

def create_dummy_logo(filename, color, text):
    """Create a simple logo for testing"""
    img = Image.new('RGBA', (400, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw a circle
    draw.ellipse([20, 20, 380, 380], fill=color, outline='white', width=5)
    # Add text
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 60)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text((200 - text_width//2, 200 - text_height//2), text, fill='white', font=font)
    img.save(os.path.join('test_logos', filename))

# Create logos matching the example
create_dummy_logo('apex_predators_logo.png', (220, 20, 60), 'AP')
create_dummy_logo('vista_vipers_logo.png', (60, 180, 75), 'VV')

# Temporarily override config
original_logos_dir = config.LOGOS_DIRECTORY
config.LOGOS_DIRECTORY = 'test_logos'

# Create mock data matching the image description
team1 = game_logic.Team("Apex Predators")
team2 = game_logic.Team("Vista Vipers")

team1_detail = game_logic.ScoringDetail()
team1_detail.runs = 8
team1_detail.throws = 5
team1_detail.kicks = 3
team1_detail.cascade_runs = 2
team1_detail.cascade_throws = 1

team2_detail = game_logic.ScoringDetail()
team2_detail.runs = 5
team2_detail.throws = 7
team2_detail.kicks = 4
team2_detail.cascade_runs = 1
team2_detail.cascade_throws = 2
team2_detail.cascade_kicks = 1

game_result = {
    'team1': team1,
    'team2': team2,
    'team1_score': 32,
    'team2_score': 24,
    'team1_detail': team1_detail,
    'team2_detail': team2_detail,
    'upset': False
}

# Generate image
print("Generating preview of modern design...")
success = image_generator.generate_game_image(game_result, 'preview_modern_design.png', week=3, game_type="Game")

# Restore original config
config.LOGOS_DIRECTORY = original_logos_dir

if success:
    print("✓ Successfully generated preview_modern_design.png")
    print("  This shows the new modern design with:")
    print("  - Winner's logo as translucent background")
    print("  - Glass-morphism team cards")
    print("  - Clean typography with shadows")
    print("  - Small loser logo in bottom right")
else:
    print("✗ Failed to generate image")

