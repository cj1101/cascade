import os
import shutil
import json
from datetime import datetime
from webapp.app import app, db
from webapp.database import User, Season, Game, Bet, Transaction

# Config
STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webapp', 'static')

def initialize_season():
    """
    Checks existing season folders, creates a new one (season_N+1),
    and initializes a new Season record in the database.
    """
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
    with app.app_context():
        # Deactivate old seasons
        existing_active = Season.query.filter_by(is_active=True).all()
        for s in existing_active:
            s.is_active = False

        new_season = Season(name=f"Season {next_season_num}", is_active=True)
        db.session.add(new_season)
        db.session.commit()
        print(f"Initialized Season {next_season_num} in database (ID: {new_season.id})")
        return new_season.id, new_season_folder

def upload_schedule(season_id, schedule_data):
    """
    Populates the Game table with scheduled games.
    schedule_data: List of tuples/dicts with (week, team1, team2)
    """
    with app.app_context():
        # Clear existing scheduled games for this season to avoid duplicates if re-run
        # (Or handle upsert logic. For now, we assume fresh season start)
        pass

        # We need to adapt the schedule_data format coming from game_logic
        # Assuming schedule_data is list of (week, [(team1, team2), ...])

        game_count = 0
        for week_num, matches in schedule_data:
            for match in matches:
                team1, team2 = match
                new_game = Game(
                    season_id=season_id,
                    week=week_num,
                    team1=team1.name,
                    team2=team2.name,
                    status='scheduled'
                )
                db.session.add(new_game)
                game_count += 1

        db.session.commit()
        print(f"Uploaded schedule: {game_count} games created.")

def upload_game_data(season_id, week, game_results, season_folder_name):
    """
    Updates game results in DB and copies images.
    game_results: List of (filename, game_result_dict)
    """
    with app.app_context():
        target_dir = os.path.join(STATIC_ROOT, season_folder_name)

        for item in game_results:
            if isinstance(item, tuple):
                filename, result = item
            else:
                # Handle case where it might just be the result dict (rare but possible in logic)
                continue

            # Copy Image
            src_path = filename # Assuming filename is in current working dir
            if os.path.exists(src_path):
                shutil.copy(src_path, os.path.join(target_dir, filename))

            # Update Database
            # Find the scheduled game
            game = Game.query.filter_by(season_id=season_id,
                                      week=week,
                                      team1=result['team1'].name,
                                      team2=result['team2'].name).first()

            # If not found (e.g. tournament dynamic games), create it
            if not game:
                game = Game(season_id=season_id, week=week,
                            team1=result['team1'].name, team2=result['team2'].name)
                db.session.add(game)

            game.status = 'completed'
            game.team1_score = result['team1_score']
            game.team2_score = result['team2_score']
            game.winner = result['team1'].name if result['team1_score'] > result['team2_score'] else result['team2'].name
            game.is_upset = result.get('upset', False)

            # Serialize stats details
            details = {
                'team1_stats': str(result['team1_detail']),
                'team2_stats': str(result['team2_detail'])
            }
            game.details = json.dumps(details)

            # Settle Bets for this game
            _settle_bets_for_game(game, result)

        db.session.commit()
        print(f"Uploaded Week {week} data and settled bets.")

def _settle_bets_for_game(game, result):
    """
    Internal function to settle bets for a specific game result.
    """
    pending_bets = Bet.query.filter_by(game_id=game.id, status='pending').all()

    for bet in pending_bets:
        won = False

        if bet.bet_type == 'moneyline':
            if bet.selection == game.winner:
                won = True

        elif bet.bet_type == 'spread':
            # Format "TeamName -5.5" -> selection stores the team name
            # This requires parsing the selection string stored in DB
            # For simplicity in this plan, assume selection IS the team name picked to cover
            # And we need to know the spread value.
            # In a real app, we'd store the line value separately.
            # Let's assume we implement strict logic later or simplify:
            pass # TODO: Implement complex spread logic if time permits

        elif bet.bet_type == 'total':
            total_score = game.team1_score + game.team2_score
            # selection is "Over X" or "Under X"
            try:
                direction, line_val = bet.selection.split(' ')
                line = float(line_val)
                if direction == 'Over' and total_score > line:
                    won = True
                elif direction == 'Under' and total_score < line:
                    won = True
            except:
                pass

        # If won
        if won:
            bet.status = 'won'
            user = User.query.get(bet.user_id)
            user.tokens += bet.potential_payout

            trans = Transaction(user_id=user.id, amount=bet.potential_payout,
                                description=f"Won bet on Game {game.id}")
            db.session.add(trans)
        else:
            bet.status = 'lost'

def reset_season_tokens():
    """
    End of season: If tokens < 1000, set to 1000.
    """
    with app.app_context():
        users = User.query.filter(User.tokens < 1000).all()
        for user in users:
            diff = 1000 - user.tokens
            user.tokens = 1000
            trans = Transaction(user_id=user.id, amount=diff, description="Season Reset Bonus")
            db.session.add(trans)
        db.session.commit()
        print("Season tokens reset.")
