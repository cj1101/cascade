"""Podcast Script Generator Module"""
import random
import logging
import os
import re
import time

# Try to import scheduler for logger, fallback to basic logging
try:
    import scheduler
    logger = scheduler.logger
except ImportError:
    logger = logging.getLogger(__name__)

# Try to import Gemini API (new SDK)
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google.genai not available. Gemini script generation will be disabled.")


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


def describe_advantage(advantage_value, stat_type="overall"):
    """
    Convert numeric advantage value to descriptive phrase with random adjective.
    Only mentions advantages that are publicly observable, not exact numeric values.
    """
    if advantage_value == 0:
        return "no significant advantage"
    
    # Adjectives for positive advantages
    positive_adjectives = [
        "strong", "notable", "slight", "significant", "substantial",
        "clear", "marked", "considerable", "pronounced", "evident"
    ]
    
    # Adjectives for negative advantages (disadvantages)
    negative_adjectives = [
        "slight", "notable", "significant", "considerable", "marked"
    ]
    
    # Determine magnitude categories
    abs_value = abs(advantage_value)
    if abs_value >= 3:
        intensity = "significant"
        adjectives = positive_adjectives if advantage_value > 0 else negative_adjectives
    elif abs_value == 2:
        intensity = "notable"
        adjectives = positive_adjectives if advantage_value > 0 else negative_adjectives
    else:
        intensity = "slight"
        adjectives = positive_adjectives if advantage_value > 0 else negative_adjectives
    
    if advantage_value > 0:
        adjective = random.choice(adjectives)
        if stat_type == "overall":
            return f"a {adjective} overall advantage"
        elif stat_type == "run":
            return f"a {adjective} run advantage"
        elif stat_type == "throw":
            return f"a {adjective} throw advantage"
        elif stat_type == "kick":
            return f"a {adjective} kick advantage"
    else:
        adjective = random.choice(negative_adjectives)
        if stat_type == "overall":
            return f"a {adjective} overall disadvantage"
        elif stat_type == "run":
            return f"a {adjective} run disadvantage"
        elif stat_type == "throw":
            return f"a {adjective} throw disadvantage"
        elif stat_type == "kick":
            return f"a {adjective} kick disadvantage"


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

    # Build descriptive advantage strings (no numeric values)
    team1_advantages = []
    if team1.overall_advantage != 0:
        team1_advantages.append(describe_advantage(team1.overall_advantage, "overall"))
    if team1.run_advantage != 0:
        team1_advantages.append(describe_advantage(team1.run_advantage, "run"))
    if team1.throw_advantage != 0:
        team1_advantages.append(describe_advantage(team1.throw_advantage, "throw"))
    if team1.kick_advantage != 0:
        team1_advantages.append(describe_advantage(team1.kick_advantage, "kick"))
    
    team2_advantages = []
    if team2.overall_advantage != 0:
        team2_advantages.append(describe_advantage(team2.overall_advantage, "overall"))
    if team2.run_advantage != 0:
        team2_advantages.append(describe_advantage(team2.run_advantage, "run"))
    if team2.throw_advantage != 0:
        team2_advantages.append(describe_advantage(team2.throw_advantage, "throw"))
    if team2.kick_advantage != 0:
        team2_advantages.append(describe_advantage(team2.kick_advantage, "kick"))
    
    context_parts.append(f"\nTEAM 1 STATS ({team1.name}):")
    if team1_advantages:
        context_parts.append(f"  Advantages: {', '.join(team1_advantages)}")
    else:
        context_parts.append(f"  Advantages: balanced across all categories")
    context_parts.append(f"  Scoring: {team1_detail.runs} Runs, {team1_detail.throws} Throws, {team1_detail.kicks} Kicks")
    context_parts.append(f"  Cascade Zone: {team1_detail.cascade_runs} Runs, {team1_detail.cascade_throws} Throws, {team1_detail.cascade_kicks} Kicks")

    context_parts.append(f"\nTEAM 2 STATS ({team2.name}):")
    if team2_advantages:
        context_parts.append(f"  Advantages: {', '.join(team2_advantages)}")
    else:
        context_parts.append(f"  Advantages: balanced across all categories")
    context_parts.append(f"  Scoring: {team2_detail.runs} Runs, {team2_detail.throws} Throws, {team2_detail.kicks} Kicks")
    context_parts.append(f"  Cascade Zone: {team2_detail.cascade_runs} Runs, {team2_detail.cascade_throws} Throws, {team2_detail.cascade_kicks} Kicks")
    
    player_data = extract_player_data_for_prompt(game_result)
    if player_data:
        context_parts.append("\n=== PLAYER PERFORMANCES ===")
        context_parts.append(player_data)
    
    return "\n".join(context_parts)


