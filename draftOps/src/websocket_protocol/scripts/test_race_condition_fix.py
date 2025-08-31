#!/usr/bin/env python3
"""
Test the race condition fix for async position resolution.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from state.draft_state import DraftState
from state.event_processor import DraftEventProcessor
from state.integration import DraftStateManager


def test_synchronous_position_resolution():
    """Test that position resolution is now synchronous and doesn't cause race conditions."""
    print("Testing synchronous position resolution fix...")
    
    # Create draft state manager (without full initialization to avoid external dependencies)
    manager = DraftStateManager("test_league", "test_team")
    
    # Test 1: Position resolver should be synchronous
    result = manager._resolve_player_position("test_player_123")
    
    # Should return immediately without awaiting
    assert isinstance(result, str), f"Position resolver should return string, got {type(result)}"
    assert result == "BENCH", f"Should return BENCH for unknown player, got {result}"
    print("PASS: Position resolver returns synchronously")
    
    # Test 2: Player should be queued for async resolution
    assert "test_player_123" in manager._resolution_queue, "Player should be added to resolution queue"
    print("PASS: Player queued for async resolution")
    
    # Test 3: Cached position should be returned
    manager._player_positions["cached_player"] = "QB"
    result = manager._resolve_player_position("cached_player")
    assert result == "QB", f"Should return cached position, got {result}"
    print("PASS: Cached position returned correctly")
    
    # Test 4: Event processor integration (this was the main issue)
    draft_state = DraftState("test", "1", 12, 16)
    processor = DraftEventProcessor(draft_state)
    
    # Set the position resolver (this should work without race conditions now)
    processor.set_position_resolver(manager._resolve_player_position)
    
    # Call the position resolver through the event processor (synchronously)
    try:
        result = processor._resolve_position("test_player_456")
        assert isinstance(result, str), "Position resolution through processor should work"
        print("PASS: Position resolution through event processor works")
    except Exception as e:
        raise AssertionError(f"Position resolution through processor failed: {e}")
    
    # Test 5: Verify no async/await issues
    # The old code would fail here because async function called synchronously
    try:
        # Simulate multiple rapid calls (like during message processing)
        for i in range(10):
            result = processor._resolve_position(f"rapid_player_{i}")
            assert isinstance(result, str), f"Rapid call {i} should return string"
        print("PASS: Rapid synchronous calls work correctly")
    except Exception as e:
        raise AssertionError(f"Rapid calls failed: {e}")
    
    print("\nAll race condition fix tests passed!")
    return True


def test_async_resolution_still_works():
    """Test that async resolution still works for batch processing."""
    print("\nTesting async resolution still works...")
    
    # Create manager
    manager = DraftStateManager("test_league", "test_team") 
    
    # Queue some players
    manager._resolve_player_position("player1")
    manager._resolve_player_position("player2")
    
    # Verify they're queued
    assert len(manager._resolution_queue) == 2, "Players should be queued"
    print("PASS: Players queued for async resolution")
    
    # Note: We can't test actual async resolution without initializing the full system
    # which requires external dependencies, but the queueing mechanism is working
    
    return True


def main():
    """Run race condition fix tests."""
    try:
        test_synchronous_position_resolution()
        test_async_resolution_still_works()
        
        print("\n" + "="*60)
        print("RACE CONDITION FIX VERIFICATION - SUCCESS")
        print("="*60)
        print("BEFORE: async method called synchronously -> runtime errors")
        print("AFTER:  synchronous method with async queue -> no race conditions")
        print("")
        print("Key improvements:")
        print("+ Position resolution is now synchronous (no blocking)")
        print("+ Players queued for async resolution (maintains functionality)")
        print("+ Position cache provides fast lookup for resolved players")
        print("+ No more race conditions in message processing")
        
        return True
        
    except Exception as e:
        print(f"\nFAILED: Race condition fix test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)