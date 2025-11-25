"""Generate a test image using the actual team logos"""
import os
import sys
import config
import game_logic
import image_generator

# Create mock game data matching the example
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

# Generate the image using actual logos
output_filename = 'test_with_real_logos.png'
print(f"Using logos from: {config.LOGOS_DIRECTORY}")
print(f"Generating image: {output_filename}...")

# Check if logos exist
logo1_path = os.path.join(config.LOGOS_DIRECTORY, team1.get_logo_filename())
logo2_path = os.path.join(config.LOGOS_DIRECTORY, team2.get_logo_filename())
print(f"Team 1 logo: {logo1_path} - {'EXISTS' if os.path.exists(logo1_path) else 'NOT FOUND'}")
print(f"Team 2 logo: {logo2_path} - {'EXISTS' if os.path.exists(logo2_path) else 'NOT FOUND'}")

success = image_generator.generate_game_image(
    game_result, 
    output_filename, 
    week=3, 
    game_type="Game"
)

if success:
    print(f"\n✓ Successfully generated {output_filename}")
    print(f"  File location: {os.path.abspath(output_filename)}")
    print("\nThe image now shows:")
    print("  - Actual team logos in the background and cards")
    print("  - Winner's logo (Apex Predators) as translucent background")
    print("  - Glass-morphism team cards with real logos")
    print("  - Modern clean design")
else:
    print("✗ Failed to generate image")
    import traceback
    traceback.print_exc()

