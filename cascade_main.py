"""Main entry point for Cascade game simulation - Oracle Cloud Automation"""
import argparse
import sys
import logging
import threading
import webbrowser
import game_logic
import image_generator
import instagram_poster
import config
import scheduler
import os
import webapp_bridge
import simulation_status
import atexit
import signal
import glob

# Configure root logger to ensure output is visible
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Try to import Gemini image generator (optional)
try:
    import gemini_image_generator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    scheduler.logger.warning("Gemini image generation not available. Install google-generativeai to use it.")

# Try to import podcast generation modules (optional)
try:
    import podcast_rulebook_reader
    import podcast_audio_generator
    PODCAST_AVAILABLE = True
except ImportError:
    PODCAST_AVAILABLE = False
    scheduler.logger.warning("Podcast generation not available. Install required packages (pdfplumber, gtts, pydub) to use it.")


def validate_imports(enable_podcast=False, enable_gemini=False):
    """
    Validate that required modules are available based on enabled features.
    Raises ImportError if a required feature is missing dependencies.
    """
    if enable_podcast and not PODCAST_AVAILABLE:
        raise ImportError(
            "Podcast generation is enabled but dependencies are missing. "
            "Please install required packages (pdfplumber, gtts, pydub) or use --no-podcast."
        )

    if enable_gemini and not GEMINI_AVAILABLE:
        raise ImportError(
            "Gemini image generation is enabled but google-generativeai is missing. "
            "Please install it or use --no-gemini."
        )


# Flag to ensure exit cleanup only runs once
_cleanup_done = False


def _cleanup_podcasts_directory():
    """
    Internal function to delete all podcast files and script files from the podcasts directory.
    This can be called multiple times (e.g., at startup and on exit).
    """
    try:
        podcasts_dir = "podcasts"
        if not os.path.exists(podcasts_dir):
            scheduler.logger.debug(f"Podcasts directory '{podcasts_dir}' does not exist, skipping cleanup")
            return
        
        # Find all files in the podcasts directory
        podcast_files = glob.glob(os.path.join(podcasts_dir, "*"))
        deleted_count = 0
        
        for file_path in podcast_files:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    scheduler.logger.debug(f"Deleted: {file_path}")
            except Exception as e:
                scheduler.logger.warning(f"Failed to delete {file_path}: {e}")
        
        if deleted_count > 0:
            scheduler.logger.info(f"Cleaned up {deleted_count} podcast/script file(s) from {podcasts_dir}/")
        else:
            scheduler.logger.debug(f"No files to clean up in {podcasts_dir}/")
            
    except Exception as e:
        scheduler.logger.error(f"Error during cleanup of podcasts and scripts: {e}", exc_info=True)


def cleanup_podcasts_and_scripts():
    """
    Delete all podcast files and script files from the podcasts directory.
    This function is registered to run on program exit.
    """
    global _cleanup_done
    if _cleanup_done:
        return
    
    _cleanup_done = True
    _cleanup_podcasts_directory()


def _signal_handler(signum, frame):
    """Handle termination signals (SIGINT, SIGTERM)"""
    scheduler.logger.info(f"Received signal {signum}, cleaning up...")
    cleanup_podcasts_and_scripts()
    sys.exit(0)


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
        
        # Check for injured players in team 1
        team1_player_stats = game_result.get('team1_player_stats', {})
        injured_players_team1 = []
        for player_id, stats in team1_player_stats.items():
            if stats.get('injured', False):
                player_name = stats.get('player_name', player_id)
                if stats.get('injured_during_game', False):
                    injured_players_team1.append(f"{player_name} (injured during game)")
                else:
                    injured_players_team1.append(f"{player_name} (playing injured)")
        if injured_players_team1:
            lines.append(f"  ⚠️ {team1.name} Injuries: {', '.join(injured_players_team1)}")
        
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
        
        # Check for injured players in team 2
        team2_player_stats = game_result.get('team2_player_stats', {})
        injured_players_team2 = []
        for player_id, stats in team2_player_stats.items():
            if stats.get('injured', False):
                player_name = stats.get('player_name', player_id)
                if stats.get('injured_during_game', False):
                    injured_players_team2.append(f"{player_name} (injured during game)")
                else:
                    injured_players_team2.append(f"{player_name} (playing injured)")
        if injured_players_team2:
            lines.append(f"  ⚠️ {team2.name} Injuries: {', '.join(injured_players_team2)}")
    
    return lines


def _precalculate_betting_lines_threaded(season_id, week):
    """
    Wrapper function for pre-calculating betting lines in a background thread.
    This function handles errors gracefully so they don't break the simulation.
    """
    try:
        scheduler.logger.info(f"Starting background thread to pre-calculate betting lines for Week {week}...")
        webapp_bridge.precalculate_betting_lines_for_week(season_id, week)
        scheduler.logger.info(f"Background betting lines calculation for Week {week} completed")
    except Exception as e:
        scheduler.logger.error(f"Error in background betting lines calculation for Week {week}: {e}", exc_info=True)


def _generate_all_images_for_week(week, week_game_results, enable_gemini_images, result_dict, season_id=None, season_folder=None):
    """
    Generate all images for a week (scoreboard + gemini if enabled).
    This function is designed to run in a thread.
    
    Args:
        week: Week number
        week_game_results: List of (filename, game_result) tuples
        enable_gemini_images: Whether to generate Gemini images
        result_dict: Dictionary to store results {'image_files': [], 'error': None}
        season_id: Optional season ID for updating Game records
        season_folder: Optional season folder name (e.g., "season_3") for saving Gemini images
    """
    try:
        scheduler.logger.info(f"Generating all images for Week {week}...")
        week_image_files = []
        
        for game_num, item in enumerate(week_game_results, 1):
            # Unpack the tuple (filename, game_result)
            filename, game_result = item
            
            # Generate scoreboard image
            image_filename = f"week_{week}_game_{game_num}.png"
            image_generator.generate_game_image(game_result, image_filename, game_type="game", week=week, season_id=season_id)
            week_image_files.append(image_filename)
            
            # Post to Instagram Stories if enabled
            if config.ENABLE_INSTAGRAM_STORIES:
                try:
                    stories_filename = image_filename.replace('.png', '_stories.png')
                    if os.path.exists(stories_filename):
                        import instagram_poster
                        success = instagram_poster.post_story_to_instagram(stories_filename)
                        if success:
                            scheduler.logger.info(f"Posted {stories_filename} to Instagram Stories")
                        else:
                            scheduler.logger.warning(f"Failed to post {stories_filename} to Instagram Stories")
                except Exception as stories_error:
                    scheduler.logger.warning(f"Error posting to Instagram Stories: {stories_error}")
            
            # Generate Gemini artistic photo (if enabled)
            if enable_gemini_images and config.USE_GEMINI and GEMINI_AVAILABLE:
                gemini_filename = f"week_{week}_game_{game_num}_gemini.png"
                success = gemini_image_generator.generate_game_image_with_gemini(
                    game_result, gemini_filename, game_type="game", week=week, is_champion=False, season_folder=season_folder
                )
                if success:
                    week_image_files.append(gemini_filename)
                    
                    # Update Game record with gemini_image_path if season info is available
                    if season_id and season_folder:
                        try:
                            # Construct relative path (e.g., "season_3/week_1_game_1_gemini.png")
                            gemini_image_path = f"{season_folder}/{gemini_filename}"
                            team1_name = game_result['team1'].name
                            team2_name = game_result['team2'].name
                            webapp_bridge.update_game_gemini_image(
                                season_id, week, game_num, gemini_image_path,
                                team1_name=team1_name, team2_name=team2_name
                            )
                        except Exception as update_error:
                            scheduler.logger.warning(f"Failed to update Game record with gemini_image_path: {update_error}")
                else:
                    scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
            elif not enable_gemini_images:
                scheduler.logger.debug("Gemini image generation disabled - skipping")
        
        result_dict['image_files'] = week_image_files
        scheduler.logger.info(f"Successfully generated {len(week_image_files)} images for Week {week}")
    except Exception as e:
        scheduler.logger.error(f"Error generating images for Week {week}: {e}", exc_info=True)
        result_dict['error'] = str(e)


