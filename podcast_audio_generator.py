"""Podcast Audio Generator Module"""
import os
import logging
import time

# Try to import scheduler for logger, fallback to basic logging
try:
    import scheduler
    logger = scheduler.logger
except ImportError:
    logger = logging.getLogger(__name__)

# Try to import TTS and audio libraries
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.error("gTTS not available. Install gtts to generate audio.")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not available. Install pydub to combine audio files.")


# gTTS has a character limit per request (around 5000 characters)
GTTS_CHUNK_SIZE = 4500  # Safe limit with some buffer

# Rate limiting constants
MIN_DELAY_BETWEEN_CHUNKS = 2.0  # Minimum delay between chunks (seconds)
MIN_DELAY_BETWEEN_GAMES = 3.0  # Minimum delay between games (seconds)
MAX_RETRIES = 5  # Maximum retries for rate-limited requests
INITIAL_RETRY_DELAY = 10  # Initial retry delay for 429 errors (seconds)


def chunk_text_for_tts(text):
    """
    Split text into chunks that are safe for gTTS.
    
    Args:
        text: Text to chunk
        
    Returns:
        list: List of text chunks
    """
    if len(text) <= GTTS_CHUNK_SIZE:
        return [text]
    
    chunks = []
    words = text.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        if current_length + word_length > GTTS_CHUNK_SIZE and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


def generate_tts_chunk_with_retry(chunk_text, output_filename, lang='en', slow=False):
    """
    Generate TTS audio for a single chunk with retry logic for rate limiting.
    
    Args:
        chunk_text: Text to convert to speech
        output_filename: Path to output MP3 file
        lang: Language code (default: 'en')
        slow: Whether to speak slowly (default: False)
        
    Returns:
        bool: True if successful, False otherwise
    """
    for attempt in range(MAX_RETRIES):
        try:
            tts = gTTS(text=chunk_text, lang=lang, slow=slow)
            tts.save(output_filename)
            return True
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            
            # Check if it's a rate limit error (429)
            # gTTS may raise HTTPError or include 429 in the error message
            is_rate_limit = (
                '429' in error_str or 
                'Too Many Requests' in error_str or 
                'rate limit' in error_str.lower() or
                error_type == 'HTTPError' and '429' in error_str
            )
            
            # Also check for HTTP status code 429 in response objects
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                is_rate_limit = is_rate_limit or e.response.status_code == 429
            
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                # Exponential backoff: wait longer for each retry
                retry_delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}). Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                continue
            else:
                # Log the error and re-raise if it's not a rate limit or we've exhausted retries
                if is_rate_limit:
                    logger.error(f"Rate limit error after {MAX_RETRIES} attempts: {e}")
                else:
                    logger.error(f"Error generating TTS chunk: {e}")
                # Only raise on last attempt or non-rate-limit errors
                if attempt == MAX_RETRIES - 1 or not is_rate_limit:
                    raise
    
    return False


def generate_audio_from_script(script_text, output_filename, lang='en', slow=False):
    """
    Generate audio file from script text using gTTS with rate limiting protection.
    
    Args:
        script_text: Text to convert to speech
        output_filename: Path to output MP3 file
        lang: Language code (default: 'en')
        slow: Whether to speak slowly (default: False)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not GTTS_AVAILABLE:
        logger.error("gTTS not available. Cannot generate audio.")
        return False
    
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Split text into chunks
        chunks = chunk_text_for_tts(script_text)
        logger.info(f"Split script into {len(chunks)} chunks for TTS processing")
        
        if len(chunks) == 1:
            # Single chunk - simple case with retry logic
            if generate_tts_chunk_with_retry(chunks[0], output_filename, lang, slow):
                logger.info(f"Generated audio file: {output_filename}")
                return True
            else:
                logger.error(f"Failed to generate audio file after retries: {output_filename}")
                return False
        else:
            # Multiple chunks - need to combine
            temp_files = []
            try:
                for i, chunk in enumerate(chunks):
                    temp_filename = output_filename.replace('.mp3', f'_chunk_{i}.mp3')
                    
                    # Generate chunk with retry logic
                    if not generate_tts_chunk_with_retry(chunk, temp_filename, lang, slow):
                        logger.error(f"Failed to generate chunk {i+1}/{len(chunks)} after retries")
                        # Clean up temp files on error
                        for temp_file in temp_files:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        return False
                    
                    temp_files.append(temp_filename)
                    logger.info(f"Generated chunk {i+1}/{len(chunks)}")
                    
                    # Delay between chunks to avoid rate limiting (except after last chunk)
                    if i < len(chunks) - 1:
                        time.sleep(MIN_DELAY_BETWEEN_CHUNKS)
                
                # Combine chunks
                if PYDUB_AVAILABLE:
                    combined = AudioSegment.empty()
                    for temp_file in temp_files:
                        audio = AudioSegment.from_mp3(temp_file)
                        combined += audio
                        # Add brief pause between chunks
                        combined += AudioSegment.silent(duration=500)  # 500ms pause
                    
                    combined.export(output_filename, format="mp3")
                    logger.info(f"Combined {len(chunks)} chunks into: {output_filename}")
                else:
                    # Fallback: just use first chunk (not ideal but better than nothing)
                    logger.warning("pydub not available. Using first chunk only.")
                    if temp_files:
                        os.rename(temp_files[0], output_filename)
                
                # Clean up temp files
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                
                return True
                
            except Exception as e:
                logger.error(f"Error combining audio chunks: {e}")
                # Clean up temp files on error
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                return False
        
    except Exception as e:
        logger.error(f"Error generating audio from script: {e}")
        return False


def combine_audio_files(audio_files, output_filename, transition_duration_ms=1000):
    """
    Combine multiple audio files into a single podcast file.
    
    Args:
        audio_files: List of paths to audio files to combine
        output_filename: Path to output combined MP3 file
        transition_duration_ms: Duration of silence between files in milliseconds
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not PYDUB_AVAILABLE:
        logger.error("pydub not available. Cannot combine audio files.")
        return False
    
    if not audio_files:
        logger.error("No audio files provided to combine.")
        return False
    
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        combined = AudioSegment.empty()
        
        for i, audio_file in enumerate(audio_files):
            if not os.path.exists(audio_file):
                logger.warning(f"Audio file not found: {audio_file}. Skipping...")
                continue
            
            logger.info(f"Adding audio file {i+1}/{len(audio_files)}: {audio_file}")
            audio = AudioSegment.from_mp3(audio_file)
            combined += audio
            
            # Add transition (except after last file)
            if i < len(audio_files) - 1:
                combined += AudioSegment.silent(duration=transition_duration_ms)
        
        combined.export(output_filename, format="mp3")
        logger.info(f"Successfully combined {len(audio_files)} audio files into: {output_filename}")
        
        # Log final duration
        duration_seconds = len(combined) / 1000.0
        duration_minutes = duration_seconds / 60.0
        logger.info(f"Final podcast duration: {duration_minutes:.1f} minutes ({duration_seconds:.0f} seconds)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error combining audio files: {e}")
        return False


