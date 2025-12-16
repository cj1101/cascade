"""Podcast Script Generator Module"""
import random
import logging
import os

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
    
    Args:
        game_result: Dictionary containing game result data
        
    Returns:
        str: Formatted player data string, or empty string if no player data
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
        
        # Create a mapping of player names to their metadata
        player_metadata = {p['name']: p for p in team1.players}
        
        # Sort players by ranking
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
            
            # Calculate completion percentages
            run_pct = (runs_completed / runs_attempted * 100) if runs_attempted > 0 else 0
            throw_pct = (throws_completed / throws_attempted * 100) if throws_attempted > 0 else 0
            kick_pct = (kicks_completed / kicks_attempted * 100) if kicks_attempted > 0 else 0
            
            player_data_parts.append(
                f"\n#{ranking} {player_name} ({role}, Best: {best_stat}) - {points} points\n"
                f"  Runs: {runs_attempted} attempts, {runs_completed} completions ({run_pct:.1f}% success rate)\n"
                f"  Throws: {throws_attempted} attempts, {throws_completed} completions ({throw_pct:.1f}% success rate)\n"
                f"  Kicks: {kicks_attempted} attempts, {kicks_completed} completions ({kick_pct:.1f}% success rate)"
            )
    
    # Process Team 2 players
    if team2 and hasattr(team2, 'players') and team2.players:
        player_data_parts.append(f"\n=== {team2.name} PLAYERS ===")
        
        # Sort players by ranking
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
            
            # Calculate completion percentages
            run_pct = (runs_completed / runs_attempted * 100) if runs_attempted > 0 else 0
            throw_pct = (throws_completed / throws_attempted * 100) if throws_attempted > 0 else 0
            kick_pct = (kicks_completed / kicks_attempted * 100) if kicks_attempted > 0 else 0
            
            player_data_parts.append(
                f"\n#{ranking} {player_name} ({role}, Best: {best_stat}) - {points} points\n"
                f"  Runs: {runs_attempted} attempts, {runs_completed} completions ({run_pct:.1f}% success rate)\n"
                f"  Throws: {throws_attempted} attempts, {throws_completed} completions ({throw_pct:.1f}% success rate)\n"
                f"  Kicks: {kicks_attempted} attempts, {kicks_completed} completions ({kick_pct:.1f}% success rate)"
            )
    
    return "\n".join(player_data_parts)


def build_game_context_for_gemini(game_result, week, game_num, game_type="game"):
    """
    Build comprehensive game context string for Gemini prompt.
    
    Args:
        game_result: Dictionary containing game result data
        week: Week number (or None for tournament games)
        game_num: Game number within the week
        game_type: Type of game ("game", "quarterfinal", "semifinal", "final")
        
    Returns:
        str: Comprehensive game context string
    """
    team1 = game_result['team1']
    team2 = game_result['team2']
    team1_score = game_result['team1_score']
    team2_score = game_result['team2_score']
    team1_detail = game_result['team1_detail']
    team2_detail = game_result['team2_detail']
    upset = game_result.get('upset', False)
    
    context_parts = []
    
    # Game context header
    if game_type == "quarterfinal":
        context_parts.append("=== TOURNAMENT QUARTERFINAL GAME ===")
    elif game_type == "semifinal":
        context_parts.append("=== TOURNAMENT SEMIFINAL GAME ===")
    elif game_type == "final":
        context_parts.append("=== TOURNAMENT FINAL GAME (Best of 3 Series) ===")
    else:
        context_parts.append(f"=== WEEK {week}, GAME {game_num} ===")
    
    # Team information
    context_parts.append(f"\nTEAM 1: {team1.name}")
    context_parts.append(f"  Overall Advantage: {team1.overall_advantage}")
    context_parts.append(f"  Run Advantage: {team1.run_advantage}")
    context_parts.append(f"  Throw Advantage: {team1.throw_advantage}")
    context_parts.append(f"  Kick Advantage: {team1.kick_advantage}")
    context_parts.append(f"  Best Stat: {team1.best_stat()}")
    
    context_parts.append(f"\nTEAM 2: {team2.name}")
    context_parts.append(f"  Overall Advantage: {team2.overall_advantage}")
    context_parts.append(f"  Run Advantage: {team2.run_advantage}")
    context_parts.append(f"  Throw Advantage: {team2.throw_advantage}")
    context_parts.append(f"  Kick Advantage: {team2.kick_advantage}")
    context_parts.append(f"  Best Stat: {team2.best_stat()}")
    
    # Scoring breakdown
    context_parts.append(f"\n=== SCORING BREAKDOWN ===")
    context_parts.append(f"\n{team1.name} Final Score: {team1_score} points")
    context_parts.append(f"  Runs: {team1_detail.runs} total ({team1_detail.cascade_runs} in Cascade zone = {team1_detail.cascade_runs * 3} bonus points)")
    context_parts.append(f"  Throws: {team1_detail.throws} total ({team1_detail.cascade_throws} in Cascade zone = {team1_detail.cascade_throws * 2} bonus points)")
    context_parts.append(f"  Kicks: {team1_detail.kicks} total ({team1_detail.cascade_kicks} in Cascade zone = {team1_detail.cascade_kicks * 1} bonus points)")
    
    context_parts.append(f"\n{team2.name} Final Score: {team2_score} points")
    context_parts.append(f"  Runs: {team2_detail.runs} total ({team2_detail.cascade_runs} in Cascade zone = {team2_detail.cascade_runs * 3} bonus points)")
    context_parts.append(f"  Throws: {team2_detail.throws} total ({team2_detail.cascade_throws} in Cascade zone = {team2_detail.cascade_throws * 2} bonus points)")
    context_parts.append(f"  Kicks: {team2_detail.kicks} total ({team2_detail.cascade_kicks} in Cascade zone = {team2_detail.cascade_kicks * 1} bonus points)")
    
    # Upset flag
    if upset:
        winner = team1 if team1_score > team2_score else team2
        loser = team2 if team1_score > team2_score else team1
        context_parts.append(f"\n⚠️ UPSET ALERT: {winner.name} (lower advantage) defeated {loser.name} (higher advantage)")
    
    # Player performance data
    player_data = extract_player_data_for_prompt(game_result)
    if player_data:
        context_parts.append("\n=== INDIVIDUAL PLAYER PERFORMANCES ===")
        context_parts.append(player_data)
    
    return "\n".join(context_parts)


