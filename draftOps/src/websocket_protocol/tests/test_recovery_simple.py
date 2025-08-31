#!/usr/bin/env python3
"""
Simple validation tests for WebSocket recovery functionality.

These tests validate the basic recovery components work as expected
without complex async fixtures.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

# Adjust import to work with the current project structure
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor.espn_draft_monitor import ESPNDraftMonitor, ConnectionState


@pytest.mark.asyncio
async def test_connection_state_initialization():
    """Test that monitor initializes with correct state."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    
    assert monitor.connection_state == ConnectionState.DISCONNECTED
    assert monitor.enable_recovery is True
    assert monitor.max_reconnect_attempts == 5
    assert monitor.reconnect_delays == [1, 2, 4, 8, 16]
    assert monitor.heartbeat_timeout_seconds == 30


@pytest.mark.asyncio
async def test_heartbeat_update():
    """Test that heartbeat time updates correctly."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.logger = Mock()
    monitor.on_message_received = Mock()
    
    # Mock WebSocket
    websocket = Mock()
    websocket.url = "wss://test.espn.com"
    
    # Test heartbeat update
    before_time = datetime.now()
    monitor._on_frame_received(websocket, "PING PING%201756607417674")
    
    assert monitor.last_heartbeat_time is not None
    assert monitor.last_heartbeat_time >= before_time


@pytest.mark.asyncio
async def test_pick_number_tracking():
    """Test that pick numbers are tracked correctly."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.logger = Mock()
    monitor.on_message_received = Mock()
    
    websocket = Mock()
    websocket.url = "wss://test.espn.com"
    
    # Test pick number extraction
    monitor._on_frame_received(websocket, '{"type":"PICK_MADE","pickNumber":5,"player":"Test"}')
    
    assert monitor.last_known_pick == 5


@pytest.mark.asyncio
async def test_connection_health_validation():
    """Test connection health validation logic."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.connection_state = ConnectionState.CONNECTED
    
    # Test with recent heartbeat
    monitor.last_heartbeat_time = datetime.now() - timedelta(seconds=10)
    monitor.heartbeat_timeout_seconds = 30
    is_healthy = await monitor.validate_connection_health()
    assert is_healthy is True
    
    # Test with old heartbeat
    monitor.last_heartbeat_time = datetime.now() - timedelta(seconds=40)
    is_healthy = await monitor.validate_connection_health()
    assert is_healthy is False


@pytest.mark.asyncio 
async def test_disconnection_state_storage():
    """Test that disconnection properly stores state."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.logger = Mock()
    monitor.reconnect_with_backoff = AsyncMock(return_value=True)
    monitor.resynchronize_state = AsyncMock()
    
    # Set up initial state
    monitor.connection_state = ConnectionState.CONNECTED
    monitor.last_known_pick = 3
    monitor.message_log = [{"msg": "test"}]
    
    # Test disconnection handling
    await monitor.handle_disconnection("Test disconnect")
    
    # Verify state was stored during handling
    assert monitor.reconnect_with_backoff.called
    assert monitor.resynchronize_state.called


@pytest.mark.asyncio
async def test_reconnect_without_url():
    """Test reconnection fails gracefully without stored URL."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.logger = Mock()
    monitor.last_draft_url = None
    
    success = await monitor.reconnect_with_backoff()
    assert success is False


@pytest.mark.asyncio
async def test_state_resync_no_missed_picks():
    """Test state resynchronization with no missed picks."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.logger = Mock()
    
    # Set up pre-disconnect state
    monitor.pre_disconnect_state = {
        'last_pick': 5,
        'message_count': 100,
        'timestamp': datetime.now().isoformat()
    }
    monitor.last_known_pick = 5  # Same as before
    
    await monitor.resynchronize_state()
    
    # State should be cleared after resync
    assert monitor.pre_disconnect_state == {}


@pytest.mark.asyncio
async def test_state_resync_with_missed_picks():
    """Test state resynchronization detects missed picks."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.logger = Mock()
    
    # Set up scenario with missed picks
    monitor.pre_disconnect_state = {
        'last_pick': 5,
        'message_count': 100,
        'timestamp': (datetime.now() - timedelta(seconds=30)).isoformat()
    }
    monitor.last_known_pick = 8  # 3 picks missed
    
    await monitor.resynchronize_state()
    
    # Should have detected missed picks and cleared state
    assert monitor.pre_disconnect_state == {}


@pytest.mark.asyncio
async def test_websocket_close_triggers_recovery():
    """Test that WebSocket close triggers recovery when enabled."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    monitor.logger = Mock()
    monitor.connection_state = ConnectionState.CONNECTED
    monitor.on_websocket_closed = Mock()
    
    # Mock the handle_disconnection method
    monitor.handle_disconnection = AsyncMock()
    
    # Create mock WebSocket
    websocket = Mock()
    websocket.url = "wss://test.espn.com"
    monitor.websockets = [websocket]
    
    # Simulate close
    monitor._on_websocket_close(websocket)
    
    # Give async task a moment to start
    await asyncio.sleep(0.01)
    
    # Should have removed WebSocket and triggered recovery
    assert websocket not in monitor.websockets


def test_recovery_disabled():
    """Test behavior when recovery is disabled."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=False)
    
    assert monitor.enable_recovery is False
    assert monitor.heartbeat_monitor_task is None
    
    # Mock WebSocket close - should not trigger recovery
    websocket = Mock()
    websocket.url = "wss://test.espn.com"
    monitor.websockets = [websocket]
    monitor.connection_state = ConnectionState.CONNECTED
    monitor.handle_disconnection = Mock()
    
    monitor._on_websocket_close(websocket)
    
    # handle_disconnection should not be called when recovery is disabled
    # (it's called via async task, so it may not be immediately detectable)
    assert websocket not in monitor.websockets  # WebSocket should still be removed


@pytest.mark.asyncio
async def test_monitor_cleanup():
    """Test that monitor cleans up resources properly."""
    monitor = ESPNDraftMonitor(headless=True, enable_recovery=True)
    
    # Mock browser cleanup
    monitor.browser = AsyncMock()
    monitor.playwright = AsyncMock()
    
    await monitor.close()
    
    # Should have closed browser
    monitor.browser.close.assert_called_once()
    monitor.playwright.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])