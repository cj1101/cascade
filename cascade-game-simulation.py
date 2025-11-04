import random
import os
import hashlib
import time
from itertools import combinations
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Configuration Settings
ROUNDS_PER_ROUND_ROBIN = None  # Number of rounds to play in each round-robin cycle (None = play all rounds)
ROUND_ROBIN_REPETITIONS = 2  # Number of times to repeat the complete round-robin cycle
LOGOS_DIRECTORY = r"C:\Users\charl\CodingProjets\logos"

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
            score_type = random.choices(['run', 'throw', 'kick'], 
                                        weights=[3 + team1.run_advantage, 
                                                 3 + team1.throw_advantage, 
                                                 3 + team1.kick_advantage])[0]
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
            score_type = random.choices(['run', 'throw', 'kick'], 
                                        weights=[3 + team2.run_advantage, 
                                                 3 + team2.throw_advantage, 
                                                 3 + team2.kick_advantage])[0]
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

def draw_gradient_background(img, width, height, color1, color2, direction='vertical'):
    """Draw a gradient background on the image"""
    draw = ImageDraw.Draw(img)
    
    # Parse colors
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    if direction == 'vertical':
        for y in range(height):
            ratio = y / height
            r = int(rgb1[0] * (1 - ratio) + rgb2[0] * ratio)
            g = int(rgb1[1] * (1 - ratio) + rgb2[1] * ratio)
            b = int(rgb1[2] * (1 - ratio) + rgb2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    else:  # horizontal
        for x in range(width):
            ratio = x / width
            r = int(rgb1[0] * (1 - ratio) + rgb2[0] * ratio)
            g = int(rgb1[1] * (1 - ratio) + rgb2[1] * ratio)
            b = int(rgb1[2] * (1 - ratio) + rgb2[2] * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))

