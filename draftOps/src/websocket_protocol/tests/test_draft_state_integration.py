#!/usr/bin/env python3
"""
Integration tests for draft state management system.

Tests the complete pipeline using Sprint 0's captured WebSocket messages
to ensure state tracking works correctly end-to-end.
"""

import pytest
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from ..state.draft_state import DraftState, DraftStatus
from ..state.event_processor import DraftEventProcessor
from ..state.state_handlers import StateUpdateHandlers
from ..state.integration import DraftStateManager, create_draft_state_manager


class TestDraftStateIntegration:
    """Integration tests for complete draft state system."""
    
    @pytest.fixture
    def draft_state(self):
        """Create test draft state."""
        return DraftState(
            league_id="262233108",
            team_id="1", 
            team_count=12,
            rounds=16
        )
        
    @pytest.fixture
    def event_processor(self, draft_state):
        """Create event processor with draft state."""
        return DraftEventProcessor(draft_state)
        
    @pytest.fixture
    def state_handlers(self, draft_state):
        """Create state handlers."""
        return StateUpdateHandlers(draft_state)
        
    @pytest.fixture
    async def draft_manager(self):
        """Create draft state manager for testing."""
        manager = DraftStateManager(
            league_id="262233108",
            team_id="1",
            team_count=12,
            rounds=16
        )
        # Don't initialize for unit tests (requires external resources)
        return manager
        
    def test_draft_state_initialization(self, draft_state):
        """Test basic draft state initialization."""
        assert draft_state.league_id == "262233108"
        assert draft_state.team_id == "1"
        assert draft_state.team_count == 12
        assert draft_state.rounds == 16
        assert draft_state.current_pick == 0
        assert draft_state.draft_status == DraftStatus.WAITING
        assert len(draft_state.drafted_players) == 0
        
    def test_event_processor_message_parsing(self, event_processor):
        """Test Sprint 0 message format parsing."""
        
        # Test SELECTED message
        selected_msg = "SELECTED 1 4362628 1 {856970E3-67E6-42D4-8198-28B1FB3BCA26}"
        parsed = event_processor._parse_message(selected_msg)
        
        assert parsed['type'] == 'SELECTED'
        assert parsed['team_id'] == 1
        assert parsed['player_id'] == '4362628'
        assert parsed['team_draft_position'] == 1  # This is team draft position, not overall pick!
        assert parsed['member_id'] == '{856970E3-67E6-42D4-8198-28B1FB3BCA26}'
        
        # Test SELECTING message  
        selecting_msg = "SELECTING 2 30000"
        parsed = event_processor._parse_message(selecting_msg)
        
        assert parsed['type'] == 'SELECTING'
        assert parsed['team_id'] == 2
        assert parsed['time_ms'] == 30000
        
        # Test CLOCK message
        clock_msg = "CLOCK 6 17239 1"
        parsed = event_processor._parse_message(clock_msg)
        
        assert parsed['type'] == 'CLOCK'
        assert parsed['team_id'] == 6
        assert parsed['time_remaining_ms'] == 17239
        assert parsed['round'] == 1
        
    def test_event_processing_pipeline(self, event_processor, draft_state):
        """Test complete message processing pipeline."""
        
        # Initialize player pool
        draft_state.initialize_player_pool(['4362628', '3918298', '4429795'])
        
        # Process SELECTING message (team 1 on clock)
        selecting_msg = "SELECTING 1 30000"
        success = event_processor.process_websocket_message(selecting_msg)
        
        assert success
        assert draft_state.current_pick == 1
        assert draft_state.on_the_clock == "1"
        assert draft_state.time_remaining == 30.0
        
        # Process SELECTED message (pick made)
        selected_msg = "SELECTED 1 4362628 1 {856970E3-67E6-42D4-8198-28B1FB3BCA26}"
        success = event_processor.process_websocket_message(selected_msg)
        
        assert success
        assert '4362628' in draft_state.drafted_players
        assert '4362628' not in draft_state.available_players
        assert len(draft_state.pick_history) == 1
        assert draft_state.pick_history[0]['player_id'] == '4362628'
        
    def test_sprint_0_message_replay(self, event_processor, draft_state):
        """Test with actual Sprint 0 captured messages."""
        
        # Sample messages from Sprint 0 protocol analysis
        sprint_0_messages = [
            "SELECTING 1 30000",
            "SELECTED 1 3918298 1 {MEMBER_ID}",
            "SELECTING 2 30000", 
            "CLOCK 2 25000 1",
            "CLOCK 2 20000 1",
            "SELECTED 2 4362238 2 {MEMBER_ID}",
            "SELECTING 3 30000",
            "SELECTED 3 4429795 3 {MEMBER_ID}"
        ]
        
        # Initialize available players
        player_ids = ['3918298', '4362238', '4429795', '4890973', '4242335']
        draft_state.initialize_player_pool(player_ids)
        
        # Process messages sequentially
        for msg in sprint_0_messages:
            success = event_processor.process_websocket_message(msg)
            assert success, f"Failed to process message: {msg}"
            
        # Verify final state
        assert draft_state.current_pick == 3
        assert len(draft_state.drafted_players) == 3
        assert '3918298' in draft_state.drafted_players
        assert '4362238' in draft_state.drafted_players 
        assert '4429795' in draft_state.drafted_players
        
        # Verify pick history
        history = draft_state.pick_history
        assert len(history) == 3
        assert history[0]['player_id'] == '3918298'
        assert history[1]['player_id'] == '4362238'
        assert history[2]['player_id'] == '4429795'
        
    def test_state_validation(self, state_handlers, draft_state):
        """Test state consistency validation."""
        
        # Initialize and make some picks
        draft_state.initialize_player_pool(['1001', '1002', '1003'])
        draft_state.apply_pick('1001', '1', 1, 'QB')
        draft_state.apply_pick('1002', '2', 2, 'RB')
        
        # Validate state
        validation = state_handlers.validate_draft_consistency()
        
        assert validation.is_valid
        assert len(validation.errors) == 0
        assert draft_state.current_pick == 2
        assert len(draft_state.drafted_players) == 2
        
    def test_snake_draft_calculation(self, draft_state):
        """Test snake draft position calculations."""
        
        # Set up 12-team draft order
        team_order = [f"team_{i}" for i in range(1, 13)]
        draft_state.set_draft_order(team_order)
        
        # Test our pick positions (if we're team_1, position 0)
        expected_picks = [1, 24, 25, 48, 49, 72, 73, 96, 97, 120, 121, 144, 145, 168, 169, 192]
        assert draft_state._my_pick_positions == expected_picks
        
        # Test picks_until_next calculation
        draft_state._current_pick = 1
        draft_state._update_picks_until_next()
        assert draft_state.picks_until_next == 23  # 24 - 1
        
        draft_state._current_pick = 23
        draft_state._update_picks_until_next()
        assert draft_state.picks_until_next == 1  # 24 - 23
        
    def test_error_handling(self, event_processor):
        """Test error handling for malformed messages."""
        
        # Test malformed messages
        bad_messages = [
            "INVALID_COMMAND",
            "SELECTED 1",  # Too few parameters
            "SELECTING abc 30000",  # Invalid team ID
            "CLOCK 1 abc",  # Invalid time
            ""  # Empty message
        ]
        
        for msg in bad_messages:
            # Should not crash, may return False for some
            try:
                event_processor.process_websocket_message(msg)
            except Exception as e:
                pytest.fail(f"Exception on bad message '{msg}': {e}")
                
    def test_state_snapshots(self, draft_state):
        """Test state snapshot functionality."""
        
        # Make a pick to trigger snapshot
        draft_state.apply_pick('1001', '1', 1, 'QB')
        
        # Should have snapshot
        assert len(draft_state._state_snapshots) > 0
        
        # Get latest snapshot
        snapshot = draft_state.get_snapshot()
        assert snapshot is not None
        assert '1001' in snapshot.drafted_players
        assert snapshot.current_pick == 1
        
        # Test rollback
        draft_state.apply_pick('1002', '2', 2, 'RB')
        assert draft_state.current_pick == 2
        
        # Rollback to first snapshot
        success = draft_state.rollback_to_snapshot(0)
        assert success
        assert draft_state.current_pick == 1
        assert '1002' not in draft_state.drafted_players
        
    def test_performance_requirements(self, event_processor):
        """Test that processing meets <200ms requirement."""
        import time
        
        # Test message processing speed
        test_message = "SELECTED 1 4362628 1 {MEMBER_ID}"
        
        start_time = time.time()
        for _ in range(100):  # Process 100 messages
            event_processor.process_websocket_message(test_message)
        end_time = time.time()
        
        avg_time_per_message = (end_time - start_time) / 100
        avg_time_ms = avg_time_per_message * 1000
        
        # Should be well under 200ms per message
        assert avg_time_ms < 200, f"Average processing time {avg_time_ms:.2f}ms exceeds 200ms requirement"
        
    def test_draft_completion(self, draft_state, state_handlers):
        """Test draft completion handling."""
        
        # Simulate complete draft
        draft_state.initialize_player_pool(['1001', '1002'])
        draft_state.apply_pick('1001', '1', 1, 'QB')
        draft_state.apply_pick('1002', '2', 2, 'RB')
        
        # Complete draft
        validation = state_handlers.handle_draft_completion()
        
        assert draft_state.draft_status == DraftStatus.COMPLETED
        assert draft_state.on_the_clock == ""
        assert draft_state.time_remaining == 0.0
        
    @pytest.mark.asyncio
    async def test_integration_manager_lifecycle(self):
        """Test complete manager lifecycle without external dependencies."""
        
        # Create manager (without initialization that requires external resources)
        manager = DraftStateManager("test_league", "test_team")
        
        # Test basic functionality
        assert manager.league_id == "test_league"
        assert manager.team_id == "test_team"
        assert manager.draft_state is not None
        assert manager.event_processor is not None
        assert manager.state_handlers is not None
        
        # Test state summary
        summary = manager.get_state_summary()
        assert 'league_id' in summary
        assert 'performance' in summary
        
        # Clean up
        await manager.close()


