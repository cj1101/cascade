from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
import logging
import re
from PIL import Image

# Add parent directory to path so webapp can be imported as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.database import db, User, Season, Game, Bet, Transaction, Parlay, SimulationStatus, SeasonHistory
from sqlalchemy import func, inspect, text
import config

# Get absolute path to instance directory
basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
os.makedirs(instance_dir, exist_ok=True)
db_path = os.path.join(instance_dir, 'cascade.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-this-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Set up logger
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def index():
    import json
    active_season = Season.query.filter_by(is_active=True).first()
    # Get recent completed games for live feed
    recent_games = []
    if active_season:
        games = Game.query.filter_by(season_id=active_season.id, status='completed')\
                          .order_by(Game.id.desc()).limit(5).all()
        # Parse details JSON for each game
        for game in games:
            if game.details:
                try:
                    game.details_dict = json.loads(game.details)
                    # Ensure player stats are included (for backward compatibility)
                    if 'team1_player_stats' not in game.details_dict:
                        game.details_dict['team1_player_stats'] = {}
                    if 'team2_player_stats' not in game.details_dict:
                        game.details_dict['team2_player_stats'] = {}
                except:
                    game.details_dict = None
            else:
                game.details_dict = None
        recent_games = games

    return render_template('index.html', recent_games=recent_games, active_season=active_season)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('signup'))

        new_user = User(username=username,
                        password=generate_password_hash(password, method='scrypt'))
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('index'))

    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/betting')
@login_required
def betting():
    import json
    import os
    from game_logic import Team, generate_betting_lines, generate_player_prop_odds, generate_first_score_props, generate_margin_props, probability_to_american_odds
    
    active_season = Season.query.filter_by(is_active=True).first()
    upcoming_games = []
    
    if active_season:
        games = Game.query.filter_by(season_id=active_season.id, status='scheduled').all()
        
        # Load teams from game_state.json to calculate odds
        teams_dict = {}
        # game_state.json is in the project root, one level up from webapp
        state_file = os.path.join(os.path.dirname(basedir), 'game_state.json')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
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
            except Exception as e:
                print(f"Error loading teams for odds calculation: {e}")
        
        # First, load existing betting lines for games that have them
        games_with_lines = []
        games_needing_lines = []
        for game in games:
            if game.betting_lines:
                games_with_lines.append(game)
                try:
                    game.betting_lines_dict = json.loads(game.betting_lines)
                    game.team1_odds = int(game.betting_lines_dict.get('moneyline', [-110, -110])[0])
                    game.team2_odds = int(game.betting_lines_dict.get('moneyline', [-110, -110])[1])
                except:
                    game.betting_lines_dict = None
                    game.team1_odds = -110
                    game.team2_odds = -110
            else:
                games_needing_lines.append(game)
        
        # Betting lines should be pre-generated during simulation, not on-demand
        # If games are missing lines, log a warning but don't generate them here (would cause timeout)
        if games_needing_lines:
            logger.warning(f"{len(games_needing_lines)} games are missing betting lines. They should be pre-generated during simulation.")
            # Set default odds for games without lines so the page still loads
            for game in games_needing_lines:
                game.team1_odds = -110
                game.team2_odds = -110
                game.betting_lines_dict = None
        
        # Use only games that have betting lines (or default fallback)
        games_to_display = games_with_lines + games_needing_lines
        
        # OLD CODE REMOVED: On-demand betting line generation removed to prevent timeouts
        # Betting lines are now pre-generated during schedule upload
        
        # REMOVED: The entire on-demand generation loop that was causing timeouts
        # Games should have betting lines pre-generated during simulation
        # If they don't, they'll show with default odds (-110)
        
        # OLD GENERATION CODE REMOVED - was here but caused 37+ second timeouts
        # The generation loop has been completely removed
        
        # All games should now have betting lines pre-generated
        # If any are missing, they'll use default odds (-110) so the page still loads
        
        # Use games that have lines (or default fallback for missing ones)
        all_games = games_to_display
        
        # Convert games to dictionaries for template
        games_data = []
        for game in all_games:
            game_dict = {
                'id': game.id,
                'week': game.week,
                'game_number': game.game_number,
                'team1': game.team1,
                'team2': game.team2,
                'team1_odds': getattr(game, 'team1_odds', -110),
                'team2_odds': getattr(game, 'team2_odds', -110),
                'betting_lines': game.betting_lines,
                'betting_lines_dict': getattr(game, 'betting_lines_dict', None)
            }
            games_data.append(game_dict)
        
        upcoming_games = games_data

    return render_template('betting.html', games=upcoming_games, user=current_user)

@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.tokens.desc()).all()
    
    # Calculate tokens bet and tokens distributed for each user
    user_stats = []
    for user in users:
        # Sum all bet amounts for this user
        tokens_bet = db.session.query(func.sum(Bet.amount)).filter(
            Bet.user_id == user.id
        ).scalar() or 0
        
        # Sum all potential payouts from won bets for this user
        tokens_distributed = db.session.query(func.sum(Bet.potential_payout)).filter(
            Bet.user_id == user.id,
            Bet.status == 'won'
        ).scalar() or 0
        
        user_stats.append({
            'user': user,
            'tokens_bet': int(tokens_bet),
            'tokens_distributed': int(tokens_distributed)
        })
    
    return render_template('leaderboard.html', user_stats=user_stats)

