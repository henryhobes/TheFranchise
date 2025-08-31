#!/usr/bin/env python3
"""
Debug rollback functionality to understand the issue.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from state.draft_state import DraftState


def debug_rollback():
    """Debug rollback to see what's happening."""
    print("Debugging rollback functionality...")
    
    draft_state = DraftState("test", "1", 12, 16)
    draft_state.initialize_player_pool(['p1', 'p2', 'p3'])
    
    print(f"Initial snapshots: {len(draft_state._state_snapshots)}")
    
    # Make first pick
    success = draft_state.apply_pick('p1', '1', 1, 'QB')
    print(f"First pick success: {success}")
    print(f"Snapshots after first pick: {len(draft_state._state_snapshots)}")
    print(f"Current pick: {draft_state.current_pick}")
    
    # Make second pick
    success = draft_state.apply_pick('p2', '2', 2, 'RB')
    print(f"Second pick success: {success}")
    print(f"Snapshots after second pick: {len(draft_state._state_snapshots)}")
    print(f"Current pick: {draft_state.current_pick}")
    
    # Try to rollback to index 0
    print("\nTesting rollback to index 0:")
    print(f"Snapshots available: {len(draft_state._state_snapshots)}")
    print(f"Trying to rollback to index 0...")
    
    success = draft_state.rollback_to_snapshot(0)
    print(f"Rollback success: {success}")
    print(f"Current pick after rollback: {draft_state.current_pick}")
    
    # Try to rollback to index 1
    print("\nResetting state...")
    draft_state.apply_pick('p2', '2', 2, 'RB')
    print(f"Current pick after reset: {draft_state.current_pick}")
    print(f"Available snapshots: {len(draft_state._state_snapshots)}")
    
    print("Trying to rollback to index 1...")
    success = draft_state.rollback_to_snapshot(1)
    print(f"Rollback to index 1 success: {success}")
    
    if not success:
        print("Rollback failed. Let's check why...")
        
        # Check bounds manually
        index = 1
        snapshots_count = len(draft_state._state_snapshots)
        print(f"Index: {index}, Snapshots count: {snapshots_count}")
        print(f"Bounds check: {index} >= {snapshots_count} or {index} < -{snapshots_count}")
        print(f"First condition: {index >= snapshots_count}")
        print(f"Second condition: {index < -snapshots_count}")
        
        bounds_ok = not (index >= snapshots_count or index < -snapshots_count)
        print(f"Bounds OK: {bounds_ok}")


if __name__ == "__main__":
    debug_rollback()