"""Preview script to generate sample images showing the new design with all team stats"""
import os
from PIL import Image, ImageDraw, ImageFont
import game_logic

def draw_gradient_background(img, width, height, color1, color2, direction='vertical'):
    """Draw a gradient background on the image"""
    draw = ImageDraw.Draw(img)
    
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
    else:
        for x in range(width):
            ratio = x / width
            r = int(rgb1[0] * (1 - ratio) + rgb2[0] * ratio)
            g = int(rgb1[1] * (1 - ratio) + rgb2[1] * ratio)
            b = int(rgb2[2] * (1 - ratio) + rgb2[2] * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))


def generate_preview_image():
    """Generate a preview image showing the new design with all stats"""
    
    # Create mock teams with stats
    team1 = game_logic.Team("Apex Predators")
    team1.overall_advantage = 2
    team1.run_advantage = 3
    team1.throw_advantage = 1
    team1.kick_advantage = -1
    team1.wins = 5
    team1.losses = 2
    team1.points_for = 145
    team1.points_against = 120
    
    team2 = game_logic.Team("Vista Vipers")
    team2.overall_advantage = -1
    team2.run_advantage = 0
    team2.throw_advantage = 2
    team2.kick_advantage = 1
    team2.wins = 3
    team2.losses = 4
    team2.points_for = 110
    team2.points_against = 135
    
    # Create mock game result
    team1_detail = game_logic.ScoringDetail()
    team1_detail.runs = 8
    team1_detail.throws = 5
    team1_detail.kicks = 3
    team1_detail.cascade_runs = 2
    team1_detail.cascade_throws = 1
    team1_detail.cascade_kicks = 0
    
    team2_detail = game_logic.ScoringDetail()
    team2_detail.runs = 5
    team2_detail.throws = 7
    team2_detail.kicks = 4
    team2_detail.cascade_runs = 1
    team2_detail.cascade_throws = 2
    team2_detail.cascade_kicks = 1
    
    game_result = {
        'team1': team1,
        'team2': team2,
        'team1_score': 32,
        'team2_score': 24,
        'team1_detail': team1_detail,
        'team2_detail': team2_detail,
        'upset': False
    }
    
    # Create image
    width, height = 1600, 1600
    img = Image.new('RGB', (width, height), color='#0a0a1a')
    draw = ImageDraw.Draw(img)
    
    # Draw gradient background
    draw_gradient_background(img, width, height, '#0a0a1a', '#1a1a2e', 'vertical')
    
    # Try to load fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 64)
        team_font = ImageFont.truetype("arial.ttf", 48)
        stat_label_font = ImageFont.truetype("arial.ttf", 32)
        stat_value_font = ImageFont.truetype("arial.ttf", 36)
        score_font = ImageFont.truetype("arial.ttf", 180)
        small_font = ImageFont.truetype("arial.ttf", 24)
    except:
        try:
            title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 64)
            team_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
            stat_label_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
            stat_value_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
            score_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 180)
            small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            team_font = ImageFont.load_default()
            stat_label_font = ImageFont.load_default()
            stat_value_font = ImageFont.load_default()
            score_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    
    # Title section
    title = "Week 3 - Game 2"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = 30
    
    # Title with glow
    for offset in [6, 5, 4, 3, 2]:
        draw.text((title_x + offset, title_y + offset), title, fill='#000000', font=title_font)
    draw.text((title_x + 2, title_y + 2), title, fill='#4ecdc4', font=title_font)
    draw.text((title_x, title_y), title, fill='#ffffff', font=title_font)
    
    # Team cards layout
    card_width = 700
    card_height = 1200
    card_margin = 50
    card1_x = card_margin
    card2_x = width - card_margin - card_width
    card_y = 150
    
    # Draw glass morphism effect for cards
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([card1_x, card_y, card1_x + card_width, card_y + card_height], 
                          fill=(200, 220, 240, 30), outline='#4ecdc4', width=3)
    overlay_draw.rectangle([card2_x, card_y, card2_x + card_width, card_y + card_height], 
                          fill=(200, 220, 240, 30), outline='#4ecdc4', width=3)
    img.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(img)
    
    # Team 1 Card
    y_pos = card_y + 40
    
    # Team name
    team1_bbox = draw.textbbox((0, 0), team1.name, font=team_font)
    team1_width = team1_bbox[2] - team1_bbox[0]
    team1_x = card1_x + (card_width - team1_width) // 2
    for offset in [4, 3, 2]:
        draw.text((team1_x + offset, y_pos + offset), team1.name, fill='#000000', font=team_font)
    draw.text((team1_x + 1, y_pos + 1), team1.name, fill='#4ecdc4', font=team_font)
    draw.text((team1_x, y_pos), team1.name, fill='#ffffff', font=team_font)
    y_pos += 80
    
    # Game Stats Section
    draw.text((card1_x + 30, y_pos), "GAME STATS", fill='#ffd93d', font=stat_label_font)
    y_pos += 50
    
    # Runs
    runs_text = f"Runs: {team1_detail.runs}"
    if team1_detail.cascade_runs > 0:
        runs_text += f" (⚡{team1_detail.cascade_runs})"
    draw.text((card1_x + 50, y_pos), runs_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    # Throws
    throws_text = f"Throws: {team1_detail.throws}"
    if team1_detail.cascade_throws > 0:
        throws_text += f" (⚡{team1_detail.cascade_throws})"
    draw.text((card1_x + 50, y_pos), throws_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    # Kicks
    kicks_text = f"Kicks: {team1_detail.kicks}"
    if team1_detail.cascade_kicks > 0:
        kicks_text += f" (⚡{team1_detail.cascade_kicks})"
    draw.text((card1_x + 50, y_pos), kicks_text, fill='#ffffff', font=stat_value_font)
    y_pos += 70
    
    # Season Stats Section
    draw.text((card1_x + 30, y_pos), "SEASON STATS", fill='#ffd93d', font=stat_label_font)
    y_pos += 50
    
    record_text = f"Record: {team1.wins}-{team1.losses}"
    draw.text((card1_x + 50, y_pos), record_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    points_text = f"Points: {team1.points_for}-{team1.points_against}"
    draw.text((card1_x + 50, y_pos), points_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    point_diff = team1.points_for - team1.points_against
    diff_text = f"Diff: {'+' if point_diff >= 0 else ''}{point_diff}"
    diff_color = '#00ff00' if point_diff >= 0 else '#ff0000'
    draw.text((card1_x + 50, y_pos), diff_text, fill=diff_color, font=stat_value_font)
    y_pos += 70
    
    # Advantage Stats Section
    draw.text((card1_x + 30, y_pos), "ADVANTAGES", fill='#ffd93d', font=stat_label_font)
    y_pos += 50
    
    overall_text = f"Overall: {team1.overall_advantage:+d}"
    overall_color = '#00ff00' if team1.overall_advantage >= 0 else '#ff0000'
    draw.text((card1_x + 50, y_pos), overall_text, fill=overall_color, font=stat_value_font)
    y_pos += 45
    
    run_adv_text = f"Run: {team1.run_advantage:+d}"
    run_color = '#00ff00' if team1.run_advantage >= 0 else '#ff0000'
    draw.text((card1_x + 50, y_pos), run_adv_text, fill=run_color, font=stat_value_font)
    y_pos += 45
    
    throw_adv_text = f"Throw: {team1.throw_advantage:+d}"
    throw_color = '#00ff00' if team1.throw_advantage >= 0 else '#ff0000'
    draw.text((card1_x + 50, y_pos), throw_adv_text, fill=throw_color, font=stat_value_font)
    y_pos += 45
    
    kick_adv_text = f"Kick: {team1.kick_advantage:+d}"
    kick_color = '#00ff00' if team1.kick_advantage >= 0 else '#ff0000'
    draw.text((card1_x + 50, y_pos), kick_adv_text, fill=kick_color, font=stat_value_font)
    
    # Team 2 Card (same layout)
    y_pos = card_y + 40
    
    team2_bbox = draw.textbbox((0, 0), team2.name, font=team_font)
    team2_width = team2_bbox[2] - team2_bbox[0]
    team2_x = card2_x + (card_width - team2_width) // 2
    for offset in [4, 3, 2]:
        draw.text((team2_x + offset, y_pos + offset), team2.name, fill='#000000', font=team_font)
    draw.text((team2_x + 1, y_pos + 1), team2.name, fill='#4ecdc4', font=team_font)
    draw.text((team2_x, y_pos), team2.name, fill='#ffffff', font=team_font)
    y_pos += 80
    
    draw.text((card2_x + 30, y_pos), "GAME STATS", fill='#ffd93d', font=stat_label_font)
    y_pos += 50
    
    runs_text = f"Runs: {team2_detail.runs}"
    if team2_detail.cascade_runs > 0:
        runs_text += f" (⚡{team2_detail.cascade_runs})"
    draw.text((card2_x + 50, y_pos), runs_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    throws_text = f"Throws: {team2_detail.throws}"
    if team2_detail.cascade_throws > 0:
        throws_text += f" (⚡{team2_detail.cascade_throws})"
    draw.text((card2_x + 50, y_pos), throws_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    kicks_text = f"Kicks: {team2_detail.kicks}"
    if team2_detail.cascade_kicks > 0:
        kicks_text += f" (⚡{team2_detail.cascade_kicks})"
    draw.text((card2_x + 50, y_pos), kicks_text, fill='#ffffff', font=stat_value_font)
    y_pos += 70
    
    draw.text((card2_x + 30, y_pos), "SEASON STATS", fill='#ffd93d', font=stat_label_font)
    y_pos += 50
    
    record_text = f"Record: {team2.wins}-{team2.losses}"
    draw.text((card2_x + 50, y_pos), record_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    points_text = f"Points: {team2.points_for}-{team2.points_against}"
    draw.text((card2_x + 50, y_pos), points_text, fill='#ffffff', font=stat_value_font)
    y_pos += 45
    
    point_diff = team2.points_for - team2.points_against
    diff_text = f"Diff: {'+' if point_diff >= 0 else ''}{point_diff}"
    diff_color = '#00ff00' if point_diff >= 0 else '#ff0000'
    draw.text((card2_x + 50, y_pos), diff_text, fill=diff_color, font=stat_value_font)
    y_pos += 70
    
    draw.text((card2_x + 30, y_pos), "ADVANTAGES", fill='#ffd93d', font=stat_label_font)
    y_pos += 50
    
    overall_text = f"Overall: {team2.overall_advantage:+d}"
    overall_color = '#00ff00' if team2.overall_advantage >= 0 else '#ff0000'
    draw.text((card2_x + 50, y_pos), overall_text, fill=overall_color, font=stat_value_font)
    y_pos += 45
    
    run_adv_text = f"Run: {team2.run_advantage:+d}"
    run_color = '#00ff00' if team2.run_advantage >= 0 else '#ff0000'
    draw.text((card2_x + 50, y_pos), run_adv_text, fill=run_color, font=stat_value_font)
    y_pos += 45
    
    throw_adv_text = f"Throw: {team2.throw_advantage:+d}"
    throw_color = '#00ff00' if team2.throw_advantage >= 0 else '#ff0000'
    draw.text((card2_x + 50, y_pos), throw_adv_text, fill=throw_color, font=stat_value_font)
    y_pos += 45
    
    kick_adv_text = f"Kick: {team2.kick_advantage:+d}"
    kick_color = '#00ff00' if team2.kick_advantage >= 0 else '#ff0000'
    draw.text((card2_x + 50, y_pos), kick_adv_text, fill=kick_color, font=stat_value_font)
    
    # Center Score Section
    center_x = width // 2
    center_y = card_y + card_height // 2
    
    # VS indicator
    vs_bbox = draw.textbbox((0, 0), "VS", font=team_font)
    vs_width = vs_bbox[2] - vs_bbox[0]
    vs_x = center_x - vs_width // 2
    vs_y = center_y - 100
    for offset in [5, 4, 3, 2]:
        draw.text((vs_x + offset, vs_y + offset), "VS", fill='#000000', font=team_font)
    draw.text((vs_x + 2, vs_y + 2), "VS", fill='#ffd93d', font=team_font)
    draw.text((vs_x, vs_y), "VS", fill='#ffffff', font=team_font)
    
    # Scores
    team1_score = 32
    team2_score = 24
    score1_text = str(team1_score)
    score1_bbox = draw.textbbox((0, 0), score1_text, font=score_font)
    score1_width = score1_bbox[2] - score1_bbox[0]
    score1_x = center_x - score1_width - 30
    score1_y = center_y - 50
    for offset in [10, 8, 6, 4, 3]:
        draw.text((score1_x + offset, score1_y + offset), score1_text, fill='#000000', font=score_font)
    draw.text((score1_x + 3, score1_y + 3), score1_text, fill='#00ff00', font=score_font)
    draw.text((score1_x, score1_y), score1_text, fill='#ffffff', font=score_font)
    
    score2_text = str(team2_score)
    score2_bbox = draw.textbbox((0, 0), score2_text, font=score_font)
    score2_width = score2_bbox[2] - score2_bbox[0]
    score2_x = center_x + 30
    score2_y = center_y - 50
    for offset in [10, 8, 6, 4, 3]:
        draw.text((score2_x + offset, score2_y + offset), score2_text, fill='#000000', font=score_font)
    draw.text((score2_x + 3, score2_y + 3), score2_text, fill='#ff0000', font=score_font)
    draw.text((score2_x, score2_y), score2_text, fill='#ffffff', font=score_font)
    
    # Bottom legend
    legend_y = height - 60
    legend_text = "⚡ = Cascade Zone"
    legend_bbox = draw.textbbox((0, 0), legend_text, font=small_font)
    legend_width = legend_bbox[2] - legend_bbox[0]
    legend_x = (width - legend_width) // 2
    draw.text((legend_x, legend_y), legend_text, fill='#ffffff', font=small_font)
    
    # Border
    border_width = 8
    border_color = '#4ecdc4'
    for i in range(3):
        draw.rectangle([i, i, width-1-i, height-1-i], outline=border_color, width=1)
    draw.rectangle([3, 3, width-4, height-4], outline=border_color, width=border_width)
    
    # Save preview
    filename = "preview_new_design.png"
    img.save(filename)
    print(f"Preview image saved as {filename}")
    return filename


if __name__ == "__main__":
    generate_preview_image()
    print("Preview generation complete!")