@app.route('/player_analytics/<int:user_id>')
def player_analytics(user_id):
    """Display comprehensive betting analytics for a specific user"""
    # Get user
    user = User.query.get_or_404(user_id)
    
    # Get all settled bets (exclude pending and parlays)
    all_bets = Bet.query.filter(
        Bet.user_id == user_id,
        Bet.status.in_(['won', 'lost', 'push']),
        Bet.parlay_id.is_(None)
    ).all()
    
    if not all_bets:
        # No bets yet, return empty analytics
        return render_template('player_analytics.html', 
                             user=user,
                             financial={},
                             performance={},
                             by_bet_type={},
                             patterns={})
    
    # Financial Metrics
    total_won = sum(b.potential_payout for b in all_bets if b.status == 'won')
    total_lost = sum(b.amount for b in all_bets if b.status == 'lost')
    net_profit = total_won - total_lost
    total_bet = sum(b.amount for b in all_bets)
    avg_bet_size = total_bet / len(all_bets) if all_bets else 0
    
    won_bets = [b for b in all_bets if b.status == 'won']
    lost_bets = [b for b in all_bets if b.status == 'lost']
    largest_win = max((b.potential_payout for b in won_bets), default=0)
    largest_loss = max((b.amount for b in lost_bets), default=0)
    
    roi = ((total_won - total_lost) / total_bet * 100) if total_bet > 0 else 0
    
    financial = {
        'total_won': int(total_won),
        'total_lost': int(total_lost),
        'net_profit': int(net_profit),
        'roi': round(roi, 2),
        'total_bet': int(total_bet),
        'avg_bet_size': round(avg_bet_size, 2),
        'largest_win': int(largest_win),
        'largest_loss': int(largest_loss)
    }
    
    # Performance Metrics
    wins = len(won_bets)
    losses = len(lost_bets)
    pushes = len([b for b in all_bets if b.status == 'push'])
    total_settled = wins + losses + pushes
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    
    performance = {
        'total_bets': len(all_bets),
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'win_rate': round(win_rate, 2)
    }
    
    # Performance by Bet Type
    bet_types = ['moneyline', 'spread', 'total', 'team_total', 'player_prop', 'team_prop']
    by_bet_type = {}
    
    for bet_type in bet_types:
        type_bets = [b for b in all_bets if b.bet_type == bet_type]
        if type_bets:
            type_wins = len([b for b in type_bets if b.status == 'won'])
            type_losses = len([b for b in type_bets if b.status == 'lost'])
            type_pushes = len([b for b in type_bets if b.status == 'push'])
            type_win_rate = (type_wins / (type_wins + type_losses) * 100) if (type_wins + type_losses) > 0 else 0
            
            by_bet_type[bet_type] = {
                'wins': type_wins,
                'losses': type_losses,
                'pushes': type_pushes,
                'win_rate': round(type_win_rate, 2),
                'total': len(type_bets)
            }
    
    # Patterns: Best/Worst Bet Type
    best_bet_type = None
    worst_bet_type = None
    best_win_rate = -1
    worst_win_rate = 101
    
    for bet_type, stats in by_bet_type.items():
        if stats['wins'] + stats['losses'] >= 5:  # Minimum threshold
            if stats['win_rate'] > best_win_rate:
                best_win_rate = stats['win_rate']
                best_bet_type = bet_type
            if stats['win_rate'] < worst_win_rate:
                worst_win_rate = stats['win_rate']
                worst_bet_type = bet_type
    
    # Team Performance (for moneyline and spread bets)
    team_performance = {}
    ml_spread_bets = [b for b in all_bets if b.bet_type in ['moneyline', 'spread']]
    
    for bet in ml_spread_bets:
        team = bet.selection
        if team not in team_performance:
            team_performance[team] = {'wins': 0, 'losses': 0, 'pushes': 0}
        if bet.status == 'won':
            team_performance[team]['wins'] += 1
        elif bet.status == 'lost':
            team_performance[team]['losses'] += 1
        elif bet.status == 'push':
            team_performance[team]['pushes'] += 1
    
    # Calculate win rates for teams
    team_win_rates = {}
    for team, stats in team_performance.items():
        total = stats['wins'] + stats['losses']
        if total > 0:
            team_win_rates[team] = round((stats['wins'] / total * 100), 2)
        else:
            team_win_rates[team] = 0
    
    # Over/Under Performance (for totals and team_totals)
    over_under_stats = {'over': {'wins': 0, 'losses': 0}, 'under': {'wins': 0, 'losses': 0}}
    total_bets_list = [b for b in all_bets if b.bet_type in ['total', 'team_total']]
    
    for bet in total_bets_list:
        if bet.status == 'push':
            continue
        selection_lower = bet.selection.lower()
        if 'over' in selection_lower:
            if bet.status == 'won':
                over_under_stats['over']['wins'] += 1
            else:
                over_under_stats['over']['losses'] += 1
        elif 'under' in selection_lower:
            if bet.status == 'won':
                over_under_stats['under']['wins'] += 1
            else:
                over_under_stats['under']['losses'] += 1
    
    over_total = over_under_stats['over']['wins'] + over_under_stats['over']['losses']
    under_total = over_under_stats['under']['wins'] + over_under_stats['under']['losses']
    over_rate = (over_under_stats['over']['wins'] / over_total * 100) if over_total > 0 else 0
    under_rate = (over_under_stats['under']['wins'] / under_total * 100) if under_total > 0 else 0
    
    # Favorite vs Underdog Performance (for moneylines)
    favorite_stats = {'wins': 0, 'losses': 0}
    underdog_stats = {'wins': 0, 'losses': 0}
    ml_bets = [b for b in all_bets if b.bet_type == 'moneyline']
    
    for bet in ml_bets:
        if bet.status == 'push':
            continue
        # Negative odds = favorite, positive odds = underdog
        if bet.odds < 0:
            if bet.status == 'won':
                favorite_stats['wins'] += 1
            else:
                favorite_stats['losses'] += 1
        else:
            if bet.status == 'won':
                underdog_stats['wins'] += 1
            else:
                underdog_stats['losses'] += 1
    
    fav_total = favorite_stats['wins'] + favorite_stats['losses']
    dog_total = underdog_stats['wins'] + underdog_stats['losses']
    fav_rate = (favorite_stats['wins'] / fav_total * 100) if fav_total > 0 else 0
    dog_rate = (underdog_stats['wins'] / dog_total * 100) if dog_total > 0 else 0
    
    patterns = {
        'best_bet_type': best_bet_type,
        'worst_bet_type': worst_bet_type,
        'team_performance': team_win_rates,
        'team_detailed': team_performance,
        'over_under': {
            'over': round(over_rate, 2),
            'under': round(under_rate, 2),
            'over_count': over_under_stats['over']['wins'] + over_under_stats['over']['losses'],
            'under_count': over_under_stats['under']['wins'] + over_under_stats['under']['losses']
        },
        'favorite_vs_underdog': {
            'favorite': round(fav_rate, 2),
            'underdog': round(dog_rate, 2),
            'favorite_count': fav_total,
            'underdog_count': dog_total
        }
    }
    
    return render_template('player_analytics.html',
                         user=user,
                         financial=financial,
                         performance=performance,
                         by_bet_type=by_bet_type,
                         patterns=patterns)

@app.route('/franchise_history')
def franchise_history():
    """Display all completed seasons with tournament winners"""
    import json
    seasons_history = SeasonHistory.query.order_by(SeasonHistory.season_number.desc()).all()
    
    # Build list with image URLs
    seasons_data = []
    for season_hist in seasons_history:
        image_url = None
        if season_hist.champion_image_path:
            image_url = url_for('static', filename=season_hist.champion_image_path)
        
        seasons_data.append({
            'id': season_hist.season_id,
            'season_number': season_hist.season_number,
            'champion': season_hist.champion_team,
            'image_url': image_url,
            'completed_at': season_hist.completed_at
        })
    
    return render_template('franchise_history.html', seasons=seasons_data)

@app.route('/franchise_history/<int:season_id>')
def season_detail(season_id):
    """Display detailed season stats week by week"""
    import json
    season = Season.query.get_or_404(season_id)
    season_history = SeasonHistory.query.filter_by(season_id=season_id).first()
    
    # Get all completed games for this season, ordered by week and game_number
    games = Game.query.filter_by(season_id=season_id, status='completed')\
                      .order_by(Game.week, Game.game_number).all()
    
    # Group games by week and extract stats
    weeks_data = {}
    for game in games:
        week_num = game.week
        if week_num not in weeks_data:
            weeks_data[week_num] = []
        
        # Parse game details
        game_data = {
            'id': game.id,
            'game_number': game.game_number,
            'team1': game.team1,
            'team2': game.team2,
            'team1_score': game.team1_score,
            'team2_score': game.team2_score,
            'winner': game.winner,
            'is_upset': game.is_upset,
            'player_stats': {}
        }
        
        # Extract player stats from details JSON
        if game.details:
            try:
                details = json.loads(game.details)
                team1_player_stats = details.get('team1_player_stats', {})
                team2_player_stats = details.get('team2_player_stats', {})
                
                # Combine player stats
                all_player_stats = {}
                for player_name, stats in team1_player_stats.items():
                    all_player_stats[player_name] = {
                        'team': game.team1,
                        **stats
                    }
                for player_name, stats in team2_player_stats.items():
                    all_player_stats[player_name] = {
                        'team': game.team2,
                        **stats
                    }
                
                game_data['player_stats'] = all_player_stats
            except (json.JSONDecodeError, TypeError) as e:
                game_data['player_stats'] = {}
        
        weeks_data[week_num].append(game_data)
    
    # Sort weeks
    sorted_weeks = sorted(weeks_data.keys())
    
    # Build image URL if available
    image_url = None
    if season_history and season_history.champion_image_path:
        image_url = url_for('static', filename=season_history.champion_image_path)
    
    # Collect all Gemini images for gallery
    all_gemini_images = []
    for week_num in sorted_weeks:
        for game_data in weeks_data[week_num]:
            if game_data.get('gemini_image_url'):
                all_gemini_images.append({
                    'url': game_data['gemini_image_url'],
                    'week': week_num,
                    'game_number': game_data.get('game_number'),
                    'team1': game_data['team1'],
                    'team2': game_data['team2'],
                    'winner': game_data['winner']
                })
    
    return render_template('season_detail.html', 
                         season=season,
                         season_history=season_history,
                         weeks_data=weeks_data,
                         sorted_weeks=sorted_weeks,
                         image_url=image_url,
                         gemini_gallery=all_gemini_images)

