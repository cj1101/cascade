"""Image generation module for Cascade game simulation"""
import os
import random
import math
try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except ImportError:
    raise ImportError(
        "PIL (Pillow) is required for image generation. "
        "Please install it with: pip install pillow"
    )
try:
    import numpy as np
except ImportError:
    np = None  # Will use PIL-only method if numpy not available
import config


# Font paths to try in order: generic name, Windows path, Linux paths
FONT_PATHS_REGULAR = [
    "arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]
FONT_PATHS_BOLD = [
    "arialbd.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]


def load_font(paths, size):
    """Try to load a font from a list of paths, falling back to default if none work."""
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()


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


def extract_dominant_color(logo_image):
    """
    Extract the single most dominant color from a logo image.
    Returns RGB tuple of the dominant color.
    """
    if logo_image is None:
        return (78, 205, 196)  # Default teal color
    
    # Convert to RGB if needed
    if logo_image.mode != 'RGB':
        rgb_logo = Image.new('RGB', logo_image.size, (255, 255, 255))
        if logo_image.mode == 'RGBA':
            rgb_logo.paste(logo_image, mask=logo_image.split()[3])  # Use alpha channel as mask
        else:
            rgb_logo.paste(logo_image)
        logo_image = rgb_logo
    
    # Resize to smaller size for faster processing
    small_logo = logo_image.resize((50, 50), Image.Resampling.LANCZOS)
    
    # Get all pixel colors
    pixels = list(small_logo.getdata())
    
    # Filter out white/very light colors (background) and black/very dark colors
    # Keep only meaningful colors
    meaningful_pixels = []
    for r, g, b in pixels:
        # Skip very light colors (likely background)
        if r > 240 and g > 240 and b > 240:
            continue
        # Skip very dark colors (likely outlines/shadows)
        if r < 30 and g < 30 and b < 30:
            continue
        meaningful_pixels.append((r, g, b))
    
    if not meaningful_pixels:
        # If no meaningful pixels found, use all pixels
        meaningful_pixels = pixels
    
    # Calculate average of top colors by frequency
    # Group similar colors together
    color_buckets = {}
    bucket_size = 20  # Group colors within 20 RGB units
    
    for r, g, b in meaningful_pixels:
        # Round to bucket size
        bucket = (r // bucket_size, g // bucket_size, b // bucket_size)
        if bucket not in color_buckets:
            color_buckets[bucket] = []
        color_buckets[bucket].append((r, g, b))
    
    # Find the bucket with most pixels
    if color_buckets:
        largest_bucket = max(color_buckets.values(), key=len)
        # Average the colors in the largest bucket
        avg_r = sum(c[0] for c in largest_bucket) // len(largest_bucket)
        avg_g = sum(c[1] for c in largest_bucket) // len(largest_bucket)
        avg_b = sum(c[2] for c in largest_bucket) // len(largest_bucket)
        return (avg_r, avg_g, avg_b)
    
    # Fallback: use average of all pixels
    if pixels:
        avg_r = sum(p[0] for p in pixels) // len(pixels)
        avg_g = sum(p[1] for p in pixels) // len(pixels)
        avg_b = sum(p[2] for p in pixels) // len(pixels)
        return (avg_r, avg_g, avg_b)
    
    return (78, 205, 196)  # Default teal color


def apply_translucent_logo_background(img, logo_image, width, height):
    """
    Apply a translucent version of the winner's logo as the background.
    Scales the logo to cover the entire image and centers it.
    The logo becomes the primary background element.
    """
    if logo_image is None:
        return
    
    # Convert to RGBA if needed
    if logo_image.mode != 'RGBA':
        logo_rgba = Image.new('RGBA', logo_image.size, (255, 255, 255, 255))
        if logo_image.mode == 'RGB':
            logo_rgba.paste(logo_image)
        else:
            logo_rgba.paste(logo_image.convert('RGB'))
        logo_image = logo_rgba
    
    # Scale logo to cover the entire image (scale to fill while maintaining aspect ratio)
    # Use the larger dimension to ensure it covers the entire image
    scale_factor = max(width / logo_image.width, height / logo_image.height)
    logo_width = int(logo_image.width * scale_factor)
    logo_height = int(logo_image.height * scale_factor)
    logo_resized = logo_image.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
    
    # Make logo translucent but visible (18% opacity for more presence)
    alpha = logo_resized.split()[3]
    alpha_reduced = alpha.point(lambda p: int(p * 0.18))
    logo_translucent = logo_resized.copy()
    logo_translucent.putalpha(alpha_reduced)
    
    # Center the logo on the background
    logo_x = (width - logo_width) // 2
    logo_y = (height - logo_height) // 2
    
    # Paste the logo directly onto the image (this becomes the background)
    img.paste(logo_translucent, (logo_x, logo_y), logo_translucent)


def draw_text_with_shadow(draw, xy, text, font, fill='#ffffff', shadow_color='#000000', shadow_offset=(4, 4), anchor=None):
    """Helper to draw text with a drop shadow"""
    x, y = xy
    # Draw shadow
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color, anchor=anchor)
    # Draw text
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)



def apply_logo_to_rectangle(img, logo_image, rect_coords, opacity=0.18):
    """
    Apply a translucent version of the logo to a specific rectangle area.
    
    Args:
        img: The main image to paste onto
        logo_image: The logo image (RGBA)
        rect_coords: Tuple of (left, top, right, bottom) defining the rectangle
        opacity: Opacity level (0.0 to 1.0, default 0.18 = 18%)
    """
    if logo_image is None:
        return
    
    left, top, right, bottom = rect_coords
    rect_width = right - left
    rect_height = bottom - top
    
    # Convert to RGBA if needed
    if logo_image.mode != 'RGBA':
        logo_rgba = Image.new('RGBA', logo_image.size, (255, 255, 255, 255))
        if logo_image.mode == 'RGB':
            logo_rgba.paste(logo_image)
        else:
            logo_rgba.paste(logo_image.convert('RGB'))
        logo_image = logo_rgba
    
    # Create overlay for this rectangle
    overlay = Image.new('RGBA', (rect_width, rect_height), (0, 0, 0, 0))
    
    # Scale logo to fill most of the rectangle (make it large and visible)
    # Use a size that's about 80% of the smaller dimension
    logo_size = int(min(rect_width, rect_height) * 0.8)
    logo_resized = logo_image.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # Make logo translucent
    alpha = logo_resized.split()[3]
    alpha_reduced = alpha.point(lambda p: int(p * opacity))
    logo_translucent = logo_resized.copy()
    logo_translucent.putalpha(alpha_reduced)
    
    # Center the logo in the rectangle (single large logo instead of tiling)
    logo_x = (rect_width - logo_size) // 2
    logo_y = (rect_height - logo_size) // 2
    overlay.paste(logo_translucent, (logo_x, logo_y), logo_translucent)
    
    # Also add a smaller tiled version for pattern effect
    small_logo_size = logo_size // 2
    small_logo_resized = logo_image.resize((small_logo_size, small_logo_size), Image.Resampling.LANCZOS)
    small_alpha = small_logo_resized.split()[3]
    small_alpha_reduced = small_alpha.point(lambda p: int(p * opacity * 0.5))  # Even more transparent
    small_logo_translucent = small_logo_resized.copy()
    small_logo_translucent.putalpha(small_alpha_reduced)
    
    # Tile small logos in corners/edges for subtle pattern
    for x in range(0, rect_width, small_logo_size * 2):
        for y in range(0, rect_height, small_logo_size * 2):
            overlay.paste(small_logo_translucent, (x, y), small_logo_translucent)
    
    # Composite onto the specific rectangle area
    img.paste(overlay, (left, top), overlay)


def generate_game_image(game_result, filename, game_type="game", week=None, game_number=None):
    """Generate a game scoreboard image with team logos and scores - modern sports broadcast style"""
    try:
        # Create square image (Instagram-friendly 1:1 aspect ratio)
        width, height = 1600, 1600
        
        # Get team scores early to determine winner for background theme
        team1 = game_result['team1']
        team2 = game_result['team2']
        team1_score = game_result['team1_score']
        team2_score = game_result['team2_score']
        
        # Load logos first to determine winner and set background
        logo1_original = None
        logo1_path = os.path.join(config.LOGOS_DIRECTORY, team1.get_logo_filename())
        for logo_file in [logo1_path, logo1_path.replace("'", "'"), logo1_path.replace("'", "'")]:
            try:
                if os.path.exists(logo_file):
                    logo1_original = Image.open(logo_file).convert('RGBA')
                    break
            except:
                continue
        
        logo2_original = None
        logo2_path = os.path.join(config.LOGOS_DIRECTORY, team2.get_logo_filename())
        for logo_file in [logo2_path, logo2_path.replace("'", "'"), logo2_path.replace("'", "'")]:
            try:
                if os.path.exists(logo_file):
                    logo2_original = Image.open(logo_file).convert('RGBA')
                    break
            except:
                continue
        
        # Determine winner and loser
        if team1_score > team2_score:
            winning_team_logo = logo1_original
            losing_team_logo = logo2_original
            winner = team1
            loser = team2
        elif team2_score > team1_score:
            winning_team_logo = logo2_original
            losing_team_logo = logo1_original
            winner = team2
            loser = team1
        else:
            # Tie - use team1 as winner by default
            winning_team_logo = logo1_original
            losing_team_logo = logo2_original
            winner = team1
            loser = team2
        
        # Start with a very dark base (extract from logo if available, otherwise use dark color)
        if winning_team_logo:
            # Extract a dark version of the dominant color for base
            dominant_color = extract_dominant_color(winning_team_logo)
            # Darken it significantly for base
            base_r = max(5, dominant_color[0] // 8)
            base_g = max(5, dominant_color[1] // 8)
            base_b = max(5, dominant_color[2] // 8)
            base_color = (base_r, base_g, base_b)
        else:
            base_color = (5, 5, 16)  # Very dark blue
        
        # Create image with dark base
        img = Image.new('RGB', (width, height), color=base_color)
        draw = ImageDraw.Draw(img)
        
        # Apply winner's logo as the primary background (before any overlays)
        apply_translucent_logo_background(img, winning_team_logo, width, height)
        
        # Add a very subtle dark overlay for overall depth (only if logo exists)
        if winning_team_logo:
            dark_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 40))  # Very subtle darkening
            img.paste(dark_overlay, (0, 0), dark_overlay)
        
        # Load fonts with cross-platform fallbacks
        title_font = load_font(FONT_PATHS_BOLD, 64)
        score_font = load_font(FONT_PATHS_BOLD, 220)
        team_font = load_font(FONT_PATHS_BOLD, 56)
        stat_label_font = load_font(FONT_PATHS_REGULAR, 36)
        stat_value_font = load_font(FONT_PATHS_BOLD, 48)
        vs_font = load_font(FONT_PATHS_BOLD, 48)
        legend_font = load_font(FONT_PATHS_REGULAR, 24)
        
        team1_detail = game_result['team1_detail']
        team2_detail = game_result['team2_detail']
        
        # Logo size for display in cards
        logo_size = 300
        
        # Draw "Glass Cards" for teams
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Card dimensions
        card_width = 650
        card_height = 1000
        card_y = 350
        card1_x = 100
        card2_x = width - 100 - card_width
        
        # Glass effect style
        glass_fill = (20, 30, 50, 180)  # Dark blue-ish semi-transparent
        glass_border = (78, 205, 196, 100)  # Teal border
        
        # Draw cards
        overlay_draw.rounded_rectangle([card1_x, card_y, card1_x + card_width, card_y + card_height], 
                                      radius=20, fill=glass_fill, outline=glass_border, width=2)
        overlay_draw.rounded_rectangle([card2_x, card_y, card2_x + card_width, card_y + card_height], 
                                      radius=20, fill=glass_fill, outline=glass_border, width=2)
        
        # Title Background
        overlay_draw.rectangle([0, 0, width, 180], fill=(0, 0, 0, 200))
        
        img.paste(overlay, (0, 0), overlay)
        
        # Recreate draw object
        draw = ImageDraw.Draw(img)
        
        # Draw title
        title = f"{game_type.replace('_', ' ').title()}"
        if week:
            title = f"Week {week} - {title}"
        elif game_number:
            title = f"{title} {game_number}"
            
        draw_text_with_shadow(draw, (width//2, 90), title, title_font, anchor="mm")
        
        # --- Team 1 Content ---
        # Logo
        if logo1_original:
            logo1 = logo1_original.resize((200, 200), Image.Resampling.LANCZOS)
            logo_x = card1_x + (card_width - 200) // 2
            logo_y = card_y + 40
            img.paste(logo1, (logo_x, logo_y), logo1)
        
        # Name
        team1_name_y = card_y + 260
        draw_text_with_shadow(draw, (card1_x + card_width//2, team1_name_y), team1.name, team_font, anchor="mm")
        
        # Score
        score_y = team1_name_y + 140
        draw_text_with_shadow(draw, (card1_x + card_width//2, score_y), str(team1_score), score_font, anchor="mm")
        
        # Stats
        stats_start_y = score_y + 160
        stat_spacing = 80
        
        # Helper for stats
        def draw_stat_row(x, y, label, value, cascade_count, width):
            label_text = label
            value_text = str(value)
            
            # Use fixed offsets from center
            center = x + width // 2
            draw_text_with_shadow(draw, (center - 20, y), label_text, stat_label_font, fill='#aaaaaa', anchor="rm")
            draw_text_with_shadow(draw, (center + 20, y), value_text, stat_value_font, anchor="lm")
            
            # Cascade circles
            if cascade_count > 0:
                circle_radius = 8
                circle_spacing = 8
                # Position to right of value
                value_bbox = draw.textbbox((0, 0), value_text, font=stat_value_font)
                value_width = value_bbox[2] - value_bbox[0]
                circle_start_x = center + 20 + value_width + 25
                
                for i in range(cascade_count):
                    circle_x = circle_start_x + i * (circle_radius * 2 + circle_spacing)
                    draw.ellipse([circle_x - circle_radius, y - circle_radius, 
                                 circle_x + circle_radius, y + circle_radius], 
                                fill='#ffd93d', outline='#ffffff', width=1)

        draw_stat_row(card1_x, stats_start_y, "RUNS", team1_detail.runs, team1_detail.cascade_runs, card_width)
        draw_stat_row(card1_x, stats_start_y + stat_spacing, "THROWS", team1_detail.throws, team1_detail.cascade_throws, card_width)
        draw_stat_row(card1_x, stats_start_y + stat_spacing * 2, "KICKS", team1_detail.kicks, team1_detail.cascade_kicks, card_width)

        # --- Team 2 Content ---
        # Logo
        if logo2_original:
            logo2 = logo2_original.resize((200, 200), Image.Resampling.LANCZOS)
            logo_x = card2_x + (card_width - 200) // 2
            logo_y = card_y + 40
            img.paste(logo2, (logo_x, logo_y), logo2)
        
        # Name
        team2_name_y = card_y + 260
        draw_text_with_shadow(draw, (card2_x + card_width//2, team2_name_y), team2.name, team_font, anchor="mm")
        
        # Score
        score_y = team2_name_y + 140
        draw_text_with_shadow(draw, (card2_x + card_width//2, score_y), str(team2_score), score_font, anchor="mm")
        
        # Stats
        draw_stat_row(card2_x, stats_start_y, "RUNS", team2_detail.runs, team2_detail.cascade_runs, card_width)
        draw_stat_row(card2_x, stats_start_y + stat_spacing, "THROWS", team2_detail.throws, team2_detail.cascade_throws, card_width)
        draw_stat_row(card2_x, stats_start_y + stat_spacing * 2, "KICKS", team2_detail.kicks, team2_detail.cascade_kicks, card_width)

        # VS Text in center
        draw_text_with_shadow(draw, (width//2, card_y + card_height//2), "VS", vs_font, fill='#888888', anchor="mm")

        # Loser Logo (Small, Bottom Right)
        if losing_team_logo:
            loser_logo_size = 120
            loser_logo = losing_team_logo.resize((loser_logo_size, loser_logo_size), Image.Resampling.LANCZOS)
            loser_x = width - loser_logo_size - 30
            loser_y = height - loser_logo_size - 30
            # Add a small label
            draw_text_with_shadow(draw, (loser_x + loser_logo_size//2, loser_y - 20), "Matchup", legend_font, anchor="ms")
            img.paste(loser_logo, (loser_x, loser_y), loser_logo)

        # Legend
        legend_y = height - 40
        legend_text = "= Cascade Zone"
        # Draw circle
        circle_radius = 8
        legend_text_bbox = draw.textbbox((0, 0), legend_text, font=legend_font)
        total_width = legend_text_bbox[2] - legend_text_bbox[0] + 25
        start_x = (width - total_width) // 2
        
        draw.ellipse([start_x, legend_y - circle_radius, start_x + circle_radius*2, legend_y + circle_radius], fill='#ffd93d', outline='white')
        draw_text_with_shadow(draw, (start_x + 25, legend_y), legend_text, legend_font, anchor="lm")

        # Save image
        img.save(filename)
        return True
    except Exception as e:
        print(f"Error generating image {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_tournament_bracket(teams, filename, round_stage='quarterfinals', quarterfinal_winners=None, semifinal_winners=None):
    """Generate a tournament bracket image showing teams in bracket format with logos
    round_stage: 'quarterfinals', 'semifinals', or 'finals'
    quarterfinal_winners: List of 4 teams (winners of quarterfinals) - needed for semifinals/finals
    semifinal_winners: List of 2 teams (winners of semifinals) - needed for finals
    """
    try:
        # Sort teams by wins, then by point difference (same as tournament seeding)
        sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for - t.points_against), reverse=True)
        
        # Create square image (1:1 aspect ratio) for Instagram
        width, height = 1600, 1600
        img = Image.new('RGB', (width, height), color='#0a0a1a')
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        draw_gradient_background(img, width, height, '#0a0a1a', '#1a1a2e', 'vertical')
        
        # Load fonts with cross-platform fallbacks
        title_font = load_font(FONT_PATHS_REGULAR, 64)
        round_font = load_font(FONT_PATHS_REGULAR, 40)
        team_font = load_font(FONT_PATHS_REGULAR, 28)
        seed_font = load_font(FONT_PATHS_REGULAR, 20)
        
        # Draw title
        title = "TOURNAMENT BRACKET"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = 30
        
        # Title with shadow
        for offset in [5, 4, 3, 2]:
            draw.text((title_x + offset, title_y + offset), title, fill='#000000', font=title_font)
        draw.text((title_x, title_y), title, fill='#4ecdc4', font=title_font)
        
        # Constants for bracket layout (adjusted for square format)
        bracket_y_start = 120
        match_height = 140
        match_spacing = 160
        logo_size = 60
        
        if round_stage == 'quarterfinals':
            # Show all 8 teams in quarterfinals
            qf_start_x = 100
            sf_start_x = 600
            final_start_x = 1100
            box_width = 450
            
            # Quarterfinals section
            round_label = "Quarterfinals"
            draw.text((qf_start_x, bracket_y_start - 50), round_label, fill='#ffffff', font=round_font)
            
            qf_matchups = [
                (sorted_teams[0], sorted_teams[7]),  # 1 vs 8
                (sorted_teams[1], sorted_teams[6]),  # 2 vs 7
                (sorted_teams[2], sorted_teams[5]),  # 3 vs 6
                (sorted_teams[3], sorted_teams[4])   # 4 vs 5
            ]
            
            # Draw quarterfinal matchups
            for i, (team1, team2) in enumerate(qf_matchups):
                y_pos = bracket_y_start + i * match_spacing
                
                # Draw matchup box
                box_height = match_height
                box_x = qf_start_x
                box_y = y_pos
                
                # Background box for matchup
                draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], 
                              fill='#1a1a2e', outline='#4ecdc4', width=3)
                
                # Draw team 1 (top)
                team1_y = box_y + 8
                team1_seed = sorted_teams.index(team1) + 1
                
                # Load and draw team1 logo
                logo1 = None
                logo1_path = os.path.join(config.LOGOS_DIRECTORY, team1.get_logo_filename())
                for logo_file in [logo1_path, logo1_path.replace("'", "'"), logo1_path.replace("'", "'")]:
                    try:
                        if os.path.exists(logo_file):
                            logo1 = Image.open(logo_file).convert('RGBA')
                            logo1 = logo1.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                            break
                    except:
                        continue
                
                if logo1:
                    img.paste(logo1, (box_x + 8, team1_y), logo1)
                
                # Draw team 1 name and seed
                seed_text = f"#{team1_seed}"
                draw.text((box_x + 80, team1_y + 3), seed_text, fill='#888888', font=seed_font)
                team1_text = team1.name
                # Truncate long team names
                if len(team1_text) > 20:
                    team1_text = team1_text[:17] + "..."
                draw.text((box_x + 80, team1_y + 20), team1_text, fill='#ffffff', font=team_font)
                
                # Draw team 2 (bottom)
                team2_y = box_y + 70
                team2_seed = sorted_teams.index(team2) + 1
                
                # Load and draw team2 logo
                logo2 = None
                logo2_path = os.path.join(config.LOGOS_DIRECTORY, team2.get_logo_filename())
                for logo_file in [logo2_path, logo2_path.replace("'", "'"), logo2_path.replace("'", "'")]:
                    try:
                        if os.path.exists(logo_file):
                            logo2 = Image.open(logo_file).convert('RGBA')
                            logo2 = logo2.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                            break
                    except:
                        continue
                
                if logo2:
                    img.paste(logo2, (box_x + 8, team2_y), logo2)
                
                # Draw team 2 name and seed
                seed_text = f"#{team2_seed}"
                draw.text((box_x + 80, team2_y + 3), seed_text, fill='#888888', font=seed_font)
                team2_text = team2.name
                # Truncate long team names
                if len(team2_text) > 20:
                    team2_text = team2_text[:17] + "..."
                draw.text((box_x + 80, team2_y + 20), team2_text, fill='#ffffff', font=team_font)
                
                # Draw line connecting to semifinal (light gray, dashed appearance)
                line_start_x = box_x + box_width
                line_start_y = box_y + box_height // 2
                line_end_x = sf_start_x
                
                # Connect QF1 and QF2 to SF1, QF3 and QF4 to SF2
                if i == 0:  # QF1 -> top of SF1
                    line_end_y = bracket_y_start + 25
                elif i == 1:  # QF2 -> bottom of SF1
                    line_end_y = bracket_y_start + match_height - 25
                elif i == 2:  # QF3 -> top of SF2
                    line_end_y = bracket_y_start + match_spacing * 2 + 25
                else:  # QF4 -> bottom of SF2
                    line_end_y = bracket_y_start + match_spacing * 2 + match_height - 25
                
                # Draw connecting line
                draw.line([(line_start_x, line_start_y), (line_start_x + 40, line_start_y)], 
                         fill='#4ecdc4', width=2)
                draw.line([(line_start_x + 40, line_start_y), (line_start_x + 40, line_end_y)], 
                         fill='#4ecdc4', width=2)
                draw.line([(line_start_x + 40, line_end_y), (line_end_x, line_end_y)], 
                         fill='#4ecdc4', width=2)
            
            # Semifinals section (placeholders)
            round_label = "Semifinals"
            draw.text((sf_start_x, bracket_y_start - 50), round_label, fill='#666666', font=round_font)
            
            for i in range(2):
                y_pos = bracket_y_start + i * match_spacing * 2
                box_height = match_height
                box_x = sf_start_x
                box_y = y_pos
                draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], 
                              fill='#1a1a2e', outline='#666666', width=2)
                placeholder_text = "Winner"
                draw.text((box_x + 20, box_y + 50), placeholder_text, fill='#666666', font=team_font)
                
                # Draw line to final
                line_start_x = box_x + box_width
                line_start_y = box_y + box_height // 2
                line_end_x = final_start_x
                final_center_y = bracket_y_start + match_spacing + match_height // 2
                
                if i == 0:
                    line_end_y = final_center_y - 30
                else:
                    line_end_y = final_center_y + 30
                
                draw.line([(line_start_x, line_start_y), (line_start_x + 40, line_start_y)], 
                         fill='#666666', width=2)
                draw.line([(line_start_x + 40, line_start_y), (line_start_x + 40, line_end_y)], 
                         fill='#666666', width=2)
                draw.line([(line_start_x + 40, line_end_y), (line_end_x, line_end_y)], 
                         fill='#666666', width=2)
            
            # Final section (placeholder)
            round_label = "Final"
            draw.text((final_start_x, bracket_y_start - 50), round_label, fill='#666666', font=round_font)
            y_pos = bracket_y_start + match_spacing
            box_height = match_height + 20
            box_width = 400
            box_x = final_start_x
            box_y = y_pos
            draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], 
                          fill='#1a1a2e', outline='#666666', width=2)
            placeholder_text = "Winner"
            draw.text((box_x + 20, box_y + 60), placeholder_text, fill='#666666', font=team_font)
            
        elif round_stage == 'semifinals' and quarterfinal_winners:
            # Show semifinal matchups with QF winners
            sf_start_x = 300
            final_start_x = 900
            box_width = 500
            
            # Semifinals section
            round_label = "Semifinals"
            draw.text((sf_start_x, bracket_y_start - 50), round_label, fill='#ffffff', font=round_font)
            
            sf_matchups = [
                (quarterfinal_winners[0], quarterfinal_winners[1]),
                (quarterfinal_winners[2], quarterfinal_winners[3])
            ]
            
            # Draw semifinal matchups
            for i, (team1, team2) in enumerate(sf_matchups):
                y_pos = bracket_y_start + i * match_spacing * 2
                
                box_height = match_height
                box_x = sf_start_x
                box_y = y_pos
                
                draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], 
                              fill='#1a1a2e', outline='#4ecdc4', width=3)
                
                # Team 1
                team1_y = box_y + 8
                logo1 = None
                logo1_path = os.path.join(config.LOGOS_DIRECTORY, team1.get_logo_filename())
                for logo_file in [logo1_path, logo1_path.replace("'", "'"), logo1_path.replace("'", "'")]:
                    try:
                        if os.path.exists(logo_file):
                            logo1 = Image.open(logo_file).convert('RGBA')
                            logo1 = logo1.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                            break
                    except:
                        continue
                
                if logo1:
                    img.paste(logo1, (box_x + 8, team1_y), logo1)
                
                team1_text = team1.name
                if len(team1_text) > 22:
                    team1_text = team1_text[:19] + "..."
                draw.text((box_x + 80, team1_y + 20), team1_text, fill='#ffffff', font=team_font)
                
                # Team 2
                team2_y = box_y + 70
                logo2 = None
                logo2_path = os.path.join(config.LOGOS_DIRECTORY, team2.get_logo_filename())
                for logo_file in [logo2_path, logo2_path.replace("'", "'"), logo2_path.replace("'", "'")]:
                    try:
                        if os.path.exists(logo_file):
                            logo2 = Image.open(logo_file).convert('RGBA')
                            logo2 = logo2.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                            break
                    except:
                        continue
                
                if logo2:
                    img.paste(logo2, (box_x + 8, team2_y), logo2)
                
                team2_text = team2.name
                if len(team2_text) > 22:
                    team2_text = team2_text[:19] + "..."
                draw.text((box_x + 80, team2_y + 20), team2_text, fill='#ffffff', font=team_font)
                
                # Draw line connecting to final
                line_start_x = box_x + box_width
                line_start_y = box_y + box_height // 2
                line_end_x = final_start_x
                final_center_y = bracket_y_start + match_spacing + match_height // 2
                
                if i == 0:
                    line_end_y = final_center_y - 30
                else:
                    line_end_y = final_center_y + 30
                
                draw.line([(line_start_x, line_start_y), (line_start_x + 40, line_start_y)], 
                         fill='#4ecdc4', width=2)
                draw.line([(line_start_x + 40, line_start_y), (line_start_x + 40, line_end_y)], 
                         fill='#4ecdc4', width=2)
                draw.line([(line_start_x + 40, line_end_y), (line_end_x, line_end_y)], 
                         fill='#4ecdc4', width=2)
            
            # Final section (placeholder)
            round_label = "Final"
            draw.text((final_start_x, bracket_y_start - 50), round_label, fill='#666666', font=round_font)
            y_pos = bracket_y_start + match_spacing
            box_height = match_height + 20
            box_width = 450
            box_x = final_start_x
            box_y = y_pos
            draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], 
                          fill='#1a1a2e', outline='#666666', width=2)
            placeholder_text = "Winner"
            draw.text((box_x + 20, box_y + 60), placeholder_text, fill='#666666', font=team_font)
            
        elif round_stage == 'finals' and semifinal_winners:
            # Show final matchup with SF winners
            final_start_x = 400
            box_width = 700
            
            # Final section
            round_label = "Final"
            draw.text((final_start_x, bracket_y_start - 50), round_label, fill='#ffffff', font=round_font)
            
            y_pos = bracket_y_start + match_spacing
            box_height = match_height + 40
            box_x = final_start_x
            box_y = y_pos
            
            draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], 
                          fill='#1a1a2e', outline='#ffd700', width=4)
            
            # Team 1
            team1 = semifinal_winners[0]
            team1_y = box_y + 15
            logo1 = None
            logo1_path = os.path.join(config.LOGOS_DIRECTORY, team1.get_logo_filename())
            for logo_file in [logo1_path, logo1_path.replace("'", "'"), logo1_path.replace("'", "'")]:
                try:
                    if os.path.exists(logo_file):
                        logo1 = Image.open(logo_file).convert('RGBA')
                        logo1 = logo1.resize((logo_size + 20, logo_size + 20), Image.Resampling.LANCZOS)
                        break
                except:
                    continue
            
            if logo1:
                img.paste(logo1, (box_x + 15, team1_y), logo1)
            
            team1_text = team1.name
            if len(team1_text) > 25:
                team1_text = team1_text[:22] + "..."
            draw.text((box_x + 100, team1_y + 25), team1_text, fill='#ffffff', font=team_font)
            
            # Team 2
            team2 = semifinal_winners[1]
            team2_y = box_y + 95
            logo2 = None
            logo2_path = os.path.join(config.LOGOS_DIRECTORY, team2.get_logo_filename())
            for logo_file in [logo2_path, logo2_path.replace("'", "'"), logo2_path.replace("'", "'")]:
                try:
                    if os.path.exists(logo_file):
                        logo2 = Image.open(logo_file).convert('RGBA')
                        logo2 = logo2.resize((logo_size + 20, logo_size + 20), Image.Resampling.LANCZOS)
                        break
                except:
                    continue
            
            if logo2:
                img.paste(logo2, (box_x + 15, team2_y), logo2)
            
            team2_text = team2.name
            if len(team2_text) > 25:
                team2_text = team2_text[:22] + "..."
            draw.text((box_x + 100, team2_y + 25), team2_text, fill='#ffffff', font=team_font)
        
        # Add decorative border
        border_width = 8
        border_color = '#4ecdc4'
        for i in range(3):
            draw.rectangle([i, i, width-1-i, height-1-i], outline=border_color, width=1)
        draw.rectangle([3, 3, width-4, height-4], outline=border_color, width=border_width)
        
        # Save image
        img.save(filename)
        print(f"Generated tournament bracket ({round_stage}): {filename}")
        return True
    except Exception as e:
        print(f"Error generating tournament bracket {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False

