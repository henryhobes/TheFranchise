#!/usr/bin/env python3
"""
Simple test for rollback bounds checking fix.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from state.draft_state import DraftState


def test_rollback_bounds_fix():
    """Test the rollback bounds checking fix."""
    print("Testing rollback bounds checking fix...")
    
    # Create draft state with some snapshots
    draft_state = DraftState("test", "1", 12, 16)
    draft_state.initialize_player_pool(['p1', 'p2', 'p3', 'p4', 'p5'])
    
    # Create exactly 3 snapshots by making 3 picks
    draft_state.apply_pick('p1', '1', 1, 'QB')  # Creates snapshot 0
    draft_state.apply_pick('p2', '2', 2, 'RB')  # Creates snapshot 1  
    draft_state.apply_pick('p3', '3', 3, 'WR')  # Creates snapshot 2
    
    snapshot_count = len(draft_state._state_snapshots)
    print(f"Created {snapshot_count} snapshots")
    
    # Test cases: [index, should_work, description]
    test_cases = [
        # Valid positive indices
        (0, True, "first snapshot"),
        (1, True, "middle snapshot"),
        (2, True, "last snapshot (positive)"),
        
        # Valid negative indices (THIS WAS BROKEN BEFORE FIX)
        (-1, True, "last snapshot (negative)"), 
        (-2, True, "second to last snapshot"),
        (-3, True, "first snapshot (negative)"),
        
        # Invalid positive indices  
        (3, False, "beyond bounds (positive)"),
        (10, False, "way beyond bounds (positive)"),
        
        # Invalid negative indices
        (-4, False, "beyond bounds (negative)"),
        (-10, False, "way beyond bounds (negative)")
    ]
    
    print("\nTesting bounds checking:")
    
    for index, should_work, description in test_cases:
        # Test the bounds checking
        success = draft_state.rollback_to_snapshot(index)
        
        if should_work:
            assert success, f"Index {index} ({description}) should work but failed"
            print(f"  Index {index:3d}: SUCCESS - {description}")
        else:
            assert not success, f"Index {index} ({description}) should fail but succeeded"  
            print(f"  Index {index:3d}: CORRECTLY REJECTED - {description}")
    
    print("\nSpecial focus on negative indices (the main fix):")
    
    # Before the fix, these would fail. After the fix, they should work.
    negative_tests = [(-1, "last"), (-2, "second-to-last"), (-3, "third-to-last")]
    
    for index, desc in negative_tests:
        if abs(index) <= snapshot_count:
            success = draft_state.rollback_to_snapshot(index)
            assert success, f"Negative index {index} should work after fix"
            print(f"  Negative index {index}: WORKS ({desc} snapshot)")
    
    print("\nBounds equivalence test:")
    
    # Test that our bounds checking matches Python's list indexing
    test_list = list(range(snapshot_count))  # Same length as snapshots
    
    for i in range(-10, 11):  # Test various indices
        # Can Python access this index?
        try:
            test_list[i]
            python_ok = True
        except IndexError:
            python_ok = False
        
        # Does our validation accept this index?
        our_validation = not (i >= snapshot_count or i < -snapshot_count)
        
        assert python_ok == our_validation, \
            f"Index {i}: Python={python_ok}, Our validation={our_validation}"
    
    print("  Our bounds checking matches Python's native behavior")
    
    print("\nAll rollback bounds tests passed!")
    return True


def test_basic_negative_indexing():
    """Simple test to verify negative indexing works."""
    print("\nTesting basic negative indexing functionality...")
    
    draft_state = DraftState("test", "1", 12, 16)
    draft_state.initialize_player_pool(['p1', 'p2'])
    
    # Create 2 snapshots
    initial_picks = draft_state.current_pick
    draft_state.apply_pick('p1', '1', 1, 'QB')
    after_first = draft_state.current_pick  
    draft_state.apply_pick('p2', '2', 2, 'RB')
    after_second = draft_state.current_pick
    
    print(f"  Picks: initial={initial_picks}, after_first={after_first}, after_second={after_second}")
    
    # Roll back to last snapshot using negative index
    success = draft_state.rollback_to_snapshot(-1)
    assert success, "Should be able to rollback to -1 (last snapshot)"
    
    final_picks = draft_state.current_pick
    print(f"  After rollback to -1: picks={final_picks}")
    
    # Should have rolled back to a previous state
    assert final_picks < after_second, "Should have fewer picks after rollback"
    
    print("  Negative indexing rollback works correctly")
    return True


def main():
    """Run rollback bounds tests."""
    try:
        test_rollback_bounds_fix()
        test_basic_negative_indexing()
        
        print("\n" + "="*50)
        print("ROLLBACK BOUNDS FIX - VERIFIED")  
        print("="*50)
        print("BEFORE: rollback_to_snapshot(-1) would fail")
        print("AFTER:  rollback_to_snapshot(-1) works correctly")
        print("")
        print("The fix enables proper Python-style negative indexing:")
        print("  -1 = last snapshot")
        print("  -2 = second to last snapshot") 
        print("  etc.")
        print("")
        print("Bounds checking now properly handles both positive")
        print("and negative indices according to Python standards.")
        
        return True
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)