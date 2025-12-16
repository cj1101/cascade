"""Scheduler module for Cascade game simulation - handles timing, state management, and logging"""
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
import pytz
import game_logic
import config

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# EST/EDT timezone
EST = pytz.timezone('US/Eastern')


def get_initial_teams():
    """
    Create initial teams with random advantages and players.
    
    Returns:
        List of Team objects with random advantages and 7 players each
    """
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
    
    # Curated list of 56 unique player names
    all_player_names = [
        "Alex Rivera", "Blake Chen", "Casey Morgan", "Dakota Kim", "Eli Thompson",
        "Finley Park", "Gray Martinez", "Harper Lee", "Indigo Singh", "Jade Williams",
        "Kai Johnson", "Lane Davis", "Morgan Taylor", "Nova Anderson", "Ocean Brown",
        "Phoenix Garcia", "Quinn Rodriguez", "River White", "Sage Martinez", "Tatum Lopez",
        "Vesper Clark", "Wren Lewis", "Xander Walker", "Yuki Hall", "Zephyr Young",
        "Aria King", "Briar Wright", "Cedar Hill", "Dune Scott", "Echo Green",
        "Frost Adams", "Gale Baker", "Haze Nelson", "Iris Carter", "Jasper Mitchell",
        "Kestrel Perez", "Lark Roberts", "Mist Turner", "Nimbus Phillips", "Onyx Campbell",
        "Pax Parker", "Quill Evans", "Raven Edwards", "Storm Collins", "Tide Stewart",
        "Vale Sanchez", "Willow Morris", "Zen Rogers", "Aurora Reed", "Blaze Cook",
        "Cinder Morgan", "Dawn Bailey", "Ember Rivera", "Flame Ward", "Glow Bell",
        "Halo Murphy", "Iris Alexander", "Jewel Wood", "Karma Watson", "Luna Brooks"
    ]
    
    # Shuffle to randomize assignment
    random.shuffle(all_player_names)
    name_index = 0
    
    teams = []
    for name in team_names:
        team = game_logic.Team(name)
        # Assign random advantages (overall between -5 and 5, individual stats between -3 and 3)
        team.overall_advantage = random.randint(-5, 5)
        team.run_advantage = random.randint(-3, 3)
        team.throw_advantage = random.randint(-3, 3)
        team.kick_advantage = random.randint(-3, 3)
        
        # Generate 7 players for this team
        team.players = []
        player_names_for_team = all_player_names[name_index:name_index + 7]
        name_index += 7
        
        # Assign rankings 1-7 (1 is best)
        rankings = list(range(1, 8))
        random.shuffle(rankings)
        
        # Assign roles: 3 Anchors, 4 Runners
        roles = ['Anchor'] * 3 + ['Runner'] * 4
        random.shuffle(roles)
        
        # Assign best stats randomly
        best_stats = ['Run', 'Throw', 'Kick']
        
        for i, player_name in enumerate(player_names_for_team):
            player = {
                'name': player_name,
                'ranking': rankings[i],
                'best_stat': random.choice(best_stats),
                'role': roles[i]
            }
            team.players.append(player)
        
        teams.append(team)
    
    return teams


