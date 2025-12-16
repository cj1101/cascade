"""Core game logic for Cascade game simulation"""
import random
from itertools import combinations


class Team:
    def __init__(self, name):
        self.name = name
        self.overall_advantage = 0
        self.run_advantage = 0
        self.throw_advantage = 0
        self.kick_advantage = 0
        self.wins = 0
        self.losses = 0
        self.points_for = 0
        self.points_against = 0
        self.players = []  # List of player dictionaries with name, ranking, best_stat, role

    def __str__(self):
        return (f"{self.name} (Overall: {self.overall_advantage}, "
                f"Run: {self.run_advantage}, Throw: {self.throw_advantage}, "
                f"Kick: {self.kick_advantage}, W-L: {self.wins}-{self.losses})")

    def best_stat(self):
        """Determine team's best stat from majority of players' best stats"""
        if not self.players:
            # Fallback to old method if no players
            stats = [("Run", self.run_advantage), ("Throw", self.throw_advantage), ("Kick", self.kick_advantage)]
            return max(stats, key=lambda x: x[1])[0]
        
        # Count player best stats
        stat_counts = {"Run": 0, "Throw": 0, "Kick": 0}
        for player in self.players:
            best_stat = player.get('best_stat', 'Run')
            if best_stat in stat_counts:
                stat_counts[best_stat] += 1
        
        # Find majority
        max_count = max(stat_counts.values())
        majority_stats = [stat for stat, count in stat_counts.items() if count == max_count]
        
        # If there's a clear majority (more than half), return it
        if len(majority_stats) == 1:
            return majority_stats[0]
        
        # If tie, randomly select from tied stats
        return random.choice(majority_stats)
    
    def get_player_strength_score(self):
        """Calculate weighted average of player rankings (top players weighted more heavily)"""
        if not self.players:
            return 0.5  # Default neutral score
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for player in self.players:
            ranking = player.get('ranking', 4)  # Default to middle if missing
            # Weight: higher weight for better players (lower ranking number)
            # Ranking 1 gets weight 7, ranking 7 gets weight 1
            weight = 8 - ranking
            # Score: convert ranking to 0-1 scale (1 = best = 1.0, 7 = worst = 0.0)
            score = (8 - ranking) / 7.0
            total_weighted_score += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        return total_weighted_score / total_weight
    
    def get_logo_filename(self):
        """Convert team name to logo filename format"""
        name_lower = self.name.lower()
        # Replace spaces with underscores, keep apostrophes as-is
        return name_lower.replace(" ", "_") + "_logo.png"


class ScoringDetail:
    def __init__(self):
        self.runs = 0
        self.throws = 0
        self.kicks = 0
        self.cascade_runs = 0
        self.cascade_throws = 0
        self.cascade_kicks = 0

    def __str__(self):
        return (f"Runs: {self.runs} (Cascade: {self.cascade_runs}), "
                f"Throws: {self.throws} (Cascade: {self.cascade_throws}), "
                f"Kicks: {self.kicks} (Cascade: {self.cascade_kicks})")


