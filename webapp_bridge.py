import os
import shutil
import json
import re
import logging
from datetime import datetime, timezone
from webapp.app import app, db, init_db, migrate_bet_table, migrate_game_gemini_image
from webapp.database import User, Season, Game, Bet, Transaction, Parlay, SimulationStatus, SeasonHistory
import game_logic

# Set up logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Config
STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webapp', 'static')

def ensure_db_initialized():
    """Ensure database tables exist before use"""
    try:
        with app.app_context():
            # Check if tables exist by trying to query a table
            try:
                Season.query.first()
            except Exception as e:
                # Tables don't exist, initialize them
                logger.info(f"Database tables not found, initializing: {e}")
                init_db()
            else:
                # Tables exist, but check if bet table needs migration
                migrate_bet_table()
                migrate_game_gemini_image()
    except Exception as e:
        logger.error(f"Error ensuring database initialization: {e}")
        raise

def initialize_season():
    """
    Checks existing season folders, creates a new one (season_N+1),
    and initializes a new Season record in the database.
    """
    ensure_db_initialized()
    
    if not os.path.exists(STATIC_ROOT):
        os.makedirs(STATIC_ROOT)

    # Find existing seasons
    existing_seasons = [d for d in os.listdir(STATIC_ROOT) if d.startswith('season_') and os.path.isdir(os.path.join(STATIC_ROOT, d))]
    season_nums = []
    for s in existing_seasons:
        try:
            num = int(s.split('_')[1])
            season_nums.append(num)
        except ValueError:
            pass

    next_season_num = max(season_nums) + 1 if season_nums else 1
    new_season_folder = f"season_{next_season_num}"
    new_season_path = os.path.join(STATIC_ROOT, new_season_folder)

    os.makedirs(new_season_path)
    print(f"Created season folder: {new_season_path}")

    # Database update
    try:
        with app.app_context():
            # Deactivate old seasons
            existing_active = Season.query.filter_by(is_active=True).all()
            for s in existing_active:
                s.is_active = False

            new_season = Season(name=f"Season {next_season_num}", is_active=True)
            db.session.add(new_season)
            db.session.commit()
            logger.info(f"Initialized Season {next_season_num} in database (ID: {new_season.id})")
            print(f"Initialized Season {next_season_num} in database (ID: {new_season.id})")
            return new_season.id, new_season_folder
    except Exception as e:
        logger.error(f"Error initializing season: {e}", exc_info=True)
        raise

def upload_schedule(season_id, schedule_data):
    """
    Populates the Game table with scheduled games.
    schedule_data: List of tuples/dicts with (week, team1, team2)
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            # Clear existing scheduled games for this season to avoid duplicates if re-run
            # (Or handle upsert logic. For now, we assume fresh season start)
            pass

            # We need to adapt the schedule_data format coming from game_logic
            # Assuming schedule_data is list of (week, [(team1, team2), ...])

            game_count = 0
            for week_num, matches in schedule_data:
                for game_num, match in enumerate(matches, 1):
                    team1, team2 = match
                    new_game = Game(
                        season_id=season_id,
                        week=week_num,
                        game_number=game_num,
                        team1=team1.name,
                        team2=team2.name,
                        status='scheduled'
                    )
                    db.session.add(new_game)
                    game_count += 1

            db.session.commit()
            logger.info(f"Uploaded schedule: {game_count} games created.")
            print(f"Uploaded schedule: {game_count} games created.")
            
            # Pre-generate betting lines for all scheduled games
            logger.info("Pre-generating betting lines for all scheduled games...")
            print("Pre-generating betting lines for all scheduled games...")
            try:
                # Get all weeks that have scheduled games
                weeks_with_games = db.session.query(Game.week).filter_by(
                    season_id=season_id, 
                    status='scheduled'
                ).distinct().all()
                weeks_list = [w[0] for w in weeks_with_games]
                
                for week_num in weeks_list:
                    logger.info(f"Pre-generating betting lines for Week {week_num}...")
                    precalculate_betting_lines_for_week(season_id, week_num)
                    
                logger.info(f"Betting lines pre-generation complete for {len(weeks_list)} weeks")
                print(f"Betting lines pre-generation complete for {len(weeks_list)} weeks")
            except Exception as e:
                logger.error(f"Error pre-generating betting lines during schedule upload: {e}", exc_info=True)
                # Don't raise - schedule upload should succeed even if betting lines fail
                print(f"Warning: Could not pre-generate betting lines: {e}")
                
    except Exception as e:
        logger.error(f"Error uploading schedule: {e}", exc_info=True)
        raise

def upload_game_data(season_id, week, game_results, season_folder_name):
    """
    Updates game results in DB and copies images.
    game_results: List of (filename, game_result_dict)
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            target_dir = os.path.join(STATIC_ROOT, season_folder_name)

            for item in game_results:
                try:
                    if isinstance(item, tuple):
                        filename, result = item
                    else:
                        # Handle case where it might just be the result dict (rare but possible in logic)
                        logger.warning(f"Skipping invalid game result item: {type(item)}")
                        continue

                    # Extract game_number from filename
                    # Patterns: week_X_game_Y.png, tournament_quarterfinal_game_Y.png, etc.
                    game_number = None
                    match = re.search(r'_game_(\d+)', filename)
                    if match:
                        game_number = int(match.group(1))
                    
                    # Copy Image - try multiple possible locations
                    src_path = None
                    possible_paths = [
                        filename,  # Current working directory
                        os.path.abspath(filename),  # Absolute path from current dir
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),  # Project root
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            src_path = path
                            break
                    
                    if src_path and os.path.exists(src_path):
                        dest_path = os.path.join(target_dir, filename)
                        os.makedirs(target_dir, exist_ok=True)
                        shutil.copy(src_path, dest_path)
                        logger.debug(f"Copied image: {src_path} -> {dest_path}")
                        print(f"Copied image: {src_path} -> {dest_path}")
                    else:
                        logger.warning(f"Image not found: {filename} (tried: {possible_paths})")
                        print(f"Warning: Image not found: {filename} (tried: {possible_paths})")

                    # Update Database
                    # Find the scheduled game - try with game_number first, then without
                    game = None
                    if game_number is not None:
                        game = Game.query.filter_by(season_id=season_id,
                                                  week=week,
                                                  game_number=game_number,
                                                  team1=result['team1'].name,
                                                  team2=result['team2'].name).first()
                    
                    # Fallback: find by team names only
                    if not game:
                        game = Game.query.filter_by(season_id=season_id,
                                                  week=week,
                                                  team1=result['team1'].name,
                                                  team2=result['team2'].name).first()

                    # If not found (e.g. tournament dynamic games), create it
                    if not game:
                        game = Game(season_id=season_id, week=week,
                                    game_number=game_number,
                                    team1=result['team1'].name, team2=result['team2'].name)
                        db.session.add(game)
                        logger.info(f"Created new game: {result['team1'].name} vs {result['team2'].name} (Week {week}, Game {game_number})")
                    elif game_number is not None and game.game_number != game_number:
                        # Update game_number if it wasn't set before
                        game.game_number = game_number

                    game.status = 'completed'
                    game.team1_score = result['team1_score']
                    game.team2_score = result['team2_score']
                    game.winner = result['team1'].name if result['team1_score'] > result['team2_score'] else result['team2'].name
                    game.is_upset = result.get('upset', False)

                    # Serialize stats details
                    details = {
                        'team1_stats': str(result['team1_detail']),
                        'team2_stats': str(result['team2_detail']),
                        'team1_player_stats': result.get('team1_player_stats', {}),
                        'team2_player_stats': result.get('team2_player_stats', {})
                    }
                    game.details = json.dumps(details)

                    # Settle Bets for this game
                    _settle_bets_for_game(game, result)
                except Exception as e:
                    logger.error(f"Error processing game result item: {e}", exc_info=True)
                    print(f"Error processing game result: {e}")
                    continue

            db.session.commit()
            logger.info(f"Uploaded Week {week} data and settled bets.")
            print(f"Uploaded Week {week} data and settled bets.")
    except Exception as e:
        logger.error(f"Error uploading game data: {e}", exc_info=True)
        raise

