"""Main entry point for Cascade game simulation - Oracle Cloud Automation"""
import argparse
import sys
import game_logic
import image_generator
import instagram_poster
import config
import scheduler
import os

# Try to import Gemini image generator (optional)
try:
    import gemini_image_generator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    scheduler.logger.warning("Gemini image generation not available. Install google-generativeai to use it.")


def format_game_results_for_caption(week_game_results):
    """
    Format game results for Instagram caption.
    
    Args:
        week_game_results: List of (filename, game_result) tuples
        
    Returns:
        List of formatted strings for the caption
    """
    lines = []
    lines.append("📊 Game Results:")
    
    for filename, game_result in week_game_results:
        # Skip gemini images (they have "_gemini" in the filename)
        if "_gemini" in filename:
            continue
            
        team1 = game_result['team1']
        team2 = game_result['team2']
        team1_score = game_result['team1_score']
        team2_score = game_result['team2_score']
        team1_detail = game_result['team1_detail']
        team2_detail = game_result['team2_detail']
        upset = game_result.get('upset', False)
        
        # Format score line
        upset_emoji = "🔥" if upset else ""
        score_line = f"{team1.name} {team1_score} - {team2_score} {team2.name}"
        if upset:
            score_line += f" {upset_emoji} Upset!"
        lines.append(score_line)
        
        # Format scoring breakdown for team1
        team1_breakdown = []
        if team1_detail.runs > 0:
            cascade_str = f" ({team1_detail.cascade_runs} cascade)" if team1_detail.cascade_runs > 0 else ""
            team1_breakdown.append(f"{team1_detail.runs} Run{'s' if team1_detail.runs != 1 else ''}{cascade_str}")
        if team1_detail.throws > 0:
            cascade_str = f" ({team1_detail.cascade_throws} cascade)" if team1_detail.cascade_throws > 0 else ""
            team1_breakdown.append(f"{team1_detail.throws} Throw{'s' if team1_detail.throws != 1 else ''}{cascade_str}")
        if team1_detail.kicks > 0:
            cascade_str = f" ({team1_detail.cascade_kicks} cascade)" if team1_detail.cascade_kicks > 0 else ""
            team1_breakdown.append(f"{team1_detail.kicks} Kick{'s' if team1_detail.kicks != 1 else ''}{cascade_str}")
        
        if team1_breakdown:
            lines.append(f"  {team1.name}: {', '.join(team1_breakdown)}")
        
        # Format scoring breakdown for team2
        team2_breakdown = []
        if team2_detail.runs > 0:
            cascade_str = f" ({team2_detail.cascade_runs} cascade)" if team2_detail.cascade_runs > 0 else ""
            team2_breakdown.append(f"{team2_detail.runs} Run{'s' if team2_detail.runs != 1 else ''}{cascade_str}")
        if team2_detail.throws > 0:
            cascade_str = f" ({team2_detail.cascade_throws} cascade)" if team2_detail.cascade_throws > 0 else ""
            team2_breakdown.append(f"{team2_detail.throws} Throw{'s' if team2_detail.throws != 1 else ''}{cascade_str}")
        if team2_detail.kicks > 0:
            cascade_str = f" ({team2_detail.cascade_kicks} cascade)" if team2_detail.cascade_kicks > 0 else ""
            team2_breakdown.append(f"{team2_detail.kicks} Kick{'s' if team2_detail.kicks != 1 else ''}{cascade_str}")
        
        if team2_breakdown:
            lines.append(f"  {team2.name}: {', '.join(team2_breakdown)}")
    
    return lines


