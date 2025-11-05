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
    
    # Create a large overlay for the background
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    # Scale logo to cover the entire image (scale to fill while maintaining aspect ratio)
    # Use the larger dimension to ensure it covers the entire image
    scale_factor = max(width / logo_image.width, height / logo_image.height)
    logo_width = int(logo_image.width * scale_factor)
    logo_height = int(logo_image.height * scale_factor)
    logo_resized = logo_image.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
    
    # Make logo translucent (reduce alpha)
    alpha = logo_resized.split()[3]
    alpha_reduced = alpha.point(lambda p: int(p * 0.7))  # 70% opacity
    logo_translucent = logo_resized.copy()
    logo_translucent.putalpha(alpha_reduced)
    
    # Center the logo on the background
    logo_x = (width - logo_width) // 2
    logo_y = (height - logo_height) // 2
    overlay.paste(logo_translucent, (logo_x, logo_y), logo_translucent)
    
    # Composite onto image
    img.paste(overlay, (0, 0), overlay)


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
    """Generate a game scoreboard image with team logos and scores - enhanced with modern styling in 1:1 square format"""
    try:
        # Create square image with gradient background (Instagram-friendly 1:1 aspect ratio)
        width, height = 1600, 1600
        img = Image.new('RGB', (width, height), color='#0a0a1a')
        draw = ImageDraw.Draw(img)
        
        # Get team scores early to determine winner for background theme
        team1 = game_result['team1']
        team2 = game_result['team2']
        team1_score = game_result['team1_score']
        team2_score = game_result['team2_score']
        
        # Draw base gradient background
        draw_gradient_background(img, width, height, '#0a0a1a', '#1a1a2e', 'vertical')
        
        # Try to load fonts, fallback to default if not available
        try:
            title_font = ImageFont.truetype("arial.ttf", 72)
            try:
                title_bold_font = ImageFont.truetype("arialbd.ttf", 72)
            except:
                title_bold_font = ImageFont.truetype("arial.ttf", 72)
            score_font = ImageFont.truetype("arial.ttf", 160)
            team_font = ImageFont.truetype("arial.ttf", 52)
            detail_font = ImageFont.truetype("arial.ttf", 32)
            vs_font = ImageFont.truetype("arial.ttf", 52)
        except:
            try:
                title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
                try:
                    title_bold_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 72)
                except:
                    title_bold_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
                score_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 160)
                team_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 52)
                detail_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
                vs_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 52)
            except:
                title_font = ImageFont.load_default()
                title_bold_font = ImageFont.load_default()
                score_font = ImageFont.load_default()
                team_font = ImageFont.load_default()
                detail_font = ImageFont.load_default()
                vs_font = ImageFont.load_default()
        
        team1_detail = game_result['team1_detail']
        team2_detail = game_result['team2_detail']
        
        # Load logos early to extract colors for background theme
        logo_size = 300
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
        
        # Apply translucent winner's logo as background
        apply_translucent_logo_background(img, winning_team_logo, width, height)
        
        # Add semi-transparent glass effect overlay behind text areas for readability
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        # Glass effect behind stats areas - light white/blue tint with low alpha for transparency
        card_area_alpha = 25  # Low alpha for glass effect, allows backdrop logo to show through
        # Use light white/blue tint for glass effect instead of pure black
        overlay_draw.rectangle([50, 400, 650, height - 200], fill=(200, 220, 240, card_area_alpha), outline=None)
        overlay_draw.rectangle([950, 400, width - 50, height - 200], fill=(200, 220, 240, card_area_alpha), outline=None)
        # Dark overlay behind title (keep this for readability)
        overlay_draw.rectangle([0, 0, width, 150], fill=(0, 0, 0, 180), outline=None)
        img.paste(overlay, (0, 0), overlay)
        
        # Recreate draw object after compositing overlay
        draw = ImageDraw.Draw(img)
        
        # Resize logos for display
        logo1 = None
        if logo1_original:
            logo1 = logo1_original.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        logo2 = None
        if logo2_original:
            logo2 = logo2_original.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        # Resize loser logo for bottom right corner
        loser_logo_size = 200
        loser_logo = None
        if losing_team_logo:
            loser_logo = losing_team_logo.resize((loser_logo_size, loser_logo_size), Image.Resampling.LANCZOS)
        
        # Draw decorative border with glow effect
        border_width = 8
        border_color = '#4ecdc4'
        for i in range(3):
            draw.rectangle([i, i, width-1-i, height-1-i], outline=border_color, width=1)
        draw.rectangle([3, 3, width-4, height-4], outline=border_color, width=border_width)
        
        # Draw title with word art styling
        title = f"{game_type.replace('_', ' ').title()}"
        if week:
            title = f"Week {week} - {title}"
        elif game_number:
            title = f"{title} {game_number}"
        
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = 40
        
        # Word art title with multiple glow layers
        for offset in [8, 6, 5, 4, 3, 2]:
            draw.text((title_x + offset, title_y + offset), title, fill='#000000', font=title_font)
        draw.text((title_x + 3, title_y + 3), title, fill='#ff6b6b', font=title_font)
        draw.text((title_x + 2, title_y + 2), title, fill='#4ecdc4', font=title_font)
        draw.text((title_x + 1, title_y + 1), title, fill='#ffffff', font=title_font)
        draw.text((title_x, title_y), title, fill='#ffff00', font=title_font)  # Bright yellow
        
        # Draw team names as headers with word art
        # Calculate center positions for each scorecard section
        scorecard1_left = 50
        scorecard1_right = 650
        scorecard1_center_x = (scorecard1_left + scorecard1_right) // 2
        
        scorecard2_left = 950
        scorecard2_right = width - 50
        scorecard2_center_x = (scorecard2_left + scorecard2_right) // 2
        
        team1_start_y = 400
        team2_start_y = 400
        
        # Team 1 name header (centered)
        team1_name_bbox = draw.textbbox((0, 0), team1.name, font=team_font)
        team1_name_width = team1_name_bbox[2] - team1_name_bbox[0]
        team1_name_x = scorecard1_center_x - team1_name_width // 2
        for offset in [5, 4, 3, 2]:
            draw.text((team1_name_x + offset, team1_start_y + offset), team1.name, fill='#000000', font=team_font)
        draw.text((team1_name_x + 2, team1_start_y + 2), team1.name, fill='#4ecdc4', font=team_font)
        draw.text((team1_name_x, team1_start_y), team1.name, fill='#ffffff', font=team_font)
        
        # Team 2 name header (centered)
        team2_name_bbox = draw.textbbox((0, 0), team2.name, font=team_font)
        team2_name_width = team2_name_bbox[2] - team2_name_bbox[0]
        team2_name_x = scorecard2_center_x - team2_name_width // 2
        for offset in [5, 4, 3, 2]:
            draw.text((team2_name_x + offset, team2_start_y + offset), team2.name, fill='#000000', font=team_font)
        draw.text((team2_name_x + 2, team2_start_y + 2), team2.name, fill='#4ecdc4', font=team_font)
        draw.text((team2_name_x, team2_start_y), team2.name, fill='#ffffff', font=team_font)
        
        # Draw stats vertically: Runs, Throws, Kicks, then big Score
        stat_spacing = 80
        stat_label_font_size = 36
        try:
            stat_label_font = ImageFont.truetype("arial.ttf", stat_label_font_size)
        except:
            try:
                stat_label_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", stat_label_font_size)
            except:
                stat_label_font = ImageFont.load_default()
        
        # Team 1 stats (left side, centered)
        y_pos = team1_start_y + 70
        # Runs
        runs1_text = f"RUNS: {team1_detail.runs}"
        runs1_bbox = draw.textbbox((0, 0), runs1_text, font=stat_label_font)
        runs1_width = runs1_bbox[2] - runs1_bbox[0]
        runs1_x = scorecard1_center_x - runs1_width // 2
        for offset in [4, 3, 2]:
            draw.text((runs1_x + offset, y_pos + offset), runs1_text, fill='#000000', font=stat_label_font)
        draw.text((runs1_x + 1, y_pos + 1), runs1_text, fill='#ff6b6b', font=stat_label_font)
        draw.text((runs1_x, y_pos), runs1_text, fill='#ffffff', font=stat_label_font)
        # Draw yellow circles for cascade runs
        if team1_detail.cascade_runs > 0:
            circle_radius = 7
            circle_spacing = 6
            circle_start_x = runs1_x + runs1_width + 15
            circle_y = y_pos + stat_label_font_size // 2 - circle_radius
            for i in range(team1_detail.cascade_runs):
                circle_x = circle_start_x + i * (circle_radius * 2 + circle_spacing)
                draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, 
                             circle_x + circle_radius, circle_y + circle_radius], 
                            fill='#ffd93d', outline='#ffffff', width=1)
        y_pos += stat_spacing
        
        # Throws
        throws1_text = f"THROWS: {team1_detail.throws}"
        throws1_bbox = draw.textbbox((0, 0), throws1_text, font=stat_label_font)
        throws1_width = throws1_bbox[2] - throws1_bbox[0]
        throws1_x = scorecard1_center_x - throws1_width // 2
        for offset in [4, 3, 2]:
            draw.text((throws1_x + offset, y_pos + offset), throws1_text, fill='#000000', font=stat_label_font)
        draw.text((throws1_x + 1, y_pos + 1), throws1_text, fill='#4ecdc4', font=stat_label_font)
        draw.text((throws1_x, y_pos), throws1_text, fill='#ffffff', font=stat_label_font)
        # Draw yellow circles for cascade throws
        if team1_detail.cascade_throws > 0:
            circle_radius = 7
            circle_spacing = 6
            circle_start_x = throws1_x + throws1_width + 15
            circle_y = y_pos + stat_label_font_size // 2 - circle_radius
            for i in range(team1_detail.cascade_throws):
                circle_x = circle_start_x + i * (circle_radius * 2 + circle_spacing)
                draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, 
                             circle_x + circle_radius, circle_y + circle_radius], 
                            fill='#ffd93d', outline='#ffffff', width=1)
        y_pos += stat_spacing
        
        # Kicks
        kicks1_text = f"KICKS: {team1_detail.kicks}"
        kicks1_bbox = draw.textbbox((0, 0), kicks1_text, font=stat_label_font)
        kicks1_width = kicks1_bbox[2] - kicks1_bbox[0]
        kicks1_x = scorecard1_center_x - kicks1_width // 2
        for offset in [4, 3, 2]:
            draw.text((kicks1_x + offset, y_pos + offset), kicks1_text, fill='#000000', font=stat_label_font)
        draw.text((kicks1_x + 1, y_pos + 1), kicks1_text, fill='#ffd93d', font=stat_label_font)
        draw.text((kicks1_x, y_pos), kicks1_text, fill='#ffffff', font=stat_label_font)
        # Draw yellow circles for cascade kicks
        if team1_detail.cascade_kicks > 0:
            circle_radius = 7
            circle_spacing = 6
            circle_start_x = kicks1_x + kicks1_width + 15
            circle_y = y_pos + stat_label_font_size // 2 - circle_radius
            for i in range(team1_detail.cascade_kicks):
                circle_x = circle_start_x + i * (circle_radius * 2 + circle_spacing)
                draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, 
                             circle_x + circle_radius, circle_y + circle_radius], 
                            fill='#ffd93d', outline='#ffffff', width=1)
        y_pos += stat_spacing + 20
        
        # Big Score for Team 1
        score1_text = str(team1_score)
        big_score_font_size = 200
        try:
            big_score_font = ImageFont.truetype("arial.ttf", big_score_font_size)
        except:
            try:
                big_score_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", big_score_font_size)
            except:
                big_score_font = ImageFont.load_default()
        
        score1_bbox = draw.textbbox((0, 0), score1_text, font=big_score_font)
        score1_width = score1_bbox[2] - score1_bbox[0]
        score1_x = scorecard1_center_x - score1_width // 2
        for offset in [12, 10, 8, 6, 5, 4, 3]:
            draw.text((score1_x + offset, y_pos + offset), score1_text, fill='#000000', font=big_score_font)
        draw.text((score1_x + 4, y_pos + 4), score1_text, fill='#ff6b6b', font=big_score_font)
        draw.text((score1_x + 3, y_pos + 3), score1_text, fill='#4ecdc4', font=big_score_font)
        draw.text((score1_x + 2, y_pos + 2), score1_text, fill='#ffffff', font=big_score_font)
        draw.text((score1_x, y_pos), score1_text, fill='#ffff00', font=big_score_font)
        
        # Team 2 stats (right side, centered)
        y_pos = team2_start_y + 70
        # Runs
        runs2_text = f"RUNS: {team2_detail.runs}"
        runs2_bbox = draw.textbbox((0, 0), runs2_text, font=stat_label_font)
        runs2_width = runs2_bbox[2] - runs2_bbox[0]
        runs2_x = scorecard2_center_x - runs2_width // 2
        for offset in [4, 3, 2]:
            draw.text((runs2_x + offset, y_pos + offset), runs2_text, fill='#000000', font=stat_label_font)
        draw.text((runs2_x + 1, y_pos + 1), runs2_text, fill='#ff6b6b', font=stat_label_font)
        draw.text((runs2_x, y_pos), runs2_text, fill='#ffffff', font=stat_label_font)
        # Draw yellow circles for cascade runs
        if team2_detail.cascade_runs > 0:
            circle_radius = 7
            circle_spacing = 6
            circle_start_x = runs2_x + runs2_width + 15
            circle_y = y_pos + stat_label_font_size // 2 - circle_radius
            for i in range(team2_detail.cascade_runs):
                circle_x = circle_start_x + i * (circle_radius * 2 + circle_spacing)
                draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, 
                             circle_x + circle_radius, circle_y + circle_radius], 
                            fill='#ffd93d', outline='#ffffff', width=1)
        y_pos += stat_spacing
        
        # Throws
        throws2_text = f"THROWS: {team2_detail.throws}"
        throws2_bbox = draw.textbbox((0, 0), throws2_text, font=stat_label_font)
        throws2_width = throws2_bbox[2] - throws2_bbox[0]
        throws2_x = scorecard2_center_x - throws2_width // 2
        for offset in [4, 3, 2]:
            draw.text((throws2_x + offset, y_pos + offset), throws2_text, fill='#000000', font=stat_label_font)
        draw.text((throws2_x + 1, y_pos + 1), throws2_text, fill='#4ecdc4', font=stat_label_font)
        draw.text((throws2_x, y_pos), throws2_text, fill='#ffffff', font=stat_label_font)
        # Draw yellow circles for cascade throws
        if team2_detail.cascade_throws > 0:
            circle_radius = 7
            circle_spacing = 6
            circle_start_x = throws2_x + throws2_width + 15
            circle_y = y_pos + stat_label_font_size // 2 - circle_radius
            for i in range(team2_detail.cascade_throws):
                circle_x = circle_start_x + i * (circle_radius * 2 + circle_spacing)
                draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, 
                             circle_x + circle_radius, circle_y + circle_radius], 
                            fill='#ffd93d', outline='#ffffff', width=1)
        y_pos += stat_spacing
        
        # Kicks
        kicks2_text = f"KICKS: {team2_detail.kicks}"
        kicks2_bbox = draw.textbbox((0, 0), kicks2_text, font=stat_label_font)
        kicks2_width = kicks2_bbox[2] - kicks2_bbox[0]
        kicks2_x = scorecard2_center_x - kicks2_width // 2
        for offset in [4, 3, 2]:
            draw.text((kicks2_x + offset, y_pos + offset), kicks2_text, fill='#000000', font=stat_label_font)
        draw.text((kicks2_x + 1, y_pos + 1), kicks2_text, fill='#ffd93d', font=stat_label_font)
        draw.text((kicks2_x, y_pos), kicks2_text, fill='#ffffff', font=stat_label_font)
        # Draw yellow circles for cascade kicks
        if team2_detail.cascade_kicks > 0:
            circle_radius = 7
            circle_spacing = 6
            circle_start_x = kicks2_x + kicks2_width + 15
            circle_y = y_pos + stat_label_font_size // 2 - circle_radius
            for i in range(team2_detail.cascade_kicks):
                circle_x = circle_start_x + i * (circle_radius * 2 + circle_spacing)
                draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, 
                             circle_x + circle_radius, circle_y + circle_radius], 
                            fill='#ffd93d', outline='#ffffff', width=1)
        y_pos += stat_spacing + 20
        
        # Big Score for Team 2
        score2_text = str(team2_score)
        score2_bbox = draw.textbbox((0, 0), score2_text, font=big_score_font)
        score2_width = score2_bbox[2] - score2_bbox[0]
        score2_x = scorecard2_center_x - score2_width // 2
        for offset in [12, 10, 8, 6, 5, 4, 3]:
            draw.text((score2_x + offset, y_pos + offset), score2_text, fill='#000000', font=big_score_font)
        draw.text((score2_x + 4, y_pos + 4), score2_text, fill='#ff6b6b', font=big_score_font)
        draw.text((score2_x + 3, y_pos + 3), score2_text, fill='#4ecdc4', font=big_score_font)
        draw.text((score2_x + 2, y_pos + 2), score2_text, fill='#ffffff', font=big_score_font)
        draw.text((score2_x, y_pos), score2_text, fill='#ffff00', font=big_score_font)
        
        # Draw loser logo in bottom right corner
        if loser_logo:
            loser_logo_x = width - loser_logo_size - 40
            loser_logo_y = height - loser_logo_size - 40
            # Add shadow behind logo
            shadow_img = Image.new('RGBA', (loser_logo_size + 10, loser_logo_size + 10), (0, 0, 0, 0))
            shadow_mask = Image.new('RGBA', loser_logo.size, (0, 0, 0, 150))
            shadow_img.paste(shadow_mask, (5, 5), shadow_mask)
            img.paste(shadow_img, (loser_logo_x - 5, loser_logo_y - 5), shadow_img)
            img.paste(loser_logo, (loser_logo_x, loser_logo_y), loser_logo)
        
        # Draw legend for Cascade Zone indicator
        legend_font_size = 26
        try:
            legend_font = ImageFont.truetype("arial.ttf", legend_font_size)
        except:
            try:
                legend_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", legend_font_size)
            except:
                legend_font = ImageFont.load_default()
        
        legend_y = height - 80
        legend_circle_radius = 7
        legend_circle_x = width // 2 - 90
        legend_circle_y = legend_y + legend_font_size // 2 - legend_circle_radius
        draw.ellipse([legend_circle_x - legend_circle_radius, legend_circle_y - legend_circle_radius,
                     legend_circle_x + legend_circle_radius, legend_circle_y + legend_circle_radius],
                    fill='#ffd93d', outline='#ffffff', width=1)
        
        legend_text = "= Cascade Zone"
        legend_text_bbox = draw.textbbox((0, 0), legend_text, font=legend_font)
        legend_text_width = legend_text_bbox[2] - legend_text_bbox[0]
        legend_text_x = legend_circle_x + legend_circle_radius + 10
        draw.text((legend_text_x, legend_y), legend_text, fill='#ffffff', font=legend_font)
        
        # Save image
        img.save(filename)
        return True
    except Exception as e:
        print(f"Error generating image {filename}: {e}")
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
        
        # Try to load fonts
        try:
            title_font = ImageFont.truetype("arial.ttf", 64)
            round_font = ImageFont.truetype("arial.ttf", 40)
            team_font = ImageFont.truetype("arial.ttf", 28)
            seed_font = ImageFont.truetype("arial.ttf", 20)
        except:
            try:
                title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 64)
                round_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
                team_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
                seed_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
            except:
                title_font = ImageFont.load_default()
                round_font = ImageFont.load_default()
                team_font = ImageFont.load_default()
                seed_font = ImageFont.load_default()
        
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

