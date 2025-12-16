"""Create preview using actual image generator"""
import game_logic
import image_generator

# Create mock teams with stats
team1 = game_logic.Team("Apex Predators")
team1.overall_advantage = 2
team1.run_advantage = 3
team1.throw_advantage = 1
team1.kick_advantage = -1
team1.wins = 5
team1.losses = 2
team1.points_for = 145
team1.points_against = 120

team2 = game_logic.Team("Vista Vipers")
team2.overall_advantage = -1
team2.run_advantage = 0
team2.throw_advantage = 2
team2.kick_advantage = 1
team2.wins = 3
team2.losses = 4
team2.points_for = 110
team2.points_against = 135

# Create mock game result
team1_detail = game_logic.ScoringDetail()
team1_detail.runs = 8
team1_detail.throws = 5
team1_detail.kicks = 3
team1_detail.cascade_runs = 2
team1_detail.cascade_throws = 1
team1_detail.cascade_kicks = 0

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

# Generate preview image
print("Generating preview image with new design...")
filename = "preview_new_design.png"
success = image_generator.generate_game_image(game_result, filename, game_type="Game", week=3)

if success:
    print(f"✓ Preview image saved as {filename}")
    print("\nThe preview shows:")
    print("- Game Stats: Runs, Throws, Kicks (with cascade indicators)")
    print("- Season Stats: Record (W-L), Points (PF-PA), Point Differential")
    print("- Advantage Stats: Overall, Run, Throw, Kick (color-coded)")
else:
    print("✗ Failed to generate preview image")