def calculate_win_probability(team1, team2):
    """
    Calculate the probability that team1 wins against team2.
    Factors in: advantage differences, point differential, stat matchup bonuses, and player rankings.
    
    Returns: float between 0.25 and 0.75 (allowing meaningful upsets)
    """
    base_chance = 0.5
    
    # 1. Base probability from advantage difference (reduced impact - halved)
    advantage_diff = team1.overall_advantage - team2.overall_advantage
    team1_win_prob = base_chance + advantage_diff * 0.01  # Reduced from 0.02 to 0.01
    
    # 2. Add point differential adjustment
    if team1.points_for + team1.points_against > 0 and team2.points_for + team2.points_against > 0:
        team1_pd = team1.points_for - team1.points_against
        team2_pd = team2.points_for - team2.points_against
        
        # Normalize point differential by total points to get a relative strength measure
        # Typical game scores around 20-40 points, so scale appropriately
        team1_total = team1.points_for + team1.points_against
        team2_total = team2.points_for + team2.points_against
        avg_total_per_team = (team1_total + team2_total) / 2.0
        
        if avg_total_per_team > 0:
            # Normalize PD difference by average total points (gives per-game strength)
            pd_diff_normalized = (team1_pd - team2_pd) / max(40, avg_total_per_team)
            pd_adjustment = pd_diff_normalized * 0.05  # Max ±5% adjustment
            team1_win_prob += pd_adjustment
    
    # 3. Add stat matchup bonus (rock-paper-scissors: run > kick > throw > run)
    team1_best = team1.best_stat()
    team2_best = team2.best_stat()
    
    # Determine if team1 has a favorable matchup
    stat_matchup_bonus = 0.0
    if team1_best == "Run" and team2_best == "Kick":
        stat_matchup_bonus = 0.04  # Run beats kick
    elif team1_best == "Kick" and team2_best == "Throw":
        stat_matchup_bonus = 0.04  # Kick beats throw
    elif team1_best == "Throw" and team2_best == "Run":
        stat_matchup_bonus = 0.04  # Throw beats run
    elif team2_best == "Run" and team1_best == "Kick":
        stat_matchup_bonus = -0.04  # Team2's run beats team1's kick
    elif team2_best == "Kick" and team1_best == "Throw":
        stat_matchup_bonus = -0.04  # Team2's kick beats team1's throw
    elif team2_best == "Throw" and team1_best == "Run":
        stat_matchup_bonus = -0.04  # Team2's throw beats team1's run
    
    team1_win_prob += stat_matchup_bonus
    
    # 4. Add player ranking factor (±3% based on average player strength difference)
    team1_strength = team1.get_player_strength_score()
    team2_strength = team2.get_player_strength_score()
    strength_diff = team1_strength - team2_strength
    # Normalize to ±3% range (strength_diff ranges from -1 to 1, so multiply by 0.03)
    player_adjustment = strength_diff * 0.03
    team1_win_prob += player_adjustment
    
    # Cap between 25% and 75% to ensure meaningful upsets can occur
    team1_win_prob = max(0.25, min(0.75, team1_win_prob))
    
    return team1_win_prob


def _select_player_by_ranking(team):
    """Select a player from team based on ranking-weighted probability"""
    if not team.players:
        return None
    
    # Calculate weights: better ranked players (lower number) have higher weight
    # Ranking 1 gets weight 7, ranking 7 gets weight 1
    player_weights = [8 - player.get('ranking', 4) for player in team.players]
    selected_player = random.choices(team.players, weights=player_weights)[0]
    return selected_player


def _select_stat_type_by_best_stat(player):
    """Select stat type (run/throw/kick) based on player's best_stat with bias"""
    best_stat = player.get('best_stat', 'Run')
    
    # Bias weights: best_stat gets higher weight
    if best_stat == 'Run':
        weights = [5, 2, 1]  # run:throw:kick
    elif best_stat == 'Throw':
        weights = [1, 5, 2]  # run:throw:kick
    else:  # Kick
        weights = [1, 2, 5]  # run:throw:kick
    
    stat_types = ['run', 'throw', 'kick']
    return random.choices(stat_types, weights=weights)[0]


def _process_scoring_opportunity(team, team_detail, team_score, team_player_stats):
    """Process a single scoring opportunity for a team, tracking player stats"""
    # Select player based on ranking
    player = _select_player_by_ranking(team)
    if not player:
        # Fallback to old method if no players
        team_weights = [
            max(1, 3 + team.run_advantage),
            max(1, 3 + team.throw_advantage),
            max(1, 3 + team.kick_advantage)
        ]
        score_type = random.choices(['run', 'throw', 'kick'], weights=team_weights)[0]
    else:
        # Select stat type based on player's best_stat
        score_type = _select_stat_type_by_best_stat(player)
        player_name = player['name']
        
        # Initialize player stats if needed
        if player_name not in team_player_stats:
            team_player_stats[player_name] = {
                'points': 0,
                'runs_attempted': 0,
                'runs_completed': 0,
                'throws_attempted': 0,
                'throws_completed': 0,
                'kicks_attempted': 0,
                'kicks_completed': 0,
                'cascade_runs': 0,
                'cascade_throws': 0,
                'cascade_kicks': 0
            }
        
        # Track attempt
        if score_type == 'run':
            team_player_stats[player_name]['runs_attempted'] += 1
        elif score_type == 'throw':
            team_player_stats[player_name]['throws_attempted'] += 1
        else:  # kick
            team_player_stats[player_name]['kicks_attempted'] += 1
    
    # Determine completion probability based on action type
    # Run: ~30%, Throw: 45-50%, Kick: ~70%
    completion_success = False
    if score_type == 'run':
        # Run completion: roughly 30% (use 0.30 with some variance)
        completion_success = random.random() < 0.30
    elif score_type == 'throw':
        # Throw completion: 45-50% (use 0.475 average, random between 0.45-0.50)
        throw_prob = random.uniform(0.45, 0.50)
        completion_success = random.random() < throw_prob
    else:  # kick
        # Kick completion: ~70% (use 0.70)
        completion_success = random.random() < 0.70
    
    # If attempt failed, return 0 points (attempt was already tracked)
    if not completion_success:
        return 0
    
    # Determine if scoring is successful (cascade chance) - only if completion succeeded
    cascade = random.random() < 1/15  # Cascade zone chance
    
    # Calculate points
    if score_type == 'run':
        points = 3
        team_detail.runs += 1
        if cascade:
            points *= 2
            team_detail.cascade_runs += 1
    elif score_type == 'throw':
        points = 2
        team_detail.throws += 1
        if cascade:
            points *= 2
            team_detail.cascade_throws += 1
    else:  # kick
        points = 1
        team_detail.kicks += 1
        if cascade:
            points *= 2
            team_detail.cascade_kicks += 1
    
    # Track completion and points for player (only if attempt succeeded)
    if player:
        player_name = player['name']
        if score_type == 'run':
            team_player_stats[player_name]['runs_completed'] += 1
            if cascade:
                team_player_stats[player_name]['cascade_runs'] += 1
        elif score_type == 'throw':
            team_player_stats[player_name]['throws_completed'] += 1
            if cascade:
                team_player_stats[player_name]['cascade_throws'] += 1
        else:  # kick
            team_player_stats[player_name]['kicks_completed'] += 1
            if cascade:
                team_player_stats[player_name]['cascade_kicks'] += 1
        team_player_stats[player_name]['points'] += points
    
    return points