class TestMessageReplay:
    """Test system with complete Sprint 0 message logs."""
    
    @pytest.fixture
    def sample_har_messages(self):
        """Sample WebSocket messages from Sprint 0 HAR files."""
        return [
            "TOKEN 1756607368924",
            "JOINED 1 {MEMBER_ID}",
            "CLOCK 0 76305",
            "SELECTING 1 30000",
            "CLOCK 1 30000 1",
            "CLOCK 1 25000 1",
            "CLOCK 1 20000 1",
            "SELECTED 1 3918298 1 {MEMBER_ID}",
            "AUTOSUGGEST 4262921",
            "SELECTING 2 30000",
            "CLOCK 2 30000 1", 
            "CLOCK 2 25000 1",
            "SELECTED 2 4362238 2 {MEMBER_ID}",
            "SELECTING 3 30000",
            "SELECTED 3 4429795 3 {MEMBER_ID}",
            "PING PING%201756607417674",
            "PONG PING%201756607417674"
        ]
        
    def test_complete_message_replay(self, sample_har_messages):
        """Test complete message sequence from Sprint 0."""
        
        # Create system
        draft_state = DraftState("262233108", "1", 12, 16)
        processor = DraftEventProcessor(draft_state)
        
        # Initialize players from Sprint 0 discovery
        sprint_0_players = [
            '3918298', '4362238', '4429795', '4379399', '4890973', 
            '4242335', '4362628', '4047365', '4430807', '4361307'
        ]
        draft_state.initialize_player_pool(sprint_0_players)
        
        # Process all messages
        processed_count = 0
        for msg in sample_har_messages:
            try:
                success = processor.process_websocket_message(msg)
                if success:
                    processed_count += 1
            except Exception as e:
                pytest.fail(f"Failed on message '{msg}': {e}")
                
        # Verify results match Sprint 0 findings
        assert len(draft_state.drafted_players) == 3  # 3 picks made
        assert draft_state.current_pick == 3
        assert '3918298' in draft_state.drafted_players
        assert '4362238' in draft_state.drafted_players 
        assert '4429795' in draft_state.drafted_players
        
        # Check processing stats
        stats = processor.get_stats()
        assert stats['selected_messages'] == 3
        assert stats['selecting_messages'] == 3
        assert stats['parse_errors'] == 0


if __name__ == "__main__":
    # Set up logging for test runs
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Run tests
    pytest.main([__file__, "-v"])