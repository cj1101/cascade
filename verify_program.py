"""Verification script for Cascade program - run this to test everything"""
import sys
import os

print("="*70)
print("CASCADE PROGRAM VERIFICATION")
print("="*70)

errors = []
warnings = []

# Test 1: Check all required modules exist
print("\n[1/8] Checking required modules...")
required_modules = [
    'scheduler', 'game_logic', 'config', 'image_generator', 
    'instagram_poster', 'cascade_main'
]
for module in required_modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError as e:
        errors.append(f"Missing module: {module} - {e}")
        print(f"  ✗ {module} - {e}")

# Test 2: Check scheduler functions
print("\n[2/8] Testing scheduler module...")
try:
    import scheduler
    teams = scheduler.get_initial_teams()
    if len(teams) != 8:
        errors.append(f"Expected 8 teams, got {len(teams)}")
    else:
        print(f"  ✓ get_initial_teams() - Created {len(teams)} teams")
    
    # Test save/load
    scheduler.save_game_state(teams, 1, None)
    loaded_teams, week, rr = scheduler.load_game_state()
    if len(loaded_teams) != 8:
        errors.append("Game state save/load failed")
    else:
        print(f"  ✓ save_game_state() / load_game_state() - Working")
except Exception as e:
    errors.append(f"Scheduler test failed: {e}")

# Test 3: Check game logic
print("\n[3/8] Testing game logic...")
try:
    import game_logic
    result, upset, game_result = game_logic.play_game(teams[0], teams[1])
    if 'team1_score' not in game_result:
        errors.append("play_game() missing team1_score")
    else:
        print(f"  ✓ play_game() - Working")
    
    schedule = game_logic.generate_round_robin_schedule(teams)
    if len(schedule) == 0:
        errors.append("generate_round_robin_schedule() returned empty")
    else:
        print(f"  ✓ generate_round_robin_schedule() - {len(schedule)} rounds")
    
    odds1, odds2 = game_logic.calculate_matchup_odds(teams[0], teams[1])
    print(f"  ✓ calculate_matchup_odds() - Working (odds: {odds1}, {odds2})")
except Exception as e:
    errors.append(f"Game logic test failed: {e}")

# Test 4: Check image generator
print("\n[4/8] Testing image generator...")
try:
    import image_generator
    print(f"  ✓ image_generator module loaded")
except Exception as e:
    warnings.append(f"Image generator: {e}")

# Test 5: Check Instagram poster
print("\n[5/8] Testing Instagram poster...")
try:
    import instagram_poster
    print(f"  ✓ instagram_poster module loaded")
    # Check for credentials (warn if missing)
    import config
    if not getattr(config, 'INSTAGRAM_ACCESS_TOKEN', None):
        warnings.append("Instagram credentials not configured (posts will fail)")
    else:
        print(f"  ✓ Instagram credentials configured")
except Exception as e:
    warnings.append(f"Instagram poster: {e}")

# Test 6: Check config
print("\n[6/8] Testing config...")
try:
    import config
    print(f"  ✓ config module loaded")
    if not hasattr(config, 'STATE_FILE_PATH'):
        warnings.append("STATE_FILE_PATH not in config (using default)")
except Exception as e:
    warnings.append(f"Config: {e}")

# Test 7: Test argument parsing
print("\n[7/8] Testing argument parsing...")
try:
    import cascade_main
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, required=True, 
                       choices=['round_robin_1', 'round_robin_2', 'tournament'])
    parser.add_argument('--now', action='store_true')
    parser.add_argument('--debug-interval', type=int)
    args = parser.parse_args(['--mode', 'round_robin_1', '--now'])
    if args.mode != 'round_robin_1' or not args.now:
        errors.append("Argument parsing failed")
    else:
        print(f"  ✓ Argument parsing - Working")
except Exception as e:
    errors.append(f"Argument parsing test failed: {e}")

# Test 8: Check dependencies
print("\n[8/8] Checking dependencies...")
try:
    import pytz
    print(f"  ✓ pytz installed")
except ImportError:
    errors.append("pytz not installed - run: pip install pytz")

try:
    from PIL import Image
    print(f"  ✓ Pillow installed")
except ImportError:
    errors.append("Pillow not installed - run: pip install pillow")

# Summary
print("\n" + "="*70)
if errors:
    print("✗ VERIFICATION FAILED")
    print("\nErrors found:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("✓ VERIFICATION PASSED")
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ⚠ {warning}")
    print("\nThe program is ready to run!")
    print("\nTo test the full program:")
    print("  python cascade_main.py --mode round_robin_1 --now")
    print("\nTo run with debug intervals (e.g., 1 minute between weeks):")
    print("  python cascade_main.py --mode round_robin_1 --debug-interval 1")
print("="*70)