def simulate_game_session(team1, team2):
    """
    Simulates a single game session without modifying team states.
    Returns scores, details, and stats.
    """
    # Use the comprehensive win probability calculation
    team1_chance = calculate_win_probability(team1, team2)

    team1_score = 0
    team2_score = 0
    team1_detail = ScoringDetail()
    team2_detail = ScoringDetail()
    
    # Track player stats for each team
    team1_player_stats = {}
    team2_player_stats = {}

    for _ in range(20):  # 20 "scoring opportunities"
        if random.random() < team1_chance:
            points = _process_scoring_opportunity(team1, team1_detail, team1_score, team1_player_stats)
            team1_score += points
        else:
            points = _process_scoring_opportunity(team2, team2_detail, team2_score, team2_player_stats)
            team2_score += points

    # Handle ties with a tie-breaking scoring opportunity
    while team1_score == team2_score:
        if random.random() < team1_chance:
            points = _process_scoring_opportunity(team1, team1_detail, team1_score, team1_player_stats)
            team1_score += points
        else:
            points = _process_scoring_opportunity(team2, team2_detail, team2_score, team2_player_stats)
            team2_score += points

    return team1_score, team2_score, team1_detail, team2_detail, team1_player_stats, team2_player_stats


def play_game(team1, team2):
    """
    Plays a game, updates team stats, and returns results.
    """
    # Run the simulation
    team1_score, team2_score, team1_detail, team2_detail, team1_player_stats, team2_player_stats = simulate_game_session(team1, team2)

    if team1_score > team2_score:
        winner, loser = team1, team2
        winner_detail, loser_detail = team1_detail, team2_detail
        winner_player_stats, loser_player_stats = team1_player_stats, team2_player_stats
    else:
        winner, loser = team2, team1
        winner_detail, loser_detail = team2_detail, team1_detail
        winner_player_stats, loser_player_stats = team2_player_stats, team1_player_stats

    # Check for upset BEFORE updating advantages (upset = lower advantage team wins)
    upset = (winner.overall_advantage < loser.overall_advantage)
    
    winner.wins += 1
    loser.losses += 1
    winner.points_for += max(team1_score, team2_score)
    winner.points_against += min(team1_score, team2_score)
    loser.points_for += min(team1_score, team2_score)
    loser.points_against += max(team1_score, team2_score)

    # Update advantages
    winner.overall_advantage = min(3, winner.overall_advantage + 1)
    loser.overall_advantage = max(-3, loser.overall_advantage - 1)

    # Update specific advantages
    if winner_detail.runs > loser_detail.runs:
        winner.run_advantage = min(3, winner.run_advantage + 1)
        loser.run_advantage = max(-3, loser.run_advantage - 1)
    elif winner_detail.runs < loser_detail.runs:
        loser.run_advantage = min(3, loser.run_advantage + 1)
        winner.run_advantage = max(-3, winner.run_advantage - 1)

    if winner_detail.throws > loser_detail.throws:
        winner.throw_advantage = min(3, winner.throw_advantage + 1)
        loser.throw_advantage = max(-3, loser.throw_advantage - 1)
    elif winner_detail.throws < loser_detail.throws:
        loser.throw_advantage = min(3, loser.throw_advantage + 1)
        winner.throw_advantage = max(-3, winner.throw_advantage - 1)

    if winner_detail.kicks > loser_detail.kicks:
        winner.kick_advantage = min(3, winner.kick_advantage + 1)
        loser.kick_advantage = max(-3, loser.kick_advantage - 1)
    elif winner_detail.kicks < loser_detail.kicks:
        loser.kick_advantage = min(3, loser.kick_advantage + 1)
        winner.kick_advantage = max(-3, winner.kick_advantage - 1)
    
    game_result = {
        'team1': team1,
        'team2': team2,
        'team1_score': team1_score,
        'team2_score': team2_score,
        'team1_detail': team1_detail,
        'team2_detail': team2_detail,
        'team1_player_stats': team1_player_stats,
        'team2_player_stats': team2_player_stats,
        'upset': upset
    }
    
    result_text = (f"{team1.name} {team1_score} - {team2_score} {team2.name}\n"
                   f"{team1.name} scoring: {team1_detail}\n"
                   f"{team2.name} scoring: {team2_detail}")
    
    return result_text, upset, game_result