def run_round_robin_1(skip_wait=False, debug_interval=None):
    """Run first round robin (Friday 1pm EST)"""
    scheduler.logger.info("="*60)
    scheduler.logger.info("CASCADE GAME SIMULATION - ROUND ROBIN 1")
    if skip_wait:
        scheduler.logger.info("Running in IMMEDIATE mode (skipping schedule waits)")
    scheduler.logger.info("="*60)
    
    # Load or create teams
    teams, current_week, _ = scheduler.load_game_state()
    if teams is None:
        teams = scheduler.get_initial_teams()
        current_week = 1
        scheduler.logger.info("Starting fresh round robin 1")
    else:
        scheduler.logger.info(f"Loaded game state: Week {current_week}")
    
    # Save initial team states for standings calculation
    initial_teams = []
    for team in teams:
        initial_team = game_logic.Team(team.name)
        initial_team.overall_advantage = team.overall_advantage
        initial_team.run_advantage = team.run_advantage
        initial_team.throw_advantage = team.throw_advantage
        initial_team.kick_advantage = team.kick_advantage
        initial_teams.append(initial_team)
    
    # Verify credentials
    # Check for META_ACCESS_TOKEN and map to INSTAGRAM_ACCESS_TOKEN if needed
    if 'META_ACCESS_TOKEN' in os.environ and not getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None):
        os.environ['INSTAGRAM_ACCESS_TOKEN'] = os.environ['META_ACCESS_TOKEN']
        # Also update config module if it loaded from env
        config.INSTAGRAM_ACCESS_TOKEN = os.environ['META_ACCESS_TOKEN']
        scheduler.logger.info("Mapped META_ACCESS_TOKEN to INSTAGRAM_ACCESS_TOKEN")
    
    # Check for CASCADIA_ACCESS_TOKEN and map to INSTAGRAM_ACCESS_TOKEN if needed
    if 'CASCADIA_ACCESS_TOKEN' in os.environ and not getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None):
        os.environ['INSTAGRAM_ACCESS_TOKEN'] = os.environ['CASCADIA_ACCESS_TOKEN']
        config.INSTAGRAM_ACCESS_TOKEN = os.environ['CASCADIA_ACCESS_TOKEN']
        scheduler.logger.info("Mapped CASCADIA_ACCESS_TOKEN to INSTAGRAM_ACCESS_TOKEN")
    
    # Check for CASCADIA_ACCOUNT_ID and map to INSTAGRAM_ACCOUNT_ID if needed
    if 'CASCADIA_ACCOUNT_ID' in os.environ and not getattr(config, 'INSTAGRAM_ACCOUNT_ID', None):
        os.environ['INSTAGRAM_ACCOUNT_ID'] = os.environ['CASCADIA_ACCOUNT_ID']
        config.INSTAGRAM_ACCOUNT_ID = os.environ['CASCADIA_ACCOUNT_ID']
        scheduler.logger.info("Mapped CASCADIA_ACCOUNT_ID to INSTAGRAM_ACCOUNT_ID")

    access_token = getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None)
    account_id = getattr(config, 'INSTAGRAM_ACCOUNT_ID', None)
    if not access_token or not account_id:
        scheduler.logger.warning("Instagram Graph API credentials not configured!")
        scheduler.logger.warning("Instagram posts will fail until credentials are configured.")
    else:
        scheduler.logger.info("✓ Instagram Graph API credentials configured")
    
    # Get start time from config (defaults to 1:00 PM EST)
    start_hour = getattr(config, 'ROUND_ROBIN_1_START_HOUR', 13)
    start_minute = getattr(config, 'ROUND_ROBIN_1_START_MINUTE', 0)
    first_match_datetime = scheduler.get_next_fourth_weekend_friday_datetime(start_hour, start_minute)
    
    # Generate full schedule for this round robin
    full_schedule = game_logic.generate_round_robin_schedule(teams)
    max_rounds = config.ROUNDS_PER_ROUND_ROBIN if config.ROUNDS_PER_ROUND_ROBIN else len(full_schedule)
    
    # Track game results by week for standings calculation
    game_results_by_week = {}
    # Track upcoming schedule for odds calculation
    upcoming_schedule = {}
    
    # Process each week one at a time: generate and post on schedule
    for week_offset, matches in enumerate(full_schedule[:max_rounds], 0):
        week = current_week + week_offset
        
        # Calculate and wait for this week's 4th-weekend Friday slot
        match_datetime = scheduler.get_fourth_weekend_friday_at_offset(first_match_datetime, week_offset)
        readable_match_time = match_datetime.strftime("%Y-%m-%d %I:%M %p %Z")
        
        if debug_interval:
            scheduler.wait_for_interval(debug_interval)
        elif not skip_wait:
            scheduler.logger.info(f"Scheduled kickoff: {readable_match_time}")
            scheduler.wait_until_datetime(match_datetime)
        else:
            scheduler.logger.info(f"Skipping wait for {readable_match_time} (IMMEDIATE mode)")
        
        # Store upcoming matchups for odds calculation
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            upcoming_schedule[next_week] = full_schedule[week_offset + 1]
        
        scheduler.logger.info(f"\nWeek {week} (Posting at {readable_match_time}):")
        week_image_files = []
        week_game_results = []
        upsets = []
        
        # Play games for this week
        for game_num, (team1, team2) in enumerate(matches, 1):
            result, upset, game_result = game_logic.play_game(team1, team2)
            scheduler.logger.info(result)
            
            if upset:
                upsets.append(f"{team2.name} (adv: {team2.overall_advantage}) upset {team1.name} (adv: {team1.overall_advantage})")
            
            # Generate scoreboard image
            filename = f"week_{week}_game_{game_num}.png"
            image_generator.generate_game_image(game_result, filename, game_type="game", week=week)
            week_image_files.append(filename)
            week_game_results.append((filename, game_result))
            
            # Generate Gemini artistic photo (always enabled)
            if config.USE_GEMINI and GEMINI_AVAILABLE:
                gemini_filename = f"week_{week}_game_{game_num}_gemini.png"
                success = gemini_image_generator.generate_game_image_with_gemini(
                    game_result, gemini_filename, game_type="game", week=week, is_champion=False
                )
                if success:
                    week_image_files.append(gemini_filename)
                else:
                    scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        
        if upsets:
            scheduler.logger.info("\nUpsets this week:")
            for upset in upsets:
                scheduler.logger.info(upset)
        
        scheduler.logger.info("\nCurrent Standings:")
        game_logic.display_standings(teams)
        
        # Store game results
        game_results_by_week[week] = week_game_results
        
        # Post to Instagram immediately after generating images for this week
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Posting Week {week} to Instagram...")
        scheduler.logger.info(f"{'='*60}")
        
        # Generate caption with game results, standings and next week odds
        caption_parts = [f"Week {week} Game Results"]
        
        # Add detailed game results
        if week_game_results:
            caption_parts.append("")
            game_result_lines = format_game_results_for_caption(week_game_results)
            caption_parts.extend(game_result_lines)
        
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
        success = instagram_poster.post_to_instagram(week_image_files, caption)
        if not success:
            scheduler.logger.warning(f"Failed to post Week {week} images")
            scheduler.logger.info("Continuing to next week automatically...")
    
    # Update current week for next round robin
    num_teams = len(teams)
    weeks_per_round_robin = num_teams - 1 if num_teams % 2 == 0 else num_teams
    new_current_week = current_week + weeks_per_round_robin
    
    # Save state after round robin 1
    scheduler.save_game_state(teams, new_current_week, round_robin_num=1)
    
    scheduler.logger.info(f"\nFinal Standings after Round Robin 1:")
    game_logic.display_standings(teams)
    scheduler.logger.info("Round Robin 1 complete. State saved for Round Robin 2.")