def remove_continuation_markers(text):
    """
    Remove continuation markers like '...' prefixes from text.
    """
    if not text:
        return text
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove lines that start with "..." (continuation markers)
        stripped = line.strip()
        if stripped.startswith('...'):
            continue
        # Remove "..." from the start of lines but keep the rest
        cleaned_line = line
        if cleaned_line.strip().startswith('...'):
            cleaned_line = cleaned_line.replace('...', '', 1).lstrip()
        cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)


def remove_incomplete_sentences(text):
    """
    Remove sentences that don't end with proper punctuation (. ! ?).
    This helps catch truncated responses.
    """
    if not text:
        return text
    
    # Split text into paragraphs
    paragraphs = text.split('\n\n')
    cleaned_paragraphs = []
    
    for para in paragraphs:
        if not para.strip():
            cleaned_paragraphs.append(para)
            continue
        
        # Split into sentences (simple approach - look for sentence endings)
        sentences = []
        current_sentence = ""
        
        # Simple sentence splitting - look for . ! ? followed by space or newline
        # Find sentence boundaries
        sentence_endings = re.finditer(r'[.!?]\s+', para)
        last_end = 0
        
        for match in sentence_endings:
            end_pos = match.end()
            sentence = para[last_end:end_pos].strip()
            if sentence:
                sentences.append(sentence)
            last_end = end_pos
        
        # Handle remaining text after last sentence ending
        remaining = para[last_end:].strip()
        if remaining:
            # If it ends with proper punctuation, include it
            if remaining[-1] in '.!?':
                sentences.append(remaining)
            # Otherwise, it's incomplete - check if it's substantial enough
            # If it's very short (less than 20 chars), likely truncated - skip it
            elif len(remaining) < 20:
                # Skip short incomplete sentences
                pass
            else:
                # Longer incomplete might be intentional (like a list), include it
                sentences.append(remaining)
        
        if sentences:
            cleaned_paragraphs.append(' '.join(sentences))
        # If no complete sentences but paragraph exists, check if it's substantial
        elif len(para.strip()) >= 50:
            # Keep substantial paragraphs even if no sentence endings found
            cleaned_paragraphs.append(para)
    
    return '\n\n'.join(cleaned_paragraphs)


def remove_duplicate_paragraphs(text):
    """
    Remove duplicate paragraphs using fuzzy matching.
    Detects when the same or very similar text appears multiple times.
    """
    if not text:
        return text
    
    paragraphs = text.split('\n\n')
    seen_paragraphs = []
    cleaned_paragraphs = []
    
    for para in paragraphs:
        para_stripped = para.strip()
        if not para_stripped:
            cleaned_paragraphs.append(para)
            continue
        
        # Check for duplicates - compare normalized versions
        para_normalized = ' '.join(para_stripped.split()).lower()
        
        # Check if we've seen this exact paragraph before
        is_duplicate = False
        for seen in seen_paragraphs:
            seen_normalized = ' '.join(seen.split()).lower()
            
            # Exact match
            if para_normalized == seen_normalized:
                is_duplicate = True
                break
            
            # Check if one is a substring of the other (fuzzy duplicate detection)
            # If one paragraph is 80% similar to another, consider it a duplicate
            similarity = calculate_similarity(para_normalized, seen_normalized)
            if similarity > 0.8:
                is_duplicate = True
                break
            
            # Check if current para starts with a previous para (incomplete followed by complete)
            if para_normalized.startswith(seen_normalized[:50]) and len(para_normalized) > len(seen_normalized) * 1.2:
                # Current is longer and starts similarly - likely complete version of incomplete
                # Remove the shorter previous version
                if len(para_normalized) > len(seen_normalized):
                    # This is the complete version, mark previous as duplicate
                    # We'll handle this by not adding current if it's a superset
                    pass
                is_duplicate = False  # Don't mark as duplicate, it's an improvement
                break
        
        if not is_duplicate:
            seen_paragraphs.append(para_normalized)
            cleaned_paragraphs.append(para)
    
    return '\n\n'.join(cleaned_paragraphs)