def build_gemini_prompt(game_context, rulebook_text, game_type="game"):
    """
    Build the action-packed prompt for Gemini to generate podcast script.
    
    Args:
        game_context: Comprehensive game context string
        rulebook_text: Text from rulebook (will use summary)
        game_type: Type of game ("game", "quarterfinal", "semifinal", "final")
        
    Returns:
        str: Complete prompt for Gemini
    """
    # Use rulebook summary (first 1000 chars) to reduce token usage
    rulebook_summary = rulebook_text[:1000] if rulebook_text else "Cascade is a sport with runs (3pts), throws (2pts), and kicks (1pt). Cascade zone doubles points."
    
    # Determine game stage description
    if game_type == "quarterfinal":
        stage_desc = "TOURNAMENT QUARTERFINAL"
        stakes_desc = "The stakes are incredibly high - one loss and you're out of the tournament!"
    elif game_type == "semifinal":
        stage_desc = "TOURNAMENT SEMIFINAL"
        stakes_desc = "The pressure is immense - we're one step away from the finals!"
    elif game_type == "final":
        stage_desc = "TOURNAMENT FINAL (Best of 3 Series)"
        stakes_desc = "This is it - the championship is on the line! Every game matters in this best-of-three series!"
    else:
        stage_desc = "REGULAR SEASON"
        stakes_desc = "Every game matters in the race for the playoffs!"
    
    prompt = f"""You are a world-class sports commentator writing an absolutely CRAZY, ACTION-PACKED podcast script for a {stage_desc} Cascade game.

{stakes_desc}

## STYLE REQUIREMENTS:
- Write with dramatic, high-energy sports commentary
- Create vivid, cinematic descriptions of player actions
- Build tension and excitement throughout the entire script
- Use creative metaphors and analogies
- Make the listener feel like they're watching a live, intense sporting event
- Use exclamations, dramatic pauses, and emotional language
- Describe crowd reactions, player emotions, and game atmosphere

## PLAYER INTEGRATION REQUIREMENTS (CRITICAL):
- Feature individual players BY NAME throughout the narrative
- Describe specific player actions, successes, and failures using their names
- Highlight standout performances using player names and rankings (#1-#7)
- Create dramatic moments around player attempts and completions
- Show player matchups and individual battles between players
- Use player statistics (attempts, completions, success rates) to add depth and realism
- Reference player rankings, roles (Anchor/Runner), and best stats naturally
- Make players the heroes and protagonists of the story

## NARRATIVE FREEDOM:
- You have FULL CREATIVE DISCRETION to craft an engaging story
- Create dramatic moments, comebacks, clutch plays, and emotional highs/lows
- Invent specific play-by-play action sequences
- Describe crowd reactions, player emotions, and game atmosphere
- Create narrative arcs and storylines within the game
- Build suspense and excitement throughout

## ACCURACY REQUIREMENTS (MUST BE MAINTAINED):
- The final score MUST match exactly as shown in the game context above
- The total scoring breakdown MUST match the provided statistics exactly
- All scoring plays must follow Cascade rules:
  * Runs = 3 points (6 if in Cascade zone)
  * Throws = 2 points (4 if in Cascade zone)
  * Kicks = 1 point (2 if in Cascade zone)
- Player statistics (attempts/completions) should be referenced accurately
- The game must be playable within the rules - no impossible scenarios
- All player names, rankings, and stats must be accurate

## STRUCTURE REQUIREMENTS:
- Target length: ~2250 words (15 minutes at 150 words/minute)
- Opening: Exciting introduction (200-300 words) that sets the stage and builds anticipation
- Body: Chronological game narrative with player highlights (1500-1700 words)
  * Describe the game as it unfolds
  * Feature players by name throughout
  * Build tension and excitement
  * Describe key moments and turning points
- Closing: Analysis and wrap-up (200-300 words) that reflects on the game and highlights key performances

## GAME CONTEXT:
{game_context}

## CASCADE RULES SUMMARY:
{rulebook_summary}

Now write the complete podcast script. Make it absolutely electrifying, action-packed, and feature the players prominently throughout!"""

    return prompt