@app.route('/analytics')
def analytics():
    # #region agent log
    import json as json_module
    import time
    log_path = r'c:\Users\charl\CodingProjets\Cascade\.cursor\debug.log'
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'A','location':'app.py:302','message':'analytics route entry','data':{'user_authenticated':current_user.is_authenticated if current_user else False},'timestamp':int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    import json
    # #region agent log
    try:
        active_season = Season.query.filter_by(is_active=True).first()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'A','location':'app.py:305','message':'active_season query result analytics','data':{'active_season_id':active_season.id if active_season else None},'timestamp':int(time.time()*1000)})+'\n')
    except Exception as db_err:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'A','location':'app.py:305','message':'active_season query failed analytics','data':{'error':str(db_err)},'timestamp':int(time.time()*1000)})+'\n')
        raise
    # #endregion
    
    # Load player info from game_state.json
    players_info = {}
    state_file = os.path.join(os.path.dirname(basedir), 'game_state.json')
    # #region agent log
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'B','location':'app.py:309','message':'checking game_state.json analytics','data':{'state_file':state_file,'exists':os.path.exists(state_file)},'timestamp':int(time.time()*1000)})+'\n')
    # #endregion
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            # #region agent log
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'B','location':'app.py:313','message':'game_state.json loaded analytics','data':{'teams_count':len(state_data.get('teams',[]))},'timestamp':int(time.time()*1000)})+'\n')
            # #endregion
            
            for team_data in state_data.get('teams', []):
                for player in team_data.get('players', []):
                    players_info[player['name']] = {
                        'team': team_data['name'],
                        'ranking': player.get('ranking', 0),
                        'best_stat': player.get('best_stat', ''),
                        'role': player.get('role', '')
                    }
        except Exception as e:
            # #region agent log
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'B','location':'app.py:323','message':'error loading player info','data':{'error':str(e),'error_type':type(e).__name__},'timestamp':int(time.time()*1000)})+'\n')
            # #endregion
            print(f"Error loading player info: {e}")
    
    # Aggregate player stats across all games
    player_stats_aggregated = {}
    team_stats_aggregated = {}
    games_processed = 0
    
    if active_season:
        games = Game.query.filter_by(season_id=active_season.id, status='completed')\
                          .order_by(Game.week, Game.game_number).all()
        
        for game in games:
            if not game.details:
                continue
            
            try:
                details = json.loads(game.details)
                games_processed += 1
                
                # Process team 1 players
                team1_players = details.get('team1_player_stats', {})
                for player_key, stats in team1_players.items():
                    # Use player_id + team_name as composite key if available, otherwise fallback to name + team
                    player_id = stats.get('player_id', player_key)
                    player_name = stats.get('player_name', player_key)
                    composite_key = f"{player_id}_{game.team1}"
                    
                    if composite_key not in player_stats_aggregated:
                        player_stats_aggregated[composite_key] = {
                            'player_id': player_id,
                            'player_name': player_name,
                            'team': game.team1,
                            'points': 0,
                            'runs_attempted': 0, 'runs_completed': 0, 'cascade_runs': 0,
                            'throws_attempted': 0, 'throws_completed': 0, 'cascade_throws': 0,
                            'kicks_attempted': 0, 'kicks_completed': 0, 'cascade_kicks': 0,
                            'games_played': 0,
                            'game_points': []  # Track points per game for consistency
                        }
                    
                    agg = player_stats_aggregated[composite_key]
                    agg['points'] += stats.get('points', 0)
                    agg['runs_attempted'] += stats.get('runs_attempted', 0)
                    agg['runs_completed'] += stats.get('runs_completed', 0)
                    agg['cascade_runs'] += stats.get('cascade_runs', 0)
                    agg['throws_attempted'] += stats.get('throws_attempted', 0)
                    agg['throws_completed'] += stats.get('throws_completed', 0)
                    agg['cascade_throws'] += stats.get('cascade_throws', 0)
                    agg['kicks_attempted'] += stats.get('kicks_attempted', 0)
                    agg['kicks_completed'] += stats.get('kicks_completed', 0)
                    agg['cascade_kicks'] += stats.get('cascade_kicks', 0)
                    agg['games_played'] += 1
                    agg['game_points'].append(stats.get('points', 0))
                
                # Process team 2 players
                team2_players = details.get('team2_player_stats', {})
                for player_key, stats in team2_players.items():
                    # Use player_id + team_name as composite key if available, otherwise fallback to name + team
                    player_id = stats.get('player_id', player_key)
                    player_name = stats.get('player_name', player_key)
                    composite_key = f"{player_id}_{game.team2}"
                    
                    if composite_key not in player_stats_aggregated:
                        player_stats_aggregated[composite_key] = {
                            'player_id': player_id,
                            'player_name': player_name,
                            'team': game.team2,
                            'points': 0,
                            'runs_attempted': 0, 'runs_completed': 0, 'cascade_runs': 0,
                            'throws_attempted': 0, 'throws_completed': 0, 'cascade_throws': 0,
                            'kicks_attempted': 0, 'kicks_completed': 0, 'cascade_kicks': 0,
                            'games_played': 0,
                            'game_points': []
                        }
                    
                    agg = player_stats_aggregated[composite_key]
                    agg['points'] += stats.get('points', 0)
                    agg['runs_attempted'] += stats.get('runs_attempted', 0)
                    agg['runs_completed'] += stats.get('runs_completed', 0)
                    agg['cascade_runs'] += stats.get('cascade_runs', 0)
                    agg['throws_attempted'] += stats.get('throws_attempted', 0)
                    agg['throws_completed'] += stats.get('throws_completed', 0)
                    agg['cascade_throws'] += stats.get('cascade_throws', 0)
                    agg['kicks_attempted'] += stats.get('kicks_attempted', 0)
                    agg['kicks_completed'] += stats.get('kicks_completed', 0)
                    agg['cascade_kicks'] += stats.get('cascade_kicks', 0)
                    agg['games_played'] += 1
                    agg['game_points'].append(stats.get('points', 0))
                
                # Aggregate team stats
                for team_name in [game.team1, game.team2]:
                    if team_name not in team_stats_aggregated:
                        team_stats_aggregated[team_name] = {
                            'games': 0, 'wins': 0, 'points_for': 0, 'points_against': 0
                        }
                    team_stats_aggregated[team_name]['games'] += 1
                    if team_name == game.winner:
                        team_stats_aggregated[team_name]['wins'] += 1
                    if team_name == game.team1:
                        team_stats_aggregated[team_name]['points_for'] += game.team1_score
                        team_stats_aggregated[team_name]['points_against'] += game.team2_score
                    else:
                        team_stats_aggregated[team_name]['points_for'] += game.team2_score
                        team_stats_aggregated[team_name]['points_against'] += game.team1_score
                        
            except Exception as e:
                # #region agent log
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'E','location':'app.py:413','message':'error processing game analytics','data':{'game_id':game.id,'error':str(e),'error_type':type(e).__name__},'timestamp':int(time.time()*1000)})+'\n')
                # #endregion
                print(f"Error processing game {game.id} for analytics: {e}")
                continue
    
    # Calculate advanced metrics for players
    for player_key, stats in player_stats_aggregated.items():
        total_attempts = stats['runs_attempted'] + stats['throws_attempted'] + stats['kicks_attempted']
        total_completions = stats['runs_completed'] + stats['throws_completed'] + stats['kicks_completed']
        total_cascades = stats['cascade_runs'] + stats['cascade_throws'] + stats['cascade_kicks']
        
        stats['success_rate'] = (total_completions / total_attempts * 100) if total_attempts > 0 else 0
        stats['cascade_rate'] = (total_cascades / total_completions * 100) if total_completions > 0 else 0
        stats['points_per_game'] = stats['points'] / stats['games_played'] if stats['games_played'] > 0 else 0
        stats['points_per_attempt'] = stats['points'] / total_attempts if total_attempts > 0 else 0
        
        # Consistency metrics
        if stats['game_points']:
            stats['best_game'] = max(stats['game_points'])
            stats['worst_game'] = min(stats['game_points'])
            avg_points = sum(stats['game_points']) / len(stats['game_points'])
            variance = sum((x - avg_points) ** 2 for x in stats['game_points']) / len(stats['game_points'])
            stats['consistency'] = 100 - (variance ** 0.5)  # Lower variance = higher consistency
        else:
            stats['best_game'] = 0
            stats['worst_game'] = 0
            stats['consistency'] = 0
        
        # Add player info (use player_name from stats if available)
        player_name = stats.get('player_name', player_key)
        if player_name in players_info:
            # Only update if not already set from game data
            if 'team' not in stats or not stats.get('team'):
                stats.update(players_info[player_name])
    
    # Sort players by different metrics (use player_name for display)
    players_by_points = sorted(player_stats_aggregated.items(), 
                              key=lambda x: (x[1]['points'], x[1].get('player_name', '')), reverse=True)
    players_by_success = sorted(player_stats_aggregated.items(),
                                key=lambda x: (x[1]['success_rate'], x[1].get('player_name', '')), reverse=True)
    players_by_cascade = sorted(player_stats_aggregated.items(),
                                key=lambda x: (x[1]['cascade_runs'] + x[1]['cascade_throws'] + x[1]['cascade_kicks'], x[1].get('player_name', '')),
                                reverse=True)
    players_by_consistency = sorted(player_stats_aggregated.items(),
                                   key=lambda x: (x[1]['consistency'], x[1].get('player_name', '')), reverse=True)
    players_by_best_game = sorted(player_stats_aggregated.items(),
                                 key=lambda x: (x[1]['best_game'], x[1].get('player_name', '')), reverse=True)
    
    # #region agent log
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'D','location':'app.py:457','message':'before render_template analytics','data':{'players_count':len(player_stats_aggregated),'games_processed':games_processed},'timestamp':int(time.time()*1000)})+'\n')
    # #endregion
    try:
        result = render_template('analytics.html',
                             player_stats=player_stats_aggregated,
                             players_by_points=players_by_points,
                             players_by_success=players_by_success,
                             players_by_cascade=players_by_cascade,
                             players_by_consistency=players_by_consistency,
                             players_by_best_game=players_by_best_game,
                             team_stats=team_stats_aggregated,
                             games_processed=games_processed,
                             active_season=active_season)
        # #region agent log
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'D','location':'app.py:457','message':'render_template analytics success','data':{'result_length':len(result) if result else 0},'timestamp':int(time.time()*1000)})+'\n')
        # #endregion
        return result
    except Exception as render_err:
        # #region agent log
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'D','location':'app.py:457','message':'render_template analytics failed','data':{'error':str(render_err),'error_type':type(render_err).__name__},'timestamp':int(time.time()*1000)})+'\n')
        # #endregion
        raise