def load_game_state():
    """
    Load game state from JSON file.
    
    Returns:
        Tuple of (teams, current_week, round_robin_num) or (None, 1, None) if file doesn't exist
    """
    state_file = getattr(config, 'STATE_FILE_PATH', 'game_state.json')
    
    if not os.path.exists(state_file):
        return None, 1, None
    
    try:
        with open(state_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct teams from JSON
        teams = []
        for team_data in data.get('teams', []):
            team = game_logic.Team(team_data['name'])
            team.overall_advantage = team_data.get('overall_advantage', 0)
            team.run_advantage = team_data.get('run_advantage', 0)
            team.throw_advantage = team_data.get('throw_advantage', 0)
            team.kick_advantage = team_data.get('kick_advantage', 0)
            team.wins = team_data.get('wins', 0)
            team.losses = team_data.get('losses', 0)
            team.points_for = team_data.get('points_for', 0)
            team.points_against = team_data.get('points_against', 0)
            
            # Load player data if available (backward compatibility)
            if 'players' in team_data:
                team.players = team_data['players']
            else:
                # Generate default players for backward compatibility
                team.players = _generate_default_players(team.name)
            
            teams.append(team)
        
        current_week = data.get('current_week', 1)
        round_robin_num = data.get('round_robin_num', None)
        
        return teams, current_week, round_robin_num
    except Exception as e:
        logger.error(f"Error loading game state: {e}")
        return None, 1, None


def _generate_default_players(team_name):
    """Generate default players for backward compatibility"""
    all_player_names = [
        "Alex Rivera", "Blake Chen", "Casey Morgan", "Dakota Kim", "Eli Thompson",
        "Finley Park", "Gray Martinez", "Harper Lee", "Indigo Singh", "Jade Williams",
        "Kai Johnson", "Lane Davis", "Morgan Taylor", "Nova Anderson", "Ocean Brown",
        "Phoenix Garcia", "Quinn Rodriguez", "River White", "Sage Martinez", "Tatum Lopez",
        "Vesper Clark", "Wren Lewis", "Xander Walker", "Yuki Hall", "Zephyr Young",
        "Aria King", "Briar Wright", "Cedar Hill", "Dune Scott", "Echo Green",
        "Frost Adams", "Gale Baker", "Haze Nelson", "Iris Carter", "Jasper Mitchell",
        "Kestrel Perez", "Lark Roberts", "Mist Turner", "Nimbus Phillips", "Onyx Campbell",
        "Pax Parker", "Quill Evans", "Raven Edwards", "Storm Collins", "Tide Stewart",
        "Vale Sanchez", "Willow Morris", "Zen Rogers", "Aurora Reed", "Blaze Cook",
        "Cinder Morgan", "Dawn Bailey", "Ember Rivera", "Flame Ward", "Glow Bell",
        "Halo Murphy", "Iris Alexander", "Jewel Wood", "Karma Watson", "Luna Brooks"
    ]
    
    # Use team name hash to get consistent subset
    team_hash = hash(team_name) % (len(all_player_names) - 6)
    player_names = all_player_names[team_hash:team_hash + 7]
    
    rankings = list(range(1, 8))
    random.shuffle(rankings)
    roles = ['Anchor'] * 3 + ['Runner'] * 4
    random.shuffle(roles)
    best_stats = ['Run', 'Throw', 'Kick']
    
    players = []
    for i, player_name in enumerate(player_names):
        player = {
            'name': player_name,
            'ranking': rankings[i],
            'best_stat': random.choice(best_stats),
            'role': roles[i]
        }
        players.append(player)
    
    return players


def save_game_state(teams, current_week, round_robin_num=None):
    """
    Save game state to JSON file.
    
    Args:
        teams: List of Team objects
        current_week: Current week number
        round_robin_num: Round robin number (1 or 2) or None
    """
    state_file = getattr(config, 'STATE_FILE_PATH', 'game_state.json')
    
    data = {
        'teams': [],
        'current_week': current_week,
        'round_robin_num': round_robin_num
    }
    
    for team in teams:
        team_data = {
            'name': team.name,
            'overall_advantage': team.overall_advantage,
            'run_advantage': team.run_advantage,
            'throw_advantage': team.throw_advantage,
            'kick_advantage': team.kick_advantage,
            'wins': team.wins,
            'losses': team.losses,
            'points_for': team.points_for,
            'points_against': team.points_against,
            'players': team.players if hasattr(team, 'players') else []
        }
        data['teams'].append(team_data)
    
    try:
        with open(state_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Game state saved to {state_file}")
    except Exception as e:
        logger.error(f"Error saving game state: {e}")


def get_next_fourth_weekend_friday_datetime(hour=13, minute=0):
    """
    Get the next 4th weekend Friday datetime in EST/EDT.
    
    The 4th weekend is defined as the last Friday of the month.
    
    Args:
        hour: Hour in 24-hour format (default 13 for 1pm)
        minute: Minute (default 0)
        
    Returns:
        datetime object in EST/EDT timezone
    """
    now = datetime.now(EST)
    
    # Find the last Friday of the current month
    # Start from the last day of the month and work backwards
    if now.month == 12:
        last_day = datetime(now.year + 1, 1, 1, tzinfo=EST) - timedelta(days=1)
    else:
        last_day = datetime(now.year, now.month + 1, 1, tzinfo=EST) - timedelta(days=1)
    
    # Find the last Friday
    last_friday = last_day
    while last_friday.weekday() != 4:  # 4 = Friday
        last_friday -= timedelta(days=1)
    
    # Set the time
    last_friday = last_friday.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If we've already passed this Friday, move to next month's last Friday
    if last_friday < now:
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=EST)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=EST)
        
        # Get last day of next month
        if next_month.month == 12:
            last_day = datetime(next_month.year + 1, 1, 1, tzinfo=EST) - timedelta(days=1)
        else:
            last_day = datetime(next_month.year, next_month.month + 1, 1, tzinfo=EST) - timedelta(days=1)
        
        # Find the last Friday
        last_friday = last_day
        while last_friday.weekday() != 4:
            last_friday -= timedelta(days=1)
        
        last_friday = last_friday.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    return last_friday


