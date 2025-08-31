#!/usr/bin/env python3
"""
Simple test for validation fix - no Unicode characters.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from state.draft_state import DraftState
from state.event_processor import DraftEventProcessor
from state.state_handlers import StateUpdateHandlers


def test_validation_fix():
    """Test that validation correctly handles in-progress picks."""
    print("Testing validation fix for in-progress picks...")
    
    # Create system
    draft_state = DraftState("262233108", "1", 12, 16)
    processor = DraftEventProcessor(draft_state)
    handlers = StateUpdateHandlers(draft_state)
    
    # Initialize player pool
    draft_state.initialize_player_pool(['3918298', '4362238', '4429795'])
    
    # Test 1: Process SELECTING message (team goes on clock)
    processor.process_websocket_message("SELECTING 1 30000")
    
    # State: current_pick=1, drafted_players=0 (in-progress pick)
    # This should NOT be flagged as corruption anymore
    validation = handlers.validate_draft_consistency()
    
    print(f"After SELECTING: current_pick={draft_state.current_pick}, drafted_players={len(draft_state.drafted_players)}")
    print(f"Validation result: is_valid={validation.is_valid}")
    if validation.errors:
        print(f"Errors: {validation.errors}")
    
    # This should pass now (was failing before the fix)
    assert validation.is_valid, f"In-progress pick should be valid: {validation.errors}"
    print("PASS: In-progress pick validation works")
    
    # Test 2: Complete the pick
    processor.process_websocket_message("SELECTED 1 3918298 1 {MEMBER_ID}")
    
    # State: current_pick=1, drafted_players=1 (completed pick)
    validation = handlers.validate_draft_consistency()
    
    print(f"After SELECTED: current_pick={draft_state.current_pick}, drafted_players={len(draft_state.drafted_players)}")
    print(f"Validation result: is_valid={validation.is_valid}")
    
    assert validation.is_valid, f"Completed pick should be valid: {validation.errors}"
    print("PASS: Completed pick validation works")
    
    # Test 3: Test that real corruption is still detected
    # Force invalid state: current_pick behind completed picks
    draft_state._current_pick = 0
    
    validation = handlers.validate_draft_consistency()
    print(f"Forced invalid state: current_pick={draft_state.current_pick}, drafted_players={len(draft_state.drafted_players)}")
    print(f"Validation result: is_valid={validation.is_valid}")
    
    assert not validation.is_valid, "Should detect corruption when pick is behind"
    print("PASS: Still detects real corruption")
    
    print("\nAll validation fix tests passed!")
    return True


def main():
    try:
        test_validation_fix()
        print("\nSUCCESS: Validation fix working correctly")
        print("- In-progress picks no longer trigger false alarms")
        print("- Real corruption is still detected")
        return True
    except Exception as e:
        print(f"\nFAILED: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)