"""Main entry point for Cascade game simulation"""
import game_logic
import image_generator
import instagram_poster
import config

# Try to import Gemini image generator (optional)
try:
    import gemini_image_generator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Note: Gemini image generation not available. Install google-generativeai to use it.")


def main():
    # Get user input for number of round robins
    print("="*60)
    print("CASCADE GAME SIMULATION")
    print("="*60)
    
    while True:
        try:
            num_round_robins = input("\nHow many round robins would you like to play before the tournament? ")
            num_round_robins = int(num_round_robins)
            if num_round_robins > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    
    ROUND_ROBIN_REPETITIONS = num_round_robins
    
    # Ask user if they want to use Gemini API for image generation
    use_gemini = False
    if GEMINI_AVAILABLE:
        print("\n" + "="*60)
        gemini_choice = input("Would you like to use Gemini API for image generation? (y/n): ")
        if gemini_choice.lower() == 'y':
            use_gemini = True
            print("Using Gemini API with random prompts for image generation.")
        else:
            print("Using default PIL-based image generation.")
    
    team_names = [
        "Apex Predators",
        "Vista Vipers",
        "Skybound Storm",
        "Raven's Renegades",
        "Cove Crushers",
        "Ember Enforcers",
        "Pinnacle Pioneers",
        "Evan City Commies"
    ]
    teams = [game_logic.Team(name) for name in team_names]
    
    # Track all generated images by week
    all_images_by_week = {}
    current_week = 1
    # Track upcoming schedule for odds calculation
    upcoming_schedule = {}
    
    repetition_text = "Round Robin" if ROUND_ROBIN_REPETITIONS == 1 else f"Round Robin ({ROUND_ROBIN_REPETITIONS} repetitions)"
    print(f"\n{repetition_text}:")
    for round_robin_num in range(ROUND_ROBIN_REPETITIONS):
        # Generate the full schedule for this round robin to know upcoming matchups
        full_schedule = game_logic.generate_round_robin_schedule(teams)
        max_rounds = config.ROUNDS_PER_ROUND_ROBIN if config.ROUNDS_PER_ROUND_ROBIN else len(full_schedule)
        
        # Store upcoming matchups in the schedule
        for week_offset, matches in enumerate(full_schedule[:max_rounds], 0):
            week = current_week + week_offset
            upcoming_schedule[week] = matches
        
        results, generated_images = game_logic.round_robin(teams, max_rounds=max_rounds, start_week=current_week)
        
        # Generate images for this round robin
        for week, week_data in generated_images.items():
            week_image_files = []
            for filename, game_result in week_data:
                # Check if this is a Gemini artistic photo or a scoreboard
                is_gemini_photo = filename.endswith("_gemini.png")
                
                if is_gemini_photo:
                    # Generate Gemini artistic photo - only if user wants Gemini
                    if use_gemini and GEMINI_AVAILABLE:
                        success = gemini_image_generator.generate_game_image_with_gemini(
                            game_result, filename, game_type="game", week=week, is_champion=False
                        )
                        if not success:
                            print(f"Warning: Gemini artistic photo generation failed for {filename}")
                        else:
                            # Only append if image was successfully generated
                            week_image_files.append(filename)
                    else:
                        # Skip Gemini artistic photo if user said no or Gemini not available
                        print(f"Skipping Gemini artistic photo {filename} (user choice or Gemini not available)")
                        # Don't append skipped images
                else:
                    # Generate scoreboard image
                    if use_gemini:
                        # Use Gemini for scoreboard generation
                        success = gemini_image_generator.generate_game_image_with_gemini(
                            game_result, filename, game_type="game", week=week, is_champion=False
                        )
                        if not success:
                            # Fallback to default if Gemini fails
                            print(f"Gemini generation failed, using default for {filename}")
                            image_generator.generate_game_image(game_result, filename, game_type="game", week=week)
                        # Always append scoreboard (either Gemini or fallback default)
                        week_image_files.append(filename)
                    else:
                        # Use default PIL-based scoreboard
                        image_generator.generate_game_image(game_result, filename, game_type="game", week=week)
                        # Always append scoreboard
                        week_image_files.append(filename)
            
            # Store filenames in tracking dict
            if week not in all_images_by_week:
                all_images_by_week[week] = []
            all_images_by_week[week].extend(week_image_files)
        
        # Update current week for next round robin
        if generated_images:
            current_week = max(generated_images.keys()) + 1
        else:
            # Calculate next week based on number of teams
            num_teams = len(teams)
            weeks_per_round_robin = num_teams - 1 if num_teams % 2 == 0 else num_teams
            current_week += weeks_per_round_robin
    
    repetition_label = "Round Robin" if ROUND_ROBIN_REPETITIONS == 1 else f"{ROUND_ROBIN_REPETITIONS}x Round Robin"
    print(f"\nFinal Standings after {repetition_label}:")
    game_logic.display_standings(teams)
    
    print("\nTournament:")
    quarterfinals, semifinals, final_result, tournament_images = game_logic.tournament(teams)
    
    # Generate tournament images
    tournament_image_files = []
    for filename, game_result in tournament_images:
        # Check if this is a champion trophy image
        is_champion_trophy = "champion_trophy" in filename
        is_gemini_photo = filename.endswith("_gemini.png")
        
        # Determine game type and number from filename
        if "quarterfinal" in filename:
            game_type = "quarterfinal"
            # Extract number from "tournament_quarterfinal_game_X.png" or "tournament_quarterfinal_game_X_gemini.png"
            parts = filename.split("_")
            game_number = int(parts[-2]) if "_gemini" in filename else int(parts[-1].split(".")[0])
        elif "semifinal" in filename:
            game_type = "semifinal"
            # Extract number from "tournament_semifinal_game_X.png" or "tournament_semifinal_game_X_gemini.png"
            parts = filename.split("_")
            game_number = int(parts[-2]) if "_gemini" in filename else int(parts[-1].split(".")[0])
        elif "final" in filename or "champion" in filename:
            game_type = "final"
            # Extract number from "tournament_final_game_X.png" or "tournament_final_game_X_gemini.png"
            if "champion" not in filename:
                parts = filename.split("_")
                game_number = int(parts[-2]) if "_gemini" in filename else int(parts[-1].split(".")[0])
            else:
                game_number = None
        else:
            game_type = "game"
            game_number = None
        
        if is_champion_trophy:
            # Generate champion trophy image with Gemini - only if user wants Gemini
            if use_gemini and GEMINI_AVAILABLE:
                success = gemini_image_generator.generate_game_image_with_gemini(
                    game_result, filename, game_type=game_type, game_number=game_number, is_champion=True
                )
                if not success:
                    print(f"Warning: Champion trophy image generation failed for {filename}")
                else:
                    # Only append if image was successfully generated
                    tournament_image_files.append(filename)
            else:
                print(f"Skipping champion trophy image {filename} (user choice or Gemini not available)")
                # Don't append skipped images
        elif is_gemini_photo:
            # Generate Gemini artistic photo for tournament game - only if user wants Gemini
            if use_gemini and GEMINI_AVAILABLE:
                success = gemini_image_generator.generate_game_image_with_gemini(
                    game_result, filename, game_type=game_type, game_number=game_number, is_champion=False
                )
                if not success:
                    print(f"Warning: Gemini artistic photo generation failed for {filename}")
                else:
                    # Only append if image was successfully generated
                    tournament_image_files.append(filename)
            else:
                print(f"Skipping Gemini artistic photo {filename} (user choice or Gemini not available)")
                # Don't append skipped images
        else:
            # Generate scoreboard image
            if use_gemini:
                # Use Gemini for scoreboard generation
                success = gemini_image_generator.generate_game_image_with_gemini(
                    game_result, filename, game_type=game_type, game_number=game_number, is_champion=False
                )
                if not success:
                    # Fallback to default if Gemini fails
                    print(f"Gemini generation failed, using default for {filename}")
                    image_generator.generate_game_image(game_result, filename, game_type=game_type, game_number=game_number)
                # Always append scoreboard (either Gemini or fallback default)
                tournament_image_files.append(filename)
            else:
                # Use default PIL-based scoreboard
                image_generator.generate_game_image(game_result, filename, game_type=game_type, game_number=game_number)
                # Always append scoreboard
                tournament_image_files.append(filename)
    
    # Add tournament images to a special key (not a week number)
    all_images_by_week['tournament'] = tournament_image_files
    
    print("\nFinal Team Stats:")
    for team in teams:
        print(f"{team}")
    
    # Ask if user wants to post to Instagram
    print("\n" + "="*60)
    post_to_instagram_choice = input("Would you like to post images to Instagram? (y/n): ")
    
    if post_to_instagram_choice.lower() == 'y':
        # Post round robin images by week with teams and schedule for standings/odds
        instagram_poster.post_images_hourly(all_images_by_week, teams=teams, upcoming_schedule=upcoming_schedule)


if __name__ == "__main__":
    main()