def _generate_all_scripts_and_podcasts(week, game_results_by_week, rulebook_text, enable_podcast, result_dict):
    """
    Generate all scripts and podcasts for a week.
    This function is designed to run in a thread.
    
    Args:
        week: Week number
        game_results_by_week: Dict mapping week numbers to game results
        rulebook_text: Text from rulebook
        enable_podcast: Whether to generate podcasts
        result_dict: Dictionary to store results {'success': bool, 'error': None}
    """
    try:
        if not enable_podcast or not PODCAST_AVAILABLE:
            scheduler.logger.debug("Podcast generation disabled or not available - skipping")
            result_dict['success'] = True
            return
        
        scheduler.logger.info(f"Generating scripts and podcasts for Week {week}...")
        
        # Generate podcast
        podcast_success = podcast_audio_generator.generate_week_podcast(
            game_results_by_week, week, rulebook_text
        )
        
        if podcast_success:
            scheduler.logger.info(f"Successfully generated scripts and podcasts for Week {week}")
            result_dict['success'] = True
        else:
            scheduler.logger.warning(f"Failed to generate scripts and podcasts for Week {week}")
            result_dict['success'] = False
            result_dict['error'] = "Podcast generation returned False"
    except Exception as e:
        scheduler.logger.error(f"Error generating scripts and podcasts for Week {week}: {e}", exc_info=True)
        result_dict['success'] = False
        result_dict['error'] = str(e)


