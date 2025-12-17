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


def _get_player_display_name(player_stats):
    """Extract display name from player stats dict"""
    return player_stats.get('player_name') or player_stats.get('name') or 'Unknown'


def _render_player_stats_table(draw, x, y, width, player_stats_dict, team_name, max_players=7, 
                               name_font=None, stat_font=None, header_font=None, season_stats_dict=None):
    """
    Render a player stats table in ESPN style.
    
    Args:
        draw: ImageDraw object
        x, y: Top-left position
        width: Table width
        player_stats_dict: Dict of player_id -> stats
        team_name: Team name for header
        max_players: Maximum number of players to show
        name_font, stat_font, header_font: Font objects
        season_stats_dict: Optional dict of player_name -> season stats
    """
    if not player_stats_dict:
        return y
    
    # Sort players by points (descending)
    sorted_players = sorted(
        player_stats_dict.items(),
        key=lambda item: item[1].get('points', 0),
        reverse=True
    )[:max_players]
    
    if not sorted_players:
        return y
    
    # Table dimensions
    row_height = 40
    header_height = 35
    padding = 15
    
    # Header background
    header_bg = Image.new('RGBA', (width, header_height), (0, 0, 0, 180))
    draw._image.paste(header_bg, (x, y), header_bg)
    
    # Header text
    if header_font:
        draw_text_with_shadow(draw, (x + width//2, y + header_height//2), team_name, header_font, 
                             fill='#ffffff', anchor="mm", shadow_offset=(2, 2))
    
    # Column positions
    name_x = x + padding
    points_x = x + width - 280
    runs_x = x + width - 220
    throws_x = x + width - 150
    kicks_x = x + width - 80
    
    # Column headers
    header_y = y + header_height + 5
    if header_font:
        header_size = int(header_font.size * 0.7) if hasattr(header_font, 'size') else 14
        small_header_font = load_font(FONT_PATHS_REGULAR, header_size)
        draw_text_with_shadow(draw, (points_x, header_y), "PTS", small_header_font, fill='#aaaaaa', anchor="lm")
        draw_text_with_shadow(draw, (runs_x, header_y), "R", small_header_font, fill='#aaaaaa', anchor="lm")
        draw_text_with_shadow(draw, (throws_x, header_y), "T", small_header_font, fill='#aaaaaa', anchor="lm")
        draw_text_with_shadow(draw, (kicks_x, header_y), "K", small_header_font, fill='#aaaaaa', anchor="lm")
    
    # Player rows
    current_y = header_y + 25
    for idx, (player_id, stats) in enumerate(sorted_players):
        player_name = _get_player_display_name(stats)
        
        # Highlight top performer
        is_top = (idx == 0)
        if is_top:
            row_bg = Image.new('RGBA', (width, row_height), (26, 46, 58, 200))
        else:
            row_bg = Image.new('RGBA', (width, row_height), (15, 20, 25, 180))
        draw._image.paste(row_bg, (x, current_y - 5), row_bg)
        
        # Player name (truncate if too long)
        display_name = player_name[:18] + "..." if len(player_name) > 18 else player_name
        name_color = '#4ecdc4' if is_top else '#ffffff'
        if name_font:
            draw_text_with_shadow(draw, (name_x, current_y + row_height//2), display_name, name_font, 
                                 fill=name_color, anchor="lm", shadow_offset=(1, 1))
        
        # Points (highlighted)
        points = stats.get('points', 0)
        points_color = '#10b981' if points > 0 else '#888888'
        if stat_font:
            draw_text_with_shadow(draw, (points_x, current_y + row_height//2), str(points), stat_font, 
                                 fill=points_color, anchor="lm", shadow_offset=(1, 1))
        
        # Runs (completed/attempted)
        runs_comp = stats.get('runs_completed', 0)
        runs_att = stats.get('runs_attempted', 0)
        runs_text = f"{runs_comp}/{runs_att}"
        runs_color = '#4ecdc4' if runs_comp > 0 else '#666666'
        if stat_font:
            draw_text_with_shadow(draw, (runs_x, current_y + row_height//2), runs_text, stat_font, 
                                 fill=runs_color, anchor="lm", shadow_offset=(1, 1))
        
        # Throws (completed/attempted)
        throws_comp = stats.get('throws_completed', 0)
        throws_att = stats.get('throws_attempted', 0)
        throws_text = f"{throws_comp}/{throws_att}"
        throws_color = '#4ecdc4' if throws_comp > 0 else '#666666'
        if stat_font:
            draw_text_with_shadow(draw, (throws_x, current_y + row_height//2), throws_text, stat_font, 
                                 fill=throws_color, anchor="lm", shadow_offset=(1, 1))
        
        # Kicks (completed/attempted)
        kicks_comp = stats.get('kicks_completed', 0)
        kicks_att = stats.get('kicks_attempted', 0)
        kicks_text = f"{kicks_comp}/{kicks_att}"
        kicks_color = '#4ecdc4' if kicks_comp > 0 else '#666666'
        if stat_font:
            draw_text_with_shadow(draw, (kicks_x, current_y + row_height//2), kicks_text, stat_font, 
                                 fill=kicks_color, anchor="lm", shadow_offset=(1, 1))
        
        current_y += row_height
    
    return current_y + 10



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


def generate_game_image(game_result, filename, game_type="game", week=None, game_number=None, season_id=None):
    """Generate a game scoreboard image with team logos and scores - modern 2025 Instagram ESPN style"""
    try:
        # Fetch team analytics if season_id is provided
        team_analytics = None
        if season_id:
            try:
                import webapp_bridge
                team1_name = game_result['team1'].name
                team2_name = game_result['team2'].name
                team_analytics = webapp_bridge.get_team_analytics(team1_name, team2_name, season_id)
            except Exception as e:
                # If analytics fetch fails, continue without them
                print(f"Warning: Could not fetch team analytics: {e}")
        
        # Create modern scoreboard image (1:1 for Instagram feed, but taller to fit player stats)
        width, height = 1600, 2000
        
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
        
        # Modern 2025 Instagram ESPN Style Design
        # Create dark gradient background
        img = Image.new('RGB', (width, height), color='#0a0a1a')
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        draw_gradient_background(img, width, height, '#0a0a1a', '#1a1a2e', 'vertical')
        
        # Apply subtle winner logo background
        if winning_team_logo:
            apply_translucent_logo_background(img, winning_team_logo, width, height)
            dark_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 60))
            img.paste(dark_overlay, (0, 0), dark_overlay)
        
        # Load modern fonts
        title_font = load_font(FONT_PATHS_BOLD, 48)
        score_font = load_font(FONT_PATHS_BOLD, 220)
        team_font = load_font(FONT_PATHS_BOLD, 64)
        analytics_label_font = load_font(FONT_PATHS_REGULAR, 24)
        analytics_value_font = load_font(FONT_PATHS_BOLD, 32)
        stat_label_font = load_font(FONT_PATHS_REGULAR, 28)
        stat_value_font = load_font(FONT_PATHS_BOLD, 36)
        
        team1_detail = game_result['team1_detail']
        team2_detail = game_result['team2_detail']
        
        # Get analytics data
        team1_stats = team_analytics['team1_stats'] if team_analytics else None
        team2_stats = team_analytics['team2_stats'] if team_analytics else None
        
        # Header section
        header_height = 120
        header_overlay = Image.new('RGBA', (width, header_height), (0, 0, 0, 220))
        img.paste(header_overlay, (0, 0), header_overlay)
        
        # Title
        title = f"{game_type.replace('_', ' ').title()}"
        if week:
            title = f"Week {week}"
        elif game_number:
            title = f"{title} {game_number}"
        draw_text_with_shadow(draw, (width//2, 60), title, title_font, fill='#ffffff', anchor="mm")
        
        # Main scoreboard section - horizontal layout
        scoreboard_y = header_height + 40
        scoreboard_height = 900
        logo_size = 280
        
        # Team 1 section (left)
        team1_x = 80
        team1_width = 680
        
        # Team 2 section (right)
        team2_x = 840
        team2_width = 680
        
        # Create glassmorphism cards
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Glass card for team 1 - ESPN blue accent
        glass_fill = (20, 30, 50, 200)
        glass_border = (0, 51, 160, 180)  # ESPN blue
        overlay_draw.rounded_rectangle(
            [team1_x, scoreboard_y, team1_x + team1_width, scoreboard_y + scoreboard_height],
            radius=25, fill=glass_fill, outline=glass_border, width=3
        )
        
        # Glass card for team 2 - ESPN orange accent
        overlay_draw.rounded_rectangle(
            [team2_x, scoreboard_y, team2_x + team2_width, scoreboard_y + scoreboard_height],
            radius=25, fill=glass_fill, outline=(255, 102, 0, 180), width=3  # ESPN orange
        )
        
        img.paste(overlay, (0, 0), overlay)
        draw = ImageDraw.Draw(img)
        
        # --- Team 1 Rendering ---
        team1_logo_y = scoreboard_y + 50
        if logo1_original:
            logo1 = logo1_original.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo1_x = team1_x + (team1_width - logo_size) // 2
            img.paste(logo1, (logo1_x, team1_logo_y), logo1)
        
        # Team name
        team1_name_y = team1_logo_y + logo_size + 30
        draw_text_with_shadow(draw, (team1_x + team1_width//2, team1_name_y), team1.name, team_font, fill='#ffffff', anchor="mm")
        
        # Score (large and bold)
        score1_y = team1_name_y + 100
        draw_text_with_shadow(draw, (team1_x + team1_width//2, score1_y), str(team1_score), score_font, fill='#ffffff', anchor="mm")
        
        # Analytics section
        analytics_y = score1_y + 180
        analytics_spacing = 50
        
        if team1_stats:
            # Record badge
            record_text = f"{team1_stats['wins']}-{team1_stats['losses']}"
            draw_text_with_shadow(draw, (team1_x + 30, analytics_y), "RECORD", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team1_x + team1_width - 30, analytics_y), record_text, analytics_value_font, fill='#10b981', anchor="rm")
            
            # Win %
            win_pct_y = analytics_y + analytics_spacing
            win_pct_text = f"{team1_stats['win_percentage']}%"
            draw_text_with_shadow(draw, (team1_x + 30, win_pct_y), "WIN %", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team1_x + team1_width - 30, win_pct_y), win_pct_text, analytics_value_font, fill='#ffffff', anchor="rm")
            
            # PPG
            ppg_y = win_pct_y + analytics_spacing
            ppg_text = f"{team1_stats['avg_points_for']:.1f}"
            draw_text_with_shadow(draw, (team1_x + 30, ppg_y), "PPG", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team1_x + team1_width - 30, ppg_y), ppg_text, analytics_value_font, fill='#4ecdc4', anchor="rm")
            
            # Point Differential
            diff_y = ppg_y + analytics_spacing
            diff = team1_stats['point_differential']
            diff_text = f"{'+' if diff >= 0 else ''}{diff}"
            diff_color = '#10b981' if diff >= 0 else '#ef4444'
            draw_text_with_shadow(draw, (team1_x + 30, diff_y), "DIFF", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team1_x + team1_width - 30, diff_y), diff_text, analytics_value_font, fill=diff_color, anchor="rm")
        else:
            # Fallback if no analytics
            draw_text_with_shadow(draw, (team1_x + team1_width//2, analytics_y), "Season Stats", analytics_label_font, fill='#666666', anchor="mm")
        
        # Game stats
        game_stats_y = analytics_y + (analytics_spacing * 4) + 40
        game_stat_spacing = 50
        
        # Runs
        draw_text_with_shadow(draw, (team1_x + 30, game_stats_y), "RUNS", stat_label_font, fill='#aaaaaa', anchor="lm")
        runs_text = str(team1_detail.runs)
        if team1_detail.cascade_runs > 0:
            runs_text += f" ({team1_detail.cascade_runs}*)"
        draw_text_with_shadow(draw, (team1_x + team1_width - 30, game_stats_y), runs_text, stat_value_font, fill='#4ecdc4', anchor="rm")
        
        # Throws
        throw_y = game_stats_y + game_stat_spacing
        draw_text_with_shadow(draw, (team1_x + 30, throw_y), "THROWS", stat_label_font, fill='#aaaaaa', anchor="lm")
        throws_text = str(team1_detail.throws)
        if team1_detail.cascade_throws > 0:
            throws_text += f" ({team1_detail.cascade_throws}*)"
        draw_text_with_shadow(draw, (team1_x + team1_width - 30, throw_y), throws_text, stat_value_font, fill='#4ecdc4', anchor="rm")
        
        # Kicks
        kick_y = throw_y + game_stat_spacing
        draw_text_with_shadow(draw, (team1_x + 30, kick_y), "KICKS", stat_label_font, fill='#aaaaaa', anchor="lm")
        kicks_text = str(team1_detail.kicks)
        if team1_detail.cascade_kicks > 0:
            kicks_text += f" ({team1_detail.cascade_kicks}*)"
        draw_text_with_shadow(draw, (team1_x + team1_width - 30, kick_y), kicks_text, stat_value_font, fill='#4ecdc4', anchor="rm")
        
        # --- Team 2 Rendering ---
        if logo2_original:
            logo2 = logo2_original.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo2_x = team2_x + (team2_width - logo_size) // 2
            img.paste(logo2, (logo2_x, team1_logo_y), logo2)
        
        # Team name
        draw_text_with_shadow(draw, (team2_x + team2_width//2, team1_name_y), team2.name, team_font, fill='#ffffff', anchor="mm")
        
        # Score
        draw_text_with_shadow(draw, (team2_x + team2_width//2, score1_y), str(team2_score), score_font, fill='#ffffff', anchor="mm")
        
        # Analytics section
        if team2_stats:
            # Record badge
            record_text = f"{team2_stats['wins']}-{team2_stats['losses']}"
            draw_text_with_shadow(draw, (team2_x + 30, analytics_y), "RECORD", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team2_x + team2_width - 30, analytics_y), record_text, analytics_value_font, fill='#10b981', anchor="rm")
            
            # Win %
            win_pct_text = f"{team2_stats['win_percentage']}%"
            draw_text_with_shadow(draw, (team2_x + 30, win_pct_y), "WIN %", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team2_x + team2_width - 30, win_pct_y), win_pct_text, analytics_value_font, fill='#ffffff', anchor="rm")
            
            # PPG
            ppg_text = f"{team2_stats['avg_points_for']:.1f}"
            draw_text_with_shadow(draw, (team2_x + 30, ppg_y), "PPG", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team2_x + team2_width - 30, ppg_y), ppg_text, analytics_value_font, fill='#4ecdc4', anchor="rm")
            
            # Point Differential
            diff = team2_stats['point_differential']
            diff_text = f"{'+' if diff >= 0 else ''}{diff}"
            diff_color = '#10b981' if diff >= 0 else '#ef4444'
            draw_text_with_shadow(draw, (team2_x + 30, diff_y), "DIFF", analytics_label_font, fill='#aaaaaa', anchor="lm")
            draw_text_with_shadow(draw, (team2_x + team2_width - 30, diff_y), diff_text, analytics_value_font, fill=diff_color, anchor="rm")
        else:
            draw_text_with_shadow(draw, (team2_x + team2_width//2, analytics_y), "Season Stats", analytics_label_font, fill='#666666', anchor="mm")
        
        # Game stats
        # Runs
        draw_text_with_shadow(draw, (team2_x + 30, game_stats_y), "RUNS", stat_label_font, fill='#aaaaaa', anchor="lm")
        runs_text = str(team2_detail.runs)
        if team2_detail.cascade_runs > 0:
            runs_text += f" ({team2_detail.cascade_runs}*)"
        draw_text_with_shadow(draw, (team2_x + team2_width - 30, game_stats_y), runs_text, stat_value_font, fill='#4ecdc4', anchor="rm")
        
        # Throws
        draw_text_with_shadow(draw, (team2_x + 30, throw_y), "THROWS", stat_label_font, fill='#aaaaaa', anchor="lm")
        throws_text = str(team2_detail.throws)
        if team2_detail.cascade_throws > 0:
            throws_text += f" ({team2_detail.cascade_throws}*)"
        draw_text_with_shadow(draw, (team2_x + team2_width - 30, throw_y), throws_text, stat_value_font, fill='#4ecdc4', anchor="rm")
        
        # Kicks
        draw_text_with_shadow(draw, (team2_x + 30, kick_y), "KICKS", stat_label_font, fill='#aaaaaa', anchor="lm")
        kicks_text = str(team2_detail.kicks)
        if team2_detail.cascade_kicks > 0:
            kicks_text += f" ({team2_detail.cascade_kicks}*)"
        draw_text_with_shadow(draw, (team2_x + team2_width - 30, kick_y), kicks_text, stat_value_font, fill='#4ecdc4', anchor="rm")
        
        # Player Stats Section
        player_stats_y = kick_y + game_stat_spacing + 60
        player_stats_height = 400
        
        # Fetch player season stats if available
        player_season_stats = {}
        if season_id:
            try:
                import webapp_bridge
                team1_player_stats = game_result.get('team1_player_stats', {})
                team2_player_stats = game_result.get('team2_player_stats', {})
                
                # Get season stats for all players
                for player_id, stats in team1_player_stats.items():
                    player_name = _get_player_display_name(stats)
                    season_stats = webapp_bridge.get_player_season_stats(player_name, team1.name, season_id)
                    if season_stats:
                        player_season_stats[player_name] = season_stats
                
                for player_id, stats in team2_player_stats.items():
                    player_name = _get_player_display_name(stats)
                    season_stats = webapp_bridge.get_player_season_stats(player_name, team2.name, season_id)
                    if season_stats:
                        player_season_stats[player_name] = season_stats
            except Exception as e:
                print(f"Warning: Could not fetch player season stats: {e}")
        
        # Player stats fonts
        player_name_font = load_font(FONT_PATHS_BOLD, 22)
        player_stat_font = load_font(FONT_PATHS_REGULAR, 20)
        player_header_font = load_font(FONT_PATHS_BOLD, 24)
        
        # Team 1 player stats table
        team1_table_width = team1_width - 60
        team1_table_x = team1_x + 30
        team1_table_y = _render_player_stats_table(
            draw, team1_table_x, player_stats_y, team1_table_width,
            game_result.get('team1_player_stats', {}), team1.name, max_players=7,
            name_font=player_name_font, stat_font=player_stat_font, header_font=player_header_font,
            season_stats_dict=player_season_stats
        )
        
        # Team 2 player stats table
        team2_table_width = team2_width - 60
        team2_table_x = team2_x + 30
        team2_table_y = _render_player_stats_table(
            draw, team2_table_x, player_stats_y, team2_table_width,
            game_result.get('team2_player_stats', {}), team2.name, max_players=7,
            name_font=player_name_font, stat_font=player_stat_font, header_font=player_header_font,
            season_stats_dict=player_season_stats
        )
        
        # VS divider in center (moved down to accommodate player stats)
        vs_y = scoreboard_y + scoreboard_height // 2
        vs_font = load_font(FONT_PATHS_BOLD, 56)
        draw_text_with_shadow(draw, (width//2, vs_y), "VS", vs_font, fill='#888888', anchor="mm")

        # Footer with cascade indicator
        footer_y = max(team1_table_y, team2_table_y) + 30
        legend_font = load_font(FONT_PATHS_REGULAR, 20)
        legend_text = "* = Cascade Zone"
        draw_text_with_shadow(draw, (width//2, footer_y), legend_text, legend_font, fill='#888888', anchor="mm")

        # Save image
        img.save(filename)
        
        # Generate Stories version (9:16 aspect ratio)
        stories_filename = filename.replace('.png', '_stories.png')
        generate_stories_version(img, stories_filename, game_result, team_analytics, game_type, week, game_number, season_id)
        
        return True
    except Exception as e:
        print(f"Error generating image {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_stories_version(base_image, filename, game_result, team_analytics, game_type="game", week=None, game_number=None, season_id=None):
    """Generate a 9:16 Stories version of the scoreboard optimized for Instagram Stories"""
    try:
        # Stories dimensions: 1080x1920 (9:16)
        stories_width, stories_height = 1080, 1920
        
        # Resize base image to fit Stories format (crop center or letterbox)
        # We'll create a new vertical layout optimized for Stories
        stories_img = Image.new('RGB', (stories_width, stories_height), color='#0a0a1a')
        stories_draw = ImageDraw.Draw(stories_img)
        
        # Draw gradient background
        draw_gradient_background(stories_img, stories_width, stories_height, '#0a0a1a', '#1a1a2e', 'vertical')
        
        # Get team info
        team1 = game_result['team1']
        team2 = game_result['team2']
        team1_score = game_result['team1_score']
        team2_score = game_result['team2_score']
        team1_detail = game_result['team1_detail']
        team2_detail = game_result['team2_detail']
        
        # Load logos
        logo1_path = os.path.join(config.LOGOS_DIRECTORY, team1.get_logo_filename())
        logo2_path = os.path.join(config.LOGOS_DIRECTORY, team2.get_logo_filename())
        
        logo1_original = None
        for logo_file in [logo1_path, logo1_path.replace("'", "'"), logo1_path.replace("'", "'")]:
            try:
                if os.path.exists(logo_file):
                    logo1_original = Image.open(logo_file).convert('RGBA')
                    break
            except:
                continue
        
        logo2_original = None
        for logo_file in [logo2_path, logo2_path.replace("'", "'"), logo2_path.replace("'", "'")]:
            try:
                if os.path.exists(logo_file):
                    logo2_original = Image.open(logo_file).convert('RGBA')
                    break
            except:
                continue
        
        # Load fonts for Stories
        title_font = load_font(FONT_PATHS_BOLD, 36)
        score_font = load_font(FONT_PATHS_BOLD, 140)
        team_font = load_font(FONT_PATHS_BOLD, 44)
        analytics_value_font = load_font(FONT_PATHS_BOLD, 24)
        player_name_font = load_font(FONT_PATHS_BOLD, 18)
        player_stat_font = load_font(FONT_PATHS_REGULAR, 16)
        
        # Header
        header_y = 50
        title = f"{game_type.replace('_', ' ').title()}"
        if week:
            title = f"Week {week}"
        elif game_number:
            title = f"{title} {game_number}"
        draw_text_with_shadow(stories_draw, (stories_width//2, header_y), title, title_font, fill='#ffffff', anchor="mm")
        
        # Team 1 section (top) - more compact
        team1_y = 140
        logo_size = 150
        
        if logo1_original:
            logo1 = logo1_original.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo1_x = (stories_width - logo_size) // 2
            stories_img.paste(logo1, (logo1_x, team1_y), logo1)
        
        team1_name_y = team1_y + logo_size + 15
        draw_text_with_shadow(stories_draw, (stories_width//2, team1_name_y), team1.name, team_font, fill='#ffffff', anchor="mm")
        
        score1_y = team1_name_y + 60
        draw_text_with_shadow(stories_draw, (stories_width//2, score1_y), str(team1_score), score_font, fill='#ffffff', anchor="mm")
        
        # Game stats for team 1 (compact)
        game_stats_y = score1_y + 100
        stats_text = f"R:{team1_detail.runs} T:{team1_detail.throws} K:{team1_detail.kicks}"
        draw_text_with_shadow(stories_draw, (stories_width//2, game_stats_y), stats_text, analytics_value_font, fill='#4ecdc4', anchor="mm")
        
        # Analytics for team 1 (if available)
        if team_analytics:
            team1_stats = team_analytics['team1_stats']
            analytics_y = game_stats_y + 35
            record_text = f"{team1_stats['wins']}-{team1_stats['losses']} • {team1_stats['win_percentage']}% • {team1_stats['avg_points_for']:.1f} PPG"
            draw_text_with_shadow(stories_draw, (stories_width//2, analytics_y), record_text, analytics_value_font, fill='#888888', anchor="mm")
        
        # Top players for team 1 (condensed)
        player_stats_start_y = analytics_y + 50 if team_analytics else game_stats_y + 50
        team1_players = game_result.get('team1_player_stats', {})
        sorted_team1 = []
        if team1_players:
            sorted_team1 = sorted(team1_players.items(), key=lambda x: x[1].get('points', 0), reverse=True)[:3]
            player_y = player_stats_start_y
            for idx, (player_id, stats) in enumerate(sorted_team1):
                player_name = _get_player_display_name(stats)
                points = stats.get('points', 0)
                runs = f"{stats.get('runs_completed', 0)}/{stats.get('runs_attempted', 0)}"
                throws = f"{stats.get('throws_completed', 0)}/{stats.get('throws_attempted', 0)}"
                kicks = f"{stats.get('kicks_completed', 0)}/{stats.get('kicks_attempted', 0)}"
                
                player_text = f"{player_name[:15]}: {points}pts | R:{runs} T:{throws} K:{kicks}"
                color = '#4ecdc4' if idx == 0 else '#aaaaaa'
                draw_text_with_shadow(stories_draw, (stories_width//2, player_y), player_text, player_stat_font, fill=color, anchor="mm")
                player_y += 22
        
        # VS divider
        vs_y = player_stats_start_y + (len(sorted_team1) * 22) + 30 if sorted_team1 else player_stats_start_y + 30
        vs_font = load_font(FONT_PATHS_BOLD, 40)
        draw_text_with_shadow(stories_draw, (stories_width//2, vs_y), "VS", vs_font, fill='#888888', anchor="mm")
        
        # Team 2 section (bottom) - more compact
        team2_y = vs_y + 50
        
        if logo2_original:
            logo2 = logo2_original.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo2_x = (stories_width - logo_size) // 2
            stories_img.paste(logo2, (logo2_x, team2_y), logo2)
        
        team2_name_y = team2_y + logo_size + 15
        draw_text_with_shadow(stories_draw, (stories_width//2, team2_name_y), team2.name, team_font, fill='#ffffff', anchor="mm")
        
        score2_y = team2_name_y + 60
        draw_text_with_shadow(stories_draw, (stories_width//2, score2_y), str(team2_score), score_font, fill='#ffffff', anchor="mm")
        
        # Game stats for team 2 (compact)
        game_stats_y2 = score2_y + 100
        stats_text2 = f"R:{team2_detail.runs} T:{team2_detail.throws} K:{team2_detail.kicks}"
        draw_text_with_shadow(stories_draw, (stories_width//2, game_stats_y2), stats_text2, analytics_value_font, fill='#4ecdc4', anchor="mm")
        
        # Analytics for team 2 (if available)
        if team_analytics:
            team2_stats = team_analytics['team2_stats']
            analytics_y2 = game_stats_y2 + 35
            record_text2 = f"{team2_stats['wins']}-{team2_stats['losses']} • {team2_stats['win_percentage']}% • {team2_stats['avg_points_for']:.1f} PPG"
            draw_text_with_shadow(stories_draw, (stories_width//2, analytics_y2), record_text2, analytics_value_font, fill='#888888', anchor="mm")
        
        # Top players for team 2 (condensed)
        player_stats_start_y2 = analytics_y2 + 50 if team_analytics else game_stats_y2 + 50
        team2_players = game_result.get('team2_player_stats', {})
        if team2_players:
            sorted_team2 = sorted(team2_players.items(), key=lambda x: x[1].get('points', 0), reverse=True)[:3]
            player_y2 = player_stats_start_y2
            for idx, (player_id, stats) in enumerate(sorted_team2):
                player_name = _get_player_display_name(stats)
                points = stats.get('points', 0)
                runs = f"{stats.get('runs_completed', 0)}/{stats.get('runs_attempted', 0)}"
                throws = f"{stats.get('throws_completed', 0)}/{stats.get('throws_attempted', 0)}"
                kicks = f"{stats.get('kicks_completed', 0)}/{stats.get('kicks_attempted', 0)}"
                
                player_text = f"{player_name[:15]}: {points}pts | R:{runs} T:{throws} K:{kicks}"
                color = '#4ecdc4' if idx == 0 else '#aaaaaa'
                draw_text_with_shadow(stories_draw, (stories_width//2, player_y2), player_text, player_stat_font, fill=color, anchor="mm")
                player_y2 += 22
        
        # Save Stories version
        stories_img.save(filename)
        return True
    except Exception as e:
        print(f"Error generating Stories version {filename}: {e}")
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