@app.route('/teams')
def teams():
    import json
    import os
    from collections import defaultdict
    
    # Load teams from game_state.json
    state_file = os.path.join(os.path.dirname(basedir), 'game_state.json')
    teams_dict = {}
    teams_data = []
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            teams_data = state_data.get('teams', [])
            for team_data in teams_data:
                teams_dict[team_data['name']] = team_data
        except Exception as e:
            logger.error(f"Error loading teams: {e}")
    
    # Aggregate statistics for each team from all completed games
    team_stats = {}
    all_seasons = Season.query.all()
    season_dict = {s.id: s for s in all_seasons}
    
    # Get active season
    active_season = Season.query.filter_by(is_active=True).first()
    active_season_id = active_season.id if active_season else None
    
    # Initialize team stats
    for team_name in teams_dict.keys():
        team_stats[team_name] = {
            'name': team_name,
            'current_record': {'wins': 0, 'losses': 0},  # All-time record
            'season_record': {'wins': 0, 'losses': 0},  # Current season record
            'games': [],
            'games_by_season': defaultdict(list),
            'total_points_for': 0,
            'total_points_against': 0,
            'season_points_for': 0,
            'season_points_against': 0,
            'total_runs': 0,
            'total_throws': 0,
            'total_kicks': 0,
            'total_cascade_runs': 0,
            'total_cascade_throws': 0,
            'total_cascade_kicks': 0,
            'cascade_attempts': 0,
            'home_games': {'wins': 0, 'losses': 0, 'points_for': 0, 'points_against': 0},
            'away_games': {'wins': 0, 'losses': 0, 'points_for': 0, 'points_against': 0},
            'head_to_head': defaultdict(lambda: {'wins': 0, 'losses': 0, 'point_diffs': []}),
            'players': teams_dict.get(team_name, {}).get('players', [])
        }
    
    # Query all completed games
    all_games = Game.query.filter_by(status='completed')\
                          .order_by(Game.season_id, Game.week, Game.game_number).all()
    
    # Process each game
    for game in all_games:
        if not game.details:
            continue
        
        try:
            details = json.loads(game.details)
            season = season_dict.get(game.season_id)
            
            # Determine which team is which
            for team_num, team_name in [(1, game.team1), (2, game.team2)]:
                if team_name not in team_stats:
                    continue
                
                stats = team_stats[team_name]
                is_home = (team_num == 1)  # team1 is considered home
                
                # Get team's score and opponent
                if team_num == 1:
                    team_score = game.team1_score or 0
                    opp_score = game.team2_score or 0
                    opponent = game.team2
                else:
                    team_score = game.team2_score or 0
                    opp_score = game.team1_score or 0
                    opponent = game.team1
                
                # Update wins/losses (all-time)
                won = (team_score > opp_score)
                if won:
                    stats['current_record']['wins'] += 1
                    if is_home:
                        stats['home_games']['wins'] += 1
                    else:
                        stats['away_games']['wins'] += 1
                else:
                    stats['current_record']['losses'] += 1
                    if is_home:
                        stats['home_games']['losses'] += 1
                    else:
                        stats['away_games']['losses'] += 1
                
                # Update season-specific wins/losses if this is the active season
                if active_season_id and game.season_id == active_season_id:
                    if won:
                        stats['season_record']['wins'] += 1
                    else:
                        stats['season_record']['losses'] += 1
                
                # Points (all-time)
                stats['total_points_for'] += team_score
                stats['total_points_against'] += opp_score
                
                # Points (season-specific)
                if active_season_id and game.season_id == active_season_id:
                    stats['season_points_for'] += team_score
                    stats['season_points_against'] += opp_score
                
                if is_home:
                    stats['home_games']['points_for'] += team_score
                    stats['home_games']['points_against'] += opp_score
                else:
                    stats['away_games']['points_for'] += team_score
                    stats['away_games']['points_against'] += opp_score
                
                # Get scoring details from game details
                team_detail_key = f'team{team_num}_stats'
                if team_detail_key in details:
                    detail_str = details[team_detail_key]
                    # Parse the string format: "Runs: X (Cascade: Y), Throws: X (Cascade: Y), Kicks: X (Cascade: Y)"
                    import re
                    # Match pattern: "Runs: X (Cascade: Y)"
                    runs_pattern = r'Runs:\s*(\d+)\s*\(Cascade:\s*(\d+)\)'
                    throws_pattern = r'Throws:\s*(\d+)\s*\(Cascade:\s*(\d+)\)'
                    kicks_pattern = r'Kicks:\s*(\d+)\s*\(Cascade:\s*(\d+)\)'
                    
                    runs_match = re.search(runs_pattern, detail_str)
                    throws_match = re.search(throws_pattern, detail_str)
                    kicks_match = re.search(kicks_pattern, detail_str)
                    
                    if runs_match:
                        runs_count = int(runs_match.group(1))
                        cascade_runs = int(runs_match.group(2))
                        stats['total_runs'] += runs_count
                        stats['total_cascade_runs'] += cascade_runs
                        if cascade_runs > 0:
                            stats['cascade_attempts'] += 1
                    
                    if throws_match:
                        throws_count = int(throws_match.group(1))
                        cascade_throws = int(throws_match.group(2))
                        stats['total_throws'] += throws_count
                        stats['total_cascade_throws'] += cascade_throws
                        if cascade_throws > 0:
                            stats['cascade_attempts'] += 1
                    
                    if kicks_match:
                        kicks_count = int(kicks_match.group(1))
                        cascade_kicks = int(kicks_match.group(2))
                        stats['total_kicks'] += kicks_count
                        stats['total_cascade_kicks'] += cascade_kicks
                        if cascade_kicks > 0:
                            stats['cascade_attempts'] += 1
                
                # Head-to-head record
                point_diff = abs(team_score - opp_score)
                stats['head_to_head'][opponent]['point_diffs'].append(point_diff)
                if won:
                    stats['head_to_head'][opponent]['wins'] += 1
                else:
                    stats['head_to_head'][opponent]['losses'] += 1
                
                # Store game for recent results
                game_info = {
                    'season_id': game.season_id,
                    'season_name': season.name if season else f"Season {game.season_id}",
                    'week': game.week,
                    'game_number': game.game_number,
                    'opponent': opponent,
                    'team_score': team_score,
                    'opp_score': opp_score,
                    'won': won,
                    'point_diff': point_diff
                }
                stats['games'].append(game_info)
                stats['games_by_season'][game.season_id].append(game_info)
        
        except Exception as e:
            logger.error(f"Error processing game {game.id}: {e}")
            continue
    
    # Calculate derived statistics for each team
    for team_name, stats in team_stats.items():
        games_played = stats['current_record']['wins'] + stats['current_record']['losses']
        season_games_played = stats['season_record']['wins'] + stats['season_record']['losses']
        
        # All-time averages
        stats['avg_points_for'] = stats['total_points_for'] / games_played if games_played > 0 else 0
        stats['avg_points_against'] = stats['total_points_against'] / games_played if games_played > 0 else 0
        stats['avg_point_differential'] = stats['avg_points_for'] - stats['avg_points_against']
        
        # Season-specific averages
        stats['season_avg_points_for'] = stats['season_points_for'] / season_games_played if season_games_played > 0 else 0
        stats['season_avg_points_against'] = stats['season_points_against'] / season_games_played if season_games_played > 0 else 0
        stats['season_avg_point_differential'] = stats['season_avg_points_for'] - stats['season_avg_points_against']
        
        # Scoring breakdown percentages
        total_points = stats['total_points_for']
        run_points = stats['total_runs'] * 3
        throw_points = stats['total_throws'] * 2
        kick_points = stats['total_kicks'] * 1
        
        stats['run_points_pct'] = (run_points / total_points * 100) if total_points > 0 else 0
        stats['throw_points_pct'] = (throw_points / total_points * 100) if total_points > 0 else 0
        stats['kick_points_pct'] = (kick_points / total_points * 100) if total_points > 0 else 0
        
        # Cascade performance
        total_cascades = stats['total_cascade_runs'] + stats['total_cascade_throws'] + stats['total_cascade_kicks']
        stats['avg_cascades_per_game'] = total_cascades / games_played if games_played > 0 else 0
        stats['cascade_success_rate'] = (total_cascades / stats['cascade_attempts'] * 100) if stats['cascade_attempts'] > 0 else 0
        
        # Win/Loss streaks
        stats['current_streak'] = {'type': 'none', 'length': 0}
        stats['longest_win_streak'] = 0
        stats['longest_loss_streak'] = 0
        
        if stats['games']:
            # Sort games chronologically
            sorted_games = sorted(stats['games'], key=lambda g: (g['season_id'], g['week'], g.get('game_number', 0)))
            
            # Calculate streaks
            current_streak_type = None
            current_streak_length = 0
            longest_win = 0
            longest_loss = 0
            
            for game in sorted_games:
                if game['won']:
                    if current_streak_type == 'win':
                        current_streak_length += 1
                    else:
                        current_streak_type = 'win'
                        current_streak_length = 1
                    longest_win = max(longest_win, current_streak_length)
                else:
                    if current_streak_type == 'loss':
                        current_streak_length += 1
                    else:
                        current_streak_type = 'loss'
                        current_streak_length = 1
                    longest_loss = max(longest_loss, current_streak_length)
            
            stats['current_streak'] = {'type': current_streak_type or 'none', 'length': current_streak_length}
            stats['longest_win_streak'] = longest_win
            stats['longest_loss_streak'] = longest_loss
        
        # Home/Away stats
        home_games = stats['home_games']['wins'] + stats['home_games']['losses']
        away_games = stats['away_games']['wins'] + stats['away_games']['losses']
        stats['home_win_pct'] = (stats['home_games']['wins'] / home_games * 100) if home_games > 0 else 0
        stats['away_win_pct'] = (stats['away_games']['wins'] / away_games * 100) if away_games > 0 else 0
        stats['avg_home_points_for'] = (stats['home_games']['points_for'] / home_games) if home_games > 0 else 0
        stats['avg_home_points_against'] = (stats['home_games']['points_against'] / home_games) if home_games > 0 else 0
        stats['avg_away_points_for'] = (stats['away_games']['points_for'] / away_games) if away_games > 0 else 0
        stats['avg_away_points_against'] = (stats['away_games']['points_against'] / away_games) if away_games > 0 else 0
        
        # Head-to-head: find teams they win/lose against most and closest games
        if stats['head_to_head']:
            # Team they win against most
            best_opponent = None
            best_wins = 0
            for opp, h2h in stats['head_to_head'].items():
                if h2h['wins'] > best_wins:
                    best_wins = h2h['wins']
                    best_opponent = opp
            stats['beat_most'] = {
                'team': best_opponent,
                'record': f"{best_wins}-{stats['head_to_head'][best_opponent]['losses']}" if best_opponent else "N/A"
            } if best_opponent else None
            
            # Team they lose against most
            worst_opponent = None
            worst_losses = 0
            for opp, h2h in stats['head_to_head'].items():
                if h2h['losses'] > worst_losses:
                    worst_losses = h2h['losses']
                    worst_opponent = opp
            stats['lose_most'] = {
                'team': worst_opponent,
                'record': f"{stats['head_to_head'][worst_opponent]['wins']}-{worst_losses}" if worst_opponent else "N/A"
            } if worst_opponent else None
            
            # Team with closest games (lowest average point differential)
            closest_opponent = None
            closest_avg_diff = float('inf')
            for opp, h2h in stats['head_to_head'].items():
                if h2h['point_diffs']:
                    avg_diff = sum(h2h['point_diffs']) / len(h2h['point_diffs'])
                    if avg_diff < closest_avg_diff:
                        closest_avg_diff = avg_diff
                        closest_opponent = opp
            stats['closest_games'] = {
                'team': closest_opponent,
                'avg_diff': round(closest_avg_diff, 1) if closest_opponent else None,
                'record': f"{stats['head_to_head'][closest_opponent]['wins']}-{stats['head_to_head'][closest_opponent]['losses']}" if closest_opponent else "N/A"
            } if closest_opponent else None
        else:
            stats['beat_most'] = None
            stats['lose_most'] = None
            stats['closest_games'] = None
        
        # Sort games within each season by week/game number (most recent first)
        for season_id in stats['games_by_season']:
            stats['games_by_season'][season_id].sort(key=lambda g: (g['week'], g.get('game_number', 0)), reverse=True)
    
    # Sort teams by current season wins (descending), then by losses (ascending)
    # Teams with the same season record will be sorted by all-time record as a tiebreaker
    sorted_teams = sorted(team_stats.items(), key=lambda x: (
        x[1]['season_record']['wins'], 
        -x[1]['season_record']['losses'],
        x[1]['current_record']['wins'],
        -x[1]['current_record']['losses']
    ), reverse=True)
    
    # Convert defaultdict to regular dict for template
    for team_name, stats in team_stats.items():
        stats['games_by_season'] = dict(sorted(stats['games_by_season'].items(), reverse=True))
    
    return render_template('teams.html', teams_data=sorted_teams, active_season=active_season)

