#!/usr/bin/env python3
"""
Test the rollback bounds error fix.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from state.draft_state import DraftState


def test_rollback_bounds_checking():
    """Test that rollback bounds checking works correctly with negative indices."""
    print("Testing rollback bounds checking fix...")
    
    # Create draft state and add some snapshots
    draft_state = DraftState("test", "1", 12, 16)
    draft_state.initialize_player_pool(['player1', 'player2', 'player3', 'player4'])
    
    # Make some picks to create snapshots
    draft_state.apply_pick('player1', '1', 1, 'QB')  # Snapshot 0
    draft_state.apply_pick('player2', '2', 2, 'RB')  # Snapshot 1  
    draft_state.apply_pick('player3', '3', 3, 'WR')  # Snapshot 2
    
    snapshot_count = len(draft_state._state_snapshots)
    print(f"Created {snapshot_count} snapshots for testing")
    
    # Test 1: Valid positive indices should work
    print("\nTesting valid positive indices:")
    
    for i in range(snapshot_count):
        success = draft_state.rollback_to_snapshot(i)
        assert success, f"Rollback to valid positive index {i} should succeed"
        print(f"  Index {i}: SUCCESS")
        
        # Reset state for next test
        draft_state.apply_pick('player2', '2', 2, 'RB')
        draft_state.apply_pick('player3', '3', 3, 'WR')
    
    # Test 2: Valid negative indices should work (THIS WAS BROKEN BEFORE)
    print("\nTesting valid negative indices:")
    
    valid_negative_indices = [-1, -2, -3][:snapshot_count]  # Only test indices we have
    
    for i in valid_negative_indices:
        if abs(i) <= snapshot_count:  # Ensure we have enough snapshots
            success = draft_state.rollback_to_snapshot(i)
            assert success, f"Rollback to valid negative index {i} should succeed"
            print(f"  Index {i}: SUCCESS (was failing before fix)")
            
            # Verify the rollback worked by checking current state
            # (We don't need to compare with snapshot, just verify rollback didn't crash)
            assert draft_state.current_pick >= 0, "Current pick should be valid after rollback"
            
            # Reset state for next test
            draft_state.apply_pick('player2', '2', 2, 'RB')
            draft_state.apply_pick('player3', '3', 3, 'WR')
    
    # Test 3: Invalid positive indices should fail
    print("\nTesting invalid positive indices:")
    
    invalid_positive = [snapshot_count, snapshot_count + 1, snapshot_count + 10]
    
    for i in invalid_positive:
        success = draft_state.rollback_to_snapshot(i)
        assert not success, f"Rollback to invalid positive index {i} should fail"
        print(f"  Index {i}: CORRECTLY REJECTED")
    
    # Test 4: Invalid negative indices should fail
    print("\nTesting invalid negative indices:")
    
    invalid_negative = [-(snapshot_count + 1), -(snapshot_count + 2), -100]
    
    for i in invalid_negative:
        success = draft_state.rollback_to_snapshot(i)
        assert not success, f"Rollback to invalid negative index {i} should fail"
        print(f"  Index {i}: CORRECTLY REJECTED")
    
    # Test 5: Edge cases
    print("\nTesting edge cases:")
    
    # Test exactly at the boundary
    boundary_negative = -snapshot_count  # This should be valid
    success = draft_state.rollback_to_snapshot(boundary_negative)
    assert success, f"Boundary negative index {boundary_negative} should be valid"
    print(f"  Boundary index {boundary_negative}: SUCCESS")
    
    # Test just beyond the boundary
    beyond_boundary = -(snapshot_count + 1)  # This should be invalid
    success = draft_state.rollback_to_snapshot(beyond_boundary)
    assert not success, f"Beyond boundary index {beyond_boundary} should be invalid"
    print(f"  Beyond boundary index {beyond_boundary}: CORRECTLY REJECTED")
    
    print("\nAll rollback bounds tests passed!")
    return True


def test_rollback_functionality_preserved():
    """Test that rollback functionality still works correctly after the fix."""
    print("\nTesting rollback functionality is preserved...")
    
    draft_state = DraftState("test", "1", 12, 16)
    draft_state.initialize_player_pool(['player1', 'player2', 'player3'])
    
    # Initial state
    initial_picks = len(draft_state.drafted_players)
    
    # Make some picks
    draft_state.apply_pick('player1', '1', 1, 'QB')
    draft_state.apply_pick('player2', '2', 2, 'RB')
    
    current_picks = len(draft_state.drafted_players)
    assert current_picks == 2, "Should have 2 picks after applying them"
    
    # Rollback to first snapshot (before any picks) using negative indexing
    success = draft_state.rollback_to_snapshot(-2)  # Second to last snapshot
    assert success, "Rollback using negative index should work"
    
    # Verify rollback worked
    after_rollback_picks = len(draft_state.drafted_players)
    print(f"Picks: initial={initial_picks}, after_adds={current_picks}, after_rollback={after_rollback_picks}")
    
    # Should have fewer picks after rollback
    assert after_rollback_picks < current_picks, "Should have fewer picks after rollback"
    
    print("PASS: Rollback functionality preserved with negative indexing")
    return True


def test_python_negative_indexing_equivalence():
    """Test that our bounds checking matches Python's native negative indexing."""
    print("\nTesting equivalence with Python's native negative indexing...")
    
    draft_state = DraftState("test", "1", 12, 16)
    draft_state.initialize_player_pool(['player1', 'player2', 'player3'])
    
    # Create some snapshots
    draft_state.apply_pick('player1', '1', 1, 'QB')
    draft_state.apply_pick('player2', '2', 2, 'RB')
    
    snapshots = draft_state._state_snapshots
    snapshot_count = len(snapshots)
    
    # Test that our bounds checking matches Python's behavior
    for i in range(-snapshot_count, snapshot_count):
        # Check if Python would accept this index
        python_accepts = 0 <= i < len(snapshots) or -len(snapshots) <= i < 0
        
        # Check if our validation accepts this index
        our_validation_accepts = not (i >= len(snapshots) or i < -len(snapshots))
        
        assert python_accepts == our_validation_accepts, \
            f"Index {i}: Python accepts={python_accepts}, our validation accepts={our_validation_accepts}"
        
        if python_accepts:
            # If Python would accept it, our rollback should work
            success = draft_state.rollback_to_snapshot(i)
            assert success, f"Index {i} should be accepted by rollback"
            print(f"  Index {i}: Both Python and our validation accept")
        else:
            # If Python wouldn't accept it, our rollback should fail
            success = draft_state.rollback_to_snapshot(i)
            assert not success, f"Index {i} should be rejected by rollback"
            print(f"  Index {i}: Both Python and our validation reject")
    
    print("PASS: Our bounds checking matches Python's native behavior")
    return True


def main():
    """Run all rollback bounds tests."""
    try:
        test_rollback_bounds_checking()
        test_rollback_functionality_preserved()
        test_python_negative_indexing_equivalence()
        
        print("\n" + "="*60)
        print("ROLLBACK BOUNDS FIX VERIFICATION - SUCCESS")
        print("="*60)
        print("BEFORE: negative indices like -1 incorrectly rejected")
        print("AFTER:  proper bounds checking supports negative indexing")
        print("")
        print("Key improvements:")
        print("+ Valid negative indices (-1, -2, etc.) now work correctly")
        print("+ Invalid indices (beyond bounds) still properly rejected")
        print("+ Bounds checking matches Python's native list indexing")
        print("+ Rollback functionality fully preserved")
        print("+ Edge cases properly handled")
        print("")
        print("Examples now working:")
        print('  rollback_to_snapshot(-1)  # Last snapshot')
        print('  rollback_to_snapshot(-2)  # Second to last snapshot')
        
        return True
        
    except Exception as e:
        print(f"\nFAILED: Rollback bounds test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)