def generate_game_script_with_gemini(game_result, rulebook_text, week, game_num, game_type="game"):
    """
    Generate podcast script using Gemini 2.5 Flash API.
    
    Args:
        game_result: Dictionary containing game result data
        rulebook_text: Text from rulebook
        week: Week number (or None for tournament games)
        game_num: Game number within the week
        game_type: Type of game ("game", "quarterfinal", "semifinal", "final")
        
    Returns:
        str: Generated script, or None on failure
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini API not available. Cannot generate script with Gemini.")
        return None
    
    try:
        # Load API key
        api_key = load_gemini_api_key()
        genai.configure(api_key=api_key)
        
        # Build game context
        game_context = build_game_context_for_gemini(game_result, week, game_num, game_type)
        
        # Build prompt
        prompt = build_gemini_prompt(game_context, rulebook_text, game_type)
        
        # Use Gemini 2.5 Flash model (try latest available)
        model_name = "gemini-2.0-flash-exp"
        try:
            model = genai.GenerativeModel(model_name)
        except Exception:
            # Fallback to gemini-pro if flash-exp not available
            logger.warning(f"Model {model_name} not available, trying gemini-pro")
            model_name = "gemini-pro"
            model = genai.GenerativeModel(model_name)
        
        # Generate script
        logger.info(f"Generating script with Gemini ({model_name}) for {game_type} game...")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.9,  # High creativity
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,  # Allow for ~2250 words
            }
        )
        
        script = response.text.strip()
        
        # Log word count but accept whatever Gemini gives
        word_count = len(script.split())
        logger.info(f"Generated script has {word_count} words")
        
        # Optional: If first prompt produces less than 2000 words, run a second prompt for continuation
        if word_count < 2000:
            logger.info(f"First prompt generated {word_count} words. Running second prompt to extend to up to 2600 words...")
            try:
                continuation_prompt = f"""This is a continuation of the podcast script you just wrote. The script so far has {word_count} words. 

Please continue writing from where you left off, adding more detail, action, and player highlights. Extend the script with:
- More detailed play-by-play action
- Additional player moments and individual performances
- More dramatic tension and excitement
- More crowd reactions and atmosphere
- Additional analysis and commentary

Continue seamlessly from where the previous script ended. Aim to add approximately {max(300, 2600 - word_count)} more words to bring the total closer to 2600 words, but write naturally and don't force exact word counts.

Previous script ending:
{script[-500:]}  # Last 500 characters for context