def get_fourth_weekend_friday_at_offset(base_datetime, week_offset):
    """
    Get the 4th weekend Friday datetime at a given week offset.
    
    Args:
        base_datetime: Base datetime (from get_next_fourth_weekend_friday_datetime)
        week_offset: Number of weeks to offset (0 = base, 1 = next week, etc.)
        
    Returns:
        datetime object in EST/EDT timezone
    """
    return base_datetime + timedelta(weeks=week_offset)


def wait_for_interval(minutes):
    """
    Wait for a specified interval in minutes (for debug mode).
    
    Args:
        minutes: Number of minutes to wait
    """
    logger.info(f"Waiting {minutes} minute(s) before next stage...")
    time.sleep(minutes * 60)


def wait_until_datetime(target_datetime):
    """
    Wait until a specific datetime.
    
    Args:
        target_datetime: datetime object to wait until
    """
    now = datetime.now(EST)
    if target_datetime <= now:
        logger.info("Target datetime has already passed. Proceeding immediately.")
        return
    
    wait_seconds = (target_datetime - now).total_seconds()
    logger.info(f"Waiting until {target_datetime.strftime('%Y-%m-%d %I:%M %p %Z')} ({wait_seconds/3600:.1f} hours)...")
    time.sleep(wait_seconds)


def wait_until_hour(hour):
    """
    Wait until a specific hour in EST/EDT today (or tomorrow if hour has passed).
    
    Args:
        hour: Hour in 24-hour format (0-23)
    """
    now = datetime.now(EST)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # If the hour has already passed today, wait until tomorrow
    if target <= now:
        target += timedelta(days=1)
    
    wait_seconds = (target - now).total_seconds()
    logger.info(f"Waiting until {target.strftime('%Y-%m-%d %I:%M %p %Z')} ({wait_seconds/3600:.1f} hours)...")
    time.sleep(wait_seconds)


def calculate_next_posting_hour(start_hour, week_offset):
    """
    Calculate the posting hour for a given week offset.
    For round robin 2, posts are hourly starting from start_hour.
    
    Args:
        start_hour: Starting hour (e.g., 13 for 1pm)
        week_offset: Week offset (0 = first week, 1 = second week, etc.)
        
    Returns:
        Hour in 24-hour format
    """
    # Each week posts at start_hour + week_offset
    # Cap at 23 (11pm)
    posting_hour = start_hour + week_offset
    return min(posting_hour, 23)