def run_round_robin_2(skip_wait=False, debug_interval=None):
    """Run second round robin (Saturday 1pm EST)"""
    scheduler.logger.info("="*60)
    scheduler.logger.info("CASCADE GAME SIMULATION - ROUND ROBIN 2")
    if skip_wait:
        scheduler.logger.info("Running in IMMEDIATE mode (skipping schedule waits)")
    scheduler.logger.info("="*60)
    
    # Load state from round robin 1
    teams, current_week, _ = scheduler.load_game_state()
    if teams is None:
        scheduler.logger.error("No game state found! Round robin 1 must be run first.")
        sys.exit(1)
    
    scheduler.logger.info(f"Loaded game state: Week {current_week}")
    
    # Get initial teams for standings calculation (from saved state or recreate)
    initial_teams = []
    for team in teams:
        initial_team = game_logic.Team(team.name)
        initial_team.overall_advantage = team.overall_advantage
        initial_team.run_advantage = team.run_advantage
        initial_team.throw_advantage = team.throw_advantage
        initial_team.kick_advantage = team.kick_advantage
        initial_team.wins = team.wins
        initial_team.losses = team.losses
        initial_team.points_for = team.points_for
        initial_team.points_against = team.points_against
        initial_teams.append(initial_team)
    
    # Get start hour from config
    start_hour = getattr(config, 'ROUND_ROBIN_2_START_HOUR', 13)
    
    # Generate full schedule for this round robin
    full_schedule = game_logic.generate_round_robin_schedule(teams)
    max_rounds = config.ROUNDS_PER_ROUND_ROBIN if config.ROUNDS_PER_ROUND_ROBIN else len(full_schedule)
    
    # Track game results by week for standings calculation
    game_results_by_week = {}
    # Track upcoming schedule for odds calculation
    upcoming_schedule = {}
    
    # Process each week one at a time: generate and post on schedule
    for week_offset, matches in enumerate(full_schedule[:max_rounds], 0):
        week = current_week + week_offset
        
        # Calculate posting hour for this week
        posting_hour = scheduler.calculate_next_posting_hour(start_hour, week_offset)
        
        # Wait until scheduled time
        if debug_interval:
            scheduler.wait_for_interval(debug_interval)
        elif not skip_wait:
            scheduler.wait_until_hour(posting_hour)
        else:
            scheduler.logger.info(f"Skipping wait for {posting_hour:02d}:00 EST (IMMEDIATE mode)")
        
        # Store upcoming matchups for odds calculation
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            upcoming_schedule[next_week] = full_schedule[week_offset + 1]
        
        scheduler.logger.info(f"\nWeek {week} (Posting at {posting_hour:02d}:00 EST):")
        week_image_files = []
        week_game_results = []
        upsets = []
        
        # Play games for this week
        for game_num, (team1, team2) in enumerate(matches, 1):
            result, upset, game_result = game_logic.play_game(team1, team2)
            scheduler.logger.info(result)
            
            if upset:
                upsets.append(f"{team2.name} (adv: {team2.overall_advantage}) upset {team1.name} (adv: {team1.overall_advantage})")
            
            # Generate scoreboard image
            filename = f"week_{week}_game_{game_num}.png"
            image_generator.generate_game_image(game_result, filename, game_type="game", week=week)
            week_image_files.append(filename)
            week_game_results.append((filename, game_result))
            
            # Generate Gemini artistic photo (always enabled)
            if config.USE_GEMINI and GEMINI_AVAILABLE:
                gemini_filename = f"week_{week}_game_{game_num}_gemini.png"
                success = gemini_image_generator.generate_game_image_with_gemini(
                    game_result, gemini_filename, game_type="game", week=week, is_champion=False
                )
                if success:
                    week_image_files.append(gemini_filename)
                else:
                    scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        
        if upsets:
            scheduler.logger.info("\nUpsets this week:")
            for upset in upsets:
                scheduler.logger.info(upset)
        
        scheduler.logger.info("\nCurrent Standings:")
        game_logic.display_standings(teams)
        
        # Store game results
        game_results_by_week[week] = week_game_results
        
        # Post to Instagram immediately after generating images for this week
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Posting Week {week} to Instagram...")
        scheduler.logger.info(f"{'='*60}")
        
        # Generate caption with game results, standings and next week odds
        caption_parts = [f"Week {week} Game Results"]
        
        # Add detailed game results
        if week_game_results:
            caption_parts.append("")
            game_result_lines = format_game_results_for_caption(week_game_results)
            caption_parts.extend(game_result_lines)
        
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
        success = instagram_poster.post_to_instagram(week_image_files, caption)
        if not success:
            scheduler.logger.warning(f"Failed to post Week {week} images")
            scheduler.logger.info("Continuing to next week automatically...")
    
    # Update current week for tournament
    num_teams = len(teams)
    weeks_per_round_robin = num_teams - 1 if num_teams % 2 == 0 else num_teams
    new_current_week = current_week + weeks_per_round_robin
    
    # Save state after round robin 2
    scheduler.save_game_state(teams, new_current_week, round_robin_num=2)
    
    scheduler.logger.info(f"\nFinal Standings after Round Robin 2:")
    game_logic.display_standings(teams)
    scheduler.logger.info("Round Robin 2 complete. State saved for Tournament.")


