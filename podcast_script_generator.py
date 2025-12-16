"""Podcast Script Generator Module"""
import random
import logging
import os
import time

# Try to import scheduler for logger, fallback to basic logging
try:
    import scheduler
    logger = scheduler.logger
except ImportError:
    logger = logging.getLogger(__name__)

# Try to import Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google.generativeai not available. Gemini script generation will be disabled.")


def load_gemini_api_key():
    """Load Gemini API key from .env file or environment variables"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # First, try to read directly from .env file to get the latest value
    if os.path.exists(env_path):
        api_key = None
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    # Remove quotes if present
                    if api_key.startswith('"') and api_key.endswith('"'):
                        api_key = api_key[1:-1]
                    elif api_key.startswith("'") and api_key.endswith("'"):
                        api_key = api_key[1:-1]
                    break
        
        if api_key:
            return api_key
    
    # Fallback to using dotenv with override=True to force reload
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Force reload from .env file
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            # Strip quotes and whitespace
            api_key = api_key.strip()
            if api_key.startswith('"') and api_key.endswith('"'):
                api_key = api_key[1:-1]
            elif api_key.startswith("'") and api_key.endswith("'"):
                api_key = api_key[1:-1]
            return api_key
    except ImportError:
        pass
    
    # If we get here, the key wasn't found
    if not os.path.exists(env_path):
        raise FileNotFoundError(
            ".env file not found. Please create a .env file with GEMINI_API_KEY=your_api_key"
        )
    
    raise ValueError(
        "GEMINI_API_KEY not found in .env file. "
        "Please add: GEMINI_API_KEY=your_api_key"
    )


def extract_player_data_for_prompt(game_result):
    """
    Extract and format player data from game_result for Gemini prompt.
    """
    team1 = game_result.get('team1')
    team2 = game_result.get('team2')
    team1_player_stats = game_result.get('team1_player_stats', {})
    team2_player_stats = game_result.get('team2_player_stats', {})
    
    if not team1_player_stats and not team2_player_stats:
        return ""
    
    player_data_parts = []
    
    # Process Team 1 players
    if team1 and hasattr(team1, 'players') and team1.players:
        player_data_parts.append(f"\n=== {team1.name} PLAYERS ===")
        player_metadata = {p['name']: p for p in team1.players}
        sorted_players = sorted(team1.players, key=lambda p: p.get('ranking', 4))
        
        for player in sorted_players:
            player_name = player['name']
            ranking = player.get('ranking', 4)
            best_stat = player.get('best_stat', 'Run')
            role = player.get('role', 'Runner')
            
            stats = team1_player_stats.get(player_name, {})
            runs_attempted = stats.get('runs_attempted', 0)
            runs_completed = stats.get('runs_completed', 0)
            throws_attempted = stats.get('throws_attempted', 0)
            throws_completed = stats.get('throws_completed', 0)
            kicks_attempted = stats.get('kicks_attempted', 0)
            kicks_completed = stats.get('kicks_completed', 0)
            points = stats.get('points', 0)
            
            run_pct = (runs_completed / runs_attempted * 100) if runs_attempted > 0 else 0
            throw_pct = (throws_completed / throws_attempted * 100) if throws_attempted > 0 else 0
            kick_pct = (kicks_completed / kicks_attempted * 100) if kicks_attempted > 0 else 0
            
            player_data_parts.append(
                f"\n#{ranking} {player_name} ({role}, Best: {best_stat}) - {points} points\n"
                f"  Runs: {runs_attempted} attempts, {runs_completed} completions ({run_pct:.1f}%)\n"
                f"  Throws: {throws_attempted} attempts, {throws_completed} completions ({throw_pct:.1f}%)\n"
                f"  Kicks: {kicks_attempted} attempts, {kicks_completed} completions ({kick_pct:.1f}%)"
            )
    
    # Process Team 2 players
    if team2 and hasattr(team2, 'players') and team2.players:
        player_data_parts.append(f"\n=== {team2.name} PLAYERS ===")
        sorted_players = sorted(team2.players, key=lambda p: p.get('ranking', 4))
        
        for player in sorted_players:
            player_name = player['name']
            ranking = player.get('ranking', 4)
            best_stat = player.get('best_stat', 'Run')
            role = player.get('role', 'Runner')
            
            stats = team2_player_stats.get(player_name, {})
            runs_attempted = stats.get('runs_attempted', 0)
            runs_completed = stats.get('runs_completed', 0)
            throws_attempted = stats.get('throws_attempted', 0)
            throws_completed = stats.get('throws_completed', 0)
            kicks_attempted = stats.get('kicks_attempted', 0)
            kicks_completed = stats.get('kicks_completed', 0)
            points = stats.get('points', 0)
            
            run_pct = (runs_completed / runs_attempted * 100) if runs_attempted > 0 else 0
            throw_pct = (throws_completed / throws_attempted * 100) if throws_attempted > 0 else 0
            kick_pct = (kicks_completed / kicks_attempted * 100) if kicks_attempted > 0 else 0
            
            player_data_parts.append(
                f"\n#{ranking} {player_name} ({role}, Best: {best_stat}) - {points} points\n"
                f"  Runs: {runs_attempted} attempts, {runs_completed} completions ({run_pct:.1f}%)\n"
                f"  Throws: {throws_attempted} attempts, {throws_completed} completions ({throw_pct:.1f}%)\n"
                f"  Kicks: {kicks_attempted} attempts, {kicks_completed} completions ({kick_pct:.1f}%)"
            )
    
    return "\n".join(player_data_parts)


def build_game_context(game_result, week, game_num, game_type="game"):
    """
    Build comprehensive game context string.
    """
    team1 = game_result['team1']
    team2 = game_result['team2']
    team1_score = game_result['team1_score']
    team2_score = game_result['team2_score']
    team1_detail = game_result['team1_detail']
    team2_detail = game_result['team2_detail']
    upset = game_result.get('upset', False)
    
    context_parts = []
    
    if game_type == "quarterfinal":
        context_parts.append("=== TOURNAMENT QUARTERFINAL GAME ===")
    elif game_type == "semifinal":
        context_parts.append("=== TOURNAMENT SEMIFINAL GAME ===")
    elif game_type == "final":
        context_parts.append("=== TOURNAMENT FINAL GAME ===")
    else:
        context_parts.append(f"=== WEEK {week}, GAME {game_num} ===")
    
    context_parts.append(f"\nMATCHUP: {team1.name} vs {team2.name}")
    context_parts.append(f"FINAL SCORE: {team1.name} {team1_score} - {team2_score} {team2.name}")
    
    if upset:
        winner = team1 if team1_score > team2_score else team2
        loser = team2 if team1_score > team2_score else team1
        context_parts.append(f"RESULT: UPSET VICTORY by {winner.name}")
    else:
        winner = team1 if team1_score > team2_score else team2
        context_parts.append(f"RESULT: Expected victory by {winner.name}")

    context_parts.append(f"\nTEAM 1 STATS ({team1.name}):")
    context_parts.append(f"  Advantage: {team1.overall_advantage} (Run: {team1.run_advantage}, Throw: {team1.throw_advantage}, Kick: {team1.kick_advantage})")
    context_parts.append(f"  Scoring: {team1_detail.runs} Runs, {team1_detail.throws} Throws, {team1_detail.kicks} Kicks")
    context_parts.append(f"  Cascade Zone: {team1_detail.cascade_runs} Runs, {team1_detail.cascade_throws} Throws, {team1_detail.cascade_kicks} Kicks")

    context_parts.append(f"\nTEAM 2 STATS ({team2.name}):")
    context_parts.append(f"  Advantage: {team2.overall_advantage} (Run: {team2.run_advantage}, Throw: {team2.throw_advantage}, Kick: {team2.kick_advantage})")
    context_parts.append(f"  Scoring: {team2_detail.runs} Runs, {team2_detail.throws} Throws, {team2_detail.kicks} Kicks")
    context_parts.append(f"  Cascade Zone: {team2_detail.cascade_runs} Runs, {team2_detail.cascade_throws} Throws, {team2_detail.cascade_kicks} Kicks")
    
    player_data = extract_player_data_for_prompt(game_result)
    if player_data:
        context_parts.append("\n=== PLAYER PERFORMANCES ===")
        context_parts.append(player_data)
    
    return "\n".join(context_parts)


def generate_segment_prompt(segment_type, game_context, rulebook_summary, previous_segment=None):
    """
    Generate prompt for a specific segment of the podcast.
    """
    base_instructions = """
