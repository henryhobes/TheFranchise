#!/usr/bin/env python3
"""
Proof of Concept: ESPN Draft Logger

Simple script demonstrating real-time WebSocket monitoring of ESPN drafts.
This validates our ability to capture draft events as they happen.

Usage:
    python poc_draft_logger.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from monitor.espn_draft_monitor import ESPNDraftMonitor


class SimpleDraftLogger:
    """Minimal proof-of-concept draft event logger."""
    
    def __init__(self):
        self.monitor = ESPNDraftMonitor(headless=False)
        self.draft_events = []
        self.setup_callbacks()
        
    def setup_callbacks(self):
        """Set up event callbacks."""
        
        def on_websocket_opened(websocket):
            print(f"✅ Connected to WebSocket: {websocket.url}")
            
        def on_message_received(direction, websocket, payload):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Look for potential draft events
            is_draft_event = self.is_potential_draft_event(payload)
            
            if is_draft_event:
                print(f"🎯 [{timestamp}] DRAFT EVENT DETECTED")
                self.draft_events.append({
                    "timestamp": timestamp,
                    "direction": direction,
                    "websocket": websocket.url,
                    "payload": payload
                })
                
                # Try to parse and display nicely
                try:
                    parsed = json.loads(payload)
                    print(f"   📋 {json.dumps(parsed, indent=4)}")
                except:
                    print(f"   📋 {payload}")
                    
            else:
                # Just show a brief indicator for non-draft messages
                print(f"   [{timestamp}] {direction}: {len(payload)} bytes")
                
        self.monitor.on_websocket_opened = on_websocket_opened
        self.monitor.on_message_received = on_message_received
        
    def is_potential_draft_event(self, payload: str) -> bool:
        """
        Simple heuristic to identify potential draft events.
        This will be refined based on actual ESPN protocol analysis.
        """
        # Look for draft-related keywords
        draft_keywords = [
            "pick", "draft", "player", "team", "roster", 
            "clock", "turn", "selected", "available",
            "PICK_MADE", "ON_THE_CLOCK", "ROSTER_UPDATE"
        ]
        
        payload_lower = payload.lower()
        return any(keyword.lower() in payload_lower for keyword in draft_keywords)
        
    async def run_logger(self, duration: int = 600):
        """
        Run the draft logger for a specified duration.
        
        Args:
            duration: How long to run in seconds (default 10 minutes)
        """
        print("🚀 ESPN Draft Logger - Proof of Concept")
        print("=" * 50)
        print("This script will:")
        print("1. Open ESPN mock draft lobby")
        print("2. Wait for you to join a draft")
        print("3. Monitor and log draft events in real-time")
        print("4. Save results for analysis")
        print()
        
        try:
            # Connect to ESPN mock draft
            mock_draft_url = "https://fantasy.espn.com/football/mockdraftlobby"
            print(f"🔗 Opening ESPN mock draft lobby...")
            
            success = await self.monitor.connect_to_draft(mock_draft_url)
            if not success:
                print("❌ Failed to connect")
                return
                
            print("✅ Connected to ESPN")
            print()
            print("📍 NEXT STEPS:")
            print("   1. Navigate to and join a mock draft in the browser")
            print("   2. Watch this console for real-time draft events")
            print("   3. Let a few picks happen to test the system")
            print()
            
            # Wait for WebSocket connections
            print("⏳ Waiting for WebSocket connections...")
            found_websockets = await self.monitor.wait_for_websockets(timeout=120)
            
            if found_websockets:
                print(f"✅ Monitoring {len(self.monitor.websockets)} WebSocket connection(s)")
                print("🎯 Watching for draft events...")
                print()
                
                # Monitor for the specified duration
                await self.monitor.monitor_for_duration(duration)
                
            else:
                print("❌ No WebSocket connections found")
                print("   Make sure you joined a draft room")
                
        except KeyboardInterrupt:
            print("\n⏹️  Logging stopped by user")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        finally:
            await self.save_results()
            
    async def save_results(self):
        """Save captured results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create reports directory
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Save full message log
        log_file = reports_dir / f"poc_full_log_{timestamp}.json"
        self.monitor.save_message_log(str(log_file))
        
        # Save just the draft events
        events_file = reports_dir / f"poc_draft_events_{timestamp}.json"
        try:
            with open(events_file, 'w') as f:
                json.dump(self.draft_events, f, indent=2)
        except Exception as e:
            print(f"Failed to save draft events: {e}")
            
        # Print summary
        print("\n📊 Session Summary:")
        print("=" * 30)
        print(f"Total messages: {len(self.monitor.get_message_log())}")
        print(f"Draft events detected: {len(self.draft_events)}")
        print(f"WebSocket connections: {len(self.monitor.get_websocket_info())}")
        print()
        print("💾 Files saved:")
        print(f"   • Full log: {log_file}")
        print(f"   • Draft events: {events_file}")
        
        if self.draft_events:
            print("\n🎯 Draft Events Summary:")
            for i, event in enumerate(self.draft_events[-5:]):  # Show last 5
                print(f"   {i+1}. [{event['timestamp']}] {event['direction']} - {len(event['payload'])} bytes")
                
        await self.monitor.close()


async def main():
    logger = SimpleDraftLogger()
    await logger.run_logger(duration=600)  # Run for 10 minutes


if __name__ == "__main__":
    print("""
    🏈 ESPN Draft Logger - Proof of Concept
    =====================================
    
    This tool demonstrates real-time draft event monitoring.
    
    INSTRUCTIONS:
    1. Script will open ESPN mock draft lobby
    2. Navigate to and JOIN a mock draft in the browser
    3. Watch this console for detected draft events
    4. Results will be saved in the 'reports' folder
    
    Ready? Press Ctrl+C anytime to stop.
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"Error: {e}")