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
        "Evan City Vanguards"
    ]
    teams = [game_logic.Team(name) for name in team_names]
    
    # Save initial team states (before any games) for standings calculation
    initial_teams = []
    for team in teams:
        initial_team = game_logic.Team(team.name)
        initial_team.overall_advantage = team.overall_advantage
        initial_team.run_advantage = team.run_advantage
        initial_team.throw_advantage = team.throw_advantage
        initial_team.kick_advantage = team.kick_advantage
        initial_teams.append(initial_team)
    
    # Track all generated images by week
    all_images_by_week = {}
    # Track game results by week for standings calculation
    game_results_by_week = {}
    current_week = 1
    # Track upcoming schedule for odds calculation
    upcoming_schedule = {}
    
    repetition_text = "Round Robin" if ROUND_ROBIN_REPETITIONS == 1 else f"Round Robin ({ROUND_ROBIN_REPETITIONS} repetitions)"
    print(f"\n{repetition_text}:")
    
    driver = None
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import time
        
        # Create browser once at the start
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("detach", True)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Login once at the start
        username = config.INSTAGRAM_USERNAME
        password = config.INSTAGRAM_PASSWORD
        login_success = instagram_poster.login_to_instagram(driver, username, password)
        if not login_success:
            # Manual login prompt...
            print(f"Please log in to Instagram manually. Enter 'y' once logged in to continue.")
            input("Press Enter once logged in...")
        
        print("Browser session initialized. It will remain open for all posts.")
        
    except Exception as e:
        print(f"Could not initialize browser: {e}")
        driver = None

    for round_robin_num in range(ROUND_ROBIN_REPETITIONS):
        # Generate the full schedule for this round robin
        full_schedule = game_logic.generate_round_robin_schedule(teams)
        max_rounds = config.ROUNDS_PER_ROUND_ROBIN if config.ROUNDS_PER_ROUND_ROBIN else len(full_schedule)
        
        # Process each week one at a time: generate images and post immediately
        for week_offset, matches in enumerate(full_schedule[:max_rounds], 0):
            week = current_week + week_offset
            
            # Store upcoming matchups for odds calculation
            if week_offset + 1 < len(full_schedule[:max_rounds]):
                next_week = current_week + week_offset + 1
                upcoming_schedule[next_week] = full_schedule[week_offset + 1]
            
            print(f"\nWeek {week}:")
            week_image_files = []
            week_game_results = []
            upsets = []
            
            # Play games for this week
            for game_num, (team1, team2) in enumerate(matches, 1):
                result, upset, game_result = game_logic.play_game(team1, team2)
                print(result)
                
                if upset:
                    upsets.append(f"{team2.name} (adv: {team2.overall_advantage}) upset {team1.name} (adv: {team1.overall_advantage})")
                
                # Generate scoreboard image
                filename = f"week_{week}_game_{game_num}.png"
                image_generator.generate_game_image(game_result, filename, game_type="game", week=week)
                week_image_files.append(filename)
                week_game_results.append((filename, game_result))
                
                # Generate Gemini artistic photo if enabled
                if use_gemini and GEMINI_AVAILABLE:
                    gemini_filename = f"week_{week}_game_{game_num}_gemini.png"
                    success = gemini_image_generator.generate_game_image_with_gemini(
                        game_result, gemini_filename, game_type="game", week=week, is_champion=False
                    )
                    if success:
                        week_image_files.append(gemini_filename)
                    else:
                        print(f"Warning: Gemini artistic photo generation failed for {gemini_filename}")
            
            if upsets:
                print("\nUpsets this week:")
                for upset in upsets:
                    print(upset)
            
            print("\nCurrent Standings:")
            game_logic.display_standings(teams)
            
            # Store images and game results
            all_images_by_week[week] = week_image_files
            game_results_by_week[week] = week_game_results
            
            # Post to Instagram immediately after generating images for this week
            print(f"\n{'='*60}")
            print(f"Posting Week {week} to Instagram...")
            print(f"{'='*60}")
            
            # Generate caption with standings and next week odds
            caption_parts = [f"Week {week} Game Results"]
            
            # Add current standings (only up to current week)
            if initial_teams and game_results_by_week:
                caption_parts.append("")
                caption_parts.append("Current Standings:")
                standings = game_logic.calculate_standings_up_to_week(initial_teams, game_results_by_week, week)
                caption_parts.append(standings)
            
            # Add odds for next week's matchups
            next_week = week + 1
            if upcoming_schedule and next_week in upcoming_schedule and teams:
                caption_parts.append("")
                caption_parts.append(f"Odds for Week {next_week}:")
                matchups = upcoming_schedule[next_week]
                for team1, team2 in matchups:
                    odds1, odds2 = game_logic.calculate_matchup_odds(team1, team2)
                    odds1_str = f"+{odds1}" if odds1 > 0 else str(odds1)
                    odds2_str = f"+{odds2}" if odds2 > 0 else str(odds2)
                    caption_parts.append(f"{team1.name} vs {team2.name}: {team1.name} {odds1_str}, {team2.name} {odds2_str}")
            
            caption = "\n".join(caption_parts)
            
            # Post all images for this week as a single carousel/gallery post
            success = instagram_poster.post_to_instagram(week_image_files, caption, driver=driver)
            if not success:
                print(f"Warning: Failed to post Week {week} images")
                response = input("Continue to next week? (y/n): ")
                if response.lower() != 'y':
                    break
        
        # Update current week for next round robin
        num_teams = len(teams)
        weeks_per_round_robin = num_teams - 1 if num_teams % 2 == 0 else num_teams
        current_week += weeks_per_round_robin
    
    repetition_label = "Round Robin" if ROUND_ROBIN_REPETITIONS == 1 else f"{ROUND_ROBIN_REPETITIONS}x Round Robin"
    print(f"\nFinal Standings after {repetition_label}:")
    game_logic.display_standings(teams)
    
    print("\nTournament:")
    
    # Sort teams by wins, then by point difference
    sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
    
    # Generate and post bracket before quarterfinals (showing all 8 teams)
    print("\nGenerating tournament bracket (before quarterfinals)...")
    bracket_qf_filename = "tournament_bracket_quarterfinals.png"
    image_generator.generate_tournament_bracket(teams, bracket_qf_filename, round_stage='quarterfinals')
    
    print(f"\n{'='*60}")
    print("Posting Tournament Bracket - Quarterfinals")
    print(f"{'='*60}")
    instagram_poster.post_to_instagram([bracket_qf_filename], "", driver=driver)
    
    # QUARTERFINALS - Generate and post
    print("\nQuarterfinals:")
    quarterfinal_winners = []
    quarterfinal_images = []
    
    for game_num, game in enumerate([
        (sorted_teams[0], sorted_teams[7]),
        (sorted_teams[1], sorted_teams[6]),
        (sorted_teams[2], sorted_teams[5]),
        (sorted_teams[3], sorted_teams[4])
    ], 1):
        result, upset, game_result = game_logic.play_game(*game)
        print(result)
        
        if upset:
            print(f"Upset: {game[1].name} (adv: {game[1].overall_advantage}) upset {game[0].name} (adv: {game[0].overall_advantage})")
        
        # Generate scoreboard image
        filename = f"tournament_quarterfinal_game_{game_num}.png"
        image_generator.generate_game_image(game_result, filename, game_type="quarterfinal", game_number=game_num)
        quarterfinal_images.append(filename)
        
        # Generate Gemini artistic photo if enabled
        if use_gemini and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_quarterfinal_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="quarterfinal", game_number=game_num, is_champion=False
            )
            if success:
                quarterfinal_images.append(gemini_filename)
            else:
                print(f"Warning: Gemini artistic photo generation failed for {gemini_filename}")
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        quarterfinal_winners.append(winner)
    
    # Post quarterfinals to Instagram
    print(f"\n{'='*60}")
    print("Posting Quarterfinals to Instagram...")
    print(f"{'='*60}")
    caption = "Tournament Quarterfinals"
    success = instagram_poster.post_to_instagram(quarterfinal_images, caption, driver=driver)
    if not success:
        print("Warning: Failed to post quarterfinals images")
    
    # Generate and post bracket before semifinals (showing QF winners)
    print("\nGenerating tournament bracket (before semifinals)...")
    bracket_sf_filename = "tournament_bracket_semifinals.png"
    image_generator.generate_tournament_bracket(teams, bracket_sf_filename, round_stage='semifinals', quarterfinal_winners=quarterfinal_winners)
    
    print(f"\n{'='*60}")
    print("Posting Tournament Bracket - Semifinals")
    print(f"{'='*60}")
    instagram_poster.post_to_instagram([bracket_sf_filename], "", driver=driver)
    
    # SEMIFINALS - Generate and post
    print("\nSemifinals:")
    semifinal_winners = []
    semifinal_images = []
    
    for game_num, game in enumerate([
        (quarterfinal_winners[0], quarterfinal_winners[1]),  # QF1 winner vs QF2 winner
        (quarterfinal_winners[2], quarterfinal_winners[3])   # QF3 winner vs QF4 winner
    ], 1):
        result, upset, game_result = game_logic.play_game(*game)
        print(result)
        
        if upset:
            print(f"Upset: {game[1].name} (adv: {game[1].overall_advantage}) upset {game[0].name} (adv: {game[0].overall_advantage})")
        
        # Generate scoreboard image
        filename = f"tournament_semifinal_game_{game_num}.png"
        image_generator.generate_game_image(game_result, filename, game_type="semifinal", game_number=game_num)
        semifinal_images.append(filename)
        
        # Generate Gemini artistic photo if enabled
        if use_gemini and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_semifinal_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="semifinal", game_number=game_num, is_champion=False
            )
            if success:
                semifinal_images.append(gemini_filename)
            else:
                print(f"Warning: Gemini artistic photo generation failed for {gemini_filename}")
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        semifinal_winners.append(winner)
    
    # Generate bracket before finals (showing SF winners)
    print("\nGenerating tournament bracket (before finals)...")
    bracket_finals_filename = "tournament_bracket_finals.png"
    image_generator.generate_tournament_bracket(teams, bracket_finals_filename, round_stage='finals', semifinal_winners=semifinal_winners)
    # Store bracket image to be posted before finals
    if 'bracket_finals' not in all_images_by_week:
        all_images_by_week['bracket_finals'] = []
    all_images_by_week['bracket_finals'].append(bracket_finals_filename)
    
    # Post semifinals to Instagram
    print(f"\n{'='*60}")
    print("Posting Semifinals to Instagram...")
    print(f"{'='*60}")
    caption = "Tournament Semifinals"
    success = instagram_poster.post_to_instagram(semifinal_images, caption, driver=driver)
    if not success:
        print("Warning: Failed to post semifinals images")
    
    # Generate and post bracket before finals (showing SF winners)
    print("\nGenerating tournament bracket (before finals)...")
    bracket_finals_filename = "tournament_bracket_finals.png"
    image_generator.generate_tournament_bracket(teams, bracket_finals_filename, round_stage='finals', semifinal_winners=semifinal_winners)
    
    print(f"\n{'='*60}")
    print("Posting Tournament Bracket - Finals")
    print(f"{'='*60}")
    instagram_poster.post_to_instagram([bracket_finals_filename], "", driver=driver)
    
    # FINALS - Best 2 out of 3, generate and post after each game
    print("\nFinal (Best 2 out of 3):")
    team1, team2 = semifinal_winners[0], semifinal_winners[1]
    
    team1_wins = 0
    team2_wins = 0
    game_num = 1
    last_game_result = None  # Store last game result for trophy image
    
    while team1_wins < 2 and team2_wins < 2:
        print(f"\nGame {game_num}:")
        result, upset, game_result = game_logic.play_game(team1, team2)
        print(result)
        last_game_result = game_result  # Keep track of last game result
        
        # Determine winner of this game
        if game_result['team1_score'] > game_result['team2_score']:
            team1_wins += 1
            winner = team1
        else:
            team2_wins += 1
            winner = team2
        
        if upset:
            print(f"Upset: {winner.name} (adv: {winner.overall_advantage}) upset {team2.name if winner == team1 else team1.name} (adv: {(team2 if winner == team1 else team1).overall_advantage})")
        
        print(f"Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}")
        
        # Generate scoreboard image
        filename = f"tournament_final_game_{game_num}.png"
        image_generator.generate_game_image(game_result, filename, game_type="final", game_number=game_num)
        final_game_images = [filename]
        
        # Generate Gemini artistic photo if enabled
        if use_gemini and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_final_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="final", game_number=game_num, is_champion=False
            )
            if success:
                final_game_images.append(gemini_filename)
            else:
                print(f"Warning: Gemini artistic photo generation failed for {gemini_filename}")
        
        # Post this final game to Instagram immediately
        print(f"\n{'='*60}")
        print(f"Posting Final Game {game_num} to Instagram...")
        print(f"{'='*60}")
        caption = f"Tournament Final - Game {game_num}\nSeries: {team1.name} {team1_wins} - {team2_wins} {team2.name}"
        success = instagram_poster.post_to_instagram(final_game_images, caption, driver=driver)
        if not success:
            print(f"Warning: Failed to post final game {game_num} images")
        
        game_num += 1
    
    # Determine tournament champion
    if team1_wins == 2:
        champion = team1
    else:
        champion = team2
    
    print(f"\n{'='*60}")
    print(f"🏆 TOURNAMENT CHAMPION: {champion.name} 🏆")
    print(f"Final Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}")
    print(f"{'='*60}")
    
    # Generate and post champion trophy image
    if use_gemini and GEMINI_AVAILABLE and last_game_result:
        # Use the last game result as the base for trophy
        trophy_filename = "tournament_champion_trophy.png"
        trophy_game_result = {
            'team1': team1,
            'team2': team2,
            'team1_score': last_game_result['team1_score'],
            'team2_score': last_game_result['team2_score'],
            'team1_detail': last_game_result['team1_detail'],
            'team2_detail': last_game_result['team2_detail'],
            'upset': last_game_result.get('upset', False),
            'is_champion': True
        }
        
        print(f"\n{'='*60}")
        print("Generating Champion Trophy Image...")
        print(f"{'='*60}")
        
        success = gemini_image_generator.generate_game_image_with_gemini(
            trophy_game_result, trophy_filename, game_type="final", game_number=None, is_champion=True
        )
        
        if success:
            print(f"\n{'='*60}")
            print("Posting Champion Trophy to Instagram...")
            print(f"{'='*60}")
            caption = f"🏆 TOURNAMENT CHAMPION: {champion.name} 🏆\nFinal Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}"
            instagram_poster.post_to_instagram([trophy_filename], caption, driver=driver)
        else:
            print("Warning: Champion trophy image generation failed")
    
    print("\nFinal Team Stats:")
    for team in teams:
        print(f"{team}")

    if driver:
        driver.quit()


if __name__ == "__main__":
    main()