def _settle_bets_for_game(game, result):
    """
    Internal function to settle bets for a specific game result.
    Handles all bet types: moneyline, spread, total, team_total, player_prop, team_prop
    """
    import json
    
    try:
        pending_bets = Bet.query.filter_by(game_id=game.id, status='pending').all()
    except Exception as e:
        # Check if it's a missing column issue
        if "no such column" in str(e).lower() and "line_value" in str(e).lower():
            logger.warning("Bet table missing line_value column, running migration...")
            migrate_bet_table()
            # Retry query after migration
            pending_bets = Bet.query.filter_by(game_id=game.id, status='pending').all()
        else:
            raise
    
    try:
        logger.debug(f"Settling {len(pending_bets)} bets for game {game.id}")

        # Extract player stats from result if available, fallback to game.details
        team1_player_stats = result.get('team1_player_stats', {})
        team2_player_stats = result.get('team2_player_stats', {})
        team1_detail = result.get('team1_detail')
        team2_detail = result.get('team2_detail')
        
        # Fallback: try to get from game.details JSON if not in result
        if not team1_player_stats or not team2_player_stats:
            try:
                if game.details:
                    details_dict = json.loads(game.details)
                    if not team1_player_stats:
                        team1_player_stats = details_dict.get('team1_player_stats', {})
                    if not team2_player_stats:
                        team2_player_stats = details_dict.get('team2_player_stats', {})
            except:
                pass
        
        # Calculate actual spread
        actual_spread = game.team1_score - game.team2_score
        total_score = game.team1_score + game.team2_score

        for bet in pending_bets:
            try:
                won = False
                push = False

                if bet.bet_type == 'moneyline':
                    if bet.selection == game.winner:
                        won = True

                elif bet.bet_type == 'spread':
                    # selection is team name, line_value is the spread (e.g., -5.5)
                    if bet.line_value is not None:
                        selected_team = bet.selection
                        spread_line = bet.line_value
                        
                        # Determine if selected team covered
                        if selected_team == game.team1:
                            # Team1 bet: need team1_score - team2_score > spread_line (if spread_line positive) or < spread_line (if negative)
                            if spread_line > 0:  # Team1 favored
                                won = actual_spread > spread_line
                            else:  # Team1 underdog
                                won = actual_spread > abs(spread_line)
                        elif selected_team == game.team2:
                            # Team2 bet: need team2_score - team1_score > spread_line
                            team2_spread = -actual_spread
                            if spread_line > 0:  # Team2 favored
                                won = team2_spread > spread_line
                            else:  # Team2 underdog
                                won = team2_spread > abs(spread_line)
                        
                        # Check for push (exact spread)
                        if abs(actual_spread - spread_line) < 0.1:  # Allow small floating point error
                            push = True

                elif bet.bet_type == 'total':
                    # selection is "Over" or "Under", line_value is the total line
                    if bet.line_value is not None:
                        direction = bet.selection
                        line = bet.line_value
                        
                        if direction == 'Over':
                            if total_score > line:
                                won = True
                            elif total_score == line:
                                push = True
                        elif direction == 'Under':
                            if total_score < line:
                                won = True
                            elif total_score == line:
                                push = True

                elif bet.bet_type == 'team_total':
                    # selection is "TeamName Over" or "TeamName Under", line_value is the team total line
                    if bet.line_value is not None:
                        parts = bet.selection.split(' ', 1)
                        if len(parts) == 2:
                            team_name, direction = parts
                            line = bet.line_value
                            
                            team_score = game.team1_score if team_name == game.team1 else game.team2_score
                            
                            if direction == 'Over':
                                if team_score > line:
                                    won = True
                                elif team_score == line:
                                    push = True
                            elif direction == 'Under':
                                if team_score < line:
                                    won = True
                                elif team_score == line:
                                    push = True

                elif bet.bet_type == 'player_prop':
                    # selection contains player name and prop info (e.g., "PlayerName_points_ou_Over")
                    # line_value is the line
                    if bet.line_value is not None:
                        try:
                            # Parse selection: format is "PlayerName_propType_Over" or "PlayerName_propType_Under"
                            parts = bet.selection.split('_')
                            if len(parts) >= 3:
                                player_name = parts[0]
                                prop_type = '_'.join(parts[1:-1])  # Handle multi-part prop types
                                direction = parts[-1]
                                line = bet.line_value
                                
                                # Find player stats
                                player_stats = None
                                if player_name in team1_player_stats:
                                    player_stats = team1_player_stats[player_name]
                                elif player_name in team2_player_stats:
                                    player_stats = team2_player_stats[player_name]
                                
                                if player_stats:
                                    value = 0
                                    if prop_type == 'points_ou':
                                        value = player_stats.get('points', 0)
                                    elif prop_type == 'runs_attempted_ou':
                                        value = player_stats.get('runs_attempted', 0)
                                    elif prop_type == 'throws_attempted_ou':
                                        value = player_stats.get('throws_attempted', 0)
                                    elif prop_type == 'kicks_attempted_ou':
                                        value = player_stats.get('kicks_attempted', 0)
                                    elif prop_type == 'runs_completed_ou':
                                        value = player_stats.get('runs_completed', 0)
                                    elif prop_type == 'throws_completed_ou':
                                        value = player_stats.get('throws_completed', 0)
                                    elif prop_type == 'kicks_completed_ou':
                                        value = player_stats.get('kicks_completed', 0)
                                    elif prop_type == 'cascades_ou':
                                        value = (player_stats.get('cascade_runs', 0) + 
                                                player_stats.get('cascade_throws', 0) + 
                                                player_stats.get('cascade_kicks', 0))
                                    
                                    if direction == 'Over':
                                        if value > line:
                                            won = True
                                        elif value == line:
                                            push = True
                                    elif direction == 'Under':
                                        if value < line:
                                            won = True
                                        elif value == line:
                                            push = True
                        except Exception as e:
                            logger.warning(f"Error parsing player prop bet {bet.id}: {e}")

                elif bet.bet_type == 'team_prop':
                    # Various team props: first_score, most_common_method, cascade, etc.
                    try:
                        prop_parts = bet.selection.split('_')
                        prop_category = prop_parts[0] if prop_parts else ''
                        
                        if prop_category == 'first_score':
                            # Format: "first_score_team1_run" or "first_score_team2_kick"
                            if len(prop_parts) >= 3:
                                team_key = prop_parts[1]  # team1 or team2
                                score_type = prop_parts[2]  # run, throw, kick
                                
                                # Determine first score from game details
                                # This is approximate since we don't track exact order
                                # We'll use a heuristic based on which team scored first and their best stat
                                first_team_scored = game.team1 if game.team1_score > 0 else game.team2
                                # Check if the prop matches (simplified check)
                                if (team_key == 'team1' and first_team_scored == game.team1) or \
                                   (team_key == 'team2' and first_team_scored == game.team2):
                                    # Further check score type - use team's best stat as proxy
                                    # This is an approximation
                                    won = True  # Simplified - would need better tracking
                        
                        elif prop_category == 'cascade':
                            # Format: "cascade_yes" or "cascade_no"
                            if len(prop_parts) >= 2:
                                direction = prop_parts[1]
                                # Check if cascades occurred
                                cascades_occurred = False
                                if team1_detail:
                                    cascades_occurred = (team1_detail.cascade_runs > 0 or 
                                                        team1_detail.cascade_throws > 0 or 
                                                        team1_detail.cascade_kicks > 0)
                                if not cascades_occurred and team2_detail:
                                    cascades_occurred = (team2_detail.cascade_runs > 0 or 
                                                        team2_detail.cascade_throws > 0 or 
                                                        team2_detail.cascade_kicks > 0)
                                
                                if direction == 'yes' and cascades_occurred:
                                    won = True
                                elif direction == 'no' and not cascades_occurred:
                                    won = True
                        
                        elif prop_category == 'most_common':
                            # Format: "most_common_method_Run" or similar
                            if len(prop_parts) >= 3 and team1_detail and team2_detail:
                                predicted_method = prop_parts[-1]
                                
                                # Count actual methods
                                total_runs = team1_detail.runs + team2_detail.runs
                                total_throws = team1_detail.throws + team2_detail.throws
                                total_kicks = team1_detail.kicks + team2_detail.kicks
                                
                                actual_method = 'Run'
                                if total_throws > total_runs and total_throws > total_kicks:
                                    actual_method = 'Throw'
                                elif total_kicks > total_runs and total_kicks > total_throws:
                                    actual_method = 'Kick'
                                
                                if predicted_method == actual_method:
                                    won = True
                        
                        elif prop_category == 'margin':
                            # Format: "margin_team1_1_5" or "margin_team2_11_plus"
                            if len(prop_parts) >= 3:
                                margin_team = prop_parts[1]  # team1 or team2
                                margin_range = '_'.join(prop_parts[2:])  # e.g., "1_5", "6_10", "11_plus"
                                
                                margin = abs(actual_spread) if margin_team == 'team1' else abs(-actual_spread)
                                
                                if margin_range == '1_5' and 1 <= margin <= 5:
                                    won = True
                                elif margin_range == '6_10' and 6 <= margin <= 10:
                                    won = True
                                elif margin_range == '11_plus' and margin >= 11:
                                    won = True
                    except Exception as e:
                        logger.warning(f"Error parsing team prop bet {bet.id}: {e}")

                # Handle bet outcome
                if push:
                    bet.status = 'push'
                    # Refund bet amount (only for single bets, not parlays)
                    if not bet.parlay_id:
                        user = User.query.get(bet.user_id)
                        if user:
                            user.tokens += bet.amount
                            trans = Transaction(user_id=user.id, amount=bet.amount,
                                                description=f"Push bet on Game {game.id} - refund")
                            db.session.add(trans)
                elif won:
                    bet.status = 'won'
                    # Only pay out single bets here (parlays handled separately)
                    if not bet.parlay_id:
                        user = User.query.get(bet.user_id)
                        if user:
                            user.tokens += bet.potential_payout
                            trans = Transaction(user_id=user.id, amount=bet.potential_payout,
                                                description=f"Won bet on Game {game.id}")
                            db.session.add(trans)
                            logger.info(f"Bet {bet.id} won: User {user.id} gained {bet.potential_payout} tokens")
                    else:
                        logger.debug(f"Bet {bet.id} won (part of parlay {bet.parlay_id})")
                else:
                    bet.status = 'lost'
                    logger.debug(f"Bet {bet.id} lost")
                    
            except Exception as e:
                logger.error(f"Error settling bet {bet.id}: {e}", exc_info=True)
                continue
        
        # Settle parlays that involve bets from this game
        _settle_parlays_for_game(game.id)
        
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error in _settle_bets_for_game: {e}", exc_info=True)
        raise


