# Cascade Game Simulation

A modular game simulation system that generates match results and posts them to Instagram.

## Project Structure

The project has been split into multiple modules for better performance and maintainability:

- **`cascade_main.py`** - Main entry point that orchestrates the simulation
- **`game_logic.py`** - Core game logic (Team, ScoringDetail, play_game, round_robin, tournament)
- **`image_generator.py`** - Image generation functions (only loaded when needed)
- **`instagram_poster.py`** - Instagram posting functionality (only loaded when posting)
- **`config.py`** - Configuration settings

## Running the Simulation

Simply run the main script:

```bash
python cascade_main.py
```

The program will:
1. Ask how many round robins to play
2. Run the simulation
3. Generate all game images
4. Optionally post to Instagram with hourly intervals

## Benefits of Modular Structure

- **Reduced lag**: Heavy modules (image generation, Instagram posting) are only imported when needed
- **Better organization**: Each module has a clear responsibility
- **Easier maintenance**: Changes to one module don't affect others
- **Selective execution**: You can run just the game logic or just image generation if needed

## Dependencies

- `PIL` (Pillow) - For image generation
- `selenium` (optional) - For automated Instagram posting

Install with:
```bash
pip install pillow selenium
```

## Notes

- The original `cascade-game-simulation.py` file is preserved for reference
- Images are saved with standardized naming: `week_X_game_Y.png`
- Instagram posting can use automated (Selenium) or manual mode

