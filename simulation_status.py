"""Simulation status management for coordinating between simulation and webapp"""
import logging
from datetime import datetime, timedelta, timezone
from webapp.app import app, db, init_db
from webapp.database import SimulationStatus
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)

def migrate_simulation_status_table():
    """Add missing columns to simulation_status table if they don't exist"""
    with app.app_context():
        try:
            # Check what columns exist
            inspector = inspect(db.engine)
            try:
                columns = [col['name'] for col in inspector.get_columns('simulation_status')]
            except Exception as table_error:
                # Table doesn't exist, init_db will create it
                logger.info("Table doesn't exist, will be created by init_db")
                return False
            
            # Columns that should exist based on model
            required_columns = {
                'current_phase': 'INTEGER',
                'games_completed': 'INTEGER DEFAULT 0',
                'total_games': 'INTEGER',
                'phase_start_time': 'DATETIME',
                'simulation_start_time': 'DATETIME'
            }
            
            missing_columns = {col: sql_type for col, sql_type in required_columns.items() if col not in columns}
            
            if missing_columns:
                logger.info(f"Adding missing columns to simulation_status: {list(missing_columns.keys())}")
                for col_name, col_def in missing_columns.items():
                    try:
                        # SQLite doesn't support ADD COLUMN IF NOT EXISTS, but we checked above
                        db.session.execute(text(f"ALTER TABLE simulation_status ADD COLUMN {col_name} {col_def}"))
                    except Exception as e:
                        logger.warning(f"Error adding column {col_name}: {e}")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            # If table doesn't exist, init_db will create it with all columns
            if "no such table" in str(e).lower():
                logger.info("Table doesn't exist, will be created by init_db")
                return False
            raise

def ensure_status_exists():
    """Ensure a SimulationStatus record exists (singleton pattern)"""
    with app.app_context():
        try:
            status = SimulationStatus.query.first()
        except Exception as e:
            # Check if it's a missing column issue
            if "no such column" in str(e).lower():
                logger.warning("SimulationStatus table missing columns, running migration...")
                migrate_simulation_status_table()
                # Retry query after migration
                status = SimulationStatus.query.first()
            # If table doesn't exist, initialize database
            elif "no such table" in str(e).lower() or "operationalerror" in str(type(e).__name__).lower():
                logger.warning("SimulationStatus table not found, initializing database...")
                init_db()
                # Retry query after initialization
                status = SimulationStatus.query.first()
            else:
                raise
        if not status:
            status = SimulationStatus(
                is_running=False,
                current_week=0,
                next_simulation_time=None,
                status_message='',
                current_phase=None,
                games_completed=0,
                total_games=None,
                phase_start_time=None,
                simulation_start_time=None
            )
            db.session.add(status)
            db.session.commit()
            logger.info("Created initial SimulationStatus record")
        return status

def set_running(week, message=None, total_games=None):
    """
    Set simulation status to running for a specific week.
    
    Args:
        week: Week number being processed
        message: Optional custom status message
        total_games: Optional total number of games for this week
    """
    ensure_status_exists()
    with app.app_context():
        status = SimulationStatus.query.first()
        if status:
            status.is_running = True
            status.current_week = week
            if message:
                status.status_message = message
            else:
                status.status_message = f"Week {week} results are being posted... come back soon!"
            status.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            # Initialize progress tracking
            status.simulation_start_time = datetime.now(timezone.utc).replace(tzinfo=None)
            status.current_phase = 1
            status.games_completed = 0
            if total_games is not None:
                status.total_games = total_games
            status.phase_start_time = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
            logger.info(f"Simulation status set to running: Week {week}")

def set_waiting(next_time, week=None):
    """
    Set simulation status to waiting with next simulation time.
    
    Args:
        next_time: datetime object for when next simulation will start
        week: Optional week number (last completed week)
    """
    ensure_status_exists()
    with app.app_context():
        status = SimulationStatus.query.first()
        if status:
            status.is_running = False
            if week is not None:
                status.current_week = week
            status.next_simulation_time = next_time
            status.status_message = ''
            # Reset progress tracking
            status.current_phase = None
            status.games_completed = 0
            status.total_games = None
            status.phase_start_time = None
            status.simulation_start_time = None
            status.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
            logger.info(f"Simulation status set to waiting: Next simulation at {next_time}")