def generate_game_image(game_result, filename, game_type="game", week=None, game_number=None):
    """Generate a game scoreboard image with team logos and scores - enhanced with modern styling"""
    try:
        # Create image with gradient background
        width, height = 1200, 800
        img = Image.new('RGB', (width, height), color='#0a0a1a')
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        draw_gradient_background(img, width, height, '#0a0a1a', '#1a1a2e', 'vertical')
        
        # Try to load fonts, fallback to default if not available
        try:
            title_font = ImageFont.truetype("arial.ttf", 56)
            title_bold_font = ImageFont.truetype("arial.ttf", 56)
            score_font = ImageFont.truetype("arial.ttf", 96)
            team_font = ImageFont.truetype("arial.ttf", 42)
            detail_font = ImageFont.truetype("arial.ttf", 26)
            vs_font = ImageFont.truetype("arial.ttf", 48)
        except:
            try:
                title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 56)
                title_bold_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 56)
                score_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 96)
                team_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 42)
                detail_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 26)
                vs_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
            except:
                title_font = ImageFont.load_default()
                title_bold_font = ImageFont.load_default()
                score_font = ImageFont.load_default()
                team_font = ImageFont.load_default()
                detail_font = ImageFont.load_default()
                vs_font = ImageFont.load_default()
        
        team1 = game_result['team1']
        team2 = game_result['team2']
        team1_score = game_result['team1_score']
        team2_score = game_result['team2_score']
        team1_detail = game_result['team1_detail']
        team2_detail = game_result['team2_detail']
        
        # Draw decorative border
        border_width = 8
        border_color = '#4ecdc4'
        draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=border_width)
        draw.rectangle([border_width, border_width, width-border_width-1, height-border_width-1], 
                       outline='#2a2a4e', width=2)
        
        # Draw title with shadow effect
        title = f"{game_type.replace('_', ' ').title()}"
        if week:
            title = f"Week {week} - {title}"
        elif game_number:
            title = f"{title} {game_number}"
        
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = 40
        
        # Title shadow
        draw.text((title_x + 3, title_y + 3), title, fill='#000000', font=title_font)
        # Title text with gradient effect
        draw.text((title_x, title_y), title, fill='#ffffff', font=title_font)
        
        # Decorative line under title
        line_y = title_y + 60
        draw.line([(title_x - 20, line_y), (title_x + title_width + 20, line_y)], 
                  fill='#4ecdc4', width=3)
        
        # Load and resize logos with shadow effect
        logo_size = 220
        logo1 = None
        logo1_path = os.path.join(LOGOS_DIRECTORY, team1.get_logo_filename())
        for logo_file in [logo1_path, logo1_path.replace("'", "'"), logo1_path.replace("'", "'")]:
            try:
                if os.path.exists(logo_file):
                    logo1 = Image.open(logo_file).convert('RGBA')
                    logo1 = logo1.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                    break
            except:
                continue
        
        logo2 = None
        logo2_path = os.path.join(LOGOS_DIRECTORY, team2.get_logo_filename())
        for logo_file in [logo2_path, logo2_path.replace("'", "'"), logo2_path.replace("'", "'")]:
            try:
                if os.path.exists(logo_file):
                    logo2 = Image.open(logo_file).convert('RGBA')
                    logo2 = logo2.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                    break
            except:
                continue
        
        # Draw team 1 section (left) with decorative background
        team1_x = 120
        team1_y = 180
        
        # Team 1 card background with shadow
        card1_width = 400
        card1_height = 450
        draw.rectangle([team1_x - 15, team1_y - 15, team1_x + card1_width - 15, team1_y + card1_height - 15], 
                       fill='#1a1a2e', outline='#2a2a4e', width=2)
        draw.rectangle([team1_x - 10, team1_y - 10, team1_x + card1_width - 10, team1_y + card1_height - 10], 
                       fill='#0f0f1f', outline='#4ecdc4', width=2)
        
        if logo1:
            # Logo shadow
            logo1_shadow = logo1.copy()
            shadow_mask = Image.new('RGBA', logo1_shadow.size, (0, 0, 0, 128))
            shadow_img = Image.new('RGBA', (logo_size + 10, logo_size + 10), (0, 0, 0, 0))
            shadow_img.paste(shadow_mask, (5, 5), shadow_mask)
            img.paste(shadow_img, (team1_x - 5, team1_y - 5), shadow_img)
            img.paste(logo1, (team1_x, team1_y), logo1)
        
        team1_name_y = team1_y + logo_size + 30
        draw.text((team1_x, team1_name_y), team1.name, fill='#ffffff', font=team_font)
        
        # Score with glow effect
        score1_y = team1_name_y + 60
        draw.text((team1_x + 5, score1_y + 5), str(team1_score), fill='#000000', font=score_font)
        draw.text((team1_x, score1_y), str(team1_score), fill='#4ecdc4', font=score_font)
        
        # Draw VS separator with decorative styling
        vs_y = team1_y + logo_size // 2
        vs_x = width // 2
        vs_text = "VS"
        vs_bbox = draw.textbbox((0, 0), vs_text, font=vs_font)
        vs_width = vs_bbox[2] - vs_bbox[0]
        vs_height = vs_bbox[3] - vs_bbox[1]
        
        # VS background circle
        circle_radius = 60
        draw.ellipse([vs_x - circle_radius, vs_y - circle_radius, 
                     vs_x + circle_radius, vs_y + circle_radius], 
                    fill='#1a1a2e', outline='#ff6b6b', width=4)
        draw.text((vs_x - vs_width // 2, vs_y - vs_height // 2), vs_text, 
                 fill='#ff6b6b', font=vs_font)
        
        # Draw team 2 section (right) with decorative background
        team2_x = width - 120 - card1_width
        team2_y = team1_y
        
        # Team 2 card background with shadow
        draw.rectangle([team2_x - 15, team2_y - 15, team2_x + card1_width - 15, team2_y + card1_height - 15], 
                       fill='#1a1a2e', outline='#2a2a4e', width=2)
        draw.rectangle([team2_x - 10, team2_y - 10, team2_x + card1_width - 10, team2_y + card1_height - 10], 
                       fill='#0f0f1f', outline='#4ecdc4', width=2)
        
        if logo2:
            # Logo shadow
            logo2_shadow = logo2.copy()
            shadow_mask = Image.new('RGBA', logo2_shadow.size, (0, 0, 0, 128))
            shadow_img = Image.new('RGBA', (logo_size + 10, logo_size + 10), (0, 0, 0, 0))
            shadow_img.paste(shadow_mask, (5, 5), shadow_mask)
            img.paste(shadow_img, (team2_x - 5, team2_y - 5), shadow_img)
            img.paste(logo2, (team2_x, team2_y), logo2)
        
        team2_name_y = team2_y + logo_size + 30
        team2_name_bbox = draw.textbbox((0, 0), team2.name, font=team_font)
        team2_name_width = team2_name_bbox[2] - team2_name_bbox[0]
        draw.text((team2_x + card1_width - team2_name_width, team2_name_y), team2.name, 
                 fill='#ffffff', font=team_font)
        
        # Score with glow effect
        score2_y = team2_name_y + 60
        team2_score_bbox = draw.textbbox((0, 0), str(team2_score), font=score_font)
        team2_score_width = team2_score_bbox[2] - team2_score_bbox[0]
        draw.text((team2_x + card1_width - team2_score_width + 5, score2_y + 5), 
                 str(team2_score), fill='#000000', font=score_font)
        draw.text((team2_x + card1_width - team2_score_width, score2_y), 
                 str(team2_score), fill='#4ecdc4', font=score_font)
        
        # Draw scoring details with decorative boxes
        detail_y = team1_y + card1_height + 20
        detail_box_height = 80
        detail_box_y = detail_y - 10
        
        # Team 1 details box
        draw.rectangle([team1_x - 10, detail_box_y, team1_x + card1_width - 10, detail_box_y + detail_box_height], 
                      fill='#0f0f1f', outline='#2a2a4e', width=2)
        detail1 = f"Runs: {team1_detail.runs} | Throws: {team1_detail.throws} | Kicks: {team1_detail.kicks}"
        draw.text((team1_x + 10, detail_y), detail1, fill='#cccccc', font=detail_font)
        
        # Team 2 details box
        draw.rectangle([team2_x - 10, detail_box_y, team2_x + card1_width - 10, detail_box_y + detail_box_height], 
                      fill='#0f0f1f', outline='#2a2a4e', width=2)
        detail2 = f"Runs: {team2_detail.runs} | Throws: {team2_detail.throws} | Kicks: {team2_detail.kicks}"
        detail2_bbox = draw.textbbox((0, 0), detail2, font=detail_font)
        detail2_width = detail2_bbox[2] - detail2_bbox[0]
        draw.text((team2_x + card1_width - detail2_width - 10, detail_y), detail2, fill='#cccccc', font=detail_font)
        
        # Draw cascade details if any
        cascade_y = detail_y + 35
        cascade1_total = team1_detail.cascade_runs + team1_detail.cascade_throws + team1_detail.cascade_kicks
        cascade2_total = team2_detail.cascade_runs + team2_detail.cascade_throws + team2_detail.cascade_kicks
        if cascade1_total > 0 or cascade2_total > 0:
            cascade1_text = f"⚡ Cascade: {cascade1_total}"
            cascade2_text = f"⚡ Cascade: {cascade2_total}"
            draw.text((team1_x + 10, cascade_y), cascade1_text, fill='#ffd93d', font=detail_font)
            cascade2_bbox = draw.textbbox((0, 0), cascade2_text, font=detail_font)
            cascade2_width = cascade2_bbox[2] - cascade2_bbox[0]
            draw.text((team2_x + card1_width - cascade2_width - 10, cascade_y), cascade2_text, fill='#ffd93d', font=detail_font)
        
        # Draw winner indicator with decorative styling
        winner_y = height - 100
        if team1_score > team2_score:
            winner_text = f"🏆 Winner: {team1.name}"
            winner_color = '#4ecdc4'
        else:
            winner_text = f"🏆 Winner: {team2.name}"
            winner_color = '#4ecdc4'
        
        winner_bbox = draw.textbbox((0, 0), winner_text, font=team_font)
        winner_width = winner_bbox[2] - winner_bbox[0]
        winner_x = (width - winner_width) // 2
        
        # Winner background box
        draw.rectangle([winner_x - 20, winner_y - 15, winner_x + winner_width + 20, winner_y + 50], 
                      fill='#0f0f1f', outline=winner_color, width=3)
        draw.text((winner_x + 3, winner_y + 3), winner_text, fill='#000000', font=team_font)
        draw.text((winner_x, winner_y), winner_text, fill=winner_color, font=team_font)
        
        # Save image
        img.save(filename)
        return True
    except Exception as e:
        print(f"Error generating image {filename}: {e}")
        return False

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
            filename = f"week_{week}_game_{game_num}.png"
            generate_game_image(game_result, filename, game_type="game", week=week)
            week_images.append(filename)
            
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
        generate_game_image(game_result, filename, game_type="quarterfinal", game_number=game_num)
        tournament_images.append(filename)
        
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
        generate_game_image(game_result, filename, game_type="semifinal", game_number=game_num)
        tournament_images.append(filename)
        
        # Track winner
        winner = game_result['team1'] if game_result['team1_score'] > game_result['team2_score'] else game_result['team2']
        semifinal_winners.append(winner)
        
        if upset:
            print(f"Upset: {game[1].name} (adv: {game[1].overall_advantage}) upset {game[0].name} (adv: {game[0].overall_advantage})")
    
    # Final
    print("\nFinal:")
    final_result, final_upset, final_game_result = play_game(semifinal_winners[0], semifinal_winners[1])
    print(final_result)
    
    # Generate final images (best of series - 2 games)
    team1, team2 = semifinal_winners[0], semifinal_winners[1]
    filename1 = f"tournament_final_game_1.png"
    generate_game_image(final_game_result, filename1, game_type="final", game_number=1)
    tournament_images.append(filename1)
    
    # Play second game if needed (best of 2)
    final2_result, final2_upset, final2_game_result = play_game(team1, team2)
    filename2 = f"tournament_final_game_2.png"
    generate_game_image(final2_game_result, filename2, game_type="final", game_number=2)
    tournament_images.append(filename2)
    print(final2_result)
    
    if final_upset:
        print(f"Upset: {semifinal_winners[1].name} (adv: {semifinal_winners[1].overall_advantage}) upset {semifinal_winners[0].name} (adv: {semifinal_winners[0].overall_advantage})")
    
    return quarterfinals, semifinals, final_result, tournament_images

def post_to_instagram(image_paths, caption=""):
    """
    Post images to Instagram using browser automation.
    Note: This function uses browser automation tools available via MCP.
    For automated posting, you may need to install selenium or playwright.
    """
    try:
        # Try using selenium if available
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            
            # Setup Chrome driver
            chrome_options = Options()
            # chrome_options.add_argument("--headless")  # Uncomment for headless mode
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # Navigate to Instagram
                driver.get("https://www.instagram.com")
                time.sleep(3)
                
                # Check if login is needed
                if "login" in driver.current_url.lower() or "accounts/login" in driver.current_url:
                    print("\n" + "="*60)
                    print("Please log in to Instagram in the browser window.")
                    print("Press Enter once you are logged in and ready to post...")
                    print("="*60)
                    input()
                
                # Navigate to create post
                driver.get("https://www.instagram.com/create/select/")
                time.sleep(3)
                
                # Find file input
                file_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                
                # Upload images
                if len(image_paths) > 1:
                    # For multiple images, upload all at once (carousel)
                    file_paths = "\n".join([os.path.abspath(img) for img in image_paths])
                    file_input.send_keys(file_paths)
                    print(f"Uploaded {len(image_paths)} images for carousel post")
                else:
                    file_input.send_keys(os.path.abspath(image_paths[0]))
                    print(f"Uploaded image: {image_paths[0]}")
                
                time.sleep(5)  # Wait for upload
                
                # Find and fill caption
                try:
                    caption_area = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[aria-label*='Write a caption']"))
                    )
                    caption_area.send_keys(caption)
                    time.sleep(2)
                except:
                    print("Could not find caption area - you may need to add caption manually")
                
                # Click share button
                try:
                    # Try different selectors for the share button
                    share_button = None
                    for selector in [
                        "button[type='submit']",
                        "button:contains('Share')",
                        "//button[contains(text(), 'Share')]"
                    ]:
                        try:
                            if selector.startswith("//"):
                                share_button = driver.find_element(By.XPATH, selector)
                            else:
                                share_button = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                            break
                        except:
                            continue
                    
                    if share_button:
                        share_button.click()
                        print("Post shared!")
                        time.sleep(3)
                    else:
                        raise Exception("Share button not found")
                except:
                    print("Please click 'Share' button manually")
                    input("Press Enter once posted...")
                
                driver.quit()
                return True
                
            except Exception as e:
                print(f"Error during Instagram posting: {e}")
                print("Falling back to manual posting instructions...")
                driver.quit()
                return post_to_instagram_manual(image_paths, caption)
                
        except ImportError:
            # Selenium not available, use manual method
            print("Selenium not installed. Using manual posting method.")
            return post_to_instagram_manual(image_paths, caption)
            
    except Exception as e:
        print(f"Error posting to Instagram: {e}")
        return post_to_instagram_manual(image_paths, caption)

