"""Generate a test image with the new modern design"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import config
import game_logic
import image_generator

# Temporarily set logos directory to test_logos for this script
if not os.path.exists('test_logos'):
    os.makedirs('test_logos')

def create_team_logo(filename, primary_color, secondary_color, text):
    """Create a more realistic team logo"""
    size = 400
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw main circle/shield shape
    margin = 30
    draw.ellipse([margin, margin, size - margin, size - margin], 
                fill=primary_color, outline=secondary_color, width=8)
    
    # Add inner accent
    inner_margin = 60
    draw.ellipse([inner_margin, inner_margin, size - inner_margin, size - inner_margin], 
                fill=(0, 0, 0, 0), outline=secondary_color, width=4)
    
    # Add text
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 80)
    except:
        try:
            font = ImageFont.truetype("arialbd.ttf", 80)
        except:
            font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - 10
    
    # Draw text with outline
    for adj in [(2, 2), (-2, 2), (2, -2), (-2, -2), (0, 2), (0, -2), (2, 0), (-2, 0)]:
        draw.text((text_x + adj[0], text_y + adj[1]), text, fill=(0, 0, 0, 200), font=font)
    draw.text((text_x, text_y), text, fill='white', font=font)
    
    img.save(os.path.join('test_logos', filename))
    print(f"Created logo: {filename}")

# Create logos for the teams
create_team_logo('apex_predators_logo.png', (200, 20, 30), (255, 200, 0), 'AP')
create_team_logo('vista_vipers_logo.png', (20, 150, 50), (200, 255, 200), 'VV')

# Save original config and temporarily override
original_logos_dir = config.LOGOS_DIRECTORY
config.LOGOS_DIRECTORY = os.path.abspath('test_logos')

# Create mock game data
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

# Generate the image
output_filename = 'test_modern_game_image.png'
print(f"\nGenerating modern game image: {output_filename}...")
success = image_generator.generate_game_image(
    game_result, 
    output_filename, 
    week=3, 
    game_type="Game"
)

# Restore original config
config.LOGOS_DIRECTORY = original_logos_dir

if success:
    print(f"✓ Successfully generated {output_filename}")
    print(f"  File location: {os.path.abspath(output_filename)}")
    print("\nThe image shows:")
    print("  - Winner's logo (Apex Predators) as translucent background")
    print("  - Glass-morphism team cards with actual logos")
    print("  - Clean modern typography")
    print("  - Small loser logo in bottom right")
else:
    print("✗ Failed to generate image")
    import traceback
    traceback.print_exc()