Now continue writing..."""
                
                continuation_response = model.generate_content(
                    continuation_prompt,
                    generation_config={
                        "temperature": 0.9,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 8192,
                    }
                )
                
                continuation = continuation_response.text.strip()
                continuation_word_count = len(continuation.split())
                logger.info(f"Continuation added {continuation_word_count} words")
                
                # Combine scripts with a space
                script = script + " " + continuation
                final_word_count = len(script.split())
                logger.info(f"Combined script has {final_word_count} words")
            except Exception as e:
                logger.warning(f"Error generating continuation, using original script: {e}")
                # Continue with original script if continuation fails
        
        return script
        
    except Exception as e:
        logger.warning(f"Error generating script with Gemini: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def generate_game_script(game_result, rulebook_text, week, game_num, use_gemini=True, game_type="game"):
    """
    Generate a 15-minute podcast script for a single game.
    
    Target: ~2250 words (15 minutes at 150 words per minute)
    
    Args:
        game_result: Dict with keys: team1, team2, team1_score, team2_score,
                    team1_detail, team2_detail, upset, team1_player_stats, team2_player_stats
        rulebook_text: Text from the rulebook for context
        week: Week number (or None for tournament games)
        game_num: Game number within the week
        use_gemini: Whether to use Gemini API (default: True)
        game_type: Type of game ("game", "quarterfinal", "semifinal", "final")
        
    Returns:
        str: Complete script for the game
    """
    # Try Gemini generation first if enabled
    if use_gemini and GEMINI_AVAILABLE:
        gemini_script = generate_game_script_with_gemini(game_result, rulebook_text, week, game_num, game_type)
        if gemini_script:
            return gemini_script
        else:
            logger.info("Gemini generation failed or returned invalid result, falling back to template")
    
    # Fallback to template-based generation
    team1 = game_result['team1']
    team2 = game_result['team2']
    team1_score = game_result['team1_score']
    team2_score = game_result['team2_score']
    team1_detail = game_result['team1_detail']
    team2_detail = game_result['team2_detail']
    upset = game_result.get('upset', False)
    
    # Determine winner and loser
    if team1_score > team2_score:
        winner = team1
        loser = team2
        winner_score = team1_score
        loser_score = team2_score
        winner_detail = team1_detail
        loser_detail = team2_detail
    else:
        winner = team2
        loser = team1
        winner_score = team2_score
        loser_score = team1_score
        winner_detail = team2_detail
        loser_detail = team1_detail
    
    script_parts = []
    
    # Introduction (200-300 words)
    script_parts.append(f"Welcome back to Cascade Weekly, your premier destination for all things Cascade sports. I'm your host, and we're diving into Week {week}, Game {game_num}, where {team1.name} squared off against {team2.name} in what would prove to be an absolutely thrilling contest.")
    
    script_parts.append(f"Before we get into the action, let's set the stage. {team1.name} came into this matchup with their own unique strengths and strategies, while {team2.name} brought their own game plan to the field. In Cascade, as you know, teams can score through three primary methods: runs worth three points, throws worth two points, and kicks worth one point. But the real game-changer is the Cascade zone, where any scoring play can be doubled, turning the tide in an instant.")
    
    if upset:
        script_parts.append(f"Now, here's where it gets interesting. {team2.name if winner == team2 else team1.name} entered this game as the underdog, with lower overall advantage. But as we've seen time and time again in Cascade, anything can happen on game day.")
    
    # Game narrative - build tension (800-1000 words)
    script_parts.append(f"The game kicked off with both teams showing early intensity. {team1.name} came out strong, looking to establish their dominance early. Meanwhile, {team2.name} was determined to prove they belonged on this stage.")
    
    # Describe scoring plays with creative narrative
    total_plays = team1_detail.runs + team1_detail.throws + team1_detail.kicks + \
                  team2_detail.runs + team2_detail.throws + team2_detail.kicks
    
    # Create a narrative timeline of scoring events
    scoring_events = []
    
    # Team 1 scoring events
    for i in range(team1_detail.runs):
        cascade = i < team1_detail.cascade_runs
        scoring_events.append({
            'team': team1.name,
            'type': 'run',
            'points': 6 if cascade else 3,
            'cascade': cascade,
            'time': random.uniform(0.1, 0.9)  # Random time in game (0-1)
        })
    
    for i in range(team1_detail.throws):
        cascade = i < team1_detail.cascade_throws
        scoring_events.append({
            'team': team1.name,
            'type': 'throw',
            'points': 4 if cascade else 2,
            'cascade': cascade,
            'time': random.uniform(0.1, 0.9)
        })
    
    for i in range(team1_detail.kicks):
        cascade = i < team1_detail.cascade_kicks
        scoring_events.append({
            'team': team1.name,
            'type': 'kick',
            'points': 2 if cascade else 1,
            'cascade': cascade,
            'time': random.uniform(0.1, 0.9)
        })
    
    # Team 2 scoring events
    for i in range(team2_detail.runs):
        cascade = i < team2_detail.cascade_runs
        scoring_events.append({
            'team': team2.name,
            'type': 'run',
            'points': 6 if cascade else 3,
            'cascade': cascade,
            'time': random.uniform(0.1, 0.9)
        })
    
    for i in range(team2_detail.throws):
        cascade = i < team2_detail.cascade_throws
        scoring_events.append({
            'team': team2.name,
            'type': 'throw',
            'points': 4 if cascade else 2,
            'cascade': cascade,
            'time': random.uniform(0.1, 0.9)
        })
    
    for i in range(team2_detail.kicks):
        cascade = i < team2_detail.cascade_kicks
        scoring_events.append({
            'team': team2.name,
            'type': 'kick',
            'points': 2 if cascade else 1,
            'cascade': cascade,
            'time': random.uniform(0.1, 0.9)
        })
    
    # Sort by time
    scoring_events.sort(key=lambda x: x['time'])
    
    # Build narrative from scoring events
    current_score_team1 = 0
    current_score_team2 = 0
    mid_game_tension = False
    
    for i, event in enumerate(scoring_events):
        team_name = event['team']
        score_type = event['type']
        points = event['points']
        cascade = event['cascade']
        is_team1 = (team_name == team1.name)
        
        if is_team1:
            current_score_team1 += points
        else:
            current_score_team2 += points
        
        # Describe the play
        time_desc = "early" if event['time'] < 0.3 else "mid-game" if event['time'] < 0.7 else "late in the game"
        
        cascade_desc = ""
        if cascade:
            cascade_desc = " And here's the moment that changed everything - they hit the Cascade zone! The crowd erupts as the points double!"
        
        action_desc = {
            'run': f"a powerful run through the defense",
            'throw': f"a precision throw that finds its mark",
            'kick': f"a perfectly executed kick"
        }[score_type]
        
        script_parts.append(f"At the {time_desc} mark, {team_name} executes {action_desc}, putting {points} points on the board.{cascade_desc} The score now stands at {team1.name} {current_score_team1}, {team2.name} {current_score_team2}.")
        
        # Add tension if scores are close
        if abs(current_score_team1 - current_score_team2) <= 3 and not mid_game_tension:
            script_parts.append(f"This is turning into a nail-biter! Both teams are trading blows, and neither is willing to back down. The intensity on the field is palpable.")
            mid_game_tension = True
    
    # Climax and conclusion (600-800 words)
    script_parts.append(f"As we entered the final moments of the game, the tension was at its peak. {team1.name} had {team1_score} points on the board, while {team2.name} had {team2_score}. Every play mattered, every point crucial.")
    
    # Highlight key statistics
    if winner_detail.cascade_runs > 0 or winner_detail.cascade_throws > 0 or winner_detail.cascade_kicks > 0:
        cascade_count = winner_detail.cascade_runs + winner_detail.cascade_throws + winner_detail.cascade_kicks
        script_parts.append(f"{winner.name} really made the Cascade zone their friend today, hitting it {cascade_count} time{'s' if cascade_count > 1 else ''}, which proved to be a massive difference-maker in this contest.")
    
    # Breakdown of scoring
    script_parts.append(f"Let's break down the scoring. {team1.name} finished with {team1_detail.runs} run{'s' if team1_detail.runs != 1 else ''}, {team1_detail.throws} throw{'s' if team1_detail.throws != 1 else ''}, and {team1_detail.kicks} kick{'s' if team1_detail.kicks != 1 else ''}. {team2.name} countered with {team2_detail.runs} run{'s' if team2_detail.runs != 1 else ''}, {team2_detail.throws} throw{'s' if team2_detail.throws != 1 else ''}, and {team2_detail.kicks} kick{'s' if team2_detail.kicks != 1 else ''}.")
    
    # Final score announcement
    if upset:
        script_parts.append(f"In what can only be described as a stunning upset, {winner.name} has pulled off the victory! They came in as the underdog but proved that in Cascade, heart and determination can overcome any advantage. The final score: {team1.name} {team1_score}, {team2.name} {team2_score}.")
    else:
        script_parts.append(f"When the final whistle blew, {winner.name} emerged victorious with a final score of {team1.name} {team1_score} to {team2.name}'s {team2_score}. It was a hard-fought battle, and both teams left everything on the field.")
    
    # Closing thoughts (200-300 words)
    script_parts.append(f"This game was a perfect example of what makes Cascade so special. The combination of strategy, skill, and those game-changing Cascade zone moments creates an experience unlike any other. {winner.name} showed why they're a force to be reckoned with, while {loser.name} demonstrated incredible resilience and fight.")
    
    script_parts.append(f"That wraps up our coverage of Week {week}, Game {game_num}. Join us next as we continue to break down all the action from this week's slate of Cascade games. Until then, keep chasing those Cascade zones!")
    
    # Combine all parts
    full_script = " ".join(script_parts)
    
    # Ensure we're close to target word count (2250 words)
    word_count = len(full_script.split())
    if word_count < 2000:
        # Add more detail if too short
        script_parts.append(f"One thing that really stood out in this matchup was the strategic depth. Both teams had to constantly adapt their approach based on the flow of the game. The way {team1.name} utilized their {team1.best_stat().lower()} advantage was particularly noteworthy, while {team2.name} showed their versatility across all three scoring methods.")
        full_script = " ".join(script_parts)
    elif word_count > 2500:
        # Trim if too long (unlikely but possible)
        words = full_script.split()
        full_script = " ".join(words[:2250])
    
    return full_script


def generate_week_podcast_script(game_results_by_week, week, rulebook_text, use_gemini=True):
    """
    Generate complete podcast script for a week (4 games).
    
    Args:
        game_results_by_week: Dict mapping week numbers to lists of (filename, game_result) tuples
        week: Week number
        rulebook_text: Text from the rulebook
        use_gemini: Whether to use Gemini API for script generation (default: True)
        
    Returns:
        tuple: (combined_script, individual_scripts_dict)
               where individual_scripts_dict maps game_num to script text
    """
    if week not in game_results_by_week:
        logger.warning(f"No game results found for week {week}")
        return "", {}
    
    week_games = game_results_by_week[week]
    individual_scripts = {}
    combined_parts = []
    
    # Filter out gemini images first to count actual games
    actual_games = []
    for item in week_games:
        if isinstance(item, tuple):
            filename, game_result = item
            if "_gemini" not in filename:
                actual_games.append((filename, game_result))
        else:
            actual_games.append(item)
    
    num_games = len(actual_games)
    if num_games == 0:
        logger.warning(f"No valid games found for week {week}")
        return "", {}
    
    # Podcast intro (150-200 words)
    game_word = "game" if num_games == 1 else "games"
    combined_parts.append(f"Welcome to Cascade Weekly, your comprehensive guide to all the action from Week {week} of Cascade competition. I'm your host, and we've got {num_games} incredible {game_word} to break down for you today. From stunning upsets to dominant performances, this week had it all. So grab your headphones, settle in, and let's dive into the excitement.")
    combined_parts.append("")
    
    # Generate script for each game
    game_num = 1
    for item in actual_games:
        # Extract game_result (already filtered)
        if isinstance(item, tuple):
            filename, game_result = item
        else:
            game_result = item
        
        logger.info(f"Generating script for Week {week}, Game {game_num}...")
        game_script = generate_game_script(game_result, rulebook_text, week, game_num, use_gemini=use_gemini)
        individual_scripts[game_num] = game_script
        
        # Add game intro
        combined_parts.append(f"=== GAME {game_num} ===")
        combined_parts.append("")
        combined_parts.append(game_script)
        combined_parts.append("")
        combined_parts.append("---")
        combined_parts.append("")
        
        game_num += 1
    
    # Podcast outro (100-150 words)
    combined_parts.append(f"And that's a wrap on Week {week}! {num_games} {game_word}, countless moments of brilliance, and memories that will last. We've seen everything from clutch Cascade zone plays to incredible comebacks. The beauty of Cascade is that every week brings something new, something unexpected.")
    combined_parts.append(f"Thank you for joining us on this journey through Week {week}. Make sure to tune in next week as we continue to bring you all the action, analysis, and excitement from the world of Cascade. Until then, keep your eyes on those Cascade zones, and may the best team win!")
    combined_parts.append("This has been Cascade Weekly. See you next time!")
    
    combined_script = "\n".join(combined_parts)
    
    return combined_script, individual_scripts