def post_to_instagram_manual(image_paths, caption=""):
    """Manual posting method with instructions"""
    print("\n" + "="*60)
    print("MANUAL INSTAGRAM POSTING")
    print("="*60)
    print(f"Caption: {caption}")
    print(f"Images to post ({len(image_paths)}):")
    for i, img in enumerate(image_paths, 1):
        print(f"  {i}. {os.path.abspath(img)}")
    print("\nInstructions:")
    print("1. Open Instagram in your browser")
    print("2. Click the '+' button to create a new post")
    print("3. Select the images listed above")
    print(f"4. Add the caption: {caption}")
    print("5. Click 'Share'")
    print("\nPress Enter once you have posted...")
    input()
    return True

def post_images_hourly(all_images_by_week):
    """Post images to Instagram with 1 hour intervals between weeks"""
    print("\n" + "="*60)
    print("Starting Instagram posting schedule...")
    print("="*60)
    
    # Sort weeks
    sorted_weeks = sorted([w for w in all_images_by_week.keys() if isinstance(w, int)])
    
    for week in sorted_weeks:
        images = all_images_by_week[week]
        if not images:
            continue
        
        print(f"\n{'='*60}")
        print(f"Posting Week {week} ({len(images)} images)")
        print(f"{'='*60}")
        
        # Create caption for the week
        caption = f"Week {week} Game Results"
        
        # Post all images for this week
        success = post_to_instagram(images, caption)
        
        if not success:
            print(f"Warning: Failed to post Week {week} images")
            response = input("Continue to next week? (y/n): ")
            if response.lower() != 'y':
                break
        
        # Wait 1 hour before next week (unless it's the last week)
        if week < sorted_weeks[-1]:
            print(f"\nWaiting 1 hour before posting Week {week + 1}...")
            print("(You can press Ctrl+C to cancel)")
            try:
                time.sleep(3600)  # 1 hour = 3600 seconds
            except KeyboardInterrupt:
                print("\nPosting cancelled by user.")
                break
    
    print("\nInstagram posting schedule completed!")