@app.route('/account')
@login_required
def account():
    """Account settings page where users can select their favorite team"""
    import json
    
    # Load teams from game_state.json
    state_file = os.path.join(os.path.dirname(basedir), 'game_state.json')
    teams_list = []
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            teams_list = [team['name'] for team in state_data.get('teams', [])]
        except Exception as e:
            logger.error(f"Error loading teams for account page: {e}")
    
    return render_template('account.html', teams=teams_list, current_favorite=current_user.favorite_team)

@app.route('/api/update_favorite_team', methods=['POST'])
@login_required
def update_favorite_team():
    """Update user's favorite team"""
    import json
    
    try:
        data = request.json
        team_name = data.get('team_name')
        
        if not team_name:
            return jsonify({'success': False, 'message': 'Team name is required'}), 400
        
        # Validate team exists in game_state.json
        state_file = os.path.join(os.path.dirname(basedir), 'game_state.json')
        valid_teams = []
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                valid_teams = [team['name'] for team in state_data.get('teams', [])]
            except Exception as e:
                logger.error(f"Error loading teams for validation: {e}")
                return jsonify({'success': False, 'message': 'Error validating team'}), 500
        
        if team_name not in valid_teams:
            return jsonify({'success': False, 'message': 'Invalid team name'}), 400
        
        # Update user's favorite team
        current_user.favorite_team = team_name
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Favorite team updated successfully'})
    except Exception as e:
        logger.error(f"Error updating favorite team: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/check_win_notification')
@login_required
def check_win_notification():
    """Check if user's favorite team won a game and return notification data"""
    try:
        # Check if user has a favorite team set
        if not current_user.favorite_team:
            return jsonify({'has_win': False})
        
        # Query for completed games where favorite team won
        # Game id must be greater than last_win_notification_game_id (or null)
        last_notified_id = current_user.last_win_notification_game_id or 0
        
        winning_game = Game.query.filter(
            Game.winner == current_user.favorite_team,
            Game.status == 'completed',
            Game.id > last_notified_id
        ).order_by(Game.id.desc()).first()
        
        if not winning_game:
            return jsonify({'has_win': False})
        
        # Extract team color from logo
        team_color = get_team_color_from_logo(current_user.favorite_team)
        
        # Update last_win_notification_game_id to mark this notification as seen
        current_user.last_win_notification_game_id = winning_game.id
        db.session.commit()
        
        return jsonify({
            'has_win': True,
            'team_name': current_user.favorite_team,
            'team_color': team_color,
            'game_id': winning_game.id,
            'week': winning_game.week,
            'game_number': winning_game.game_number,
            'opponent': winning_game.team2 if winning_game.team1 == current_user.favorite_team else winning_game.team1,
            'score': f"{winning_game.team1_score if winning_game.team1 == current_user.favorite_team else winning_game.team2_score}-{winning_game.team2_score if winning_game.team1 == current_user.favorite_team else winning_game.team1_score}"
        })
    except Exception as e:
        logger.error(f"Error checking win notification: {e}")
        return jsonify({'has_win': False, 'error': str(e)}), 500

@app.route('/api/player_stats/<player_name>')
def player_stats_api(player_name):
    import json
    import os
    
    def calculate_stats_from_games(games, player_name):
        """Helper function to calculate stats from a list of games"""
        stats = {
            'points': 0,
            'runs_attempted': 0, 'runs_completed': 0, 'cascade_runs': 0,
            'throws_attempted': 0, 'throws_completed': 0, 'cascade_throws': 0,
            'kicks_attempted': 0, 'kicks_completed': 0, 'cascade_kicks': 0,
            'games_played': 0,
            'game_points': [],
            'game_details': []
        }
        
        for game in games:
            if not game.details:
                continue
            
            try:
                details = json.loads(game.details)
                
                # Check both teams - iterate through all players to find by player_name
                # (stats are keyed by player_id, not player_name, so we need to check the player_name field)
                for team_players in [details.get('team1_player_stats', {}), 
                                     details.get('team2_player_stats', {})]:
                    # Try direct lookup first (for backwards compatibility)
                    if player_name in team_players:
                        game_stats = team_players[player_name]
                    else:
                        # Look up by player_name field (stats are keyed by player_id)
                        game_stats = None
                        for player_key, player_data in team_players.items():
                            if isinstance(player_data, dict) and player_data.get('player_name') == player_name:
                                game_stats = player_data
                                break
                    
                    if game_stats:
                        stats['points'] += game_stats.get('points', 0)
                        stats['runs_attempted'] += game_stats.get('runs_attempted', 0)
                        stats['runs_completed'] += game_stats.get('runs_completed', 0)
                        stats['cascade_runs'] += game_stats.get('cascade_runs', 0)
                        stats['throws_attempted'] += game_stats.get('throws_attempted', 0)
                        stats['throws_completed'] += game_stats.get('throws_completed', 0)
                        stats['cascade_throws'] += game_stats.get('cascade_throws', 0)
                        stats['kicks_attempted'] += game_stats.get('kicks_attempted', 0)
                        stats['kicks_completed'] += game_stats.get('kicks_completed', 0)
                        stats['cascade_kicks'] += game_stats.get('cascade_kicks', 0)
                        stats['games_played'] += 1
                        stats['game_points'].append(game_stats.get('points', 0))
                        
                        stats['game_details'].append({
                            'week': game.week,
                            'game_number': game.game_number,
                            'team1': game.team1,
                            'team2': game.team2,
                            'winner': game.winner,
                            'points': game_stats.get('points', 0),
                            'stats': game_stats
                        })
                        break  # Player can only be on one team per game
            except Exception as e:
                continue
        
        # Calculate advanced metrics
        total_attempts = stats['runs_attempted'] + stats['throws_attempted'] + stats['kicks_attempted']
        total_completions = stats['runs_completed'] + stats['throws_completed'] + stats['kicks_completed']
        total_cascades = stats['cascade_runs'] + stats['cascade_throws'] + stats['cascade_kicks']
        
        stats['success_rate'] = (total_completions / total_attempts * 100) if total_attempts > 0 else 0
        stats['points_per_game'] = stats['points'] / stats['games_played'] if stats['games_played'] > 0 else 0
        stats['points_per_attempt'] = stats['points'] / total_attempts if total_attempts > 0 else 0
        stats['cascade_rate'] = (total_cascades / total_completions * 100) if total_completions > 0 else 0
        
        # Consistency metrics
        if stats['game_points']:
            stats['best_game'] = max(stats['game_points'])
            stats['worst_game'] = min(stats['game_points'])
            avg_points = sum(stats['game_points']) / len(stats['game_points'])
            variance = sum((x - avg_points) ** 2 for x in stats['game_points']) / len(stats['game_points'])
            stats['consistency'] = 100 - (variance ** 0.5)  # Lower variance = higher consistency
        else:
            stats['best_game'] = 0
            stats['worst_game'] = 0
            stats['consistency'] = 0
        
        return stats
    
    # Get player info from game_state.json
    players_info = {}
    state_file = os.path.join(os.path.dirname(basedir), 'game_state.json')
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            for team_data in state_data.get('teams', []):
                for player in team_data.get('players', []):
                    if player['name'] == player_name:
                        players_info = {
                            'team': team_data['name'],
                            'ranking': player.get('ranking', 0),
                            'best_stat': player.get('best_stat', ''),
                            'role': player.get('role', '')
                        }
                        break
        except Exception as e:
            pass
    
    # Calculate season stats (current active season)
    season_stats = {
        'points': 0,
        'runs_attempted': 0, 'runs_completed': 0, 'cascade_runs': 0,
        'throws_attempted': 0, 'throws_completed': 0, 'cascade_throws': 0,
        'kicks_attempted': 0, 'kicks_completed': 0, 'cascade_kicks': 0,
        'games_played': 0,
        'game_points': [],
        'game_details': []
    }
    
    active_season = Season.query.filter_by(is_active=True).first()
    if active_season:
        # Get all completed games for the active season (same as analytics route)
        season_games = Game.query.filter_by(season_id=active_season.id, status='completed')\
                                 .order_by(Game.week, Game.game_number).all()
        season_stats = calculate_stats_from_games(season_games, player_name)
        season_stats['season_name'] = active_season.name
    
    # Calculate all-time stats (all seasons)
    all_seasons = Season.query.all()
    all_time_games = Game.query.filter(Game.status == 'completed')\
                                .order_by(Game.season_id, Game.week, Game.game_number).all()
    all_time_stats = calculate_stats_from_games(all_time_games, player_name)
    
    # Add player info to both
    season_stats.update(players_info)
    all_time_stats.update(players_info)
    
    return jsonify({
        'player_name': player_name,
        'player_info': players_info,
        'season': season_stats,
        'all_time': all_time_stats
    })

@app.route('/api/get_betting_lines/<int:game_id>')
@login_required
def get_betting_lines(game_id):
    import json
    import os
    from game_logic import Team, generate_betting_lines, generate_player_prop_odds, generate_first_score_props, generate_margin_props
    
    game = Game.query.get_or_404(game_id)
    
    # Return stored lines if available
    if game.betting_lines:
        try:
            return jsonify(json.loads(game.betting_lines))
        except:
            pass
    
    # Otherwise generate on the fly
    state_file = os.path.join(os.path.dirname(basedir), 'game_state.json')
    teams_dict = {}
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
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
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    team1_obj = teams_dict.get(game.team1)
    team2_obj = teams_dict.get(game.team2)
    
    if not team1_obj or not team2_obj:
        return jsonify({'error': 'Teams not found'}), 404
    
    # On-the-fly generation uses fast calculation (not official)
    lines_data = generate_betting_lines(team1_obj, team2_obj, is_official=False)
    return jsonify(lines_data)

@app.route('/api/place_bet', methods=['POST'])
@login_required
def place_bet():
    import json
    import json as json_module
    from game_logic import calculate_parlay_odds
    
    # #region agent log
    try:
        with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'location':'app.py:890','message':'place_bet entry','data':{'user_id':current_user.id,'has_json':request.json is not None},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
    except: pass
    # #endregion
    
    try:
        data = request.json
        
        # #region agent log
        try:
            with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'location':'app.py:896','message':'request.json parsed','data':{'is_parlay':data.get('is_parlay',False),'has_bets':bool(data.get('bets')),'amount':data.get('amount'),'game_id':data.get('game_id')},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
        except: pass
        # #endregion
        
        # Check if this is a parlay bet
        is_parlay = data.get('is_parlay', False)
        bets = data.get('bets', [])  # Array of bet objects for parlays
        
        if is_parlay and len(bets) < 2:
            return jsonify({'success': False, 'message': 'Parlay must have at least 2 bets'})
        
        total_amount = int(data.get('amount', 0))
        
        if total_amount > current_user.tokens:
            return jsonify({'success': False, 'message': 'Insufficient tokens'})
        
        if total_amount <= 0:
            return jsonify({'success': False, 'message': 'Bet amount must be positive'})
        
        if is_parlay:
            # Handle parlay bet
            bet_objects = []
            bet_odds_list = []
            
            for bet_data in bets:
                odds = int(bet_data.get('odds'))
                bet_odds_list.append(odds)
                bet_objects.append(bet_data)
            
            # Calculate combined parlay odds
            combined_odds, _ = calculate_parlay_odds(bet_odds_list)
            
            # Calculate potential payout
            if combined_odds > 0:
                profit = total_amount * (combined_odds / 100)
            else:
                profit = total_amount * (100 / abs(combined_odds))
            potential_payout = int(total_amount + profit)
            
            # Create parlay record
            parlay = Parlay(
                user_id=current_user.id,
                bet_ids=json.dumps([b.get('temp_id') for b in bet_objects]),  # Will be updated with real IDs
                total_amount=total_amount,
                combined_odds=combined_odds,
                potential_payout=potential_payout
            )
            db.session.add(parlay)
            db.session.flush()  # Get parlay ID
            
            # Create individual bet records linked to parlay
            created_bets = []
            for bet_data in bet_objects:
                game_id = bet_data.get('game_id')
                bet_type = bet_data.get('bet_type')
                selection = bet_data.get('selection')
                odds = int(bet_data.get('odds'))
                line_value = bet_data.get('line_value')
                
                # Calculate individual bet payout (for reference, not used in parlay)
                if odds > 0:
                    profit = total_amount * (odds / 100)
                else:
                    profit = total_amount * (100 / abs(odds))
                individual_payout = int(total_amount + profit)
                
                bet = Bet(
                    user_id=current_user.id,
                    game_id=game_id,
                    bet_type=bet_type,
                    selection=str(selection),
                    line_value=float(line_value) if line_value is not None else None,
                    parlay_id=parlay.id,
                    amount=0,  # Individual bets in parlay have 0 amount (total is on parlay)
                    odds=odds,
                    potential_payout=individual_payout
                )
                db.session.add(bet)
                created_bets.append(bet)
            
            # Update parlay with real bet IDs
            parlay.bet_ids = json.dumps([b.id for b in created_bets])
            
            current_user.tokens -= total_amount
            
            # Record transaction
            trans = Transaction(
                user_id=current_user.id,
                amount=-total_amount,
                description=f"Parlay bet with {len(bets)} selections"
            )
            db.session.add(trans)
        
        else:
            # Handle single bet
            # #region agent log
            try:
                with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'location':'app.py:988','message':'Processing single bet','data':{'game_id':data.get('game_id'),'bet_type':data.get('bet_type'),'selection':data.get('selection'),'odds':data.get('odds'),'line_value':data.get('line_value'),'amount':total_amount},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
            except: pass
            # #endregion
            
            game_id = data.get('game_id')
            bet_type = data.get('bet_type')
            selection = data.get('selection')
            amount = total_amount
            odds = int(data.get('odds'))
            line_value = data.get('line_value')
            
            # #region agent log
            try:
                with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'location':'app.py:996','message':'Before payout calculation','data':{'odds':odds,'amount':amount,'line_value':line_value,'line_value_type':type(line_value).__name__},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
            except: pass
            # #endregion
            
            # Calculate potential payout
            if odds > 0:
                profit = amount * (odds / 100)
            else:
                profit = amount * (100 / abs(odds))
            potential_payout = int(amount + profit)
            
            # #region agent log
            try:
                with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'location':'app.py:1003','message':'Before Bet creation','data':{'game_id':game_id,'bet_type':bet_type,'selection':str(selection),'line_value':line_value,'line_value_float':float(line_value) if line_value is not None else None},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
            except Exception as e:
                try:
                    with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_module.dumps({'location':'app.py:1003','message':'Error logging before Bet creation','data':{'error':str(e)},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
                except: pass
            # #endregion
            
            bet = Bet(
                user_id=current_user.id,
                game_id=game_id,
                bet_type=bet_type,
                selection=str(selection),
                line_value=float(line_value) if line_value is not None else None,
                amount=amount,
                odds=odds,
                potential_payout=potential_payout
            )
            
            # #region agent log
            try:
                with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'location':'app.py:1014','message':'Before token deduction','data':{'current_tokens':current_user.tokens,'amount':amount},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
            except: pass
            # #endregion
            
            current_user.tokens -= amount
            
            # Record transaction
            trans = Transaction(
                user_id=current_user.id,
                amount=-amount,
                description=f"Bet on Game {game_id}: {selection} ({bet_type})"
            )
            
            # #region agent log
            try:
                with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'location':'app.py:1023','message':'Before db.session.add','data':{},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
            except: pass
            # #endregion
            
            db.session.add(bet)
            db.session.add(trans)
        
        # #region agent log
        try:
            with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'location':'app.py:1026','message':'Before db.session.commit','data':{},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
        except: pass
        # #endregion
        
        db.session.commit()
        
        # #region agent log
        try:
            with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'location':'app.py:1028','message':'place_bet success','data':{'new_balance':current_user.tokens},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'C'})+'\n')
        except: pass
        # #endregion
        
        return jsonify({'success': True, 'new_balance': current_user.tokens})
    except Exception as e:
        # #region agent log
        try:
            import traceback
            with open('c:\\Users\\charl\\CodingProjets\\Cascade\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'location':'app.py:1030','message':'place_bet exception','data':{'error':str(e),'error_type':type(e).__name__,'traceback':traceback.format_exc()},'timestamp':int(__import__('time').time()*1000),'sessionId':'debug-session','runId':'run1','hypothesisId':'D'})+'\n')
        except: pass
        # #endregion
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/my_bets')
@login_required
def my_bets():
    """Get all pending bets for the current user"""
    import json
    
    try:
        # Get single bets (not part of a parlay)
        single_bets = Bet.query.filter(
            Bet.user_id == current_user.id,
            Bet.status == 'pending',
            Bet.parlay_id.is_(None)
        ).join(Game).order_by(Bet.created_at.desc()).all()
        
        # Get parlays
        parlays = Parlay.query.filter(
            Parlay.user_id == current_user.id,
            Parlay.status == 'pending'
        ).order_by(Parlay.created_at.desc()).all()
        
        # Format single bets
        single_bets_data = []
        for bet in single_bets:
            game = bet.game
            # Format bet description based on bet type
            description = format_bet_description(bet)
            
            single_bets_data.append({
                'id': bet.id,
                'type': 'single',
                'game_id': bet.game_id,
                'game': {
                    'week': game.week,
                    'game_number': game.game_number,
                    'team1': game.team1,
                    'team2': game.team2,
                    'status': game.status
                },
                'bet_type': bet.bet_type,
                'selection': bet.selection,
                'line_value': bet.line_value,
                'odds': bet.odds,
                'amount': bet.amount,
                'potential_payout': bet.potential_payout,
                'description': description,
                'created_at': bet.created_at.isoformat() if bet.created_at else None
            })
        
        # Format parlays
        parlays_data = []
        for parlay in parlays:
            # Get all bets in this parlay
            parlay_bets = Bet.query.filter(Bet.parlay_id == parlay.id).join(Game).all()
            
            bet_descriptions = []
            for bet in parlay_bets:
                description = format_bet_description(bet)
                bet_descriptions.append({
                    'game_id': bet.game_id,
                    'game': {
                        'week': bet.game.week,
                        'game_number': bet.game.game_number,
                        'team1': bet.game.team1,
                        'team2': bet.game.team2
                    },
                    'bet_type': bet.bet_type,
                    'selection': bet.selection,
                    'line_value': bet.line_value,
                    'odds': bet.odds,
                    'description': description
                })
            
            parlays_data.append({
                'id': parlay.id,
                'type': 'parlay',
                'bets': bet_descriptions,
                'combined_odds': parlay.combined_odds,
                'amount': parlay.total_amount,
                'potential_payout': parlay.potential_payout,
                'num_selections': len(parlay_bets),
                'created_at': parlay.created_at.isoformat() if parlay.created_at else None
            })
        
        return jsonify({
            'success': True,
            'single_bets': single_bets_data,
            'parlays': parlays_data,
            'total_bets': len(single_bets_data) + len(parlays_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

def get_team_color_from_logo(team_name):
    """Extract dominant color from team logo and return as hex string"""
    try:
        # Convert team name to logo filename
        logo_filename = team_name.lower().replace(" ", "_") + "_logo.png"
        logo_path = os.path.join(config.LOGOS_DIRECTORY, logo_filename)
        
        # Try different filename variations (handle apostrophes)
        for logo_file in [logo_path, logo_path.replace("'", "'"), logo_path.replace("'", "'")]:
            if os.path.exists(logo_file):
                try:
                    logo_image = Image.open(logo_file)
                    # Import extract_dominant_color from image_generator
                    from image_generator import extract_dominant_color
                    rgb_color = extract_dominant_color(logo_image)
                    # Convert RGB tuple to hex string
                    return f"#{rgb_color[0]:02x}{rgb_color[1]:02x}{rgb_color[2]:02x}"
                except Exception as e:
                    logger.error(f"Error extracting color from logo {logo_file}: {e}")
                    continue
        
        # Default color if logo not found
        return "#4ecdc4"  # Default teal color
    except Exception as e:
        logger.error(f"Error getting team color for {team_name}: {e}")
        return "#4ecdc4"  # Default teal color

def format_bet_description(bet):
    """Format a bet into a human-readable description"""
    if bet.bet_type == 'moneyline':
        return f"{bet.selection} to win"
    elif bet.bet_type == 'spread':
        if bet.line_value is not None:
            line_str = f"{bet.line_value:+.1f}"
            return f"{bet.selection} {line_str}"
        return bet.selection
    elif bet.bet_type == 'total':
        over_under = "Over" if "Over" in bet.selection else "Under"
        if bet.line_value is not None:
            return f"{over_under} {bet.line_value}"
        return f"{over_under}"
    elif bet.bet_type == 'team_total':
        parts = bet.selection.split()
        if len(parts) >= 2:
            team = parts[0]
            over_under = parts[1]
            if bet.line_value is not None:
                return f"{team} {over_under} {bet.line_value}"
            return f"{team} {over_under}"
        return bet.selection
    elif bet.bet_type == 'player_prop':
        # Format: "Player Name Prop Type Over/Under Line"
        parts = bet.selection.split('_')
        if len(parts) >= 3:
            player = parts[0]
            prop_type = parts[1]
            over_under = parts[2]
            prop_display = prop_type.replace('_', ' ').title()
            if bet.line_value is not None:
                return f"{player} {prop_display} {over_under} {bet.line_value}"
            return f"{player} {prop_display} {over_under}"
        return bet.selection
    elif bet.bet_type == 'team_prop':
        if 'cascade' in bet.selection.lower():
            return "Cascade Yes" if 'yes' in bet.selection.lower() else "Cascade No"
        return bet.selection
    else:
        return bet.selection

# API for polling status
@app.route('/api/latest_update')
def latest_update():
    # Return timestamp of last completed game to check for updates
    last_game = Game.query.filter_by(status='completed').order_by(Game.id.desc()).first()
    if last_game:
        # We can use the ID as a proxy for "version" or add a timestamp
        return jsonify({'last_game_id': last_game.id})
    return jsonify({'last_game_id': 0})

# API for simulation status
@app.route('/api/simulation_status')
def simulation_status():
    import simulation_status as sim_status
    status = sim_status.get_status()
    return jsonify(status)

# Route to serve game images from season folders
@app.route('/static/season_<int:season_num>/<path:filename>')
def serve_season_image(season_num, filename):
    """Serve game images from webapp/static/season_X/ folders"""
    static_dir = os.path.join(basedir, 'static', f'season_{season_num}')
    if os.path.exists(static_dir) and os.path.exists(os.path.join(static_dir, filename)):
        return send_from_directory(static_dir, filename)
    else:
        flash(f'Image not found: season_{season_num}/{filename}')
        return redirect(url_for('index'))

# Podcast routes
@app.route('/podcasts')
def podcasts():
    """Render the podcasts page"""
    return render_template('podcasts.html')

@app.route('/api/podcasts')
def api_podcasts():
    """Return JSON list of podcast files with metadata"""
    from pathlib import Path
    
    # Get podcasts directory (parent of webapp)
    podcasts_dir = os.path.join(os.path.dirname(basedir), 'podcasts')
    
    if not os.path.exists(podcasts_dir):
        return jsonify({'success': False, 'error': 'Podcasts directory not found', 'podcasts': []})
    
    podcasts_list = []
    
    # Scan for audio files
    audio_extensions = {'.mp3', '.mp4'}
    for filename in os.listdir(podcasts_dir):
        file_path = os.path.join(podcasts_dir, filename)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(filename)
            if ext.lower() in audio_extensions:
                # Format display name
                display_name = format_podcast_name(filename)
                
                # Extract week and game numbers for sorting
                week_num, game_num = extract_week_game_numbers(filename)
                
                podcasts_list.append({
                    'filename': filename,
                    'display_name': display_name,
                    'url': url_for('serve_podcast', filename=filename),
                    'week': week_num,
                    'game': game_num
                })
    
    # Sort chronologically: by week, then by game
    podcasts_list.sort(key=lambda x: (x['week'] if x['week'] is not None else 999, 
                                       x['game'] if x['game'] is not None else 999,
                                       x['filename']))
    
    return jsonify({'success': True, 'podcasts': podcasts_list})

def format_podcast_name(filename):
    """Format podcast filename to readable name"""
    # Remove extension
    name = os.path.splitext(filename)[0]
    
    # Handle chunk files
    chunk_match = re.search(r'_chunk_(\d+)', name)
    if chunk_match:
        chunk_num = int(chunk_match.group(1)) + 1  # 0-indexed to 1-indexed
        name = re.sub(r'_chunk_\d+', '', name)
        suffix = f' (Part {chunk_num})'
    else:
        suffix = ''
    
    # Replace underscores with spaces and capitalize words
    name = name.replace('_', ' ')
    # Capitalize first letter of each word
    name = ' '.join(word.capitalize() for word in name.split())
    
    return name + suffix

def extract_week_game_numbers(filename):
    """Extract week and game numbers from filename for sorting"""
    week_match = re.search(r'week[_\s](\d+)', filename, re.IGNORECASE)
    game_match = re.search(r'game[_\s](\d+)', filename, re.IGNORECASE)
    
    week_num = int(week_match.group(1)) if week_match else None
    game_num = int(game_match.group(1)) if game_match else None
    
    return week_num, game_num

@app.route('/podcasts/<path:filename>')
def serve_podcast(filename):
    """Serve podcast files from podcasts directory"""
    podcasts_dir = os.path.join(os.path.dirname(basedir), 'podcasts')
    if os.path.exists(podcasts_dir) and os.path.exists(os.path.join(podcasts_dir, filename)):
        return send_from_directory(podcasts_dir, filename)
    else:
        return jsonify({'error': 'Podcast not found'}), 404

def migrate_bet_table():
    """Add missing columns (line_value, parlay_id) to bet table if they don't exist"""
    with app.app_context():
        try:
            # Check what columns exist
            inspector = inspect(db.engine)
            try:
                columns = [col['name'] for col in inspector.get_columns('bet')]
            except Exception as table_error:
                # Table doesn't exist, init_db will create it
                print("Bet table doesn't exist, will be created by init_db")
                return False
            
            migrations_applied = False
            
            # Check if line_value column exists
            if 'line_value' not in columns:
                print("Adding missing line_value column to bet table...")
                db.session.execute(text("ALTER TABLE bet ADD COLUMN line_value REAL"))
                db.session.commit()
                print("Successfully added line_value column to bet table")
                migrations_applied = True
                # Refresh columns list after adding column
                columns = [col['name'] for col in inspector.get_columns('bet')]
            
            # Check if parlay_id column exists
            if 'parlay_id' not in columns:
                print("Adding missing parlay_id column to bet table...")
                db.session.execute(text("ALTER TABLE bet ADD COLUMN parlay_id INTEGER"))
                db.session.commit()
                print("Successfully added parlay_id column to bet table")
                migrations_applied = True
            
            return migrations_applied
        except Exception as e:
            print(f"Error during bet table migration: {e}")
            # If table doesn't exist, init_db will create it with all columns
            if "no such table" in str(e).lower():
                print("Bet table doesn't exist, will be created by init_db")
                return False
            raise

def migrate_game_gemini_image():
    """Add missing gemini_image_path column to game table if it doesn't exist"""
    with app.app_context():
        try:
            # Check what columns exist
            inspector = inspect(db.engine)
            try:
                columns = [col['name'] for col in inspector.get_columns('game')]
            except Exception as table_error:
                # Table doesn't exist, init_db will create it
                print("Game table doesn't exist, will be created by init_db")
                return False
            
            # Check if gemini_image_path column exists
            if 'gemini_image_path' not in columns:
                print("Adding missing gemini_image_path column to game table...")
                db.session.execute(text("ALTER TABLE game ADD COLUMN gemini_image_path VARCHAR(200)"))
                db.session.commit()
                print("Successfully added gemini_image_path column to game table")
                return True
            
            return False
        except Exception as e:
            print(f"Error during game table migration: {e}")
            # If table doesn't exist, init_db will create it with all columns
            if "no such table" in str(e).lower():
                print("Game table doesn't exist, will be created by init_db")
                return False
            raise

def migrate_user_favorite_team():
    """Add missing favorite_team and last_win_notification_game_id columns to user table if they don't exist"""
    with app.app_context():
        try:
            # Check what columns exist
            inspector = inspect(db.engine)
            try:
                columns = [col['name'] for col in inspector.get_columns('user')]
            except Exception as table_error:
                # Table doesn't exist, init_db will create it
                print("User table doesn't exist, will be created by init_db")
                return False
            
            migrations_applied = False
            
            # Check if favorite_team column exists
            if 'favorite_team' not in columns:
                print("Adding missing favorite_team column to user table...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN favorite_team VARCHAR(80)"))
                db.session.commit()
                print("Successfully added favorite_team column to user table")
                migrations_applied = True
                # Refresh columns list after adding column
                columns = [col['name'] for col in inspector.get_columns('user')]
            
            # Check if last_win_notification_game_id column exists
            if 'last_win_notification_game_id' not in columns:
                print("Adding missing last_win_notification_game_id column to user table...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN last_win_notification_game_id INTEGER"))
                db.session.commit()
                print("Successfully added last_win_notification_game_id column to user table")
                migrations_applied = True
            
            return migrations_applied
        except Exception as e:
            print(f"Error during user table migration: {e}")
            # If table doesn't exist, init_db will create it with all columns
            if "no such table" in str(e).lower():
                print("User table doesn't exist, will be created by init_db")
                return False
            raise

def init_db():
    """Initialize database tables. Can be called from outside the app context."""
    with app.app_context():
        db.create_all()
        print(f"Database initialized at: {db_path}")

# Ensure all tables exist on app startup
with app.app_context():
    try:
        # Try to query a table to see if database is accessible
        Season.query.first()
        # If successful, ensure all tables exist (creates any missing tables)
        db.create_all()
        # Run migrations for any missing columns
        migrate_bet_table()
        migrate_game_gemini_image()
        migrate_user_favorite_team()
    except Exception:
        # Database doesn't exist or is corrupted, initialize it
        init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
