#!/usr/bin/env python3
"""
Test the validation fix for in-progress picks.
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
    
    # Test 1: Initial state should be valid
    validation = handlers.validate_draft_consistency()
    assert validation.is_valid, f"Initial state should be valid: {validation.errors}"
    print("✓ Initial state validation passes")
    
    # Test 2: After SELECTING (team on clock) - should NOT flag as corruption
    processor.process_websocket_message("SELECTING 1 30000")
    
    # At this point:
    # - current_pick = 1 (team 1 is about to make pick 1)
    # - drafted_players = 0 (no picks completed yet)
    # - This should NOT be flagged as corruption
    
    validation = handlers.validate_draft_consistency()
    assert validation.is_valid, f"In-progress pick should be valid: {validation.errors}"
    print("✓ In-progress pick validation passes (no false corruption)")
    
    # Test 3: After SELECTED (pick completed) - should be valid
    processor.process_websocket_message("SELECTED 1 3918298 1 {MEMBER_ID}")
    
    # At this point:
    # - current_pick = 1 (pick 1 completed)
    # - drafted_players = 1 (one pick completed)
    # - This should definitely be valid
    
    validation = handlers.validate_draft_consistency()
    assert validation.is_valid, f"Completed pick should be valid: {validation.errors}"
    print("✓ Completed pick validation passes")
    
    # Test 4: Next team on clock - should be valid
    processor.process_websocket_message("SELECTING 2 30000")
    
    # At this point:
    # - current_pick = 2 (team 2 is about to make pick 2)
    # - drafted_players = 1 (one pick completed)
    # - This should be valid (pick in progress)
    
    validation = handlers.validate_draft_consistency()
    assert validation.is_valid, f"Second in-progress pick should be valid: {validation.errors}"
    print("✓ Second in-progress pick validation passes")
    
    # Test 5: Test error conditions still work
    # Force invalid state: current_pick behind completed picks
    draft_state._current_pick = 0  # Force invalid state
    
    validation = handlers.validate_draft_consistency()
    assert not validation.is_valid, "Should detect current_pick behind completed picks"
    assert "behind completed picks" in str(validation.errors)
    print("✓ Still detects actual corruption (pick behind)")
    
    # Test 6: Test another error condition: current_pick too far ahead
    draft_state._current_pick = 5  # Too far ahead (should be 1 or 2)
    
    validation = handlers.validate_draft_consistency()
    assert not validation.is_valid, "Should detect current_pick too far ahead"
    assert "too far ahead" in str(validation.errors)
    print("✓ Still detects actual corruption (pick too far ahead)")
    
    print("\n🎉 All validation fix tests passed!")
    print("✅ False alarms for in-progress picks eliminated")
    print("✅ Real corruption detection still works")
    return True


def test_live_draft_sequence():
    """Test with a realistic draft sequence to ensure no false alarms."""
    print("\nTesting realistic draft sequence...")
    
    # Create system
    draft_state = DraftState("262233108", "1", 12, 16)
    processor = DraftEventProcessor(draft_state)
    handlers = StateUpdateHandlers(draft_state)
    
    # Initialize player pool
    draft_state.initialize_player_pool(['3918298', '4362238', '4429795'])
    
    # Realistic message sequence
    messages = [
        "SELECTING 1 30000",           # Team 1 on clock for pick 1
        "SELECTED 1 3918298 1 {ID}",   # Team 1 makes pick 1
        "SELECTING 2 30000",           # Team 2 on clock for pick 2  
        "SELECTED 2 4362238 2 {ID}",   # Team 2 makes pick 2
        "SELECTING 3 30000",           # Team 3 on clock for pick 3
        "SELECTED 3 4429795 3 {ID}"    # Team 3 makes pick 3
    ]
    
    validation_errors = 0
    
    for i, message in enumerate(messages, 1):
        processor.process_websocket_message(message)
        validation = handlers.validate_draft_consistency()
        
        if not validation.is_valid:
            print(f"❌ False alarm at step {i}: {message}")
            print(f"   Errors: {validation.errors}")
            validation_errors += 1
        else:
            print(f"✓ Step {i} validation passed: {message}")
    
    assert validation_errors == 0, f"Found {validation_errors} false validation alarms"
    print(f"\n🎉 Complete draft sequence processed with 0 false alarms!")
    return True


def main():
    """Run validation fix tests."""
    try:
        test_validation_fix()
        test_live_draft_sequence()
        
        print("\n" + "="*60)
        print("VALIDATION FIX VERIFICATION - SUCCESS")
        print("="*60)
        print("✅ In-progress picks no longer trigger false corruption alarms")
        print("✅ Real corruption is still detected correctly")
        print("✅ Live draft sequences process without validation errors")
        print("✅ Fix ready for production")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Validation fix test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)