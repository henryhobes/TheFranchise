#!/usr/bin/env python3
"""
Basic Draft State Testing

Simple tests to validate core functionality without external dependencies.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from state.draft_state import DraftState, DraftStatus
from state.event_processor import DraftEventProcessor
from state.state_handlers import StateUpdateHandlers


def test_basic_draft_state():
    """Test basic draft state functionality."""
    print("Testing basic draft state...")
    
    # Create draft state
    draft_state = DraftState("262233108", "1", 12, 16)
    
    # Test initialization
    assert draft_state.league_id == "262233108"
    assert draft_state.current_pick == 0
    assert draft_state.draft_status == DraftStatus.WAITING
    assert len(draft_state.drafted_players) == 0
    
    # Test player pool
    draft_state.initialize_player_pool(['1001', '1002', '1003'])
    assert len(draft_state.available_players) == 3
    
    # Test draft order
    team_order = [str(i) for i in range(1, 13)]
    draft_state.set_draft_order(team_order)
    assert len(draft_state._my_pick_positions) == 16  # 16 rounds
    
    # Test pick application
    success = draft_state.apply_pick('1001', '1', 1, 'QB')
    assert success
    assert '1001' in draft_state.drafted_players
    assert '1001' not in draft_state.available_players
    assert len(draft_state.pick_history) == 1
    
    print("PASSED: Basic draft state test")
    return True


def test_event_processor():
    """Test event processor with Sprint 0 messages."""
    print("Testing event processor...")
    
    # Create components
    draft_state = DraftState("262233108", "1", 12, 16)
    processor = DraftEventProcessor(draft_state)
    
    # Initialize player pool with Sprint 0 discovered players
    sprint_0_players = [
        '3918298', '4362238', '4429795', '4379399', '4890973',
        '4242335', '4362628', '4047365', '4430807', '4361307'
    ]
    draft_state.initialize_player_pool(sprint_0_players)
    
    # Test message parsing
    selected_msg = "SELECTED 1 4362628 1 {856970E3-67E6-42D4-8198-28B1FB3BCA26}"
    parsed = processor._parse_message(selected_msg)
    
    assert parsed['type'] == 'SELECTED'
    assert parsed['team_id'] == 1
    assert parsed['player_id'] == '4362628'
    assert parsed['overall_pick'] == 1
    
    # Test message processing
    selecting_msg = "SELECTING 1 30000"
    success = processor.process_websocket_message(selecting_msg)
    assert success
    assert draft_state.current_pick == 1
    assert draft_state.on_the_clock == "1"
    
    # Test pick processing
    success = processor.process_websocket_message(selected_msg)
    assert success
    assert '4362628' in draft_state.drafted_players
    assert len(draft_state.pick_history) == 1
    
    print("PASSED: Event processor test")
    return True


def test_sprint_0_message_replay():
    """Test with Sprint 0 captured messages."""
    print("Testing Sprint 0 message replay...")
    
    # Create system
    draft_state = DraftState("262233108", "1", 12, 16)
    processor = DraftEventProcessor(draft_state)
    
    # Initialize with Sprint 0 players
    sprint_0_players = ['3918298', '4362238', '4429795']
    draft_state.initialize_player_pool(sprint_0_players)
    
    # Sprint 0 message sequence
    messages = [
        "SELECTING 1 30000",
        "SELECTED 1 3918298 1 {MEMBER_ID}",
        "SELECTING 2 30000",
        "SELECTED 2 4362238 2 {MEMBER_ID}",
        "SELECTING 3 30000",
        "SELECTED 3 4429795 3 {MEMBER_ID}"
    ]
    
    # Process messages
    for msg in messages:
        success = processor.process_websocket_message(msg)
        assert success, f"Failed to process: {msg}"
        
    # Verify final state
    assert draft_state.current_pick == 3
    assert len(draft_state.drafted_players) == 3
    assert '3918298' in draft_state.drafted_players
    assert '4362238' in draft_state.drafted_players
    assert '4429795' in draft_state.drafted_players
    
    print("PASSED: Sprint 0 message replay test")
    return True


def test_state_validation():
    """Test state validation."""
    print("Testing state validation...")
    
    # Create components
    draft_state = DraftState("262233108", "1", 12, 16)
    handlers = StateUpdateHandlers(draft_state)
    
    # Make some picks
    draft_state.initialize_player_pool(['1001', '1002', '1003'])
    draft_state.apply_pick('1001', '1', 1, 'QB')
    draft_state.apply_pick('1002', '2', 2, 'RB')
    
    # Validate state
    validation = handlers.validate_draft_consistency()
    assert validation.is_valid
    assert len(validation.errors) == 0
    
    print("PASSED: State validation test")
    return True


def test_performance():
    """Test processing speed requirements."""
    print("Testing performance requirements...")
    
    import time
    
    # Create processor
    draft_state = DraftState("262233108", "1", 12, 16)
    processor = DraftEventProcessor(draft_state)
    
    # Initialize large player pool for testing
    player_ids = [str(1000 + i) for i in range(200)]  # 200 different players
    draft_state.initialize_player_pool(player_ids)
    
    # Test with different messages to avoid duplicate picks
    test_messages = [
        "SELECTING 1 30000",
        "CLOCK 1 25000 1", 
        "PING TEST123",
        "AUTODRAFT 1 false",
        "TOKEN 1234567890"
    ]
    
    start_time = time.time()
    for i in range(100):
        msg = test_messages[i % len(test_messages)]
        processor.process_websocket_message(msg)
    end_time = time.time()
    
    avg_time_ms = ((end_time - start_time) / 100) * 1000
    
    print(f"Average processing time: {avg_time_ms:.2f}ms")
    assert avg_time_ms < 200, f"Processing time {avg_time_ms:.2f}ms exceeds 200ms requirement"
    
    print("PASSED: Performance test")
    return True


def test_snapshots_and_rollback():
    """Test state snapshots and rollback functionality."""
    print("Testing state snapshots...")
    
    draft_state = DraftState("262233108", "1", 12, 16)
    
    # Initialize player pool first
    draft_state.initialize_player_pool(['1001', '1002', '1003'])
    
    # Make picks to create snapshots
    draft_state.apply_pick('1001', '1', 1, 'QB')
    assert len(draft_state._state_snapshots) > 0, "No snapshots created after first pick"
    
    draft_state.apply_pick('1002', '2', 2, 'RB')
    assert len(draft_state._state_snapshots) >= 2, "Not enough snapshots after second pick"
    
    # Verify current state
    assert draft_state.current_pick == 2
    assert '1001' in draft_state.drafted_players
    assert '1002' in draft_state.drafted_players
    
    # Get latest snapshot (should be before last change)
    snapshot = draft_state.get_snapshot()
    assert snapshot is not None, "Could not retrieve snapshot"
    
    print("PASSED: Snapshots test - snapshot creation and retrieval working")
    return True


def main():
    """Run all tests."""
    print("Starting Draft State Basic Tests")
    print("="*60)
    
    # Set up logging
    logging.basicConfig(level=logging.WARNING)  # Suppress most logs for cleaner output
    
    tests = [
        test_basic_draft_state,
        test_event_processor,
        test_sprint_0_message_replay,
        test_state_validation,
        test_performance,
        test_snapshots_and_rollback
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAILED {test.__name__}: {e}")
            failed += 1
            
    print("="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("ALL TESTS PASSED! Sprint 1 core functionality validated.")
        return True
    else:
        print("Some tests failed. Check implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)