def generate_round_robin_schedule(teams):
    if len(teams) % 2:
        teams = teams + [None]
    n = len(teams)
    matchups = []
    for i in range(n - 1):
        round = []
        for j in range(n // 2):
            match = (teams[j], teams[n - 1 - j])
            if match[0] is not None and match[1] is not None:
                round.append(match)
        matchups.append(round)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return matchups


def round_robin(teams, max_rounds=None, start_week=1):
    schedule = generate_round_robin_schedule(teams)
    results = []
    generated_images = {}  # Track images by week: {week: [list of filenames]}
    
    for week_offset, matches in enumerate(schedule[:max_rounds] if max_rounds else schedule, 0):
        week = start_week + week_offset
        print(f"\nWeek {week}:")
        week_results = []
        upsets = []
        week_images = []
        
        for game_num, (team1, team2) in enumerate(matches, 1):
            result, upset, game_result = play_game(team1, team2)
            week_results.append(result)
            print(result)
            
            # Generate game image with standardized naming
            # Scoreboard image
            filename = f"week_{week}_game_{game_num}.png"
            # Image generation will be handled by main script to avoid heavy imports here
            week_images.append((filename, game_result))
            
            # Gemini artistic photo (same matchup)
            gemini_filename = f"week_{week}_game_{game_num}_gemini.png"
            week_images.append((gemini_filename, game_result))
            
            if upset:
                upsets.append(f"{team2.name} (adv: {team2.overall_advantage}) upset {team1.name} (adv: {team1.overall_advantage})")
        
        results.extend(week_results)
        generated_images[week] = week_images
        
        if upsets:
            print("\nUpsets this week:")
            for upset in upsets:
                print(upset)
        
        print("\nCurrent Standings:")
        display_standings(teams)
    
    return results, generated_images


def display_standings(teams):
    sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
    for i, team in enumerate(sorted_teams, 1):
        print(f"{i}. {team.name}: W-L: {team.wins}-{team.losses}, "
              f"PF: {team.points_for}, PA: {team.points_against}, "
              f"Best Stat: {team.best_stat()}")


def probability_to_american_odds(probability):
    """
    Convert a win probability (0.0 to 1.0) to American odds format.
    
    Positive odds (+150): bet $100 to win $150
    Negative odds (-200): bet $200 to win $100
    """
    if probability <= 0:
        return 1000  # Very long odds
    if probability >= 1:
        return -1000  # Very short odds
    
    if probability > 0.5:
        # Favorite: negative odds
        odds = -100 * probability / (1 - probability)
        # Round to nearest 5
        return round(odds / 5) * 5
    else:
        # Underdog: positive odds
        odds = 100 * (1 - probability) / probability
        # Round to nearest 5
        return round(odds / 5) * 5


def calculate_matchup_odds(team1, team2):
    """
    Calculate betting odds for a specific matchup between two teams.
    
    Uses the same win probability calculation as play_game() to ensure
    betting odds accurately reflect actual game outcomes.
    
    Returns a tuple of (team1_odds, team2_odds) in American format.
    """
    # Use the same probability calculation as play_game() for consistency
    team1_win_prob = calculate_win_probability(team1, team2)
    team2_win_prob = 1.0 - team1_win_prob
    
    # Convert to American odds
    team1_odds = probability_to_american_odds(team1_win_prob)
    team2_odds = probability_to_american_odds(team2_win_prob)
    
    return team1_odds, team2_odds


def generate_betting_lines(team1, team2, num_simulations=1000):
    """
    Simulates upcoming matchup to generate Spread, Total, Moneyline, and Prop Bets.
    Returns a dictionary with all betting info.
    """

    # 1. Run Simulations
    sim_results = []

    team1_wins = 0
    total_points = 0
    margin_diff_sum = 0 # (Team1 Score - Team2 Score)

    # Prop tracking
    cascade_count = 0
    run_score_count = 0
    throw_score_count = 0
    kick_score_count = 0

    team1_total_score = 0
    team2_total_score = 0

    for _ in range(num_simulations):
        s1, s2, d1, d2, _, _ = simulate_game_session(team1, team2)

        if s1 > s2:
            team1_wins += 1

        total = s1 + s2
        margin = s1 - s2

        total_points += total
        margin_diff_sum += margin
        team1_total_score += s1
        team2_total_score += s2

        # Props
        if (d1.cascade_runs + d1.cascade_throws + d1.cascade_kicks +
            d2.cascade_runs + d2.cascade_throws + d2.cascade_kicks) > 0:
            cascade_count += 1

        # Count total scores by type for frequency prop
        run_score_count += d1.runs + d2.runs
        throw_score_count += d1.throws + d2.throws
        kick_score_count += d1.kicks + d2.kicks

    # 2. Calculate Lines

    # Moneyline
    win_prob = team1_wins / num_simulations
    ml1 = probability_to_american_odds(win_prob)
    ml2 = probability_to_american_odds(1.0 - win_prob)

    # Spread (Standard Vegas rounding to .5)
    avg_margin = margin_diff_sum / num_simulations
    # If avg_margin is positive, Team 1 is favored by that much (e.g. -5.5)
    # We round to nearest 0.5
    spread_value = round(abs(avg_margin) * 2) / 2
    if spread_value == 0:
        spread_value = 0.5 # Pick 'em usually handled as small spread or PK. Let's force a small line.

    if avg_margin > 0:
        favorite = team1
        underdog = team2
        spread_str = f"{team1.name} -{spread_value}"
        spread_fav_odds = -110
        spread_dog_odds = -110
    else:
        favorite = team2
        underdog = team1
        spread_str = f"{team2.name} -{spread_value}"
        spread_fav_odds = -110
        spread_dog_odds = -110

    # Total (Over/Under)
    avg_total = total_points / num_simulations
    total_line = round(avg_total * 2) / 2

    # Team Totals
    avg_t1 = round((team1_total_score / num_simulations) * 2) / 2
    avg_t2 = round((team2_total_score / num_simulations) * 2) / 2

    # 3. Props

    # Cascade Odds
    cascade_prob = cascade_count / num_simulations
    cascade_yes = probability_to_american_odds(cascade_prob)

    # Most Common Score Method
    score_counts = {'Run': run_score_count, 'Throw': throw_score_count, 'Kick': kick_score_count}
    most_common_method = max(score_counts, key=score_counts.get)

    return {
        'moneyline': (ml1, ml2),
        'spread_str': spread_str,
        'spread_value': spread_value,
        'favorite': favorite,
        'underdog': underdog,
        'total': total_line,
        'team1_total': avg_t1,
        'team2_total': avg_t2,
        'cascade_yes_odds': cascade_yes,
        'most_common_method': most_common_method
    }

def format_betting_slip(matchups):
    """
    Formats a list of matchups into a Vegas-style betting slip string.
    matchups: List of (team1, team2) tuples.
    """
    lines = []
    lines.append("🎰 OFFICIAL WEEKLY BETTING LINES 🎰")
    lines.append(" odds by Cascade Sportsbook")
    lines.append("")

    for team1, team2 in matchups:
        data = generate_betting_lines(team1, team2)

        lines.append(f"⚔️ {team1.name.upper()} vs {team2.name.upper()}")

        # Moneyline
        ml1 = f"+{data['moneyline'][0]}" if data['moneyline'][0] > 0 else str(data['moneyline'][0])
        ml2 = f"+{data['moneyline'][1]}" if data['moneyline'][1] > 0 else str(data['moneyline'][1])
        lines.append(f"   MONEYLINE: {team1.name} {ml1}  |  {team2.name} {ml2}")

        # Spread
        lines.append(f"   SPREAD: {data['spread_str']} (-110)")

        # Total
        lines.append(f"   TOTAL: {data['total']} (O/U -110)")

        # Props Section
        lines.append("   🎲 PROPS:")
        lines.append(f"     • {team1.name} Team Total: {data['team1_total']} (O/U -110)")
        lines.append(f"     • {team2.name} Team Total: {data['team2_total']} (O/U -110)")

        cascade_odds = f"+{data['cascade_yes_odds']}" if data['cascade_yes_odds'] > 0 else str(data['cascade_yes_odds'])
        lines.append(f"     • Will there be a Cascade? YES {cascade_odds}")
        lines.append(f"     • Most Frequent Score Type: {data['most_common_method']}")

        lines.append("") # Spacer

    return "\n".join(lines)


def calculate_team_odds(teams):
    """
    Calculate overall championship/league winner odds for all teams.
    
    Returns a dictionary mapping team names to their American odds.
    """
    # Calculate a strength score for each team
    team_strengths = {}
    for team in teams:
        # Base strength from wins
        win_pct = team.wins / max(1, team.wins + team.losses)
        
        # Point differential normalized
        pd_normalized = (team.points_for - team.points_against) / max(1, team.points_for + team.points_against)
        
        # Overall advantage (ranges from -3 to +3, normalize to 0-1)
        advantage_normalized = (team.overall_advantage + 3) / 6.0
        
        # Combined strength score
        strength = (win_pct * 0.5 + advantage_normalized * 0.3 + pd_normalized * 0.2)
        strength = max(0.01, min(0.99, strength))  # Ensure between 0.01 and 0.99
        team_strengths[team.name] = strength
    
    # Convert strengths to probabilities (sum to 1.0)
    total_strength = sum(team_strengths.values())
    team_probs = {name: strength / total_strength for name, strength in team_strengths.items()}
    
    # Convert probabilities to American odds
    team_odds = {}
    for name, prob in team_probs.items():
        team_odds[name] = probability_to_american_odds(prob)
    
    return team_odds


def format_standings_for_caption(teams):
    """
    Format current standings as a compact string suitable for Instagram caption.
    
    Returns a string with standings formatted as:
    1. Team A (W-L, PF: X, PA: Y, Best: Stat, +/-)
    2. Team B (W-L, PF: X, PA: Y, Best: Stat, +/-)
    ...
    """
    sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
    
    standings_lines = []
    for i, team in enumerate(sorted_teams, 1):
        point_diff = team.points_for - team.points_against
        point_diff_str = f"+{point_diff}" if point_diff >= 0 else str(point_diff)
        standings_lines.append(f"{i}. {team.name} ({team.wins}-{team.losses}, PF: {team.points_for}, PA: {team.points_against}, Best: {team.best_stat()}, {point_diff_str})")
    
    return "\n".join(standings_lines)


def format_game_results_for_caption(week_game_results):
    """
    Format game results for Instagram caption with scores, scoring breakdown, and upsets.
    
    Args:
        week_game_results: List of tuples (filename, game_result) where game_result contains
                          team1, team2, team1_score, team2_score, team1_detail, team2_detail, upset
    
    Returns:
        Formatted string with all game details
    """
    lines = []
    lines.append("📊 Game Results:")
    
    # Track unique games (avoid duplicates from gemini images)
    seen_games = set()
    
    for item in week_game_results:
        if isinstance(item, tuple):
            filename, game_result = item
            # Skip gemini duplicate images
            if '_gemini' in filename:
                continue
        else:
            game_result = item
        
        # Create a unique key for this game
        game_key = (game_result['team1'].name, game_result['team2'].name)
        if game_key in seen_games:
            continue
        seen_games.add(game_key)
        
        team1 = game_result['team1']
        team2 = game_result['team2']
        score1 = game_result['team1_score']
        score2 = game_result['team2_score']
        detail1 = game_result['team1_detail']
        detail2 = game_result['team2_detail']
        upset = game_result.get('upset', False)
        
        # Main score line with upset indicator
        upset_marker = " 🔥 UPSET!" if upset else ""
        lines.append(f"{team1.name} {score1} - {score2} {team2.name}{upset_marker}")
        
        # Scoring breakdown for team 1
        cascade1_parts = []
        if detail1.cascade_runs > 0:
            cascade1_parts.append(f"{detail1.cascade_runs} cascade runs")
        if detail1.cascade_throws > 0:
            cascade1_parts.append(f"{detail1.cascade_throws} cascade throws")
        if detail1.cascade_kicks > 0:
            cascade1_parts.append(f"{detail1.cascade_kicks} cascade kicks")
        cascade1_str = f" ({', '.join(cascade1_parts)})" if cascade1_parts else ""
        
        lines.append(f"  {team1.name}: {detail1.runs} runs, {detail1.throws} throws, {detail1.kicks} kicks{cascade1_str}")
        
        # Scoring breakdown for team 2
        cascade2_parts = []
        if detail2.cascade_runs > 0:
            cascade2_parts.append(f"{detail2.cascade_runs} cascade runs")
        if detail2.cascade_throws > 0:
            cascade2_parts.append(f"{detail2.cascade_throws} cascade throws")
        if detail2.cascade_kicks > 0:
            cascade2_parts.append(f"{detail2.cascade_kicks} cascade kicks")
        cascade2_str = f" ({', '.join(cascade2_parts)})" if cascade2_parts else ""
        
        lines.append(f"  {team2.name}: {detail2.runs} runs, {detail2.throws} throws, {detail2.kicks} kicks{cascade2_str}")
        lines.append("")  # Blank line between games
    
    # Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()
    
    return "\n".join(lines)


def calculate_standings_up_to_week(initial_teams, game_results_by_week, max_week):
    """
    Calculate standings up to a specific week by replaying games.
    
    Args:
        initial_teams: List of Team objects in their initial state (before any games)
        game_results_by_week: Dictionary mapping week numbers to lists of game_result dictionaries
        max_week: Maximum week to include in standings calculation
    
    Returns:
        Formatted standings string for caption
    """
    # Create temporary copies of teams with initial state
    temp_teams = []
    team_dict = {}  # Map team names to team objects for quick lookup
    
    for team in initial_teams:
        temp_team = Team(team.name)
        temp_team.overall_advantage = team.overall_advantage
        temp_team.run_advantage = team.run_advantage
        temp_team.throw_advantage = team.throw_advantage
        temp_team.kick_advantage = team.kick_advantage
        temp_team.wins = 0
        temp_team.losses = 0
        temp_team.points_for = 0
        temp_team.points_against = 0
        # Copy player data if available
        if hasattr(team, 'players') and team.players:
            temp_team.players = [player.copy() for player in team.players]
        temp_teams.append(temp_team)
        team_dict[team.name] = temp_team
    
    # Replay games up to max_week
    for week in sorted([w for w in game_results_by_week.keys() if isinstance(w, int) and w <= max_week]):
        week_games = game_results_by_week[week]
        # Extract game results (skip gemini images, they're tuples with filename first)
        for item in week_games:
            # Check if it's a tuple (filename, game_result) or just game_result
            if isinstance(item, tuple):
                _, game_result = item
            else:
                game_result = item
            
            # Apply game result to temp teams
            team1_name = game_result['team1'].name
            team2_name = game_result['team2'].name
            team1_score = game_result['team1_score']
            team2_score = game_result['team2_score']
            
            temp_team1 = team_dict[team1_name]
            temp_team2 = team_dict[team2_name]
            
            # Update stats based on game result
            if team1_score > team2_score:
                temp_team1.wins += 1
                temp_team2.losses += 1
                temp_team1.points_for += team1_score
                temp_team1.points_against += team2_score
                temp_team2.points_for += team2_score
                temp_team2.points_against += team1_score
            else:
                temp_team2.wins += 1
                temp_team1.losses += 1
                temp_team2.points_for += team2_score
                temp_team2.points_against += team1_score
                temp_team1.points_for += team1_score
                temp_team1.points_against += team2_score
    
    # Format and return standings
    return format_standings_for_caption(temp_teams)


def tournament(teams):
    # Sort teams by wins, then by point difference
    sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
    tournament_images = []
    
    # Quarterfinals
    print("\nQuarterfinals:")
    quarterfinals = []
    quarterfinal_winners = []
    for game_num, game in enumerate([
        (sorted_teams[0], sorted_teams[7]),
        (sorted_teams[1], sorted_teams[6]),
        (sorted_teams[2], sorted_teams[5]),
        (sorted_teams[3], sorted_teams[4])
    ], 1):
        result, upset, game_result = play_game(*game)
        quarterfinals.append(result)
        print(result)
        
        # Generate quarterfinal image with standardized naming
        team1, team2 = game
        filename = f"tournament_quarterfinal_game_{game_num}.png"
        tournament_images.append((filename, game_result))
        # Add Gemini artistic photo
        gemini_filename = f"tournament_quarterfinal_game_{game_num}_gemini.png"
        tournament_images.append((gemini_filename, game_result))
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        quarterfinal_winners.append(winner)
        
        if upset:
            print(f"Upset: {game[1].name} (adv: {game[1].overall_advantage}) upset {game[0].name} (adv: {game[0].overall_advantage})")
    
    # Semifinals
    print("\nSemifinals:")
    semifinals = []
    semifinal_winners = []
    for game_num, game in enumerate([
        (quarterfinal_winners[0], quarterfinal_winners[1]),  # QF1 winner vs QF2 winner
        (quarterfinal_winners[2], quarterfinal_winners[3])   # QF3 winner vs QF4 winner
    ], 1):
        result, upset, game_result = play_game(*game)
        semifinals.append(result)
        print(result)
        
        # Generate semifinal image with standardized naming
        team1, team2 = game
        filename = f"tournament_semifinal_game_{game_num}.png"
        tournament_images.append((filename, game_result))
        # Add Gemini artistic photo
        gemini_filename = f"tournament_semifinal_game_{game_num}_gemini.png"
        tournament_images.append((gemini_filename, game_result))
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        semifinal_winners.append(winner)
        
        if upset:
            print(f"Upset: {game[1].name} (adv: {game[1].overall_advantage}) upset {game[0].name} (adv: {game[0].overall_advantage})")
    
    # Final - Best 2 out of 3
    print("\nFinal (Best 2 out of 3):")
    team1, team2 = semifinal_winners[0], semifinal_winners[1]
    
    team1_wins = 0
    team2_wins = 0
    game_num = 1
    final_results = []
    
    while team1_wins < 2 and team2_wins < 2:
        print(f"\nGame {game_num}:")
        result, upset, game_result = play_game(team1, team2)
        print(result)
        
        # Determine winner of this game
        # Note: play_game() handles ties internally, so scores should never be equal here
        if game_result['team1_score'] > game_result['team2_score']:
            team1_wins += 1
            winner = team1
        elif game_result['team2_score'] > game_result['team1_score']:
            team2_wins += 1
            winner = team2
        else:
            # This should never happen since play_game() handles ties, but handle it just in case
            # Play one more scoring opportunity to break the tie
            if random.random() < 0.5:
                team1_wins += 1
                winner = team1
            else:
                team2_wins += 1
                winner = team2
        
        # Generate final game image
        filename = f"tournament_final_game_{game_num}.png"
        tournament_images.append((filename, game_result))
        # Add Gemini artistic photo for final game
        gemini_filename = f"tournament_final_game_{game_num}_gemini.png"
        tournament_images.append((gemini_filename, game_result))
        final_results.append(result)
        
        print(f"Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}")
        
        if upset:
            # The upset flag indicates the lower-advantage team won
            winner = team1 if game_result['team1_score'] > game_result['team2_score'] else team2
            loser = team2 if game_result['team1_score'] > game_result['team2_score'] else team1
            print(f"Upset: {winner.name} (adv: {winner.overall_advantage}) upset {loser.name} (adv: {loser.overall_advantage})")
        
        game_num += 1
    
    # Determine tournament champion
    if team1_wins == 2:
        champion = team1
        final_winner = team1
    else:
        champion = team2
        final_winner = team2
    
    print(f"\n{'='*60}")
    print(f"🏆 TOURNAMENT CHAMPION: {champion.name} 🏆")
    print(f"Final Series: {team1.name} {team1_wins} - {team2_wins} {team2.name}")
    print(f"{'='*60}")
    
    # Generate champion trophy image
    # Use the final winning game result as the base
    if tournament_images:
        # Get the last game result (the final winning game)
        last_game_result = tournament_images[-1][1]
        # Create trophy image entry
        trophy_filename = "tournament_champion_trophy.png"
        # Create a copy of the game result for trophy image generation
        trophy_game_result = {
            'team1': last_game_result['team1'],
            'team2': last_game_result['team2'],
            'team1_score': last_game_result['team1_score'],
            'team2_score': last_game_result['team2_score'],
            'team1_detail': last_game_result['team1_detail'],
            'team2_detail': last_game_result['team2_detail'],
            'upset': last_game_result.get('upset', False),
            'is_champion': True  # Flag to indicate this is a trophy image
        }
        tournament_images.append((trophy_filename, trophy_game_result))
    
    # Use the last game result as the final result for return value
    final_result = final_results[-1]
    
    return quarterfinals, semifinals, final_result, tournament_images