def _create_meta_post(week, week_game_results, week_image_files, teams, game_results_by_week, 
                      upcoming_schedule, initial_teams, enable_instagram):
    """
    Create and post the complete meta post for a week.
    
    Args:
        week: Week number
        week_game_results: List of (filename, game_result) tuples
        week_image_files: List of image filenames
        teams: List of team objects
        game_results_by_week: Dict mapping week numbers to game results
        upcoming_schedule: Dict mapping week numbers to matchups
        initial_teams: Initial teams list for standings calculation
        enable_instagram: Whether to post to Instagram
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not enable_instagram:
        scheduler.logger.info(f"\nInstagram posting disabled - skipping Week {week} meta post")
        return True
    
    try:
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Creating and posting meta post for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Generate comprehensive caption
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
        
        # Sort image order by game number (keeping scoreboard before gemini pairs)
        randomized_images = instagram_poster.sort_image_pairs_by_game_number(week_image_files)
        
        # Post all images for this week as a single carousel/gallery post
        success = instagram_poster.post_to_instagram(randomized_images, caption)
        if not success:
            scheduler.logger.warning(f"Failed to post Week {week} meta post")
            return False
        
        scheduler.logger.info(f"Successfully posted meta post for Week {week}")
        return True
    except Exception as e:
        scheduler.logger.error(f"Error creating meta post for Week {week}: {e}", exc_info=True)
        return False


def _open_website():
    """
    Open the website in the default browser.
    """
    try:
        url = "http://localhost:5000"
        scheduler.logger.info(f"Opening website: {url}")
        webbrowser.open(url)
        scheduler.logger.info("Website opened successfully")
    except Exception as e:
        scheduler.logger.error(f"Error opening website: {e}", exc_info=True)


def run_round_robin_1(skip_wait=False, debug_interval=None, enable_instagram=True, enable_gemini_images=True, enable_podcast=False, wait_seconds=10):
    """Run first round robin (Friday 1pm EST)"""
    # Validate imports before starting
    validate_imports(enable_podcast=enable_podcast, enable_gemini=enable_gemini_images)

    scheduler.logger.info("="*60)
    scheduler.logger.info("CASCADE GAME SIMULATION - ROUND ROBIN 1")
    if skip_wait:
        scheduler.logger.info("Running in IMMEDIATE mode (skipping schedule waits)")
    scheduler.logger.info("="*60)
    scheduler.logger.info(f"Feature toggles: Instagram={enable_instagram}, Gemini={enable_gemini_images}, Podcast={enable_podcast}, Wait={wait_seconds}s")
    
    # Load or create teams
    teams, current_week, round_robin_num = scheduler.load_game_state()
    
    # Round Robin 1 always starts at week 1, regardless of saved state
    # (Round Robin 2 will use the saved current_week which should be 8)
    current_week = 1
    scheduler.logger.info("Round Robin 1: Starting at Week 1")
    
    # Initialize Web App Season FIRST (this ensures database is initialized)
    season_id, season_folder = webapp_bridge.initialize_season()
    
    # Set status to running for Week 1 (will be processed immediately)
    simulation_status.set_running(1)
    scheduler.logger.info(f"Web App Season Initialized: ID={season_id}, Folder={season_folder}")
    
    # If in debug mode and Round Robin 1 is already complete, reset to start fresh
    if debug_interval is not None and round_robin_num == 1:
        scheduler.logger.info("Round Robin 1 already complete. Resetting game state for fresh start (debug mode).")
        teams = None
        # Reset game state file
        state_file = getattr(config, 'STATE_FILE_PATH', 'game_state.json')
        if os.path.exists(state_file):
            os.remove(state_file)
            scheduler.logger.info(f"Removed existing game state file: {state_file}")
    
    if teams is None:
        teams = scheduler.get_initial_teams()
        scheduler.logger.info("Starting fresh round robin 1")
        # Save fresh state
        scheduler.save_game_state(teams, current_week, round_robin_num=None)
    else:
        scheduler.logger.info(f"Using existing teams from game state")
    
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
        
        # Proactively check and refresh token if needed (prevent expiration issues)
        try:
            is_valid, valid_token, message = instagram_poster.check_and_refresh_token(access_token)
            scheduler.logger.info(f"Token health check: {message}")
            if not is_valid:
                scheduler.logger.error(f"❌ Token is invalid or expired. Instagram posting will fail.")
                scheduler.logger.error("   Please update your access token in .env file.")
            elif valid_token and valid_token != access_token:
                # Token was refreshed - update config
                config.INSTAGRAM_ACCESS_TOKEN = valid_token
                os.environ['INSTAGRAM_ACCESS_TOKEN'] = valid_token
                scheduler.logger.info("✓ Token automatically refreshed and updated!")
        except Exception as e:
            scheduler.logger.warning(f"⚠️  Could not check token health: {e}")
    
    # Get start time from config (defaults to 1:00 PM EST)
    start_hour = getattr(config, 'ROUND_ROBIN_1_START_HOUR', 13)
    start_minute = getattr(config, 'ROUND_ROBIN_1_START_MINUTE', 0)
    first_match_datetime = scheduler.get_next_fourth_weekend_friday_datetime(start_hour, start_minute)
    
    # Generate full schedule for this round robin
    full_schedule = game_logic.generate_round_robin_schedule(teams)
    max_rounds = config.ROUNDS_PER_ROUND_ROBIN if config.ROUNDS_PER_ROUND_ROBIN else len(full_schedule)

    # Upload Schedule to Web App
    schedule_data = []
    for week_offset, matches in enumerate(full_schedule[:max_rounds], 0):
        week = current_week + week_offset
        schedule_data.append((week, matches))
    webapp_bridge.upload_schedule(season_id, schedule_data)
    
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
        
        # Wait BEFORE processing (except for the first week - post immediately)
        # In backend mode (wait_seconds specified): wait before subsequent weeks
        # In IMMEDIATE mode (skip_wait=True without wait_seconds): skip all waits
        # In normal mode: wait before each week according to schedule
        should_wait_before = True
        if wait_seconds is not None and week_offset == 0:
            should_wait_before = False  # Post Week 1 immediately
        elif wait_seconds is not None:
            # Backend mode: use wait_seconds (even if skip_wait is True)
            should_wait_before = True
        elif skip_wait:
            # IMMEDIATE mode: skip all waits
            should_wait_before = False
            scheduler.logger.info(f"Skipping wait for {readable_match_time} (IMMEDIATE mode)")
        
        if should_wait_before:
            if wait_seconds is not None:
                import time
                from datetime import datetime, timedelta, timezone
                scheduler.logger.info(f"Waiting {wait_seconds} second(s) before Week {week}...")
                # Calculate next simulation time for countdown
                next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=wait_seconds)
                simulation_status.set_waiting(next_time, week - 1 if week > 1 else None)
                time.sleep(wait_seconds)
            elif debug_interval is not None:
                from datetime import datetime, timedelta, timezone
                scheduler.wait_for_interval(debug_interval)
                # Calculate next simulation time for countdown
                next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=debug_interval)
                simulation_status.set_waiting(next_time, week - 1 if week > 1 else None)
            elif not skip_wait:
                scheduler.logger.info(f"Scheduled kickoff: {readable_match_time}")
                # Convert match_datetime to UTC for storage
                from datetime import datetime
                import pytz
                est = pytz.timezone('US/Eastern')
                if match_datetime.tzinfo is None:
                    match_datetime = est.localize(match_datetime)
                next_time_utc = match_datetime.astimezone(pytz.UTC).replace(tzinfo=None)
                simulation_status.set_waiting(next_time_utc, week - 1 if week > 1 else None)
                scheduler.wait_until_datetime(match_datetime)
        
        # Set status to running before processing week
        total_games = len(matches)
        simulation_status.set_running(week, total_games=total_games)
        
        # Store upcoming matchups for odds calculation
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            upcoming_schedule[next_week] = full_schedule[week_offset + 1]
        
        scheduler.logger.info(f"\nWeek {week} (Posting at {readable_match_time}):")
        
        # ====================================================================
        # PHASE 1: Generate all results first (play all games)
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 1: Generating all game results for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        week_game_results = []
        upsets = []
        
        # Play all games for this week (no image generation yet)
        for game_num, (team1, team2) in enumerate(matches, 1):
            result, upset, game_result = game_logic.play_game(team1, team2)
            scheduler.logger.info(result)
            
            if upset:
                upsets.append(f"{team2.name} (adv: {team2.overall_advantage}) upset {team1.name} (adv: {team1.overall_advantage})")
            
            # Store game result with placeholder filename (will be updated after image generation)
            filename = f"week_{week}_game_{game_num}.png"
            week_game_results.append((filename, game_result))
            
            # Update progress after each game
            simulation_status.update_progress(1, games_completed=game_num, total_games=total_games)
        
        if upsets:
            scheduler.logger.info("\nUpsets this week:")
            for upset in upsets:
                scheduler.logger.info(upset)
        
        scheduler.logger.info("\nCurrent Standings:")
        game_logic.display_standings(teams)
        
        # Store game results
        game_results_by_week[week] = week_game_results
        
        # Sync data to Web App (with placeholder filenames for now)
        scheduler.logger.info(f"Syncing Week {week} data to Web App...")
        webapp_bridge.upload_game_data(season_id, week, week_game_results, season_folder)
        
        # ====================================================================
        # PHASE 2: Concurrently generate scripts/podcasts and images
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 2: Concurrently generating scripts/podcasts and images for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 2
        simulation_status.update_progress(2, games_completed=total_games, total_games=total_games)
        
        # Prepare results dictionaries for threads
        image_result = {'image_files': [], 'error': None}
        podcast_result = {'success': False, 'error': None}
        
        # Load rulebook text for podcast generation (if needed)
        rulebook_text = None
        if enable_podcast and PODCAST_AVAILABLE:
            try:
                rulebook_text = podcast_rulebook_reader.get_rulebook_text()
                if not rulebook_text:
                    scheduler.logger.warning("Could not load rulebook text. Podcast generation may be limited.")
            except Exception as e:
                scheduler.logger.warning(f"Error loading rulebook text: {e}")
        
        # Start image generation thread
        image_thread = threading.Thread(
            target=_generate_all_images_for_week,
            args=(week, week_game_results, enable_gemini_images, image_result, season_id, season_folder),
            daemon=False
        )
        
        # Start script/podcast generation thread
        podcast_thread = threading.Thread(
            target=_generate_all_scripts_and_podcasts,
            args=(week, game_results_by_week, rulebook_text, enable_podcast, podcast_result),
            daemon=False
        )
        
        # Start both threads concurrently
        image_thread.start()
        scheduler.logger.info("Started image generation thread")
        podcast_thread.start()
        scheduler.logger.info("Started script/podcast generation thread")
        
        # Wait for both threads to complete
        image_thread.join()
        podcast_thread.join()
        
        # Get results
        week_image_files = image_result['image_files']
        if image_result['error']:
            scheduler.logger.warning(f"Image generation had errors: {image_result['error']}")
        
        if podcast_result['success']:
            scheduler.logger.info(f"Scripts and podcasts generated successfully for Week {week}")
        elif podcast_result['error']:
            scheduler.logger.warning(f"Script/podcast generation had errors: {podcast_result['error']}")
        
        # ====================================================================
        # PHASE 3: Generate betting odds for current week
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 3: Generating betting odds for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 3
        simulation_status.update_progress(3, games_completed=total_games, total_games=total_games)
        
        # Generate betting lines for current week
        try:
            webapp_bridge.precalculate_betting_lines_for_week(season_id, week)
            scheduler.logger.info(f"Betting odds generated for Week {week}")
        except Exception as e:
            scheduler.logger.error(f"Error generating betting odds for Week {week}: {e}", exc_info=True)
        
        # Pre-calculate betting lines for next week in background thread (concurrently)
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            thread = threading.Thread(
                target=_precalculate_betting_lines_threaded,
                args=(season_id, next_week),
                daemon=True
            )
            thread.start()
            scheduler.logger.info(f"Started background thread to pre-calculate betting lines for Week {next_week}")
        
        # ====================================================================
        # PHASE 4: Create and post meta post
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 4: Creating and posting meta post for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 4
        simulation_status.update_progress(4, games_completed=total_games, total_games=total_games)
        
        meta_post_success = _create_meta_post(
            week, week_game_results, week_image_files, teams, game_results_by_week,
            upcoming_schedule, initial_teams, enable_instagram
        )
        
        if not meta_post_success:
            scheduler.logger.warning(f"Meta post failed for Week {week}, but continuing...")
        
        # ====================================================================
        # PHASE 5: Set waiting status and open website
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 5: Finalizing Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 5
        simulation_status.update_progress(5, games_completed=total_games, total_games=total_games)
        
        # Calculate next simulation time
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            next_match_datetime = scheduler.get_fourth_weekend_friday_at_offset(first_match_datetime, week_offset + 1)
            if wait_seconds is not None:
                from datetime import datetime, timedelta, timezone
                next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=wait_seconds)
            elif debug_interval is not None:
                from datetime import datetime, timedelta, timezone
                next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=debug_interval)
            else:
                import pytz
                est = pytz.timezone('US/Eastern')
                if next_match_datetime.tzinfo is None:
                    next_match_datetime = est.localize(next_match_datetime)
                next_time = next_match_datetime.astimezone(pytz.UTC).replace(tzinfo=None)
            simulation_status.set_waiting(next_time, week)
        else:
            # Last week - no next simulation
            simulation_status.set_waiting(None, week)
        
        # Open website after meta post is posted and scripts/podcasts are saved
        _open_website()
        
        scheduler.logger.info(f"Week {week} processing complete!")
    
    # Update current week for next round robin
    num_teams = len(teams)
    weeks_per_round_robin = num_teams - 1 if num_teams % 2 == 0 else num_teams
    new_current_week = current_week + weeks_per_round_robin
    
    # Save state after round robin 1
    scheduler.save_game_state(teams, new_current_week, round_robin_num=1)
    
    scheduler.logger.info(f"\nFinal Standings after Round Robin 1:")
    game_logic.display_standings(teams)
    scheduler.logger.info("Round Robin 1 complete. State saved for Round Robin 2.")


def run_round_robin_2(skip_wait=False, debug_interval=None, enable_instagram=True, enable_gemini_images=True, enable_podcast=False, wait_seconds=10):
    """Run second round robin (Saturday 1pm EST)"""
    # Validate imports before starting
    validate_imports(enable_podcast=enable_podcast, enable_gemini=enable_gemini_images)

    scheduler.logger.info("="*60)
    scheduler.logger.info("CASCADE GAME SIMULATION - ROUND ROBIN 2")
    if skip_wait:
        scheduler.logger.info("Running in IMMEDIATE mode (skipping schedule waits)")
    scheduler.logger.info("="*60)
    scheduler.logger.info(f"Feature toggles: Instagram={enable_instagram}, Gemini={enable_gemini_images}, Podcast={enable_podcast}, Wait={wait_seconds}s")
    
    # Load state from round robin 1
    teams, current_week, _ = scheduler.load_game_state()
    if teams is None:
        scheduler.logger.error("No game state found! Round robin 1 must be run first.")
        sys.exit(1)
    
    scheduler.logger.info(f"Loaded game state: Week {current_week}")

    # Initialize Web App Season (Assumption: This continues same season, but function checks active)
    # We re-fetch active season info
    season_id, season_folder = webapp_bridge.initialize_season()
    
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

    # Upload Schedule to Web App (Append for RR2)
    schedule_data = []
    for week_offset, matches in enumerate(full_schedule[:max_rounds], 0):
        week = current_week + week_offset
        schedule_data.append((week, matches))
    webapp_bridge.upload_schedule(season_id, schedule_data)
    
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
        if wait_seconds is not None and week_offset == 0:
            # Skip wait for first week in backend mode
            pass
        elif wait_seconds is not None:
            # Backend mode: use wait_seconds (even if skip_wait is True)
            import time
            from datetime import datetime, timedelta, timezone
            scheduler.logger.info(f"Waiting {wait_seconds} second(s) before Week {week}...")
            # Calculate next simulation time for countdown
            next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=wait_seconds)
            simulation_status.set_waiting(next_time, week - 1 if week > current_week else None)
            time.sleep(wait_seconds)
        elif skip_wait:
            scheduler.logger.info(f"Skipping wait for {posting_hour:02d}:00 EST (IMMEDIATE mode)")
        elif debug_interval:
            from datetime import datetime, timedelta, timezone
            scheduler.wait_for_interval(debug_interval)
            # Calculate next simulation time for countdown
            next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=debug_interval)
            simulation_status.set_waiting(next_time, week - 1 if week > current_week else None)
        elif not skip_wait:
            from datetime import datetime, timedelta
            import pytz
            est = pytz.timezone('US/Eastern')
            now = datetime.now(est)
            next_time_est = now.replace(hour=posting_hour, minute=0, second=0, microsecond=0)
            if next_time_est <= now:
                next_time_est += timedelta(days=1)
            next_time = next_time_est.astimezone(pytz.UTC).replace(tzinfo=None)
            simulation_status.set_waiting(next_time, week - 1 if week > current_week else None)
            scheduler.wait_until_hour(posting_hour)
        
        # Set status to running before processing week
        total_games = len(matches)
        simulation_status.set_running(week, total_games=total_games)
        
        # Store upcoming matchups for odds calculation
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            upcoming_schedule[next_week] = full_schedule[week_offset + 1]
        
        scheduler.logger.info(f"\nWeek {week} (Posting at {posting_hour:02d}:00 EST):")
        
        # ====================================================================
        # PHASE 1: Generate all results first (play all games)
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 1: Generating all game results for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        week_game_results = []
        upsets = []
        
        # Play all games for this week (no image generation yet)
        for game_num, (team1, team2) in enumerate(matches, 1):
            result, upset, game_result = game_logic.play_game(team1, team2)
            scheduler.logger.info(result)
            
            if upset:
                upsets.append(f"{team2.name} (adv: {team2.overall_advantage}) upset {team1.name} (adv: {team1.overall_advantage})")
            
            # Store game result with placeholder filename (will be updated after image generation)
            filename = f"week_{week}_game_{game_num}.png"
            week_game_results.append((filename, game_result))
            
            # Update progress after each game
            simulation_status.update_progress(1, games_completed=game_num, total_games=total_games)
        
        if upsets:
            scheduler.logger.info("\nUpsets this week:")
            for upset in upsets:
                scheduler.logger.info(upset)
        
        scheduler.logger.info("\nCurrent Standings:")
        game_logic.display_standings(teams)
        
        # Store game results
        game_results_by_week[week] = week_game_results
        
        # Sync data to Web App (with placeholder filenames for now)
        scheduler.logger.info(f"Syncing Week {week} data to Web App...")
        webapp_bridge.upload_game_data(season_id, week, week_game_results, season_folder)
        
        # ====================================================================
        # PHASE 2: Concurrently generate scripts/podcasts and images
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 2: Concurrently generating scripts/podcasts and images for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 2
        simulation_status.update_progress(2, games_completed=total_games, total_games=total_games)
        
        # Prepare results dictionaries for threads
        image_result = {'image_files': [], 'error': None}
        podcast_result = {'success': False, 'error': None}
        
        # Load rulebook text for podcast generation (if needed)
        rulebook_text = None
        if enable_podcast and PODCAST_AVAILABLE:
            try:
                rulebook_text = podcast_rulebook_reader.get_rulebook_text()
                if not rulebook_text:
                    scheduler.logger.warning("Could not load rulebook text. Podcast generation may be limited.")
            except Exception as e:
                scheduler.logger.warning(f"Error loading rulebook text: {e}")
        
        # Start image generation thread
        image_thread = threading.Thread(
            target=_generate_all_images_for_week,
            args=(week, week_game_results, enable_gemini_images, image_result, season_id, season_folder),
            daemon=False
        )
        
        # Start script/podcast generation thread
        podcast_thread = threading.Thread(
            target=_generate_all_scripts_and_podcasts,
            args=(week, game_results_by_week, rulebook_text, enable_podcast, podcast_result),
            daemon=False
        )
        
        # Start both threads concurrently
        image_thread.start()
        scheduler.logger.info("Started image generation thread")
        podcast_thread.start()
        scheduler.logger.info("Started script/podcast generation thread")
        
        # Wait for both threads to complete
        image_thread.join()
        podcast_thread.join()
        
        # Get results
        week_image_files = image_result['image_files']
        if image_result['error']:
            scheduler.logger.warning(f"Image generation had errors: {image_result['error']}")
        
        if podcast_result['success']:
            scheduler.logger.info(f"Scripts and podcasts generated successfully for Week {week}")
        elif podcast_result['error']:
            scheduler.logger.warning(f"Script/podcast generation had errors: {podcast_result['error']}")
        
        # ====================================================================
        # PHASE 3: Generate betting odds for current week
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 3: Generating betting odds for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 3
        simulation_status.update_progress(3, games_completed=total_games, total_games=total_games)
        
        # Generate betting lines for current week
        try:
            webapp_bridge.precalculate_betting_lines_for_week(season_id, week)
            scheduler.logger.info(f"Betting odds generated for Week {week}")
        except Exception as e:
            scheduler.logger.error(f"Error generating betting odds for Week {week}: {e}", exc_info=True)
        
        # Pre-calculate betting lines for next week in background thread (concurrently)
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            thread = threading.Thread(
                target=_precalculate_betting_lines_threaded,
                args=(season_id, next_week),
                daemon=True
            )
            thread.start()
            scheduler.logger.info(f"Started background thread to pre-calculate betting lines for Week {next_week}")
        
        # ====================================================================
        # PHASE 4: Create and post meta post
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 4: Creating and posting meta post for Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 4
        simulation_status.update_progress(4, games_completed=total_games, total_games=total_games)
        
        meta_post_success = _create_meta_post(
            week, week_game_results, week_image_files, teams, game_results_by_week,
            upcoming_schedule, initial_teams, enable_instagram
        )
        
        if not meta_post_success:
            scheduler.logger.warning(f"Meta post failed for Week {week}, but continuing...")
        
        # ====================================================================
        # PHASE 5: Set waiting status and open website
        # ====================================================================
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info(f"Phase 5: Finalizing Week {week}...")
        scheduler.logger.info(f"{'='*60}")
        
        # Update progress to Phase 5
        simulation_status.update_progress(5, games_completed=total_games, total_games=total_games)
        
        # Calculate next simulation time
        if week_offset + 1 < len(full_schedule[:max_rounds]):
            next_week = current_week + week_offset + 1
            if wait_seconds is not None:
                from datetime import datetime, timedelta, timezone
                next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=wait_seconds)
            elif debug_interval is not None:
                from datetime import datetime, timedelta, timezone
                next_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=debug_interval)
            else:
                # Calculate next posting hour
                posting_hour = scheduler.calculate_next_posting_hour(start_hour, week_offset + 1)
                from datetime import datetime, timedelta
                import pytz
                est = pytz.timezone('US/Eastern')
                now = datetime.now(est)
                next_time_est = now.replace(hour=posting_hour, minute=0, second=0, microsecond=0)
                if next_time_est <= now:
                    next_time_est += timedelta(days=1)
                next_time = next_time_est.astimezone(pytz.UTC).replace(tzinfo=None)
            simulation_status.set_waiting(next_time, week)
        else:
            # Last week - no next simulation
            simulation_status.set_waiting(None, week)
        
        # Open website after meta post is posted and scripts/podcasts are saved
        _open_website()
        
        scheduler.logger.info(f"Week {week} processing complete!")
    
    # Update current week for next round robin
    num_teams = len(teams)
    weeks_per_round_robin = num_teams - 1 if num_teams % 2 == 0 else num_teams
    new_current_week = current_week + weeks_per_round_robin
    
    # Save state after round robin 2
    scheduler.save_game_state(teams, new_current_week, round_robin_num=2)
    
    scheduler.logger.info(f"\nFinal Standings after Round Robin 2:")
    game_logic.display_standings(teams)
    scheduler.logger.info("Round Robin 2 complete. State saved for Tournament.")


def run_tournament(skip_wait=False, debug_interval=None, enable_instagram=True, enable_gemini_images=True, enable_podcast=False, wait_seconds=10):
    """Run tournament (Sunday 6pm/7pm/8pm EST)"""
    # Validate imports before starting
    validate_imports(enable_podcast=enable_podcast, enable_gemini=enable_gemini_images)

    scheduler.logger.info("="*60)
    scheduler.logger.info("CASCADE GAME SIMULATION - TOURNAMENT")
    if skip_wait:
        scheduler.logger.info("Running in IMMEDIATE mode (skipping schedule waits)")
    scheduler.logger.info("="*60)
    scheduler.logger.info(f"Feature toggles: Instagram={enable_instagram}, Gemini={enable_gemini_images}, Podcast={enable_podcast}, Wait={wait_seconds}s")
    
    # Load state from round robin 2
    teams, current_week, _ = scheduler.load_game_state()
    if teams is None:
        scheduler.logger.error("No game state found! Round robins must be run first.")
        sys.exit(1)
    
    scheduler.logger.info(f"Loaded game state: Week {current_week}")

    # Initialize Web App Season (fetch active)
    season_id, season_folder = webapp_bridge.initialize_season()
    
    # Sort teams by wins, then by point difference
    sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
    
    # QUARTERFINALS - Wait until 6pm EST
    quarterfinals_hour = getattr(config, 'TOURNAMENT_QUARTERFINALS_HOUR', 18)
    if wait_seconds is not None:
        # Backend mode: use wait_seconds (even if skip_wait is True)
        import time
        scheduler.logger.info(f"Waiting {wait_seconds} second(s) before Quarterfinals...")
        time.sleep(wait_seconds)
    elif skip_wait:
        scheduler.logger.info(f"Skipping wait for Quarterfinals (IMMEDIATE mode)")
    elif debug_interval:
        scheduler.wait_for_interval(debug_interval)
    elif not skip_wait:
        scheduler.logger.info(f"Waiting until {quarterfinals_hour:02d}:00 EST for Quarterfinals...")
        scheduler.wait_until_hour(quarterfinals_hour)
    
    # Generate and post bracket before quarterfinals (showing all 8 teams)
    scheduler.logger.info("\nGenerating tournament bracket (before quarterfinals)...")
    bracket_qf_filename = "tournament_bracket_quarterfinals.png"
    image_generator.generate_tournament_bracket(teams, bracket_qf_filename, round_stage='quarterfinals')
    
    if enable_instagram:
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info("Posting Tournament Bracket - Quarterfinals")
        scheduler.logger.info(f"{'='*60}")
        instagram_poster.post_to_instagram([bracket_qf_filename], "")
    else:
        scheduler.logger.info("Instagram posting disabled - skipping bracket post")
    
    # QUARTERFINALS - Generate and post
    scheduler.logger.info("\nQuarterfinals:")
    quarterfinal_winners = []
    quarterfinal_images = []
    quarterfinal_game_results = []
    
    # Upload QF schedule logic could be here, but they are dynamic.
    # webapp_bridge can handle creating games on the fly in upload_game_data if not found.

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
        image_generator.generate_game_image(game_result, filename, game_type="quarterfinal", game_number=game_num, season_id=season_id)
        
        # Post to Instagram Stories if enabled
        if config.ENABLE_INSTAGRAM_STORIES if hasattr(config, 'ENABLE_INSTAGRAM_STORIES') else False:
            try:
                stories_filename = filename.replace('.png', '_stories.png')
                if os.path.exists(stories_filename):
                    import instagram_poster
                    instagram_poster.post_story_to_instagram(stories_filename)
            except Exception as stories_error:
                scheduler.logger.warning(f"Error posting to Instagram Stories: {stories_error}")
        quarterfinal_images.append(filename)
        quarterfinal_game_results.append((filename, game_result))
        
        # Generate Gemini artistic photo if enabled
        if enable_gemini_images and config.USE_GEMINI and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_quarterfinal_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="quarterfinal", game_number=game_num, is_champion=False, season_folder=season_folder
            )
            if success:
                quarterfinal_images.append(gemini_filename)
                # Update Game record with gemini_image_path
                if season_id and season_folder:
                    try:
                        gemini_image_path = f"{season_folder}/{gemini_filename}"
                        team1_name = game_result['team1'].name
                        team2_name = game_result['team2'].name
                        webapp_bridge.update_game_gemini_image(
                            season_id, 90, game_num, gemini_image_path,
                            team1_name=team1_name, team2_name=team2_name
                        )
                    except Exception as update_error:
                        scheduler.logger.warning(f"Failed to update Game record with gemini_image_path: {update_error}")
            else:
                scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        elif not enable_gemini_images:
            scheduler.logger.debug("Gemini image generation disabled - skipping")
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        quarterfinal_winners.append(winner)

    # Sync QF data to Web App
    scheduler.logger.info("Syncing Quarterfinals data to Web App...")
    # Use a high week number for tournament rounds or handle specially. Let's say Week 90 = QF
    webapp_bridge.upload_game_data(season_id, 90, quarterfinal_game_results, season_folder)
    
    # Post quarterfinals to Instagram (if enabled)
    if enable_instagram:
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info("Posting Quarterfinals to Instagram...")
        scheduler.logger.info(f"{'='*60}")
        caption_parts = ["🏆 Tournament Quarterfinals"]
        if quarterfinal_game_results:
            caption_parts.append("")
            game_result_lines = format_game_results_for_caption(quarterfinal_game_results)
            caption_parts.extend(game_result_lines)
        caption = "\n".join(caption_parts)
        # Sort image order by game number (keeping scoreboard before gemini pairs)
        randomized_quarterfinal_images = instagram_poster.sort_image_pairs_by_game_number(quarterfinal_images)
        success = instagram_poster.post_to_instagram(randomized_quarterfinal_images, caption)
        if not success:
            scheduler.logger.warning("Failed to post quarterfinals images")
    else:
        scheduler.logger.info("Instagram posting disabled - skipping quarterfinals post")
    
    # SEMIFINALS - Wait until 7pm EST
    semifinals_hour = getattr(config, 'TOURNAMENT_SEMIFINALS_HOUR', 19)
    if wait_seconds is not None:
        # Backend mode: use wait_seconds (even if skip_wait is True)
        import time
        scheduler.logger.info(f"\nWaiting {wait_seconds} second(s) before Semifinals...")
        time.sleep(wait_seconds)
    elif skip_wait:
        scheduler.logger.info(f"Skipping wait for Semifinals (IMMEDIATE mode)")
    elif debug_interval:
        scheduler.wait_for_interval(debug_interval)
    elif not skip_wait:
        scheduler.logger.info(f"\nWaiting until {semifinals_hour:02d}:00 EST for Semifinals...")
        scheduler.wait_until_hour(semifinals_hour)
    
    # Generate and post bracket before semifinals (showing QF winners)
    scheduler.logger.info("\nGenerating tournament bracket (before semifinals)...")
    bracket_sf_filename = "tournament_bracket_semifinals.png"
    image_generator.generate_tournament_bracket(teams, bracket_sf_filename, round_stage='semifinals', quarterfinal_winners=quarterfinal_winners)
    
    if enable_instagram:
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info("Posting Tournament Bracket - Semifinals")
        scheduler.logger.info(f"{'='*60}")
        instagram_poster.post_to_instagram([bracket_sf_filename], "")
    else:
        scheduler.logger.info("Instagram posting disabled - skipping bracket post")
    
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
        image_generator.generate_game_image(game_result, filename, game_type="semifinal", game_number=game_num, season_id=season_id)
        
        # Post to Instagram Stories if enabled
        if config.ENABLE_INSTAGRAM_STORIES if hasattr(config, 'ENABLE_INSTAGRAM_STORIES') else False:
            try:
                stories_filename = filename.replace('.png', '_stories.png')
                if os.path.exists(stories_filename):
                    import instagram_poster
                    instagram_poster.post_story_to_instagram(stories_filename)
            except Exception as stories_error:
                scheduler.logger.warning(f"Error posting to Instagram Stories: {stories_error}")
        semifinal_images.append(filename)
        semifinal_game_results.append((filename, game_result))
        
        # Generate Gemini artistic photo if enabled
        if enable_gemini_images and config.USE_GEMINI and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_semifinal_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="semifinal", game_number=game_num, is_champion=False, season_folder=season_folder
            )
            if success:
                semifinal_images.append(gemini_filename)
                # Update Game record with gemini_image_path
                if season_id and season_folder:
                    try:
                        gemini_image_path = f"{season_folder}/{gemini_filename}"
                        team1_name = game_result['team1'].name
                        team2_name = game_result['team2'].name
                        webapp_bridge.update_game_gemini_image(
                            season_id, 91, game_num, gemini_image_path,
                            team1_name=team1_name, team2_name=team2_name
                        )
                    except Exception as update_error:
                        scheduler.logger.warning(f"Failed to update Game record with gemini_image_path: {update_error}")
            else:
                scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        elif not enable_gemini_images:
            scheduler.logger.debug("Gemini image generation disabled - skipping")
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        semifinal_winners.append(winner)

    # Sync SF data to Web App (Week 91)
    scheduler.logger.info("Syncing Semifinals data to Web App...")
    webapp_bridge.upload_game_data(season_id, 91, semifinal_game_results, season_folder)
    
    # Post semifinals to Instagram (if enabled)
    if enable_instagram:
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info("Posting Semifinals to Instagram...")
        scheduler.logger.info(f"{'='*60}")
        caption_parts = ["🏆 Tournament Semifinals"]
        if semifinal_game_results:
            caption_parts.append("")
            game_result_lines = format_game_results_for_caption(semifinal_game_results)
            caption_parts.extend(game_result_lines)
        caption = "\n".join(caption_parts)
        # Sort image order by game number (keeping scoreboard before gemini pairs)
        randomized_semifinal_images = instagram_poster.sort_image_pairs_by_game_number(semifinal_images)
        success = instagram_poster.post_to_instagram(randomized_semifinal_images, caption)
        if not success:
            scheduler.logger.warning("Failed to post semifinals images")
    else:
        scheduler.logger.info("Instagram posting disabled - skipping semifinals post")
    
    # FINALS - Wait until 8pm EST
    finals_hour = getattr(config, 'TOURNAMENT_FINALS_HOUR', 20)
    if wait_seconds is not None:
        # Backend mode: use wait_seconds (even if skip_wait is True)
        import time
        scheduler.logger.info(f"\nWaiting {wait_seconds} second(s) before Finals...")
        time.sleep(wait_seconds)
    elif skip_wait:
        scheduler.logger.info(f"Skipping wait for Finals (IMMEDIATE mode)")
    elif debug_interval:
        scheduler.wait_for_interval(debug_interval)
    elif not skip_wait:
        scheduler.logger.info(f"\nWaiting until {finals_hour:02d}:00 EST for Finals...")
        scheduler.wait_until_hour(finals_hour)
    
    # Generate and post bracket before finals (showing SF winners)
    scheduler.logger.info("\nGenerating tournament bracket (before finals)...")
    bracket_finals_filename = "tournament_bracket_finals.png"
    image_generator.generate_tournament_bracket(teams, bracket_finals_filename, round_stage='finals', semifinal_winners=semifinal_winners)
    
    if enable_instagram:
        scheduler.logger.info(f"\n{'='*60}")
        scheduler.logger.info("Posting Tournament Bracket - Finals")
        scheduler.logger.info(f"{'='*60}")
        instagram_poster.post_to_instagram([bracket_finals_filename], "")
    else:
        scheduler.logger.info("Instagram posting disabled - skipping bracket post")
    
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
        image_generator.generate_game_image(game_result, filename, game_type="final", game_number=game_num, season_id=season_id)
        
        # Post to Instagram Stories if enabled
        if config.ENABLE_INSTAGRAM_STORIES if hasattr(config, 'ENABLE_INSTAGRAM_STORIES') else False:
            try:
                stories_filename = filename.replace('.png', '_stories.png')
                if os.path.exists(stories_filename):
                    import instagram_poster
                    instagram_poster.post_story_to_instagram(stories_filename)
            except Exception as stories_error:
                scheduler.logger.warning(f"Error posting to Instagram Stories: {stories_error}")
        final_game_images = [filename]
        
        # Generate Gemini artistic photo if enabled
        if enable_gemini_images and config.USE_GEMINI and GEMINI_AVAILABLE:
            gemini_filename = f"tournament_final_game_{game_num}_gemini.png"
            success = gemini_image_generator.generate_game_image_with_gemini(
                game_result, gemini_filename, game_type="final", game_number=game_num, is_champion=False, season_folder=season_folder
            )
            if success:
                final_game_images.append(gemini_filename)
                # Update Game record with gemini_image_path
                if season_id and season_folder:
                    try:
                        gemini_image_path = f"{season_folder}/{gemini_filename}"
                        team1_name = game_result['team1'].name
                        team2_name = game_result['team2'].name
                        webapp_bridge.update_game_gemini_image(
                            season_id, 92, game_num, gemini_image_path,
                            team1_name=team1_name, team2_name=team2_name
                        )
                    except Exception as update_error:
                        scheduler.logger.warning(f"Failed to update Game record with gemini_image_path: {update_error}")
            else:
                scheduler.logger.warning(f"Gemini artistic photo generation failed for {gemini_filename}")
        elif not enable_gemini_images:
            scheduler.logger.debug("Gemini image generation disabled - skipping")
        
        # Sync Final Game data to Web App (Week 92)
        scheduler.logger.info(f"Syncing Final Game {game_num} data to Web App...")
        webapp_bridge.upload_game_data(season_id, 92, [(filename, game_result)], season_folder)

        # Post this final game to Instagram immediately (if enabled)
        if enable_instagram:
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
            # Sort image order by game number (keeping scoreboard before gemini pairs)
            randomized_final_images = instagram_poster.sort_image_pairs_by_game_number(final_game_images)
            success = instagram_poster.post_to_instagram(randomized_final_images, caption)
            if not success:
                scheduler.logger.warning(f"Failed to post final game {game_num} images")
        else:
            scheduler.logger.info(f"Instagram posting disabled - skipping final game {game_num} post")
        
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
    
    # Generate and post champion trophy image (if enabled)
    if enable_gemini_images and config.USE_GEMINI and GEMINI_AVAILABLE and last_game_result:
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
        
        if success and enable_instagram:
            scheduler.logger.info(f"\n{'='*60}")
            scheduler.logger.info("Posting Champion Trophy to Instagram...")
            scheduler.logger.info(f"{'='*60}")
            caption = f"🏆 TOURNAMENT CHAMPION: {champion.name} 🏆\nFinal Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}"
            instagram_poster.post_to_instagram([trophy_filename], caption)
        elif success and not enable_instagram:
            scheduler.logger.info("Instagram posting disabled - skipping trophy post")
        else:
            scheduler.logger.warning("Champion trophy image generation failed")
    elif not enable_gemini_images:
        scheduler.logger.info("Gemini image generation disabled - skipping champion trophy")
    
    scheduler.logger.info("\nFinal Team Stats:")
    for team in teams:
        scheduler.logger.info(f"{team}")
    
    # Reset Season Tokens
    scheduler.logger.info("Resetting user tokens for next season...")
    webapp_bridge.reset_season_tokens()
    
    # Save Season History
    scheduler.logger.info("Saving season history...")
    webapp_bridge.save_season_history(season_id, champion.name, season_folder)

    scheduler.logger.info("\nTournament complete!")


def run_backend(enable_instagram=True, enable_gemini_images=True, enable_podcast=False, wait_seconds=10):
    """
    Run all phases sequentially (Round Robin 1, Round Robin 2, Tournament) for local testing.
    
    Args:
        enable_instagram: Boolean to enable/disable Instagram posting
        enable_gemini_images: Boolean to enable/disable Gemini artistic image generation
        enable_podcast: Boolean to enable/disable podcast generation
        wait_seconds: Integer for seconds to wait between weeks (default: 10)
    """
    # Validate imports before starting
    validate_imports(enable_podcast=enable_podcast, enable_gemini=enable_gemini_images)

    scheduler.logger.info("="*60)
    scheduler.logger.info("CASCADE GAME SIMULATION - BACKEND MODE")
    scheduler.logger.info("="*60)
    scheduler.logger.info(f"Feature toggles: Instagram={enable_instagram}, Gemini={enable_gemini_images}, Podcast={enable_podcast}")
    scheduler.logger.info(f"Wait time between weeks: {wait_seconds} seconds")
    scheduler.logger.info("="*60)
    
    try:
        # Run Round Robin 1
        scheduler.logger.info("\n" + "="*60)
        scheduler.logger.info("STARTING ROUND ROBIN 1")
        scheduler.logger.info("="*60)
        run_round_robin_1(
            skip_wait=True,
            enable_instagram=enable_instagram,
            enable_gemini_images=enable_gemini_images,
            enable_podcast=enable_podcast,
            wait_seconds=wait_seconds
        )
        
        # Run Round Robin 2
        scheduler.logger.info("\n" + "="*60)
        scheduler.logger.info("STARTING ROUND ROBIN 2")
        scheduler.logger.info("="*60)
        run_round_robin_2(
            skip_wait=True,
            enable_instagram=enable_instagram,
            enable_gemini_images=enable_gemini_images,
            enable_podcast=enable_podcast,
            wait_seconds=wait_seconds
        )
        
        # Run Tournament
        scheduler.logger.info("\n" + "="*60)
        scheduler.logger.info("STARTING TOURNAMENT")
        scheduler.logger.info("="*60)
        run_tournament(
            skip_wait=True,
            enable_instagram=enable_instagram,
            enable_gemini_images=enable_gemini_images,
            enable_podcast=enable_podcast,
            wait_seconds=wait_seconds
        )
        
        scheduler.logger.info("\n" + "="*60)
        scheduler.logger.info("BACKEND RUN COMPLETE - ALL PHASES FINISHED")
        scheduler.logger.info("="*60)
        
    except Exception as e:
        scheduler.logger.error(f"\n{'='*60}")
        scheduler.logger.error(f"ERROR during backend run: {e}")
        scheduler.logger.error(f"{'='*60}")
        import traceback
        scheduler.logger.error(traceback.format_exc())
        raise


def main():
    """Main entry point with command-line argument parsing"""
    print("CASCADE MAIN: Starting script...", flush=True)
    sys.stdout.flush()
    
    # Clean up podcasts folder at startup (before simulations start)
    scheduler.logger.info("Cleaning podcasts folder before starting simulations...")
    _cleanup_podcasts_directory()
    
    # Register cleanup function to run on program exit
    atexit.register(cleanup_podcasts_and_scripts)
    
    # Register signal handlers for graceful shutdown (Ctrl+C, termination)
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except (AttributeError, ValueError):
        # Windows may not support all signals, or signal may not be available
        pass
    
    parser = argparse.ArgumentParser(description='Cascade Game Simulation - Oracle Cloud Automation')
    
    # Mode selection - either backend or individual phases
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--mode', type=str,
                           choices=['round_robin_1', 'round_robin_2', 'tournament'],
                           help='Execution mode: round_robin_1 (Friday), round_robin_2 (Saturday), or tournament (Sunday)')
    mode_group.add_argument('--backend', action='store_true',
                           help='Run all phases sequentially in backend mode for local testing')
    
    # Common arguments
    parser.add_argument('--now', action='store_true', help='Run immediately without waiting for schedule')
    parser.add_argument('--debug-interval', type=int, help='Debug mode: wait interval in minutes between stages')
    
    # Backend mode toggles
    parser.add_argument('--no-instagram', action='store_true', help='Disable Instagram posting (backend mode)')
    parser.add_argument('--no-gemini', action='store_true', help='Disable Gemini image generation (backend mode)')
    parser.add_argument('--no-podcast', action='store_true', help='Disable podcast generation (backend mode)')
    parser.add_argument('--wait-seconds', type=int, default=10,
                       help='Seconds to wait between weeks (backend mode, default: 10)')
    
    args = parser.parse_args()
    
    # Backend mode
    if args.backend:
        enable_instagram = not args.no_instagram
        enable_gemini_images = not args.no_gemini
        enable_podcast = not args.no_podcast
        wait_seconds = args.wait_seconds
        
        run_backend(
            enable_instagram=enable_instagram,
            enable_gemini_images=enable_gemini_images,
            enable_podcast=enable_podcast,
            wait_seconds=wait_seconds
        )
    # Individual phase modes
    elif args.mode == 'round_robin_1':
        # Default flags for individual modes (can be overridden if we added args for them)
        run_round_robin_1(
            skip_wait=args.now,
            debug_interval=args.debug_interval,
            enable_podcast=not args.no_podcast if hasattr(args, 'no_podcast') else True # Default to True
        )
    elif args.mode == 'round_robin_2':
        run_round_robin_2(
            skip_wait=args.now,
            debug_interval=args.debug_interval,
            enable_podcast=not args.no_podcast if hasattr(args, 'no_podcast') else True
        )
    elif args.mode == 'tournament':
        run_tournament(
            skip_wait=args.now,
            debug_interval=args.debug_interval,
            enable_podcast=not args.no_podcast if hasattr(args, 'no_podcast') else True
        )
    else:
        parser.error(f"Invalid mode: {args.mode}")


if __name__ == "__main__":
    main()