def generate_week_podcast(game_results_by_week, week, rulebook_text, output_dir="podcasts"):
    """
    Complete workflow: Generate scripts, convert to audio, combine into podcast.
    
    Args:
        game_results_by_week: Dict mapping week numbers to game results
        week: Week number
        rulebook_text: Text from rulebook
        output_dir: Directory to save podcast files
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Import script generator
        import podcast_script_generator as script_gen
        
        # Generate scripts
        logger.info(f"Generating podcast scripts for Week {week}...")
        combined_script, individual_scripts = script_gen.generate_week_podcast_script(
            game_results_by_week, week, rulebook_text
        )
        
        if not combined_script:
            logger.error(f"Failed to generate scripts for Week {week}")
            return False
        
        # Save combined script
        script_filename = os.path.join(output_dir, f"week_{week}_script.txt")
        os.makedirs(output_dir, exist_ok=True)
        with open(script_filename, 'w', encoding='utf-8') as f:
            f.write(combined_script)
        logger.info(f"Saved script to: {script_filename}")
        
        # Generate audio for each game
        game_audio_files = []
        for game_num, game_script in individual_scripts.items():
            game_audio_filename = os.path.join(output_dir, f"week_{week}_game_{game_num}.mp3")
            logger.info(f"Generating audio for Week {week}, Game {game_num}...")
            
            if generate_audio_from_script(game_script, game_audio_filename):
                game_audio_files.append(game_audio_filename)
                logger.info(f"Generated audio: {game_audio_filename}")
            else:
                logger.error(f"Failed to generate audio for Game {game_num}")
                return False
            
            # Delay between games to avoid rate limiting
            time.sleep(MIN_DELAY_BETWEEN_GAMES)
        
        # Combine all game audio files into final podcast
        if game_audio_files:
            podcast_filename = os.path.join(output_dir, f"week_{week}_podcast.mp3")
            logger.info(f"Combining {len(game_audio_files)} game audio files into podcast...")
            
            if combine_audio_files(game_audio_files, podcast_filename):
                logger.info(f"Successfully generated podcast: {podcast_filename}")
                
                # Try to upload all podcast files to Google Drive (non-blocking)
                try:
                    import podcast_drive_uploader
                    # Upload all files: individual game files + combined podcast
                    upload_success = podcast_drive_uploader.upload_all_podcast_files(week, output_dir)
                    if upload_success:
                        logger.info(f"Successfully uploaded all Week {week} podcast files to Google Drive (Cascade Podcast Folder)")
                    else:
                        logger.warning(f"Google Drive upload failed for Week {week}, but podcast was generated successfully")
                except ImportError:
                    logger.info("Google Drive uploader not available, skipping upload")
                except Exception as e:
                    logger.warning(f"Error during Google Drive upload: {e}. Podcast was generated successfully.")
                
                return True
            else:
                logger.error(f"Failed to combine audio files for Week {week}")
                return False
        else:
            logger.error("No audio files generated to combine")
            return False
            
    except Exception as e:
        logger.error(f"Error generating week podcast: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


