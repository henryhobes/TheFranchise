#!/usr/bin/env python3
"""
Fixed test for rollback bounds checking.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from state.draft_state import DraftState


def test_rollback_bounds_fix():
    """Test that the rollback bounds fix works correctly."""
    print("Testing rollback bounds checking fix...")
    
    # Test negative index bounds checking specifically
    print("\n1. Testing negative index support (main fix):")
    
    # Create fresh state for each test to avoid interference
    def create_test_state():
        draft_state = DraftState("test", "1", 12, 16)
        draft_state.initialize_player_pool([f'p{i}' for i in range(10)])
        
        # Create some snapshots
        draft_state.apply_pick('p1', '1', 1, 'QB')
        draft_state.apply_pick('p2', '2', 2, 'RB')  
        draft_state.apply_pick('p3', '3', 3, 'WR')
        
        return draft_state
    
    # Test that -1 works (last snapshot)
    state = create_test_state()
    success = state.rollback_to_snapshot(-1)
    assert success, "Should be able to rollback to -1 (last snapshot)"
    print("  -1 (last snapshot): SUCCESS")
    
    # Test that -2 works (second to last)  
    state = create_test_state()
    success = state.rollback_to_snapshot(-2)
    assert success, "Should be able to rollback to -2 (second to last)"
    print("  -2 (second to last): SUCCESS")
    
    # Test that -3 works (third to last, if we have 3 snapshots)
    state = create_test_state()
    if len(state._state_snapshots) >= 3:
        success = state.rollback_to_snapshot(-3)
        assert success, "Should be able to rollback to -3 (third to last)"
        print("  -3 (third to last): SUCCESS")
    
    print("\n2. Testing invalid negative indices are rejected:")
    
    # Test that invalid negative index fails
    state = create_test_state()
    snapshot_count = len(state._state_snapshots)
    invalid_negative = -(snapshot_count + 1)  # One beyond bounds
    
    success = state.rollback_to_snapshot(invalid_negative)
    assert not success, f"Should reject invalid negative index {invalid_negative}"
    print(f"  {invalid_negative} (beyond bounds): CORRECTLY REJECTED")
    
    print("\n3. Testing positive indices still work:")
    
    # Test valid positive indices
    state = create_test_state()
    for i in range(len(state._state_snapshots)):
        fresh_state = create_test_state()  # Fresh state for each test
        success = fresh_state.rollback_to_snapshot(i)
        assert success, f"Should be able to rollback to positive index {i}"
        print(f"  {i} (positive): SUCCESS")
    
    print("\n4. Testing bounds equivalence with Python lists:")
    
    # Test that our bounds checking matches Python's list behavior
    state = create_test_state() 
    test_list = list(range(len(state._state_snapshots)))
    
    for i in range(-10, 11):
        # Can Python's list handle this index?
        try:
            test_list[i]
            python_valid = True
        except IndexError:
            python_valid = False
            
        # Does our rollback accept this index?
        fresh_state = create_test_state()
        our_accepts = fresh_state.rollback_to_snapshot(i)
        
        if python_valid:
            assert our_accepts, f"Index {i} valid in Python but rejected by us"
        else:
            assert not our_accepts, f"Index {i} invalid in Python but accepted by us"
    
    print("  Bounds checking matches Python's list behavior")
    
    print("\nAll rollback bounds tests passed!")
    return True


def test_before_and_after_behavior():
    """Demonstrate the before/after behavior of the fix."""
    print("\nDemonstrating before vs after fix behavior:")
    
    draft_state = DraftState("test", "1", 12, 16)
    draft_state.initialize_player_pool(['p1', 'p2', 'p3'])
    
    # Create snapshots
    draft_state.apply_pick('p1', '1', 1, 'QB')
    draft_state.apply_pick('p2', '2', 2, 'RB')
    
    print("With the OLD bounds checking (index < 0):")
    print("  rollback_to_snapshot(-1) would FAIL (incorrect)")
    print("  rollback_to_snapshot(-2) would FAIL (incorrect)")
    
    print("\nWith the NEW bounds checking (index < -len(snapshots)):")
    
    # Test -1
    success_1 = draft_state.rollback_to_snapshot(-1)
    print(f"  rollback_to_snapshot(-1) -> {success_1} (correct)")
    
    # Reset and test -2
    draft_state.apply_pick('p2', '2', 2, 'RB')  # Reset state
    success_2 = draft_state.rollback_to_snapshot(-2)
    print(f"  rollback_to_snapshot(-2) -> {success_2} (correct)")
    
    # Test invalid negative
    draft_state.apply_pick('p2', '2', 2, 'RB')  # Reset state
    invalid_success = draft_state.rollback_to_snapshot(-10)
    print(f"  rollback_to_snapshot(-10) -> {invalid_success} (correctly rejects invalid)")
    
    return True


def main():
    """Run tests."""
    try:
        test_rollback_bounds_fix()
        test_before_and_after_behavior()
        
        print("\n" + "="*55)
        print("ROLLBACK BOUNDS INDEX FIX - VERIFIED")
        print("="*55)
        print("The index bounds error has been fixed:")
        print("")
        print("BEFORE: if index < 0: return False")
        print("        (rejected all negative indices)")
        print("")  
        print("AFTER:  if index < -len(snapshots): return False")
        print("        (supports Python-style negative indexing)")
        print("")
        print("This enables proper usage patterns like:")
        print("  rollback_to_snapshot(-1)  # last snapshot")
        print("  rollback_to_snapshot(-2)  # second-to-last snapshot")
        print("")
        print("While still properly rejecting out-of-bounds indices.")
        
        return True
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)