def _settle_parlays_for_game(game_id):
    """
    Check and settle parlays that contain bets from the specified game.
    """
    from webapp.database import Parlay
    import json
    
    try:
        # Find all parlays that have bets from this game
        bets_in_game = Bet.query.filter_by(game_id=game_id).all()
        parlay_ids = set([bet.parlay_id for bet in bets_in_game if bet.parlay_id])
        
        for parlay_id in parlay_ids:
            parlay = Parlay.query.get(parlay_id)
            if not parlay or parlay.status != 'pending':
                continue
            
            # Get all bets in this parlay
            try:
                bet_ids = json.loads(parlay.bet_ids)
            except:
                continue
            
            parlay_bets = Bet.query.filter(Bet.id.in_(bet_ids)).all()
            
            # Check status of all bets
            all_won = True
            any_lost = False
            any_pending = False
            
            for bet in parlay_bets:
                if bet.status == 'pending':
                    any_pending = True
                    break
                elif bet.status == 'lost' or bet.status == 'push':  # Push counts as loss in parlay
                    any_lost = True
                elif bet.status != 'won':
                    all_won = False
            
            # Only settle if all bets are no longer pending
            if not any_pending:
                if all_won and not any_lost:
                    # Parlay wins
                    parlay.status = 'won'
                    user = User.query.get(parlay.user_id)
                    if user:
                        user.tokens += parlay.potential_payout
                        trans = Transaction(user_id=user.id, amount=parlay.potential_payout,
                                            description=f"Won parlay {parlay.id}")
                        db.session.add(trans)
                        logger.info(f"Parlay {parlay.id} won: User {user.id} gained {parlay.potential_payout} tokens")
                else:
                    # Parlay loses
                    parlay.status = 'lost'
                    logger.debug(f"Parlay {parlay.id} lost")
                    
    except Exception as e:
        logger.error(f"Error settling parlays for game {game_id}: {e}", exc_info=True)

