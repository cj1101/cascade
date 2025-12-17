from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

def utcnow():
    """Get current UTC time as naive datetime for database defaults."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Store hashed passwords
    tokens = db.Column(db.Integer, default=1000)
    is_admin = db.Column(db.Boolean, default=False)
    favorite_team = db.Column(db.String(80), nullable=True)
    last_win_notification_game_id = db.Column(db.Integer, nullable=True)

    bets = db.relationship('Bet', backref='user', lazy=True)
    parlays = db.relationship('Parlay', backref='user', lazy=True)

class Season(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False) # e.g., "Season 1"
    start_date = db.Column(db.DateTime, default=utcnow)
    is_active = db.Column(db.Boolean, default=True)

    games = db.relationship('Game', backref='season', lazy=True)
    history = db.relationship('SeasonHistory', backref='season', uselist=False, lazy=True)

class SeasonHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False, unique=True)
    champion_team = db.Column(db.String(80), nullable=False)
    champion_image_path = db.Column(db.String(200), nullable=True)  # Relative path like "season_3/tournament_champion_trophy.png"
    season_number = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=utcnow)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    game_number = db.Column(db.Integer, nullable=True) # 1, 2, 3...
    team1 = db.Column(db.String(80), nullable=False)
    team2 = db.Column(db.String(80), nullable=False)

    # Status: 'scheduled', 'completed'
    status = db.Column(db.String(20), default='scheduled')

    # Results (nullable until played)
    team1_score = db.Column(db.Integer)
    team2_score = db.Column(db.Integer)
    winner = db.Column(db.String(80))
    is_upset = db.Column(db.Boolean, default=False)
    details = db.Column(db.Text) # JSON string for detailed stats if needed

    # Props outcomes (stored as JSON)
    props_data = db.Column(db.Text)
    
    # Pre-calculated betting lines (stored as JSON)
    betting_lines = db.Column(db.Text)
    
    # Gemini-generated artistic image path (relative to static root, e.g., "season_3/week_1_game_1_gemini.png")
    gemini_image_path = db.Column(db.String(200), nullable=True)

    bets = db.relationship('Bet', backref='game', lazy=True)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)

    # Bet Type: 'moneyline', 'spread', 'total', 'team_total', 'player_prop', 'team_prop'
    bet_type = db.Column(db.String(20), nullable=False)

    # Selection: team name, or 'over'/'under', or prop option
    selection = db.Column(db.String(200), nullable=False)  # Increased length for structured prop data

    # Line value for spread, total, team_total, or player prop (e.g., -5.5, 45.5, 12.5)
    line_value = db.Column(db.Float, nullable=True)

    # Parlay linkage
    parlay_id = db.Column(db.Integer, db.ForeignKey('parlay.id'), nullable=True)

    amount = db.Column(db.Integer, nullable=False)
    odds = db.Column(db.Integer, nullable=False) # American odds (+150, -110)
    potential_payout = db.Column(db.Integer, nullable=False)

    # Status: 'pending', 'won', 'lost', 'push'
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=utcnow)

class Parlay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bet_ids = db.Column(db.Text)  # JSON array of bet IDs
    total_amount = db.Column(db.Integer, nullable=False)
    combined_odds = db.Column(db.Integer)  # Combined American odds
    potential_payout = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, won, lost, push
    created_at = db.Column(db.DateTime, default=utcnow)
    
    bets = db.relationship('Bet', backref='parlay', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False) # Positive for win, negative for bet
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=utcnow)

class SimulationStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_running = db.Column(db.Boolean, default=False)
    current_week = db.Column(db.Integer, default=0)
    next_simulation_time = db.Column(db.DateTime, nullable=True)
    status_message = db.Column(db.String(200), default='')
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    # Progress tracking fields
    current_phase = db.Column(db.Integer, nullable=True)  # 1-5
    games_completed = db.Column(db.Integer, default=0)
    total_games = db.Column(db.Integer, nullable=True)
    phase_start_time = db.Column(db.DateTime, nullable=True)
    simulation_start_time = db.Column(db.DateTime, nullable=True)