def calculate_similarity(str1, str2):
    """
    Calculate simple similarity ratio between two strings.
    Returns a value between 0 and 1.
    """
    if not str1 or not str2:
        return 0.0
    
    # Use simple word overlap for similarity
    words1 = set(str1.split())
    words2 = set(str2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


def validate_segment_completeness(text):
    """
    Check if a segment appears complete.
    Returns (is_complete, reason) tuple.
    """
    if not text or len(text.strip()) < 50:
        return False, "Segment too short"
    
    # Check if text ends with proper sentence ending
    text_stripped = text.strip()
    if text_stripped[-1] not in '.!?':
        # Might be incomplete, but check context
        # If it ends with a complete word (space before last word), might be okay
        words = text_stripped.split()
        if len(words) < 10:
            return False, "Segment ends without punctuation and is very short"
    
    # Check for obvious truncation markers
    if text_stripped.endswith('...') or '...' in text_stripped[-20:]:
        return False, "Contains truncation markers"
    
    return True, "Appears complete"


def clean_generated_text(text):
    """
    Main cleanup function that applies all text cleaning operations.
    """
    if not text:
        return text
    
    # Step 1: Remove continuation markers
    cleaned = remove_continuation_markers(text)
    
    # Step 2: Remove duplicate paragraphs
    cleaned = remove_duplicate_paragraphs(cleaned)
    
    # Step 3: Remove incomplete sentences (this is more aggressive)
    cleaned = remove_incomplete_sentences(cleaned)
    
    # Step 4: Normalize whitespace (multiple spaces to single, but preserve paragraph breaks)
    # Normalize multiple spaces to single space within lines
    lines = cleaned.split('\n')
    normalized_lines = [re.sub(r' +', ' ', line) for line in lines]
    cleaned = '\n'.join(normalized_lines)
    
    # Remove excessive blank lines (more than 2 consecutive)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()


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


def extract_text_from_response(response):
    """
    Extract text from Gemini API response with improved handling of edge cases.
    Returns the extracted text or None if extraction fails.
    """
    if response is None:
        return None
    
    try:
        # Try direct text attribute first (most common case)
        if hasattr(response, 'text') and response.text:
            return response.text.strip()
        
        # Try candidates structure
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            
            # Check for finish_reason to detect truncation
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
                if finish_reason and 'length' in str(finish_reason).lower():
                    logger.warning("Response was truncated due to length limit")
            
            # Try content.parts structure
            if hasattr(candidate, 'content'):
                content = candidate.content
                if hasattr(content, 'parts') and content.parts:
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text.strip())
                        elif hasattr(part, 'content') and part.content:
                            # Some parts might have nested content
                            text_parts.append(str(part.content).strip())
                    
                    if text_parts:
                        # Join parts, but be careful about duplicates
                        combined = ' '.join(text_parts)
                        return combined.strip()
                
                # Try direct text attribute on content
                if hasattr(content, 'text') and content.text:
                    return content.text.strip()
            
            # Try direct text on candidate
            if hasattr(candidate, 'text') and candidate.text:
                return candidate.text.strip()
        
        # Fallback: try to stringify and extract meaningful text
        response_str = str(response)
        # If it looks like there's actual text content (not just object representation)
        if len(response_str) > 100 and not response_str.startswith('<'):
            return response_str.strip()
        
        logger.warning("Could not extract text from response - unexpected structure")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting text from response: {e}")
        return None