def main():
    # Get user input for number of round robins
    print("="*60)
    print("CASCADE GAME SIMULATION")
    print("="*60)
    
    while True:
        try:
            num_round_robins = input("\nHow many round robins would you like to play before the tournament? ")
            num_round_robins = int(num_round_robins)
            if num_round_robins > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    
    ROUND_ROBIN_REPETITIONS = num_round_robins
    
    team_names = [
        "Apex Predators",
        "Vista Vipers",
        "Skybound Storm",
        "Raven's Renegades",
        "Cove Crushers",
        "Ember Enforcers",
        "Pinnacle Pioneers",
        "Evan City Commies"
    ]
    teams = [Team(name) for name in team_names]
    
    # Track all generated images by week
    all_images_by_week = {}
    current_week = 1
    
    repetition_text = "Round Robin" if ROUND_ROBIN_REPETITIONS == 1 else f"Round Robin ({ROUND_ROBIN_REPETITIONS} repetitions)"
    print(f"\n{repetition_text}:")
    for round_robin_num in range(ROUND_ROBIN_REPETITIONS):
        results, generated_images = round_robin(teams, max_rounds=ROUNDS_PER_ROUND_ROBIN, start_week=current_week)
        # Merge images into main tracking dict
        for week, images in generated_images.items():
            if week not in all_images_by_week:
                all_images_by_week[week] = []
            all_images_by_week[week].extend(images)
        # Update current week for next round robin
        if generated_images:
            current_week = max(generated_images.keys()) + 1
        else:
            # Calculate next week based on number of teams
            num_teams = len(teams)
            weeks_per_round_robin = num_teams - 1 if num_teams % 2 == 0 else num_teams
            current_week += weeks_per_round_robin
    
    repetition_label = "Round Robin" if ROUND_ROBIN_REPETITIONS == 1 else f"{ROUND_ROBIN_REPETITIONS}x Round Robin"
    print(f"\nFinal Standings after {repetition_label}:")
    display_standings(teams)
    
    print("\nTournament:")
    quarterfinals, semifinals, final_result, tournament_images = tournament(teams)
    # Add tournament images to a special key (not a week number)
    all_images_by_week['tournament'] = tournament_images
    
    print("\nFinal Team Stats:")
    for team in teams:
        print(f"{team}")
    
    # Ask if user wants to post to Instagram
    print("\n" + "="*60)
    post_to_instagram_choice = input("Would you like to post images to Instagram? (y/n): ")
    
    if post_to_instagram_choice.lower() == 'y':
        # Post round robin images by week
        post_images_hourly(all_images_by_week)

if __name__ == "__main__":
    main()
