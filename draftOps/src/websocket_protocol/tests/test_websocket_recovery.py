#!/usr/bin/env python3
"""
Unit tests for WebSocket connection recovery functionality.

Tests the handle_disconnection, reconnect_with_backoff, validate_connection_health,
and resynchronize_state methods of ESPNDraftMonitor.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from ..monitor.espn_draft_monitor import ESPNDraftMonitor, ConnectionState


class TestWebSocketRecovery:
    """Test suite for WebSocket recovery features."""
    
    @pytest.fixture
    async def monitor(self):
        """Create a test monitor instance."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
        monitor.logger = Mock()  # Mock logger to avoid output during tests
        yield monitor
        # Cleanup
        if monitor.heartbeat_monitor_task:
            monitor.heartbeat_monitor_task.cancel()
            try:
                await monitor.heartbeat_monitor_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_handle_disconnection_stores_state(self, monitor):
        """Test that handle_disconnection properly stores pre-disconnect state."""
        monitor.last_known_pick = 5
        monitor.message_log = [{"msg": "test1"}, {"msg": "test2"}]
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.reconnect_with_backoff = AsyncMock(return_value=True)
        monitor.resynchronize_state = AsyncMock()
        
        await monitor.handle_disconnection("Test disconnect")
        
        assert monitor.pre_disconnect_state['last_pick'] == 5
        assert monitor.pre_disconnect_state['message_count'] == 2
        assert 'timestamp' in monitor.pre_disconnect_state
        monitor.reconnect_with_backoff.assert_called_once()
        monitor.resynchronize_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_disconnection_prevents_duplicate_reconnects(self, monitor):
        """Test that handle_disconnection doesn't trigger if already reconnecting."""
        monitor.connection_state = ConnectionState.RECONNECTING
        monitor.reconnect_with_backoff = AsyncMock()
        
        await monitor.handle_disconnection("Test")
        
        monitor.reconnect_with_backoff.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_reconnect_with_backoff_immediate_success(self, monitor):
        """Test immediate reconnection success (no delay on first attempt)."""
        monitor.last_draft_url = "https://fantasy.espn.com/draft/test"
        monitor.page = AsyncMock()
        monitor.page.reload = AsyncMock()
        monitor.page.wait_for_load_state = AsyncMock()
        monitor.wait_for_websockets = AsyncMock(return_value=True)
        
        start_time = datetime.now()
        success = await monitor.reconnect_with_backoff()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        assert success is True
        assert elapsed < 1  # Should be immediate (no delay on first attempt)
        assert monitor.connection_state == ConnectionState.CONNECTED
        assert monitor.reconnect_attempts == 0
    
    @pytest.mark.asyncio
    async def test_reconnect_with_backoff_exponential_delays(self, monitor):
        """Test exponential backoff delays on reconnection failures."""
        monitor.last_draft_url = "https://fantasy.espn.com/draft/test"
        monitor.max_reconnect_attempts = 3
        monitor.reconnect_delays = [1, 2, 4]
        
        # Mock page refresh to fail
        monitor.page = AsyncMock()
        monitor.page.reload = AsyncMock(side_effect=Exception("Network error"))
        monitor.connect_to_draft = AsyncMock(return_value=False)
        
        # Track sleep calls
        sleep_delays = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            sleep_delays.append(delay)
            if delay > 0.1:  # Only track backoff delays, not small internal delays
                return await original_sleep(0.01)  # Speed up test
            return await original_sleep(delay)
        
        with patch('asyncio.sleep', mock_sleep):
            success = await monitor.reconnect_with_backoff()
        
        assert success is False
        # First attempt has no delay, then 1s, 2s
        expected_delays = [1, 2]
        actual_backoff_delays = [d for d in sleep_delays if d >= 1]
        assert actual_backoff_delays == expected_delays
    
    @pytest.mark.asyncio
    async def test_validate_connection_health_with_recent_heartbeat(self, monitor):
        """Test connection health validation with recent heartbeat."""
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.last_heartbeat_time = datetime.now() - timedelta(seconds=10)
        monitor.heartbeat_timeout_seconds = 30
        
        is_healthy = await monitor.validate_connection_health()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_validate_connection_health_timeout(self, monitor):
        """Test connection health validation detects timeout."""
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.last_heartbeat_time = datetime.now() - timedelta(seconds=35)
        monitor.heartbeat_timeout_seconds = 30
        
        is_healthy = await monitor.validate_connection_health()
        
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_validate_connection_health_no_heartbeat(self, monitor):
        """Test connection health with no heartbeat recorded."""
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.last_heartbeat_time = None
        
        is_healthy = await monitor.validate_connection_health()
        
        assert is_healthy is True  # Assumes connected if no heartbeat yet
    
    @pytest.mark.asyncio
    async def test_heartbeat_monitoring_triggers_recovery(self, monitor):
        """Test that heartbeat monitor triggers recovery on timeout."""
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.last_heartbeat_time = datetime.now() - timedelta(seconds=35)
        monitor.heartbeat_timeout_seconds = 30
        monitor.handle_disconnection = AsyncMock()
        
        # Run one iteration of heartbeat monitor
        monitor._monitor_heartbeat_task = asyncio.create_task(monitor._monitor_heartbeat())
        await asyncio.sleep(6)  # Let it run one check cycle
        monitor._monitor_heartbeat_task.cancel()
        try:
            await monitor._monitor_heartbeat_task
        except asyncio.CancelledError:
            pass
        
        monitor.handle_disconnection.assert_called_with("Heartbeat timeout")
    
    @pytest.mark.asyncio
    async def test_frame_received_updates_heartbeat(self, monitor):
        """Test that receiving frames updates heartbeat time."""
        monitor.enable_recovery = True
        websocket = Mock()
        websocket.url = "wss://test.espn.com"
        
        # Test PING message
        before_time = datetime.now()
        monitor._on_frame_received(websocket, "PING PING%201756607417674")
        
        assert monitor.last_heartbeat_time is not None
        assert monitor.last_heartbeat_time >= before_time
        
        # Test PONG message
        await asyncio.sleep(0.01)
        before_time = datetime.now()
        monitor._on_frame_received(websocket, "PONG PING%201756607417674")
        
        assert monitor.last_heartbeat_time >= before_time
    
    @pytest.mark.asyncio
    async def test_frame_received_tracks_pick_number(self, monitor):
        """Test that receiving frames with pick numbers updates tracking."""
        monitor.enable_recovery = True
        websocket = Mock()
        websocket.url = "wss://test.espn.com"
        
        # Test pick number extraction
        monitor._on_frame_received(websocket, '{"type":"PICK_MADE","pickNumber":7,"player":"Test"}')
        
        assert monitor.last_known_pick == 7
    
    @pytest.mark.asyncio
    async def test_resynchronize_state_no_missed_picks(self, monitor):
        """Test state resynchronization when no picks were missed."""
        monitor.pre_disconnect_state = {
            'last_pick': 5,
            'message_count': 100,
            'timestamp': datetime.now().isoformat()
        }
        monitor.last_known_pick = 5  # Same as before disconnect
        
        await monitor.resynchronize_state()
        
        # Should log no picks missed
        assert monitor.pre_disconnect_state == {}  # State should be cleared
    
    @pytest.mark.asyncio
    async def test_resynchronize_state_with_missed_picks(self, monitor):
        """Test state resynchronization when picks were missed."""
        monitor.pre_disconnect_state = {
            'last_pick': 5,
            'message_count': 100,
            'timestamp': (datetime.now() - timedelta(seconds=10)).isoformat()
        }
        monitor.last_known_pick = 8  # 3 picks happened during disconnect
        
        await monitor.resynchronize_state()
        
        # Should detect 3 missed picks (6, 7, 8)
        assert monitor.pre_disconnect_state == {}  # State should be cleared
    
    @pytest.mark.asyncio
    async def test_websocket_close_triggers_recovery(self, monitor):
        """Test that WebSocket close event triggers recovery."""
        monitor.enable_recovery = True
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.handle_disconnection = AsyncMock()
        
        websocket = Mock()
        websocket.url = "wss://test.espn.com"
        monitor.websockets = [websocket]
        
        monitor._on_websocket_close(websocket)
        
        # Should trigger recovery
        await asyncio.sleep(0.01)  # Let async task start
        monitor.handle_disconnection.assert_called()
    
    @pytest.mark.asyncio
    async def test_reconnect_clears_old_websockets(self, monitor):
        """Test that reconnection clears old WebSocket connections."""
        monitor.last_draft_url = "https://fantasy.espn.com/draft/test"
        old_ws = Mock()
        monitor.websockets = [old_ws]
        
        monitor.page = AsyncMock()
        monitor.page.reload = AsyncMock()
        monitor.page.wait_for_load_state = AsyncMock()
        monitor.wait_for_websockets = AsyncMock(return_value=True)
        
        await monitor.reconnect_with_backoff()
        
        assert old_ws not in monitor.websockets  # Old WebSocket should be cleared
    
    @pytest.mark.asyncio
    async def test_reconnect_fallback_to_full_connection(self, monitor):
        """Test fallback from page refresh to full reconnection."""
        monitor.last_draft_url = "https://fantasy.espn.com/draft/test"
        
        # Mock page refresh to fail
        monitor.page = AsyncMock()
        monitor.page.reload = AsyncMock(side_effect=Exception("Refresh failed"))
        
        # Mock full reconnection to succeed
        monitor.connect_to_draft = AsyncMock(return_value=True)
        
        success = await monitor.reconnect_with_backoff()
        
        assert success is True
        monitor.connect_to_draft.assert_called_with(monitor.last_draft_url)
    
    @pytest.mark.asyncio
    async def test_max_reconnect_attempts_respected(self, monitor):
        """Test that maximum reconnection attempts limit is respected."""
        monitor.last_draft_url = "https://fantasy.espn.com/draft/test"
        monitor.max_reconnect_attempts = 2
        monitor.reconnect_delays = [0.01, 0.01]  # Short delays for testing
        
        # Mock all reconnection attempts to fail
        monitor.page = AsyncMock()
        monitor.page.reload = AsyncMock(side_effect=Exception("Failed"))
        monitor.connect_to_draft = AsyncMock(return_value=False)
        
        success = await monitor.reconnect_with_backoff()
        
        assert success is False
        assert monitor.connect_to_draft.call_count == 2  # Should try exactly max attempts