def precalculate_betting_lines_for_week(season_id, week):
    """
    Pre-calculate and store betting lines for all scheduled games in a specific week.
    This function loads teams from game_state.json and generates betting lines for each game.
    Should be called in a background thread to avoid blocking the simulation.
    
    Args:
        season_id: The season ID
        week: The week number to calculate betting lines for
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            # Load teams from game_state.json (same logic as /betting route)
            teams_dict = {}
            # game_state.json is in the project root
            project_root = os.path.dirname(os.path.abspath(__file__))
            state_file = os.path.join(project_root, 'game_state.json')
            
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    from game_logic import Team
                    for team_data in state_data.get('teams', []):
                        team = Team(team_data['name'])
                        team.overall_advantage = team_data.get('overall_advantage', 0)
                        team.run_advantage = team_data.get('run_advantage', 0)
                        team.throw_advantage = team_data.get('throw_advantage', 0)
                        team.kick_advantage = team_data.get('kick_advantage', 0)
                        team.wins = team_data.get('wins', 0)
                        team.losses = team_data.get('losses', 0)
                        team.points_for = team_data.get('points_for', 0)
                        team.points_against = team_data.get('points_against', 0)
                        if 'players' in team_data:
                            team.players = team_data['players']
                        teams_dict[team.name] = team
                    logger.info(f"Loaded {len(teams_dict)} teams from game_state.json for betting lines calculation")
                except Exception as e:
                    logger.error(f"Error loading teams for odds calculation: {e}", exc_info=True)
                    return
            
            # Query all scheduled games for this week
            games = Game.query.filter_by(season_id=season_id, week=week, status='scheduled').all()
            logger.info(f"Pre-calculating betting lines for {len(games)} games in Week {week}")
            
            if not games:
                logger.info(f"No scheduled games found for Week {week}")
                return
            
            # Import betting line generation functions
            from game_logic import (
                generate_betting_lines, 
                generate_player_prop_odds, 
                generate_first_score_props, 
                generate_margin_props
            )
            
            games_processed = 0
            games_skipped = 0
            games_error = 0
            
            # Generate betting lines for each game
            # Strategy: 10 official "vegas-style" bets per week
            # - Moneylines for all games (8 bets: 2 per game × 4 games)
            # - Spreads for first 2 games (2 bets: favorite spread for 2 games)
            # Total: 10 official bets using 1000 simulations, rest use faster calculation
            for idx, game in enumerate(games):
                try:
                    # Skip if betting lines already exist
                    if game.betting_lines:
                        games_skipped += 1
                        continue
                    
                    team1_obj = teams_dict.get(game.team1)
                    team2_obj = teams_dict.get(game.team2)
                    
                    if not team1_obj or not team2_obj:
                        logger.warning(f"Teams not found for game {game.id}: {game.team1} vs {game.team2}")
                        games_error += 1
                        continue
                    
                    # Generate main betting lines
                    # All games get official moneylines (1000 sims), first 2 games also get official spreads
                    is_official_main_lines = True  # All games get official moneylines
                    is_official_spread = (idx < 2)  # First 2 games get official spreads
                    lines_data = generate_betting_lines(team1_obj, team2_obj, is_official=is_official_main_lines)
                    
                    # Generate player props for all players
                    player_props = {}
                    
                    # Team 1 players
                    if team1_obj.players:
                        for player in team1_obj.players:
                            player_name = player.get('name')
                            props_to_generate = [
                                ('points_ou', 12.5),
                                ('runs_completed_ou', 1.5),
                                ('throws_completed_ou', 2.5),
                                ('kicks_completed_ou', 3.5),
                                ('cascades_ou', 0.5)
                            ]
                            for prop_type, line_val in props_to_generate:
                                # Player props are not official bets, use fast calculation
                                odds = generate_player_prop_odds(player_name, team1_obj, team2_obj, prop_type, line_val, is_official=False)
                                key = f"{player_name}_{prop_type}_{line_val}"
                                player_props[key] = {
                                    'player': player_name,
                                    'team': team1_obj.name,
                                    'prop_type': prop_type,
                                    'line_value': line_val,
                                    'over_odds': odds['over_odds'],
                                    'under_odds': odds['under_odds'],
                                    'is_official': False
                                }
                    
                    # Team 2 players
                    if team2_obj.players:
                        for player in team2_obj.players:
                            player_name = player.get('name')
                            props_to_generate = [
                                ('points_ou', 12.5),
                                ('runs_completed_ou', 1.5),
                                ('throws_completed_ou', 2.5),
                                ('kicks_completed_ou', 3.5),
                                ('cascades_ou', 0.5)
                            ]
                            for prop_type, line_val in props_to_generate:
                                # Player props are not official bets, use fast calculation
                                odds = generate_player_prop_odds(player_name, team2_obj, team1_obj, prop_type, line_val, is_official=False)
                                key = f"{player_name}_{prop_type}_{line_val}"
                                player_props[key] = {
                                    'player': player_name,
                                    'team': team2_obj.name,
                                    'prop_type': prop_type,
                                    'line_value': line_val,
                                    'over_odds': odds['over_odds'],
                                    'under_odds': odds['under_odds'],
                                    'is_official': False
                                }
                    
                    # Generate team props
                    first_score_props = generate_first_score_props(team1_obj, team2_obj)
                    margin_props = generate_margin_props(team1_obj, team2_obj)
                    
                    # Combine all betting lines
                    # Mark official bets: moneylines for all games, spreads for first 2 games
                    all_lines = {
                        'moneyline': lines_data['moneyline'],  # Keep tuple format for backwards compatibility
                        'moneyline_is_official': True,  # All moneylines are official (vegas-style)
                        'spread': {
                            'value': lines_data['spread_value'],
                            'favorite': lines_data['favorite'].name,
                            'underdog': lines_data['underdog'].name,
                            'favorite_odds': lines_data['spread_fav_odds'],
                            'underdog_odds': lines_data['spread_dog_odds'],
                            'is_official': is_official_spread  # Only first 2 games
                        },
                        'total': {
                            'value': lines_data['total'],
                            'over_odds': -110,
                            'under_odds': -110,
                            'is_official': False
                        },
                        'team_totals': {
                            'team1': {
                                'value': lines_data['team1_total'],
                                'over_odds': -110,
                                'under_odds': -110,
                                'is_official': False
                            },
                            'team2': {
                                'value': lines_data['team2_total'],
                                'over_odds': -110,
                                'under_odds': -110,
                                'is_official': False
                            }
                        },
                        'player_props': player_props,
                        'first_score': first_score_props,
                        'margin': margin_props,
                        'cascade': {
                            'yes_odds': lines_data['cascade_yes_odds'],
                            'no_odds': -200,  # Default, will be calculated from yes_odds
                            'is_official': False
                        },
                        'most_common_method': lines_data['most_common_method']
                    }
                    
                    # Store in database
                    game.betting_lines = json.dumps(all_lines)
                    games_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error generating betting lines for game {game.id} ({game.team1} vs {game.team2}): {e}", exc_info=True)
                    games_error += 1
                    continue
            
            # Commit all changes at once
            if games_processed > 0:
                db.session.commit()
                logger.info(f"Pre-calculated betting lines for Week {week}: {games_processed} games processed, {games_skipped} skipped (already existed), {games_error} errors")
            else:
                logger.info(f"Pre-calculation for Week {week} complete: {games_skipped} skipped (already existed), {games_error} errors")
                
    except Exception as e:
        logger.error(f"Error in precalculate_betting_lines_for_week for Week {week}: {e}", exc_info=True)
        # Don't raise - this is called in a background thread and errors shouldn't break simulation


def update_game_gemini_image(season_id, week, game_number, gemini_image_path, team1_name=None, team2_name=None):
    """
    Update a Game record with the gemini_image_path.
    
    Args:
        season_id: ID of the season
        week: Week number
        game_number: Game number (optional)
        gemini_image_path: Relative path to the Gemini image (e.g., "season_3/week_1_game_1_gemini.png")
        team1_name: Optional team1 name to help identify the game
        team2_name: Optional team2 name to help identify the game
    
    Returns:
        True if successful, False otherwise
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            # Try to find the game
            game = None
            
            if game_number is not None:
                # Try with game_number first
                query = Game.query.filter_by(
                    season_id=season_id,
                    week=week,
                    game_number=game_number
                )
                
                # Add team filters if provided
                if team1_name and team2_name:
                    query = query.filter(
                        ((Game.team1 == team1_name) & (Game.team2 == team2_name)) |
                        ((Game.team1 == team2_name) & (Game.team2 == team1_name))
                    )
                
                game = query.first()
            
            # Fallback: try without game_number
            if not game and team1_name and team2_name:
                game = Game.query.filter_by(
                    season_id=season_id,
                    week=week
                ).filter(
                    ((Game.team1 == team1_name) & (Game.team2 == team2_name)) |
                    ((Game.team1 == team2_name) & (Game.team2 == team1_name))
                ).first()
            
            if game:
                game.gemini_image_path = gemini_image_path
                db.session.commit()
                logger.info(f"Updated Game {game.id} with gemini_image_path: {gemini_image_path}")
                return True
            else:
                logger.warning(f"Could not find Game record for season_id={season_id}, week={week}, game_number={game_number}")
                return False
                
    except Exception as e:
        logger.error(f"Error updating game gemini image path: {e}", exc_info=True)
        return False

