#!/usr/bin/env python3
"""
Integration tests for WebSocket connection recovery.

Tests end-to-end recovery scenarios including simulated disconnections,
state preservation, and real-world recovery patterns.
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from ..monitor.espn_draft_monitor import ESPNDraftMonitor, ConnectionState
from ..state.draft_state import DraftState


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, url: str):
        self.url = url
        self.is_closed = False
        self.message_handlers = {}
        self.close_handlers = []
        
    def on(self, event: str, handler):
        """Register event handler."""
        if event == "close":
            self.close_handlers.append(handler)
        else:
            self.message_handlers[event] = handler
    
    def simulate_message(self, message: str):
        """Simulate receiving a message."""
        if "framereceived" in self.message_handlers:
            self.message_handlers["framereceived"](message)
    
    def simulate_close(self):
        """Simulate WebSocket close."""
        self.is_closed = True
        for handler in self.close_handlers:
            handler()


class TestRecoveryIntegration:
    """Integration tests for WebSocket recovery."""
    
    @pytest.fixture
    async def monitor_with_state(self):
        """Create monitor with mock state tracking."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
        monitor.logger = Mock()  # Suppress log output during tests
        
        # Mock browser setup
        monitor.page = AsyncMock()
        monitor.page.goto = AsyncMock()
        monitor.page.wait_for_load_state = AsyncMock()
        monitor.page.title = AsyncMock(return_value="ESPN Draft Room")
        monitor.page.reload = AsyncMock()
        monitor.wait_for_websockets = AsyncMock(return_value=True)
        
        yield monitor
        
        # Cleanup
        if monitor.heartbeat_monitor_task and not monitor.heartbeat_monitor_task.done():
            monitor.heartbeat_monitor_task.cancel()
            try:
                await monitor.heartbeat_monitor_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_end_to_end_recovery_with_pick_sync(self, monitor_with_state):
        """Test complete recovery flow including pick synchronization."""
        monitor = monitor_with_state
        
        # Step 1: Establish initial connection
        success = await monitor.connect_to_draft("https://fantasy.espn.com/draft/123")
        assert success
        assert monitor.connection_state == ConnectionState.CONNECTED
        
        # Step 2: Simulate receiving some draft messages
        mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/123")
        monitor.websockets = [mock_ws]
        
        # Simulate initial pick messages
        mock_ws.simulate_message('{"type":"PICK_MADE","pickNumber":1,"player":"Josh Allen"}')
        mock_ws.simulate_message('{"type":"PICK_MADE","pickNumber":2,"player":"CMC"}')
        mock_ws.simulate_message('PING PING%201756607417674')
        
        assert monitor.last_known_pick == 2
        assert monitor.last_heartbeat_time is not None
        
        # Step 3: Simulate disconnection
        original_state = {
            'last_pick': monitor.last_known_pick,
            'heartbeat_time': monitor.last_heartbeat_time
        }
        
        # Simulate WebSocket close
        mock_ws.simulate_close()
        
        # Wait for disconnection handling to complete
        await asyncio.sleep(0.1)
        
        # Should have triggered recovery
        assert monitor.connection_state == ConnectionState.CONNECTED  # Successfully reconnected
        
        # Step 4: Verify state preservation
        assert monitor.pre_disconnect_state == {}  # Should be cleared after successful recovery
        
        # Step 5: Simulate messages that occurred during disconnect
        new_mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/123")
        monitor.websockets = [new_mock_ws]
        
        # Simulate pick that happened during disconnect
        new_mock_ws.simulate_message('{"type":"PICK_MADE","pickNumber":5,"player":"Tyreek Hill"}')
        
        # Should detect missed picks
        assert monitor.last_known_pick == 5
    
    @pytest.mark.asyncio
    async def test_recovery_during_rapid_picks(self, monitor_with_state):
        """Test recovery when disconnection occurs during rapid pick sequence."""
        monitor = monitor_with_state
        
        await monitor.connect_to_draft("https://fantasy.espn.com/draft/456")
        
        # Simulate rapid picks before disconnect
        mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/456")
        monitor.websockets = [mock_ws]
        
        for pick_num in range(1, 6):  # Picks 1-5
            mock_ws.simulate_message(f'{{"type":"PICK_MADE","pickNumber":{pick_num},"player":"Player{pick_num}"}}')
        
        assert monitor.last_known_pick == 5
        
        # Simulate disconnect during pick 6
        mock_ws.simulate_close()
        await asyncio.sleep(0.1)
        
        # After reconnect, simulate catching up on missed picks
        new_mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/456")
        monitor.websockets = [new_mock_ws]
        
        # Multiple picks happened during disconnect
        for pick_num in range(8, 11):  # Picks 8-10
            new_mock_ws.simulate_message(f'{{"type":"PICK_MADE","pickNumber":{pick_num},"player":"Player{pick_num}"}}')
        
        # Should detect 5 missed picks (6, 7, 8, 9, 10)
        assert monitor.last_known_pick == 10
    
    @pytest.mark.asyncio
    async def test_heartbeat_timeout_recovery(self, monitor_with_state):
        """Test recovery triggered by heartbeat timeout."""
        monitor = monitor_with_state
        monitor.heartbeat_timeout_seconds = 1  # Very short timeout for testing
        
        await monitor.connect_to_draft("https://fantasy.espn.com/draft/789")
        
        # Establish initial heartbeat
        mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/789")
        monitor.websockets = [mock_ws]
        mock_ws.simulate_message("PING PING%201756607417674")
        
        initial_heartbeat = monitor.last_heartbeat_time
        assert initial_heartbeat is not None
        
        # Mock handle_disconnection to track if it's called
        original_handler = monitor.handle_disconnection
        monitor.handle_disconnection = AsyncMock()
        
        # Start heartbeat monitoring and let timeout occur
        monitor.heartbeat_monitor_task = asyncio.create_task(monitor._monitor_heartbeat())
        
        # Wait longer than timeout
        await asyncio.sleep(2)
        
        # Should have detected timeout and triggered recovery
        monitor.handle_disconnection.assert_called_with("Heartbeat timeout")
        
        # Restore original handler and cleanup
        monitor.handle_disconnection = original_handler
        monitor.heartbeat_monitor_task.cancel()
        try:
            await monitor.heartbeat_monitor_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_multiple_reconnection_attempts(self, monitor_with_state):
        """Test multiple reconnection attempts with backoff."""
        monitor = monitor_with_state
        monitor.max_reconnect_attempts = 3
        monitor.reconnect_delays = [0.1, 0.2, 0.3]  # Short delays for testing
        
        # Mock page reload to fail initially, then succeed
        reload_attempts = []
        
        async def mock_reload(timeout=None):
            reload_attempts.append(len(reload_attempts) + 1)
            if len(reload_attempts) < 3:
                raise Exception(f"Mock network error on attempt {len(reload_attempts)}")
        
        monitor.page.reload = mock_reload
        
        # Start with connected state
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.last_draft_url = "https://fantasy.espn.com/draft/reconnect"
        
        # Trigger disconnection
        start_time = datetime.now()
        success = await monitor.reconnect_with_backoff()
        end_time = datetime.now()
        
        # Should have succeeded on 3rd attempt
        assert success is True
        assert len(reload_attempts) == 3
        
        # Should have taken at least 0.1 + 0.2 seconds (backoff delays)
        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 0.3
    
    @pytest.mark.asyncio
    async def test_recovery_with_draft_state_integration(self, monitor_with_state):
        """Test recovery integration with DraftState object."""
        monitor = monitor_with_state
        
        # Create a draft state instance
        draft_state = DraftState(league_id="123", team_id="1", team_count=10)
        draft_state.initialize_player_pool(["player1", "player2", "player3", "player4"])
        draft_state.set_draft_order(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
        
        # Connect and start receiving messages
        await monitor.connect_to_draft("https://fantasy.espn.com/draft/with-state")
        
        mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/with-state")
        monitor.websockets = [mock_ws]
        
        # Simulate draft progression
        draft_state.apply_pick("player1", "2", 1)
        mock_ws.simulate_message('{"type":"PICK_MADE","pickNumber":1,"playerId":"player1"}')
        
        draft_state.apply_pick("player2", "3", 2)
        mock_ws.simulate_message('{"type":"PICK_MADE","pickNumber":2,"playerId":"player2"}')
        
        assert monitor.last_known_pick == 2
        assert len(draft_state.drafted_players) == 2
        
        # Store state before disconnect
        pre_disconnect_picks = draft_state.current_pick
        pre_disconnect_drafted = len(draft_state.drafted_players)
        
        # Simulate disconnect
        mock_ws.simulate_close()
        await asyncio.sleep(0.1)
        
        # After reconnect, simulate additional picks that happened during disconnect
        new_mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/with-state")
        monitor.websockets = [new_mock_ws]
        
        # Draft state would need to be updated with missed picks here
        # This simulates what would happen with API integration
        draft_state.apply_pick("player3", "4", 3)
        new_mock_ws.simulate_message('{"type":"PICK_MADE","pickNumber":3,"playerId":"player3"}')
        
        # Verify state synchronization
        assert monitor.last_known_pick == 3
        assert len(draft_state.drafted_players) == 3
    
    @pytest.mark.asyncio
    async def test_recovery_state_validation(self, monitor_with_state):
        """Test that recovery properly validates and logs state changes."""
        monitor = monitor_with_state
        
        await monitor.connect_to_draft("https://fantasy.espn.com/draft/validation")
        
        # Set up initial state
        mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/validation")
        monitor.websockets = [mock_ws]
        monitor.last_known_pick = 3
        monitor.message_log = [{"msg": f"message_{i}"} for i in range(50)]
        
        # Simulate disconnection
        await monitor.handle_disconnection("Network timeout")
        
        # Verify pre-disconnect state was captured
        expected_state = {
            'last_pick': 3,
            'message_count': 50,
            'timestamp': monitor.pre_disconnect_state['timestamp']  # Dynamic timestamp
        }
        
        assert monitor.pre_disconnect_state['last_pick'] == 3
        assert monitor.pre_disconnect_state['message_count'] == 50
        assert 'timestamp' in monitor.pre_disconnect_state
    
    @pytest.mark.asyncio
    async def test_disabled_recovery_mode(self):
        """Test monitor behavior when recovery is disabled."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=False)
        monitor.logger = Mock()
        
        # Mock browser setup
        monitor.page = AsyncMock()
        monitor.page.goto = AsyncMock()
        monitor.page.wait_for_load_state = AsyncMock()
        monitor.page.title = AsyncMock(return_value="ESPN Draft")
        
        await monitor.connect_to_draft("https://fantasy.espn.com/draft/no-recovery")
        
        # Should not start heartbeat monitoring
        assert monitor.heartbeat_monitor_task is None
        
        # Simulate WebSocket close
        mock_ws = MockWebSocket("wss://draft.fantasy.espn.com/no-recovery")
        monitor.websockets = [mock_ws]
        
        # Mock handle_disconnection to verify it's not called
        monitor.handle_disconnection = AsyncMock()
        
        mock_ws.simulate_close()
        await asyncio.sleep(0.1)
        
        # Should not trigger recovery
        monitor.handle_disconnection.assert_not_called()


class TestRecoveryPerformance:
    """Performance tests for recovery functionality."""
    
    @pytest.mark.asyncio
    async def test_recovery_speed(self):
        """Test that recovery completes within acceptable time limits."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
        monitor.logger = Mock()
        
        # Mock fast reconnection
        monitor.page = AsyncMock()
        monitor.page.reload = AsyncMock()
        monitor.page.wait_for_load_state = AsyncMock()
        monitor.wait_for_websockets = AsyncMock(return_value=True)
        monitor.last_draft_url = "https://fantasy.espn.com/draft/speed-test"
        monitor.connection_state = ConnectionState.CONNECTED
        
        # Measure recovery time
        start_time = datetime.now()
        await monitor.handle_disconnection("Speed test")
        end_time = datetime.now()
        
        recovery_time = (end_time - start_time).total_seconds()
        
        # Should recover in under 2 seconds for immediate reconnect
        assert recovery_time < 2.0
        
        # Cleanup
        if monitor.heartbeat_monitor_task:
            monitor.heartbeat_monitor_task.cancel()
            try:
                await monitor.heartbeat_monitor_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_heartbeat_monitoring_overhead(self):
        """Test that heartbeat monitoring has minimal performance impact."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
        monitor.logger = Mock()
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.last_heartbeat_time = datetime.now()
        
        # Start heartbeat monitoring
        monitor.heartbeat_monitor_task = asyncio.create_task(monitor._monitor_heartbeat())
        
        # Let it run for a short time
        start_time = datetime.now()
        await asyncio.sleep(1)
        
        # Should still be running efficiently
        assert not monitor.heartbeat_monitor_task.done()
        
        # Cleanup
        monitor.heartbeat_monitor_task.cancel()
        try:
            await monitor.heartbeat_monitor_task
        except asyncio.CancelledError:
            pass
        
        # Test passed if we reach here without hanging


if __name__ == "__main__":
    pytest.main([__file__, "-v"])