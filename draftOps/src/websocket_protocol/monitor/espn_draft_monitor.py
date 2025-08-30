import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from playwright.async_api import async_playwright, Page, Browser, WebSocket

class ESPNDraftMonitor:
    """
    ESPN Draft WebSocket Monitor for Sprint 0 reconnaissance.
    
    Connects to ESPN fantasy football draft rooms and monitors WebSocket
    communications to understand the protocol and message structure.
    """
    
    def __init__(self, headless: bool = False, log_level: int = logging.INFO):
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
            self.logger.info(f"Connecting to draft: {draft_url}")
            await self.page.goto(draft_url)
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Check if we're on the draft page
            title = await self.page.title()
            self.logger.info(f"Page loaded: {title}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to draft: {e}")
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
                "is_closed": ws.is_closed()
            }
            for ws in self.websockets
        ]
        
    async def close(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
            
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
        self.logger.info("Browser closed")


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