def get_player_season_stats(player_name, team_name, season_id=None):
    """
    Fetch season statistics for a specific player from the database.
    
    Args:
        player_name: Name of the player
        team_name: Name of the player's team
        season_id: Optional season ID (uses active season if None)
        
    Returns:
        Dictionary with player season stats:
        - points: Total points
        - points_per_game: Average points per game
        - runs_attempted, runs_completed: Run statistics
        - throws_attempted, throws_completed: Throw statistics
        - kicks_attempted, kicks_completed: Kick statistics
        - cascade_runs, cascade_throws, cascade_kicks: Cascade statistics
        - games_played: Number of games
        - success_rate: Overall success rate percentage
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            # Get season
            if season_id:
                active_season = Season.query.get(season_id)
            else:
                active_season = Season.query.filter_by(is_active=True).first()
            
            if not active_season:
                return None
            
            # Query completed games for this season
            games = Game.query.filter_by(season_id=active_season.id, status='completed')\
                              .order_by(Game.week, Game.game_number).all()
            
            # Aggregate player stats
            stats = {
                'points': 0,
                'runs_attempted': 0, 'runs_completed': 0, 'cascade_runs': 0,
                'throws_attempted': 0, 'throws_completed': 0, 'cascade_throws': 0,
                'kicks_attempted': 0, 'kicks_completed': 0, 'cascade_kicks': 0,
                'games_played': 0
            }
            
            for game in games:
                if not game.details:
                    continue
                
                try:
                    details = json.loads(game.details)
                    
                    # Check team1 players
                    if game.team1 == team_name:
                        team_players = details.get('team1_player_stats', {})
                        for player_key, player_stats in team_players.items():
                            player_name_from_stats = player_stats.get('player_name') or player_stats.get('name') or player_key
                            if player_name_from_stats == player_name:
                                stats['points'] += player_stats.get('points', 0)
                                stats['runs_attempted'] += player_stats.get('runs_attempted', 0)
                                stats['runs_completed'] += player_stats.get('runs_completed', 0)
                                stats['cascade_runs'] += player_stats.get('cascade_runs', 0)
                                stats['throws_attempted'] += player_stats.get('throws_attempted', 0)
                                stats['throws_completed'] += player_stats.get('throws_completed', 0)
                                stats['cascade_throws'] += player_stats.get('cascade_throws', 0)
                                stats['kicks_attempted'] += player_stats.get('kicks_attempted', 0)
                                stats['kicks_completed'] += player_stats.get('kicks_completed', 0)
                                stats['cascade_kicks'] += player_stats.get('cascade_kicks', 0)
                                stats['games_played'] += 1
                                break
                    
                    # Check team2 players
                    elif game.team2 == team_name:
                        team_players = details.get('team2_player_stats', {})
                        for player_key, player_stats in team_players.items():
                            player_name_from_stats = player_stats.get('player_name') or player_stats.get('name') or player_key
                            if player_name_from_stats == player_name:
                                stats['points'] += player_stats.get('points', 0)
                                stats['runs_attempted'] += player_stats.get('runs_attempted', 0)
                                stats['runs_completed'] += player_stats.get('runs_completed', 0)
                                stats['cascade_runs'] += player_stats.get('cascade_runs', 0)
                                stats['throws_attempted'] += player_stats.get('throws_attempted', 0)
                                stats['throws_completed'] += player_stats.get('throws_completed', 0)
                                stats['cascade_throws'] += player_stats.get('cascade_throws', 0)
                                stats['kicks_attempted'] += player_stats.get('kicks_attempted', 0)
                                stats['kicks_completed'] += player_stats.get('kicks_completed', 0)
                                stats['cascade_kicks'] += player_stats.get('cascade_kicks', 0)
                                stats['games_played'] += 1
                                break
                except Exception as e:
                    continue
            
            # Calculate derived stats
            if stats['games_played'] > 0:
                stats['points_per_game'] = round(stats['points'] / stats['games_played'], 1)
            else:
                stats['points_per_game'] = 0.0
            
            total_attempts = stats['runs_attempted'] + stats['throws_attempted'] + stats['kicks_attempted']
            total_completions = stats['runs_completed'] + stats['throws_completed'] + stats['kicks_completed']
            
            if total_attempts > 0:
                stats['success_rate'] = round((total_completions / total_attempts) * 100, 1)
            else:
                stats['success_rate'] = 0.0
            
            return stats
            
    except Exception as e:
        logger.error(f"Error fetching player season stats for {player_name}: {e}", exc_info=True)
        return None


def get_team_analytics(team1_name, team2_name, season_id=None):
    """
    Fetch team analytics from the database for two teams.
    Similar to the analytics() route in app.py but returns data for specific teams.
    
    Args:
        team1_name: Name of first team
        team2_name: Name of second team
        season_id: Optional season ID (uses active season if None)
        
    Returns:
        Dictionary with team1_stats and team2_stats, each containing:
        - games: Total games played
        - wins: Number of wins
        - losses: Number of losses (games - wins)
        - points_for: Total points scored
        - points_against: Total points allowed
        - win_percentage: Win percentage (0-100)
        - avg_points_for: Average points per game
        - avg_points_against: Average points allowed per game
        - point_differential: Points for - points against
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            # Get season
            if season_id:
                active_season = Season.query.get(season_id)
            else:
                active_season = Season.query.filter_by(is_active=True).first()
            
            if not active_season:
                # Return empty stats if no season
                return {
                    'team1_stats': {
                        'games': 0, 'wins': 0, 'losses': 0,
                        'points_for': 0, 'points_against': 0,
                        'win_percentage': 0.0,
                        'avg_points_for': 0.0, 'avg_points_against': 0.0,
                        'point_differential': 0
                    },
                    'team2_stats': {
                        'games': 0, 'wins': 0, 'losses': 0,
                        'points_for': 0, 'points_against': 0,
                        'win_percentage': 0.0,
                        'avg_points_for': 0.0, 'avg_points_against': 0.0,
                        'point_differential': 0
                    }
                }
            
            # Initialize team stats
            team_stats = {
                team1_name: {'games': 0, 'wins': 0, 'points_for': 0, 'points_against': 0},
                team2_name: {'games': 0, 'wins': 0, 'points_for': 0, 'points_against': 0}
            }
            
            # Query completed games for this season
            games = Game.query.filter_by(season_id=active_season.id, status='completed')\
                              .order_by(Game.week, Game.game_number).all()
            
            # Aggregate stats from games
            for game in games:
                # Process team1 stats
                if game.team1 in team_stats:
                    team_stats[game.team1]['games'] += 1
                    if game.winner == game.team1:
                        team_stats[game.team1]['wins'] += 1
                    team_stats[game.team1]['points_for'] += game.team1_score
                    team_stats[game.team1]['points_against'] += game.team2_score
                
                # Process team2 stats
                if game.team2 in team_stats:
                    team_stats[game.team2]['games'] += 1
                    if game.winner == game.team2:
                        team_stats[game.team2]['wins'] += 1
                    team_stats[game.team2]['points_for'] += game.team2_score
                    team_stats[game.team2]['points_against'] += game.team1_score
            
            # Calculate derived stats for each team
            def format_team_stats(stats):
                games = stats['games']
                wins = stats['wins']
                losses = games - wins
                points_for = stats['points_for']
                points_against = stats['points_against']
                
                win_percentage = (wins / games * 100) if games > 0 else 0.0
                avg_points_for = (points_for / games) if games > 0 else 0.0
                avg_points_against = (points_against / games) if games > 0 else 0.0
                point_differential = points_for - points_against
                
                return {
                    'games': games,
                    'wins': wins,
                    'losses': losses,
                    'points_for': points_for,
                    'points_against': points_against,
                    'win_percentage': round(win_percentage, 1),
                    'avg_points_for': round(avg_points_for, 1),
                    'avg_points_against': round(avg_points_against, 1),
                    'point_differential': point_differential
                }
            
            team1_stats = format_team_stats(team_stats.get(team1_name, {'games': 0, 'wins': 0, 'points_for': 0, 'points_against': 0}))
            team2_stats = format_team_stats(team_stats.get(team2_name, {'games': 0, 'wins': 0, 'points_for': 0, 'points_against': 0}))
            
            return {
                'team1_stats': team1_stats,
                'team2_stats': team2_stats
            }
            
    except Exception as e:
        logger.error(f"Error fetching team analytics: {e}", exc_info=True)
        # Return empty stats on error
        return {
            'team1_stats': {
                'games': 0, 'wins': 0, 'losses': 0,
                'points_for': 0, 'points_against': 0,
                'win_percentage': 0.0,
                'avg_points_for': 0.0, 'avg_points_against': 0.0,
                'point_differential': 0
            },
            'team2_stats': {
                'games': 0, 'wins': 0, 'losses': 0,
                'points_for': 0, 'points_against': 0,
                'win_percentage': 0.0,
                'avg_points_for': 0.0, 'avg_points_against': 0.0,
                'point_differential': 0
            }
        }