def run_tournament(skip_wait=False, debug_interval=None):
    """Run tournament (Sunday 6pm/7pm/8pm EST)"""
    scheduler.logger.info("="*60)
    scheduler.logger.info("CASCADE GAME SIMULATION - TOURNAMENT")
    if skip_wait:
        scheduler.logger.info("Running in IMMEDIATE mode (skipping schedule waits)")
    scheduler.logger.info("="*60)
    
    # Load state from round robin 2
    teams, current_week, _ = scheduler.load_game_state()
    if teams is None:
        scheduler.logger.error("No game state found! Round robins must be run first.")
        sys.exit(1)
    
    scheduler.logger.info(f"Loaded game state: Week {current_week}")
    
    # Sort teams by wins, then by point difference
    sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
    
    # QUARTERFINALS - Wait until 6pm EST
    quarterfinals_hour = getattr(config, 'TOURNAMENT_QUARTERFINALS_HOUR', 18)
    if debug_interval:
        scheduler.wait_for_interval(debug_interval)
    elif not skip_wait:
        scheduler.logger.info(f"Waiting until {quarterfinals_hour:02d}:00 EST for Quarterfinals...")
        scheduler.wait_until_hour(quarterfinals_hour)
    else:
        scheduler.logger.info(f"Skipping wait for Quarterfinals (IMMEDIATE mode)")
    
    # Generate and post bracket before quarterfinals (showing all 8 teams)
    scheduler.logger.info("\nGenerating tournament bracket (before quarterfinals)...")
    bracket_qf_filename = "tournament_bracket_quarterfinals.png"
    image_generator.generate_tournament_bracket(teams, bracket_qf_filename, round_stage='quarterfinals')
    
    scheduler.logger.info(f"\n{'='*60}")
    scheduler.logger.info("Posting Tournament Bracket - Quarterfinals")
    scheduler.logger.info(f"{'='*60}")
    instagram_poster.post_to_instagram([bracket_qf_filename], "")
    
    # QUARTERFINALS - Generate and post
    scheduler.logger.info("\nQuarterfinals:")
    quarterfinal_winners = []
    quarterfinal_images = []
    quarterfinal_game_results = []
    
    for game_num, game in enumerate([
        (sorted_teams[0], sorted_teams[7]),
        (sorted_teams[1], sorted_teams[6]),
        (sorted_teams[2], sorted_teams[5]),
        (sorted_teams[3], sorted_teams[4])
    ], 1):
        result, upset, game_result = game_logic.play_game(*game)
        scheduler.logger.info(result)
        
        if upset:
            scheduler.logger.info(f"Upset: {game[1].name} (adv: {game[1].overall_advantage}) upset {game[0].name} (adv: {game[0].overall_advantage})")
        
        # Generate scoreboard image
        filename = f"tournament_quarterfinal_game_{game_num}.png"
        image_generator.generate_game_image(game_result, filename, game_type="quarterfinal", game_number=game_num)
        quarterfinal_images.append(filename)
        quarterfinal_game_results.append((filename, game_result))
        
        # Generate Gemini artistic photo if enabled
        if config.USE_GEMINI and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_quarterfinal_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="quarterfinal", game_number=game_num, is_champion=False
            )
            if success:
                quarterfinal_images.append(gemini_filename)
            else:
                scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        quarterfinal_winners.append(winner)
    
    # Post quarterfinals to Instagram
    scheduler.logger.info(f"\n{'='*60}")
    scheduler.logger.info("Posting Quarterfinals to Instagram...")
    scheduler.logger.info(f"{'='*60}")
    caption_parts = ["🏆 Tournament Quarterfinals"]
    if quarterfinal_game_results:
        caption_parts.append("")
        game_result_lines = format_game_results_for_caption(quarterfinal_game_results)
        caption_parts.extend(game_result_lines)
    caption = "\n".join(caption_parts)
    success = instagram_poster.post_to_instagram(quarterfinal_images, caption)
    if not success:
        scheduler.logger.warning("Failed to post quarterfinals images")
    
    # SEMIFINALS - Wait until 7pm EST
    semifinals_hour = getattr(config, 'TOURNAMENT_SEMIFINALS_HOUR', 19)
    if debug_interval:
        scheduler.wait_for_interval(debug_interval)
    elif not skip_wait:
        scheduler.logger.info(f"\nWaiting until {semifinals_hour:02d}:00 EST for Semifinals...")
        scheduler.wait_until_hour(semifinals_hour)
    else:
        scheduler.logger.info(f"Skipping wait for Semifinals (IMMEDIATE mode)")
    
    # Generate and post bracket before semifinals (showing QF winners)
    scheduler.logger.info("\nGenerating tournament bracket (before semifinals)...")
    bracket_sf_filename = "tournament_bracket_semifinals.png"
    image_generator.generate_tournament_bracket(teams, bracket_sf_filename, round_stage='semifinals', quarterfinal_winners=quarterfinal_winners)
    
    scheduler.logger.info(f"\n{'='*60}")
    scheduler.logger.info("Posting Tournament Bracket - Semifinals")
    scheduler.logger.info(f"{'='*60}")
    instagram_poster.post_to_instagram([bracket_sf_filename], "")
    
    # SEMIFINALS - Generate and post
    scheduler.logger.info("\nSemifinals:")
    semifinal_winners = []
    semifinal_images = []
    semifinal_game_results = []
    
    for game_num, game in enumerate([
        (quarterfinal_winners[0], quarterfinal_winners[1]),  # QF1 winner vs QF2 winner
        (quarterfinal_winners[2], quarterfinal_winners[3])   # QF3 winner vs QF4 winner
    ], 1):
        result, upset, game_result = game_logic.play_game(*game)
        scheduler.logger.info(result)
        
        if upset:
            scheduler.logger.info(f"Upset: {game[1].name} (adv: {game[1].overall_advantage}) upset {game[0].name} (adv: {game[0].overall_advantage})")
        
        # Generate scoreboard image
        filename = f"tournament_semifinal_game_{game_num}.png"
        image_generator.generate_game_image(game_result, filename, game_type="semifinal", game_number=game_num)
        semifinal_images.append(filename)
        semifinal_game_results.append((filename, game_result))
        
        # Generate Gemini artistic photo if enabled
        if config.USE_GEMINI and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_semifinal_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="semifinal", game_number=game_num, is_champion=False
            )
            if success:
                semifinal_images.append(gemini_filename)
            else:
                scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        semifinal_winners.append(winner)
    
    # Post semifinals to Instagram
    scheduler.logger.info(f"\n{'='*60}")
    scheduler.logger.info("Posting Semifinals to Instagram...")
    scheduler.logger.info(f"{'='*60}")
    caption_parts = ["🏆 Tournament Semifinals"]
    if semifinal_game_results:
        caption_parts.append("")
        game_result_lines = format_game_results_for_caption(semifinal_game_results)
        caption_parts.extend(game_result_lines)
    caption = "\n".join(caption_parts)
    success = instagram_poster.post_to_instagram(semifinal_images, caption)
    if not success:
        scheduler.logger.warning("Failed to post semifinals images")
    
    # FINALS - Wait until 8pm EST
    finals_hour = getattr(config, 'TOURNAMENT_FINALS_HOUR', 20)
    if debug_interval:
        scheduler.wait_for_interval(debug_interval)
    elif not skip_wait:
        scheduler.logger.info(f"\nWaiting until {finals_hour:02d}:00 EST for Finals...")
        scheduler.wait_until_hour(finals_hour)
    else:
        scheduler.logger.info(f"Skipping wait for Finals (IMMEDIATE mode)")
    
    # Generate and post bracket before finals (showing SF winners)
    scheduler.logger.info("\nGenerating tournament bracket (before finals)...")
    bracket_finals_filename = "tournament_bracket_finals.png"
    image_generator.generate_tournament_bracket(teams, bracket_finals_filename, round_stage='finals', semifinal_winners=semifinal_winners)
    
    scheduler.logger.info(f"\n{'='*60}")
    scheduler.logger.info("Posting Tournament Bracket - Finals")
    scheduler.logger.info(f"{'='*60}")
    instagram_poster.post_to_instagram([bracket_finals_filename], "")
    
    # FINALS - Best 2 out of 3, generate and post after each game
    scheduler.logger.info("\nFinal (Best 2 out of 3):")
    team1, team2 = semifinal_winners[0], semifinal_winners[1]
    
    team1_wins = 0
    team2_wins = 0
    game_num = 1
    last_game_result = None  # Store last game result for trophy image
    
    while team1_wins < 2 and team2_wins < 2:
        scheduler.logger.info(f"\nGame {game_num}:")
        result, upset, game_result = game_logic.play_game(team1, team2)
        scheduler.logger.info(result)
        last_game_result = game_result  # Keep track of last game result
        
        # Determine winner of this game
        if game_result['team1_score'] > game_result['team2_score']:
            team1_wins += 1
            winner = team1
        else:
            team2_wins += 1
            winner = team2
        
        if upset:
            scheduler.logger.info(f"Upset: {winner.name} (adv: {winner.overall_advantage}) upset {team2.name if winner == team1 else team1.name} (adv: {(team2 if winner == team1 else team1).overall_advantage})")
        
        scheduler.logger.info(f"Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}")
        
        # Generate scoreboard image
        filename = f"tournament_final_game_{game_num}.png"
        image_generator.generate_game_image(game_result, filename, game_type="final", game_number=game_num)
        final_game_images = [filename]
        
        # Generate Gemini artistic photo if enabled
        if config.USE_GEMINI and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_final_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="final", game_number=game_num, is_champion=False
            )
            if success:
                final_game_images.append(gemini_filename)
            else:
                scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        
        # Post this final game to Instagram immediately
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Posting Final Game {game_num} to Instagram...")
        scheduler.logger.info(f"{'='*60}")
        caption_parts = [f"🏆 Tournament Final - Game {game_num}"]
        caption_parts.append(f"Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}")
        # Add detailed game results
        game_result_lines = format_game_results_for_caption([(filename, game_result)])
        caption_parts.append("")
        caption_parts.extend(game_result_lines)
        caption = "\n".join(caption_parts)
        success = instagram_poster.post_to_instagram(final_game_images, caption)
        if not success:
            scheduler.logger.warning(f"Failed to post final game {game_num} images")
        
        game_num += 1
    
    # Determine tournament champion
    if team1_wins == 2:
        champion = team1
    else:
        champion = team2
    
    scheduler.logger.info(f"\n{'='*60}")
    scheduler.logger.info(f"🏆 TOURNAMENT CHAMPION: {champion.name} 🏆")
    scheduler.logger.info(f"Final Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}")
    scheduler.logger.info(f"{'='*60}")
    
    # Generate and post champion trophy image
    if config.USE_GEMINI and GEMINI_AVAILABLE and last_game_result:
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
        
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info("Generating Champion Trophy Image...")
        scheduler.logger.info(f"{'='*60}")
        
        success = gemini_image_generator.generate_game_image_with_gemini(
            trophy_game_result, trophy_filename, game_type="final", game_number=None, is_champion=True
        )
        
        if success:
            scheduler.logger.info(f"\n{'='*60}")
            scheduler.logger.info("Posting Champion Trophy to Instagram...")
            scheduler.logger.info(f"{'='*60}")
            caption = f"🏆 TOURNAMENT CHAMPION: {champion.name} 🏆\nFinal Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}"
            instagram_poster.post_to_instagram([trophy_filename], caption)
        else:
            scheduler.logger.warning("Champion trophy image generation failed")
    
    scheduler.logger.info("\nFinal Team Stats:")
    for team in teams:
        scheduler.logger.info(f"{team}")
    
    scheduler.logger.info("\nTournament complete!")


def main():
    """Main entry point with command-line argument parsing"""
    parser = argparse.ArgumentParser(description='Cascade Game Simulation - Oracle Cloud Automation')
    parser.add_argument('--mode', type=str, required=True,
                       choices=['round_robin_1', 'round_robin_2', 'tournament'],
                       help='Execution mode: round_robin_1 (Friday), round_robin_2 (Saturday), or tournament (Sunday)')
    parser.add_argument('--now', action='store_true', help='Run immediately without waiting for schedule')
    parser.add_argument('--debug-interval', type=int, help='Debug mode: wait interval in minutes between stages')
    
    args = parser.parse_args()
    
    if args.mode == 'round_robin_1':
        run_round_robin_1(skip_wait=args.now, debug_interval=args.debug_interval)
    elif args.mode == 'round_robin_2':
        run_round_robin_2(skip_wait=args.now, debug_interval=args.debug_interval)
    elif args.mode == 'tournament':
        run_tournament(skip_wait=args.now, debug_interval=args.debug_interval)
    else:
        parser.error(f"Invalid mode: {args.mode}")


if __name__ == "__main__":
    main()