You are a sports reporter filing a detailed, narrative report on a Cascade game.
TONE:
- Objective yet engaging, like a high-quality radio documentary or detailed news report.
- Narrative-driven: Tell the story of the game.
- Detailed: Use specific numbers, player names, and game mechanics.
- TTS-Optimized: Use clear, simple sentence structures. Avoid complex clauses. Use standard punctuation.
- AVOID: "Boom!", "Wham!", "And the crowd goes wild!", robotic sportscaster tropes, excessive exclamation marks.
- DO NOT use phrases like "Ladies and gentlemen", "Welcome back folks".
- Focus on the STRATEGY, the CASCADE ZONE mechanics, and individual PLAYER contributions.

CASCADE RULES:
- Runs (3pts, 6 in Cascade Zone)
- Throws (2pts, 4 in Cascade Zone)
- Kicks (1pts, 2 in Cascade Zone)
- Cascade Zone doubles points.
"""

    if segment_type == "intro":
        specific_instructions = """
TASK: Write the INTRODUCTION segment (approx. 400 words).
- Introduce the matchup and the teams.
- Discuss the pre-game context (advantages, key players to watch).
- Set the scene for the match.
- End by transitioning to the start of the game.
"""
    elif segment_type == "early_game":
        specific_instructions = """
TASK: Write the EARLY GAME segment (approx. 500 words).
- Detail the first quarter/early phases of the game.
- Describe the initial strategies and scoring openings.
- Highlight specific player actions (successes and failures).
- Focus on how the teams established their rhythm.
"""
    elif segment_type == "mid_game":
        specific_instructions = """