class TestConnectionStateTransitions:
    """Test connection state transitions."""
    
    @pytest.mark.asyncio
    async def test_state_transitions_during_normal_connection(self):
        """Test state transitions during normal connection flow."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
        monitor.logger = Mock()
        
        # Initial state
        assert monitor.connection_state == ConnectionState.DISCONNECTED
        
        # Mock browser and page
        monitor.page = AsyncMock()
        monitor.page.goto = AsyncMock()
        monitor.page.wait_for_load_state = AsyncMock()
        monitor.page.title = AsyncMock(return_value="ESPN Draft")
        
        # Connect
        await monitor.connect_to_draft("https://fantasy.espn.com/draft/test")
        assert monitor.connection_state == ConnectionState.CONNECTED
        
        # Cleanup
        if monitor.heartbeat_monitor_task:
            monitor.heartbeat_monitor_task.cancel()
            try:
                await monitor.heartbeat_monitor_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_state_transitions_during_recovery(self):
        """Test state transitions during recovery flow."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
        monitor.logger = Mock()
        monitor.connection_state = ConnectionState.CONNECTED
        monitor.last_draft_url = "https://fantasy.espn.com/draft/test"
        
        # Mock successful reconnection
        monitor.reconnect_with_backoff = AsyncMock(return_value=True)
        monitor.resynchronize_state = AsyncMock()
        
        await monitor.handle_disconnection("Test")
        
        # Should transition through RECONNECTING during handle_disconnection
        # and end up CONNECTED after successful reconnection
        monitor.reconnect_with_backoff.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_state_transitions_on_failure(self):
        """Test state transitions when recovery fails."""
        monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
        monitor.logger = Mock()
        monitor.connection_state = ConnectionState.CONNECTED
        
        # Mock failed reconnection
        monitor.reconnect_with_backoff = AsyncMock(return_value=False)
        
        await monitor.handle_disconnection("Test")
        
        assert monitor.connection_state == ConnectionState.FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])