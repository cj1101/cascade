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

    def __str__(self):
        return (f"{self.name} (Overall: {self.overall_advantage}, "
                f"Run: {self.run_advantage}, Throw: {self.throw_advantage}, "
                f"Kick: {self.kick_advantage}, W-L: {self.wins}-{self.losses})")

    def best_stat(self):
        stats = [("Run", self.run_advantage), ("Throw", self.throw_advantage), ("Kick", self.kick_advantage)]
        return max(stats, key=lambda x: x[1])[0]
    
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


def play_game(team1, team2):
    base_chance = 0.5
    team1_chance = base_chance + (team1.overall_advantage - team2.overall_advantage) * 0.05
    team1_chance = max(0.1, min(0.9, team1_chance))  # Cap the chance between 10% and 90%

    team1_score = 0
    team2_score = 0
    team1_detail = ScoringDetail()
    team2_detail = ScoringDetail()

    for _ in range(20):  # 20 "scoring opportunities"
        if random.random() < team1_chance:
            # Ensure weights are always positive (at least 1) to avoid ValueError
            team1_weights = [
                max(1, 3 + team1.run_advantage),
                max(1, 3 + team1.throw_advantage),
                max(1, 3 + team1.kick_advantage)
            ]
            score_type = random.choices(['run', 'throw', 'kick'], 
                                        weights=team1_weights)[0]
            cascade = random.random() < 1/15  # Cascade zone chance
            if score_type == 'run':
                points = 3
                team1_detail.runs += 1
                if cascade:
                    points *= 2
                    team1_detail.cascade_runs += 1
            elif score_type == 'throw':
                points = 2
                team1_detail.throws += 1
                if cascade:
                    points *= 2
                    team1_detail.cascade_throws += 1
            else:
                points = 1
                team1_detail.kicks += 1
                if cascade:
                    points *= 2
                    team1_detail.cascade_kicks += 1
            team1_score += points
        else:
            # Ensure weights are always positive (at least 1) to avoid ValueError
            team2_weights = [
                max(1, 3 + team2.run_advantage),
                max(1, 3 + team2.throw_advantage),
                max(1, 3 + team2.kick_advantage)
            ]
            score_type = random.choices(['run', 'throw', 'kick'], 
                                        weights=team2_weights)[0]
            cascade = random.random() < 1/15  # Cascade zone chance
            if score_type == 'run':
                points = 3
                team2_detail.runs += 1
                if cascade:
                    points *= 2
                    team2_detail.cascade_runs += 1
            elif score_type == 'throw':
                points = 2
                team2_detail.throws += 1
                if cascade:
                    points *= 2
                    team2_detail.cascade_throws += 1
            else:
                points = 1
                team2_detail.kicks += 1
                if cascade:
                    points *= 2
                    team2_detail.cascade_kicks += 1
            team2_score += points

    if team1_score > team2_score:
        winner, loser = team1, team2
        winner_detail, loser_detail = team1_detail, team2_detail
    else:
        winner, loser = team2, team1
        winner_detail, loser_detail = team2_detail, team1_detail

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

    upset = (winner.overall_advantage < loser.overall_advantage)
    
    game_result = {
        'team1': team1,
        'team2': team2,
        'team1_score': team1_score,
        'team2_score': team2_score,
        'team1_detail': team1_detail,
        'team2_detail': team2_detail,
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
    
    Returns a tuple of (team1_odds, team2_odds) in American format.
    """
    base_chance = 0.5
    
    # Calculate win probability based on overall advantage (same as play_game uses)
    team1_advantage_diff = team1.overall_advantage - team2.overall_advantage
    team1_win_prob = base_chance + team1_advantage_diff * 0.05
    team1_win_prob = max(0.1, min(0.9, team1_win_prob))  # Cap between 10% and 90%
    
    # Adjust based on win percentage if teams have played games
    if team1.wins + team1.losses > 0 and team2.wins + team2.losses > 0:
        team1_win_pct = team1.wins / (team1.wins + team1.losses)
        team2_win_pct = team2.wins / (team2.wins + team2.losses)
        
        # Blend win percentage with advantage-based probability
        # Weight advantage more if teams have played fewer games
        games_weight = min(0.3, (team1.wins + team1.losses) / 20.0)
        team1_win_prob = team1_win_prob * (1 - games_weight) + team1_win_pct * games_weight
    
    # Adjust based on point differential
    if team1.wins + team1.losses > 0 and team2.wins + team2.losses > 0:
        team1_pd = team1.points_for - team1.points_against
        team2_pd = team2.points_for - team2.points_against
        total_pd = abs(team1_pd) + abs(team2_pd)
        
        if total_pd > 0:
            # Normalize point differential to affect probability
            pd_diff = (team1_pd - team2_pd) / max(100, total_pd)  # Scale by max expected PD
            pd_adjustment = pd_diff * 0.1  # Small adjustment
            team1_win_prob = max(0.1, min(0.9, team1_win_prob + pd_adjustment))
    
    team2_win_prob = 1.0 - team1_win_prob
    
    # Convert to American odds
    team1_odds = probability_to_american_odds(team1_win_prob)
    team2_odds = probability_to_american_odds(team2_win_prob)
    
    return team1_odds, team2_odds


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
    1. Team A (W-L, +/-)
    2. Team B (W-L, +/-)
    ...
    """
    sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
    
    standings_lines = []
    for i, team in enumerate(sorted_teams, 1):
        point_diff = team.points_for - team.points_against
        point_diff_str = f"+{point_diff}" if point_diff >= 0 else str(point_diff)
        standings_lines.append(f"{i}. {team.name} ({team.wins}-{team.losses}, {point_diff_str})")
    
    return "\n".join(standings_lines)


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
        if game_result['team1_score'] > game_result['team2_score']:
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

