from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from webapp.database import db, User, Season, Game, Bet, Transaction
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-this-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cascade.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def index():
    active_season = Season.query.filter_by(is_active=True).first()
    # Get recent completed games for live feed
    recent_games = []
    if active_season:
        recent_games = Game.query.filter_by(season_id=active_season.id, status='completed')\
                                 .order_by(Game.id.desc()).limit(5).all()

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
    active_season = Season.query.filter_by(is_active=True).first()
    upcoming_games = []
    if active_season:
         upcoming_games = Game.query.filter_by(season_id=active_season.id, status='scheduled').all()

    return render_template('betting.html', games=upcoming_games, user=current_user)

@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.tokens.desc()).all()
    return render_template('leaderboard.html', users=users)

@app.route('/api/place_bet', methods=['POST'])
@login_required
def place_bet():
    data = request.json
    game_id = data.get('game_id')
    bet_type = data.get('bet_type')
    selection = data.get('selection')
    amount = int(data.get('amount'))
    odds = int(data.get('odds'))

    if amount > current_user.tokens:
        return jsonify({'success': False, 'message': 'Insufficient tokens'})

    if amount <= 0:
         return jsonify({'success': False, 'message': 'Bet amount must be positive'})

    # Calculate potential payout
    if odds > 0:
        profit = amount * (odds / 100)
    else:
        profit = amount * (100 / abs(odds))
    potential_payout = amount + profit

    bet = Bet(user_id=current_user.id, game_id=game_id, bet_type=bet_type,
              selection=selection, amount=amount, odds=odds,
              potential_payout=int(potential_payout))

    current_user.tokens -= amount

    # Record transaction
    trans = Transaction(user_id=current_user.id, amount=-amount,
                        description=f"Bet on Game {game_id}: {selection} ({bet_type})")

    db.session.add(bet)
    db.session.add(trans)
    db.session.commit()

    return jsonify({'success': True, 'new_balance': current_user.tokens})

# API for polling status
@app.route('/api/latest_update')
def latest_update():
    # Return timestamp of last completed game to check for updates
    last_game = Game.query.filter_by(status='completed').order_by(Game.id.desc()).first()
    if last_game:
        # We can use the ID as a proxy for "version" or add a timestamp
        return jsonify({'last_game_id': last_game.id})
    return jsonify({'last_game_id': 0})

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized.")

if __name__ == '__main__':
    if not os.path.exists('cascade.db'):
        init_db()
    app.run(debug=True, port=5000)
