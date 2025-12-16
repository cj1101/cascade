from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Store hashed passwords
    tokens = db.Column(db.Integer, default=1000)
    is_admin = db.Column(db.Boolean, default=False)

    bets = db.relationship('Bet', backref='user', lazy=True)

class Season(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False) # e.g., "Season 1"
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    games = db.relationship('Game', backref='season', lazy=True)

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

    bets = db.relationship('Bet', backref='game', lazy=True)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)

    # Bet Type: 'moneyline', 'spread', 'total', 'prop'
    bet_type = db.Column(db.String(20), nullable=False)

    # Selection: team name, or 'over'/'under', or prop option
    selection = db.Column(db.String(80), nullable=False)

    amount = db.Column(db.Integer, nullable=False)
    odds = db.Column(db.Integer, nullable=False) # American odds (+150, -110)
    potential_payout = db.Column(db.Integer, nullable=False)

    # Status: 'pending', 'won', 'lost', 'push'
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False) # Positive for win, negative for bet
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
