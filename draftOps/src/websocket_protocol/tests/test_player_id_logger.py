#!/usr/bin/env python3
"""
Test script to run the player ID logger.
This will open a browser and monitor ESPN draft WebSocket traffic.
"""

import asyncio
from ..scripts.player_id_logger import PlayerIdDraftLogger


async def run_logger_test():
    """Run the player ID logger for a short test period."""
    print("""
    ============================================
    ESPN Player ID Logger Test
    ============================================
    
    This will:
    1. Open a browser window
    2. Navigate to ESPN mock draft lobby
    3. Monitor WebSocket traffic for player IDs
    
    IMPORTANT: 
    - You need to manually JOIN a mock draft in the browser
    - Let a few picks happen to capture data
    - Press Ctrl+C to stop and save results
    
    Starting in 3 seconds...
    """)
    
    await asyncio.sleep(3)
    
    # Create logger with visible browser (headless=False)
    logger = PlayerIdDraftLogger(headless=False)
    
    # Run for up to 20 minutes (or until Ctrl+C) to allow time for draft to start
    await logger.run_player_id_analysis(duration=1200)


if __name__ == "__main__":
    try:
        asyncio.run(run_logger_test())
    except KeyboardInterrupt:
        print("\n\nStopped by user. Check the 'reports' folder for results.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()