def update_progress(phase, games_completed=None, total_games=None):
    """
    Update simulation progress tracking.
    
    Args:
        phase: Current phase number (1-5)
        games_completed: Number of games completed (for Phase 1)
        total_games: Total games for the week (optional, only update if provided)
    """
    ensure_status_exists()
    with app.app_context():
        status = SimulationStatus.query.first()
        if status and status.is_running:
            # If phase changed, update phase_start_time
            if status.current_phase != phase:
                status.current_phase = phase
                status.phase_start_time = datetime.now(timezone.utc).replace(tzinfo=None)
                logger.info(f"Progress: Phase {phase} started")
            
            # Update games completed (only for Phase 1)
            if phase == 1 and games_completed is not None:
                status.games_completed = games_completed
            
            # Update total games if provided
            if total_games is not None:
                status.total_games = total_games
            
            status.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()

def get_progress():
    """
    Get current progress data with ETA calculation.
    
    Returns:
        dict with progress information including ETA
    """
    ensure_status_exists()
    with app.app_context():
        status = SimulationStatus.query.first()
        if not status or not status.is_running:
            return {
                'current_phase': None,
                'phase_name': None,
                'games_completed': 0,
                'total_games': 0,
                'eta_seconds': None,
                'progress_percentage': 0
            }
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        phase = status.current_phase or 1
        games_completed = status.games_completed or 0
        total_games = status.total_games or 0
        
        # Phase names
        phase_names = {
            1: "Generating game results",
            2: "Generating images & podcasts",
            3: "Calculating betting odds",
            4: "Posting to Instagram",
            5: "Finalizing"
        }
        phase_name = phase_names.get(phase, f"Phase {phase}")
        
        # Calculate ETA
        eta_seconds = None
        progress_percentage = 0
        
        if phase == 1 and total_games > 0 and games_completed > 0:
            # Phase 1: Calculate based on games completed rate
            if status.phase_start_time:
                elapsed = (now - status.phase_start_time).total_seconds()
                if elapsed > 0 and games_completed > 0:
                    time_per_game = elapsed / games_completed
                    remaining_games = total_games - games_completed
                    eta_seconds = int(remaining_games * time_per_game)
                    progress_percentage = int((games_completed / total_games) * 100)
        elif phase > 1:
            # Phases 2-5: Estimate based on elapsed time in phase
            # Based on actual timing from logs:
            # Phase 2: ~372s (6m 12s) - Generating images & podcasts (concurrent)
            # Phase 3: ~10s - Calculating betting odds
            # Phase 4: ~30s - Posting to Instagram (if enabled)
            # Phase 5: ~5s - Finalizing
            phase_estimates = {2: 372, 3: 10, 4: 30, 5: 5}
            estimated_duration = phase_estimates.get(phase, 30)
            
            if status.phase_start_time:
                elapsed = (now - status.phase_start_time).total_seconds()
                eta_seconds = max(0, int(estimated_duration - elapsed))
                # Progress based on elapsed time vs estimated duration
                progress_percentage = min(95, int((elapsed / estimated_duration) * 100))
            else:
                eta_seconds = estimated_duration
                progress_percentage = 0
        
        return {
            'current_phase': phase,
            'phase_name': phase_name,
            'games_completed': games_completed,
            'total_games': total_games,
            'eta_seconds': eta_seconds,
            'progress_percentage': progress_percentage
        }

def get_status():
    """
    Get current simulation status.
    
    Returns:
        dict with: is_running, current_week, next_simulation_time, status_message, countdown_seconds, progress data
    """
    ensure_status_exists()
    with app.app_context():
        status = SimulationStatus.query.first()
        if not status:
            return {
                'is_running': False,
                'current_week': 0,
                'next_simulation_time': None,
                'status_message': '',
                'countdown_seconds': None
            }
        
        countdown_seconds = None
        if status.next_simulation_time:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if status.next_simulation_time > now:
                delta = status.next_simulation_time - now
                countdown_seconds = int(delta.total_seconds())
            else:
                countdown_seconds = 0
        
        # Format next_simulation_time as ISO with UTC timezone indicator
        next_sim_time_str = None
        if status.next_simulation_time:
            # Since next_simulation_time is stored as naive UTC datetime, append 'Z' to indicate UTC
            next_sim_time_str = status.next_simulation_time.isoformat() + 'Z'
        
        result = {
            'is_running': status.is_running,
            'current_week': status.current_week,
            'next_simulation_time': next_sim_time_str,
            'status_message': status.status_message,
            'countdown_seconds': countdown_seconds
        }
        
        # Add progress data if simulation is running
        if status.is_running:
            progress = get_progress()
            result.update(progress)
        
        return result