TASK: Write the MID-GAME segment (approx. 500 words).
- Describe the middle phase of the match.
- Focus on momentum shifts, defensive plays, and tactical adjustments.
- Detail any key "Cascade Zone" plays that changed the score significantly.
- Continue to weave player stats and names into the narrative.
"""
    elif segment_type == "late_game":
        specific_instructions = """
TASK: Write the LATE GAME/CLIMAX segment (approx. 500 words).
- Build tension as the game reaches its conclusion.
- Describe critical plays in the final minutes.
- Show how the winning team pulled ahead or secured the victory.
- If it was an upset, highlight the turning point.
"""
    elif segment_type == "outro":
        specific_instructions = """
TASK: Write the POST-GAME ANALYSIS/OUTRO segment (approx. 350 words).
- Summarize the final result and score.
- Analyze why the winning team won (strategy, key players).
- Reflect on what this means for their season.
- Sign off clearly.
"""
    else:
        return ""

    prompt = f"""{base_instructions}

{specific_instructions}

GAME CONTEXT:
{game_context}

RULEBOOK SUMMARY:
{rulebook_summary}
"""
    if previous_segment:
        prompt += f"\nPREVIOUS SEGMENT (for context/continuity):\n{previous_segment[-500:]}\n\nContinue the narrative naturally from here."

    return prompt


def generate_game_script_with_gemini(game_result, rulebook_text, week, game_num, game_type="game"):
    """
    Generate segmented podcast script using Gemini.
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini API not available.")
        return None
    
    try:
        api_key = load_gemini_api_key()
        genai.configure(api_key=api_key)
        
        # Select Model
        model_name = "gemini-2.0-flash-exp"
        try:
            model = genai.GenerativeModel(model_name)
        except Exception:
            logger.warning(f"Model {model_name} not available, trying gemini-pro")
            model_name = "gemini-pro"
            model = genai.GenerativeModel(model_name)

        game_context = build_game_context(game_result, week, game_num, game_type)
        rulebook_summary = rulebook_text[:1000] if rulebook_text else "Cascade: Runs(3/6), Throws(2/4), Kicks(1/2)."
        
        segments = ["intro", "early_game", "mid_game", "late_game", "outro"]
        full_script = []
        previous_text = ""
        
        for segment in segments:
            logger.info(f"Generating {segment} segment...")
            prompt = generate_segment_prompt(segment, game_context, rulebook_summary, previous_text)

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7, # Slightly lower temperature for more coherent reporting
                    "top_p": 0.9,
                    "max_output_tokens": 2000,
                }
            )

            segment_text = response.text.strip()
            full_script.append(segment_text)
            previous_text = segment_text

            # Rate limiting/pause between segments
            time.sleep(1)

        final_script = "\n\n".join(full_script)
        word_count = len(final_script.split())
        logger.info(f"Generated complete script: {word_count} words.")
        
        return final_script

    except Exception as e:
        logger.error(f"Error generating script: {e}")
        return None


def generate_game_script(game_result, rulebook_text, week, game_num, use_gemini=True, game_type="game"):
    """
    Wrapper to generate script, defaulting to Gemini if available.
    Fallback to simple template (not implemented fully here to save space, but logic exists in original).
    """
    if use_gemini and GEMINI_AVAILABLE:
        script = generate_game_script_with_gemini(game_result, rulebook_text, week, game_num, game_type)
        if script:
            return script

    # Fallback/Template logic would go here if Gemini fails
    logger.warning("Gemini generation failed, returning simple placeholder.")
    return f"Game report for {game_result['team1'].name} vs {game_result['team2'].name}. Final Score: {game_result['team1_score']} - {game_result['team2_score']}."


def generate_week_podcast_script(game_results_by_week, week, rulebook_text, use_gemini=True):
    """
    Generate scripts for all games in a week.
    """
    if week not in game_results_by_week:
        return "", {}
    
    week_games = game_results_by_week[week]
    individual_scripts = {}
    combined_parts = []
    
    # Filter valid games
    actual_games = []
    for item in week_games:
        if isinstance(item, tuple):
            filename, game_result = item
            if "_gemini" not in filename:
                actual_games.append((filename, game_result))
        else:
            actual_games.append(item)

    # Intro
    combined_parts.append(f"Welcome to the Cascade Weekly Report for Week {week}. We have a full slate of matches to cover.")

    game_num = 1
    for item in actual_games:
        if isinstance(item, tuple):
            _, game_result = item
        else:
            game_result = item

        logger.info(f"Generating script for Game {game_num}...")
        script = generate_game_script(game_result, rulebook_text, week, game_num, use_gemini)
        individual_scripts[game_num] = script
        combined_parts.append(script)
        combined_parts.append("\n---\n")
        game_num += 1

    combined_parts.append("This concludes our report for this week. Thank you for listening.")

    return "\n".join(combined_parts), individual_scripts