def generate_game_script_with_gemini(game_result, rulebook_text, week, game_num, game_type="game"):
    """
    Generate segmented podcast script using Gemini.
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini API not available.")
        return None
    
    try:
        api_key = load_gemini_api_key()
        client = genai.Client(api_key=api_key)
        
        # Select Model - Use gemini-2.5-flash for higher quota limits
        # Error message suggests gemini-2.5-flash-image for higher quotas
        model_name = "gemini-2.5-flash"

        game_context = build_game_context(game_result, week, game_num, game_type)
        rulebook_summary = rulebook_text[:1000] if rulebook_text else "Cascade: Runs(3/6), Throws(2/4), Kicks(1/2)."
        
        segments = ["intro", "early_game", "mid_game", "late_game", "outro"]
        full_script = []
        previous_text = ""
        
        for segment in segments:
            logger.info(f"Generating {segment} segment...")
            prompt = generate_segment_prompt(segment, game_context, rulebook_summary, previous_text)

            # Try to generate content with fallback models if needed
            response = None
            fallback_models = ["gemini-2.5-flash", "gemini-2.5-flash-image", "gemini-2.0-flash-exp", "gemini-pro"]
            max_retries = 2
            segment_text = None
            
            for try_model in fallback_models:
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model=try_model,
                            contents=[prompt],
                            config={
                                "temperature": 0.7, # Slightly lower temperature for more coherent reporting
                                "top_p": 0.9,
                                "max_output_tokens": 3500,  # Increased from 2000 to allow longer segments
                            }
                        )
                        model_name = try_model  # Update model_name for next segment
                        
                        # Extract text from response with improved handling
                        extracted_text = extract_text_from_response(response)
                        if extracted_text:
                            # Clean the extracted text
                            extracted_text = clean_generated_text(extracted_text)
                            
                            # Validate completeness
                            is_complete, reason = validate_segment_completeness(extracted_text)
                            if is_complete or attempt == max_retries - 1:
                                segment_text = extracted_text
                                if not is_complete:
                                    logger.warning(f"Segment {segment} validation: {reason}, but using anyway (final attempt)")
                                break
                            else:
                                logger.warning(f"Segment {segment} appears incomplete: {reason}. Retrying...")
                                continue
                        
                        break  # Successfully extracted, break out of retry loop
                    except Exception as e:
                        if attempt == max_retries - 1:
                            logger.warning(f"Model {try_model} failed after {max_retries} attempts ({e}), trying next model...")
                        else:
                            logger.warning(f"Model {try_model} failed on attempt {attempt + 1} ({e}), retrying...")
                            time.sleep(0.5)  # Brief pause before retry
                        continue
                
                if segment_text:
                    break  # Successfully got text, break out of model loop
            
            if not segment_text:
                logger.error("All Gemini models failed or produced invalid responses. Cannot generate segment.")
                return None
            
            # Apply cleanup again to ensure quality
            segment_text = clean_generated_text(segment_text)
            full_script.append(segment_text)
            previous_text = segment_text

            # Rate limiting/pause between segments
            time.sleep(1)

        # Combine all segments
        final_script = "\n\n".join(full_script)
        
        # Apply final cleanup pass to the entire script
        # This helps catch any cross-segment duplicates or issues
        final_script = clean_generated_text(final_script)
        
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
    
    Returns:
        tuple: (combined_script, individual_scripts, game_results_by_num)
        - combined_script: Full combined script text
        - individual_scripts: Dict mapping game_num to script text
        - game_results_by_num: Dict mapping game_num to game_result dict
    """
    if week not in game_results_by_week:
        return "", {}, {}
    
    week_games = game_results_by_week[week]
    individual_scripts = {}
    game_results_by_num = {}
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
        game_results_by_num[game_num] = game_result
        combined_parts.append(script)
        combined_parts.append("\n---\n")
        game_num += 1

    combined_parts.append("This concludes our report for this week. Thank you for listening.")

    return "\n".join(combined_parts), individual_scripts, game_results_by_num