def reset_season_tokens():
    """
    End of season: If tokens < 1000, set to 1000.
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            users = User.query.filter(User.tokens < 1000).all()
            reset_count = 0
            for user in users:
                diff = 1000 - user.tokens
                user.tokens = 1000
                trans = Transaction(user_id=user.id, amount=diff, description="Season Reset Bonus")
                db.session.add(trans)
                reset_count += 1
            db.session.commit()
            logger.info(f"Season tokens reset for {reset_count} users.")
            print(f"Season tokens reset for {reset_count} users.")
    except Exception as e:
        logger.error(f"Error resetting season tokens: {e}", exc_info=True)
        raise


def save_season_history(season_id, champion_team, season_folder_name):
    """
    Save season history when tournament completes.
    
    Args:
        season_id: ID of the season
        champion_team: Name of the tournament champion team
        season_folder_name: Name of the season folder (e.g., "season_3")
    
    Returns:
        True if successful, False otherwise
    """
    ensure_db_initialized()
    
    try:
        with app.app_context():
            # Check if history already exists for this season
            existing = SeasonHistory.query.filter_by(season_id=season_id).first()
            if existing:
                logger.info(f"Season history already exists for season {season_id}, skipping")
                return True
            
            # Get season to extract season number
            season = Season.query.get(season_id)
            if not season:
                logger.error(f"Season {season_id} not found")
                return False
            
            # Extract season number from season name (e.g., "Season 3" -> 3)
            season_number = 1
            try:
                season_num_str = season.name.split()[-1]
                season_number = int(season_num_str)
            except (ValueError, IndexError):
                # Fallback: try to extract from folder name
                try:
                    season_num_str = season_folder_name.split('_')[-1]
                    season_number = int(season_num_str)
                except (ValueError, IndexError):
                    logger.warning(f"Could not extract season number from '{season.name}' or '{season_folder_name}', using 1")
            
            # Find champion image
            champion_image_path = None
            season_folder_path = os.path.join(STATIC_ROOT, season_folder_name)
            
            if os.path.exists(season_folder_path):
                # First try: tournament_champion_trophy.png (Gemini trophy)
                trophy_path = os.path.join(season_folder_path, "tournament_champion_trophy.png")
                if os.path.exists(trophy_path):
                    champion_image_path = f"{season_folder_name}/tournament_champion_trophy.png"
                    logger.info(f"Found champion trophy image: {champion_image_path}")
                else:
                    # Fallback: Find last tournament_final_game_X_gemini.png
                    import glob
                    gemini_pattern = os.path.join(season_folder_path, "tournament_final_game_*_gemini.png")
                    gemini_files = glob.glob(gemini_pattern)
                    if gemini_files:
                        # Sort by game number (extract from filename) and get the last one
                        def extract_game_num(filename):
                            import re
                            match = re.search(r'_game_(\d+)_gemini', filename)
                            return int(match.group(1)) if match else 0
                        
                        gemini_files.sort(key=extract_game_num, reverse=True)
                        last_gemini = gemini_files[0]
                        # Get relative path
                        champion_image_path = os.path.relpath(last_gemini, STATIC_ROOT).replace('\\', '/')
                        logger.info(f"Found champion Gemini image (fallback): {champion_image_path}")
                    else:
                        logger.warning(f"No champion image found in {season_folder_path}")
            
            # Create SeasonHistory record
            season_history = SeasonHistory(
                season_id=season_id,
                champion_team=champion_team,
                champion_image_path=champion_image_path,
                season_number=season_number,
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.session.add(season_history)
            
            # Mark season as inactive
            season.is_active = False
            
            db.session.commit()
            logger.info(f"Saved season history for Season {season_number}: Champion={champion_team}, Image={champion_image_path}")
            print(f"Saved season history for Season {season_number}: Champion={champion_team}")
            return True
            
    except Exception as e:
        logger.error(f"Error saving season history: {e}", exc_info=True)
        print(f"Error saving season history: {e}")
        return False
