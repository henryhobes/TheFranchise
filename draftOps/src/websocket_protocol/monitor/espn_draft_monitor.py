import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
from enum import Enum
from playwright.async_api import async_playwright, Page, Browser, WebSocket


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"


class ESPNDraftMonitor:
    """
    ESPN Draft WebSocket Monitor for Sprint 0 reconnaissance.
    
    Connects to ESPN fantasy football draft rooms and monitors WebSocket
    communications to understand the protocol and message structure.
    """
    
    def __init__(self, headless: bool = False, log_level: int = logging.INFO, 
                 enable_recovery: bool = True):
        self.headless = headless
        self.page: Optional[Page] = None
        self.browser: Optional[Browser] = None
        self.websockets: List[WebSocket] = []
        self.message_log: List[Dict[str, Any]] = []
        
        # Set up logging
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Message callbacks
        self.on_message_received: Optional[Callable] = None
        self.on_websocket_opened: Optional[Callable] = None
        self.on_websocket_closed: Optional[Callable] = None
        
        # Connection recovery features
        self.enable_recovery = enable_recovery
        self.connection_state = ConnectionState.DISCONNECTED
        self.last_draft_url: Optional[str] = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delays = [1, 2, 4, 8, 16]  # Exponential backoff in seconds
        
        # Heartbeat monitoring
        self.last_heartbeat_time: Optional[datetime] = None
        self.heartbeat_timeout_seconds = 30  # No heartbeat for 30s = dead connection
        self.heartbeat_monitor_task: Optional[asyncio.Task] = None
        
        # State preservation for recovery
        self.last_known_pick: int = 0
        self.pre_disconnect_state: Dict[str, Any] = {}
        
    async def start_browser(self):
        """Initialize Playwright browser and page."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Set up WebSocket monitoring
        self.page.on("websocket", self._on_websocket)
        
        self.logger.info(f"Browser started (headless={self.headless})")
        
    async def connect_to_draft(self, draft_url: str) -> bool:
        """
        Connect to ESPN draft room and start monitoring WebSocket traffic.
        
        Args:
            draft_url: URL of the ESPN draft room
            
        Returns:
            bool: True if connected successfully
        """
        if not self.page:
            await self.start_browser()
            
        try:
            self.connection_state = ConnectionState.CONNECTING
            self.last_draft_url = draft_url  # Store for reconnection
            
            self.logger.info(f"Connecting to draft: {draft_url}")
            await self.page.goto(draft_url)
            
            # Wait for page to load (increased timeout for slower connections)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            
            # Check if we're on the draft page
            title = await self.page.title()
            self.logger.info(f"Page loaded: {title}")
            
            self.connection_state = ConnectionState.CONNECTED
            
            # Start heartbeat monitoring if recovery is enabled
            if self.enable_recovery and not self.heartbeat_monitor_task:
                self.heartbeat_monitor_task = asyncio.create_task(self._monitor_heartbeat())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to draft: {e}")
            self.connection_state = ConnectionState.FAILED
            return False
            
    def _on_websocket(self, websocket: WebSocket):
        """Handle WebSocket connection events."""
        self.websockets.append(websocket)
        url = websocket.url
        
        self.logger.info(f"WebSocket opened: {url}")
        
        if self.on_websocket_opened:
            self.on_websocket_opened(websocket)
            
        # Set up frame listeners
        websocket.on("framereceived", lambda payload: self._on_frame_received(websocket, payload))
        websocket.on("framesent", lambda payload: self._on_frame_sent(websocket, payload))
        websocket.on("close", lambda: self._on_websocket_close(websocket))
        
    def _on_frame_received(self, websocket: WebSocket, payload: str):
        """Handle incoming WebSocket frames."""
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "direction": "received",
            "websocket_url": websocket.url,
            "payload": payload
        }
        
        self.message_log.append(message_data)
        
        # Update heartbeat time for any message, especially PING/PONG
        if self.enable_recovery:
            self.last_heartbeat_time = datetime.now()
            
            # Track PING/PONG specifically
            if "PING" in payload or "PONG" in payload:
                self.logger.debug(f"Heartbeat received: {payload[:50]}")
            
            # Track pick numbers for state recovery
            if "pickNumber" in payload or "current_pick" in payload:
                try:
                    # Simple extraction - could be enhanced based on actual protocol
                    if "pickNumber" in payload:
                        import re
                        match = re.search(r'"pickNumber":\s*(\d+)', payload)
                        if match:
                            self.last_known_pick = int(match.group(1))
                except Exception:
                    pass  # Non-critical, just for tracking
        
        # Try to parse as JSON for better logging
        try:
            parsed = json.loads(payload)
            self.logger.info(f"[RECV] {websocket.url}: {json.dumps(parsed, indent=2)}")
        except json.JSONDecodeError:
            self.logger.info(f"[RECV] {websocket.url}: {payload}")
            
        if self.on_message_received:
            self.on_message_received("received", websocket, payload)
            
    def _on_frame_sent(self, websocket: WebSocket, payload: str):
        """Handle outgoing WebSocket frames."""
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "direction": "sent",
            "websocket_url": websocket.url,
            "payload": payload
        }
        
        self.message_log.append(message_data)
        
        # Try to parse as JSON for better logging
        try:
            parsed = json.loads(payload)
            self.logger.info(f"[SENT] {websocket.url}: {json.dumps(parsed, indent=2)}")
        except json.JSONDecodeError:
            self.logger.info(f"[SENT] {websocket.url}: {payload}")
            
        if self.on_message_received:
            self.on_message_received("sent", websocket, payload)
            
    def _on_websocket_close(self, websocket: WebSocket):
        """Handle WebSocket close events."""
        self.logger.info(f"WebSocket closed: {websocket.url}")
        
        if websocket in self.websockets:
            self.websockets.remove(websocket)
            
        if self.on_websocket_closed:
            self.on_websocket_closed(websocket)
            
        # Trigger recovery if enabled and this was our main connection
        if self.enable_recovery and self.connection_state == ConnectionState.CONNECTED:
            asyncio.create_task(self.handle_disconnection("WebSocket closed"))
            
    async def monitor_for_duration(self, duration_seconds: int):
        """Monitor WebSocket traffic for a specified duration."""
        self.logger.info(f"Monitoring WebSocket traffic for {duration_seconds} seconds...")
        await asyncio.sleep(duration_seconds)
        self.logger.info("Monitoring duration completed")
        
    async def wait_for_websockets(self, timeout: int = 30) -> bool:
        """
        Wait for WebSocket connections to be established.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if WebSocket connections were detected
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            if self.websockets:
                self.logger.info(f"Found {len(self.websockets)} WebSocket connection(s)")
                return True
                
            await asyncio.sleep(0.5)
            
        self.logger.warning("No WebSocket connections detected within timeout")
        return False
        
    def get_message_log(self) -> List[Dict[str, Any]]:
        """Get all captured WebSocket messages."""
        return self.message_log.copy()
        
    def save_message_log(self, filename: str):
        """Save captured messages to JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.message_log, f, indent=2)
            self.logger.info(f"Message log saved to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save message log: {e}")
            
    def get_websocket_info(self) -> List[Dict[str, str]]:
        """Get information about active WebSocket connections."""
        return [
            {
                "url": ws.url,
                "is_closed": ws.is_closed
            }
            for ws in self.websockets
        ]
        
    async def close(self):
        """Clean up browser resources."""
        # Cancel heartbeat monitor if running
        if self.heartbeat_monitor_task:
            self.heartbeat_monitor_task.cancel()
            try:
                await self.heartbeat_monitor_task
            except asyncio.CancelledError:
                pass
                
        if self.browser:
            await self.browser.close()
            
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
        self.logger.info("Browser closed")
    
    async def handle_disconnection(self, reason: str = "Unknown"):
        """
        Handle WebSocket disconnection and initiate recovery.
        
        Args:
            reason: Reason for disconnection
        """
        if self.connection_state == ConnectionState.RECONNECTING:
            return  # Already reconnecting
            
        self.logger.warning(f"Disconnection detected: {reason}")
        self.connection_state = ConnectionState.RECONNECTING
        
        # Store current state for recovery
        self.pre_disconnect_state = {
            'last_pick': self.last_known_pick,
            'message_count': len(self.message_log),
            'timestamp': datetime.now().isoformat()
        }
        
        # Attempt reconnection with backoff
        success = await self.reconnect_with_backoff()
        
        if success:
            self.logger.info("Successfully reconnected to draft")
            await self.resynchronize_state()
        else:
            self.logger.error("Failed to reconnect after maximum attempts")
            self.connection_state = ConnectionState.FAILED
    
    async def reconnect_with_backoff(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.
        
        Returns:
            bool: True if reconnection successful
        """
        if not self.last_draft_url:
            self.logger.error("No draft URL stored for reconnection")
            return False
            
        for attempt in range(self.max_reconnect_attempts):
            self.reconnect_attempts = attempt + 1
            
            # Calculate delay (0 for first attempt, then exponential backoff)
            delay = 0 if attempt == 0 else self.reconnect_delays[min(attempt - 1, len(self.reconnect_delays) - 1)]
            
            if delay > 0:
                self.logger.info(f"Waiting {delay} seconds before reconnection attempt {attempt + 1}/{self.max_reconnect_attempts}")
                await asyncio.sleep(delay)
            
            self.logger.info(f"Reconnection attempt {attempt + 1}/{self.max_reconnect_attempts}")
            
            try:
                # Clear old WebSocket connections
                self.websockets.clear()
                
                # Try to refresh the page or reconnect
                if self.page:
                    try:
                        # First try to refresh the existing page
                        await self.page.reload(timeout=15000)
                        await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                        
                        # Wait for WebSocket to establish
                        if await self.wait_for_websockets(timeout=10):
                            self.connection_state = ConnectionState.CONNECTED
                            self.reconnect_attempts = 0
                            self.last_heartbeat_time = datetime.now()
                            
                            # Restart heartbeat monitor after successful reconnection
                            if self.enable_recovery:
                                self.heartbeat_monitor_task = asyncio.create_task(self._monitor_heartbeat())
                                self.logger.info("Restarted heartbeat monitor after reconnection")
                            
                            return True
                    except Exception as e:
                        self.logger.debug(f"Page refresh failed: {e}, trying full reconnect")
                
                # If refresh failed, try full reconnection
                if await self.connect_to_draft(self.last_draft_url):
                    self.connection_state = ConnectionState.CONNECTED
                    self.reconnect_attempts = 0
                    return True
                    
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
        
        return False
    
    async def validate_connection_health(self) -> bool:
        """
        Validate WebSocket connection health based on heartbeat.
        
        Returns:
            bool: True if connection is healthy
        """
        if not self.last_heartbeat_time:
            return self.connection_state == ConnectionState.CONNECTED
            
        time_since_heartbeat = (datetime.now() - self.last_heartbeat_time).total_seconds()
        
        if time_since_heartbeat > self.heartbeat_timeout_seconds:
            self.logger.warning(f"No heartbeat for {time_since_heartbeat:.1f} seconds")
            return False
            
        return True
    
    async def _monitor_heartbeat(self):
        """Background task to monitor connection health via heartbeats."""
        self.logger.info("Starting heartbeat monitor")
        
        while self.connection_state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                if self.connection_state == ConnectionState.CONNECTED:
                    if not await self.validate_connection_health():
                        self.logger.warning("Connection appears stalled, triggering recovery")
                        await self.handle_disconnection("Heartbeat timeout")
                        
            except asyncio.CancelledError:
                self.logger.info("Heartbeat monitor cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(5)
    
    async def resynchronize_state(self):
        """
        Resynchronize state after reconnection.
        
        This method compares pre/post disconnect state and attempts to
        fetch any missed information.
        """
        if not self.pre_disconnect_state:
            return
            
        self.logger.info("Resynchronizing state after reconnection")
        
        # Calculate time disconnected
        disconnect_time = self.pre_disconnect_state.get('timestamp')
        if disconnect_time:
            try:
                disconnect_duration = (datetime.now() - datetime.fromisoformat(disconnect_time)).total_seconds()
                self.logger.info(f"Was disconnected for {disconnect_duration:.1f} seconds")
            except Exception:
                pass
        
        # Check if we missed any picks
        old_pick = self.pre_disconnect_state.get('last_pick', 0)
        if self.last_known_pick > old_pick:
            missed_picks = self.last_known_pick - old_pick
            self.logger.info(f"Detected {missed_picks} picks occurred during disconnect")
            
            # Here we would integrate with the ESPN API to fetch missed picks
            # For now, just log that we need to catch up
            self.logger.info(f"Need to fetch picks {old_pick + 1} through {self.last_known_pick}")
            
            # TODO: Integrate with ESPN API client to fetch missed picks
            # This would call something like:
            # missed_data = await self.espn_api.get_picks_range(old_pick + 1, self.last_known_pick)
            # self.process_missed_picks(missed_data)
        else:
            self.logger.info("No picks missed during disconnect")
        
        # Clear pre-disconnect state
        self.pre_disconnect_state = {}


async def main():
    """Example usage for testing the monitor."""
    monitor = ESPNDraftMonitor(headless=False)
    
    try:
        # Example ESPN mock draft URL (would need to be updated with actual URL)
        draft_url = "https://fantasy.espn.com/football/mockdraftlobby"
        
        success = await monitor.connect_to_draft(draft_url)
        if success:
            # Wait for WebSocket connections
            await monitor.wait_for_websockets(timeout=30)
            
            # Monitor for 60 seconds
            await monitor.monitor_for_duration(60)
            
            # Save results
            monitor.save_message_log("espn_websocket_capture.json")
            
            # Print summary
            print(f"Captured {len(monitor.get_message_log())} WebSocket messages")
            print("Active WebSockets:", monitor.get_websocket_info())
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())