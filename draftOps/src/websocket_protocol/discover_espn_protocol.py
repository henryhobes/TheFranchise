#!/usr/bin/env python3
"""
ESPN Draft WebSocket Protocol Discovery Script

This script connects to ESPN mock drafts and captures WebSocket traffic
to reverse engineer their draft protocol. Part of Sprint 0 reconnaissance.

Usage:
    python discover_espn_protocol.py [--headless] [--duration SECONDS]
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path

from monitor.espn_draft_monitor import ESPNDraftMonitor
from utils.websocket_discovery import WebSocketDiscovery


class ESPNProtocolDiscovery:
    """Main class orchestrating ESPN draft protocol discovery."""
    
    def __init__(self, headless: bool = False):
        self.monitor = ESPNDraftMonitor(headless=headless)
        self.discovery = WebSocketDiscovery()
        self.setup_callbacks()
        
    def setup_callbacks(self):
        """Set up callbacks to integrate monitor with discovery analysis."""
        
        def on_websocket_opened(websocket):
            """Handle new WebSocket connections."""
            print(f"🔗 WebSocket discovered: {websocket.url}")
            self.discovery.record_connection(websocket.url)
            
        def on_message_received(direction, websocket, payload):
            """Handle WebSocket messages."""
            if direction == "received":
                print(f"📨 [{websocket.url}] Received: {len(payload)} bytes")
            else:
                print(f"📤 [{websocket.url}] Sent: {len(payload)} bytes")
                
            self.discovery.record_message_pattern(websocket.url, payload)
            
        self.monitor.on_websocket_opened = on_websocket_opened
        self.monitor.on_message_received = on_message_received
        
    async def discover_mock_draft_protocol(self, duration: int = 300):
        """
        Main discovery method for ESPN mock draft protocol.
        
        Args:
            duration: How long to monitor in seconds (default 5 minutes)
        """
        print("🚀 Starting ESPN Draft Protocol Discovery")
        print("=" * 50)
        
        # ESPN Mock Draft Lobby URL
        mock_draft_url = "https://fantasy.espn.com/football/mockdraftlobby"
        
        try:
            # Connect to ESPN mock draft lobby
            print(f"🔍 Connecting to ESPN Mock Draft Lobby...")
            success = await self.monitor.connect_to_draft(mock_draft_url)
            
            if not success:
                print("❌ Failed to connect to ESPN draft lobby")
                return
                
            print("✅ Connected to ESPN draft lobby")
            
            # Wait for WebSocket connections to be established
            print("⏳ Waiting for WebSocket connections...")
            found_websockets = await self.monitor.wait_for_websockets(timeout=60)
            
            if not found_websockets:
                print("❌ No WebSocket connections detected")
                print("💡 You may need to manually join a mock draft room")
                print("   Please navigate to a draft room in the browser window")
                
                # Extended wait for manual navigation
                input("Press Enter after joining a draft room...")
                await self.monitor.wait_for_websockets(timeout=30)
                
            # Monitor WebSocket traffic
            if self.monitor.websockets:
                print(f"📡 Monitoring {len(self.monitor.websockets)} WebSocket(s) for {duration} seconds...")
                print("   Watch the console for incoming messages...")
                print("   (Start a mock draft to capture draft events)")
                
                await self.monitor.monitor_for_duration(duration)
                
            else:
                print("❌ No WebSocket connections to monitor")
                
        except KeyboardInterrupt:
            print("\n⏹️  Discovery interrupted by user")
            
        except Exception as e:
            print(f"❌ Discovery error: {e}")
            
        finally:
            await self.generate_reports()
            
    async def generate_reports(self):
        """Generate discovery reports and save to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("\n📊 Generating Discovery Reports...")
        print("=" * 50)
        
        # Create reports directory
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Save raw message log
        message_log_file = reports_dir / f"espn_websocket_messages_{timestamp}.json"
        self.monitor.save_message_log(str(message_log_file))
        
        # Save discovery analysis
        discovery_report_file = reports_dir / f"espn_protocol_analysis_{timestamp}.json"
        self.discovery.save_discovery_report(str(discovery_report_file))
        
        # Print summary
        summary = self.discovery.get_discovery_summary()
        print(f"📈 Discovery Summary:")
        print(f"   • WebSocket endpoints found: {summary['total_endpoints']}")
        print(f"   • Total messages captured: {sum(url_data['total_messages'] for url_data in summary['message_summary'].values())}")
        print(f"   • Draft-related endpoints: {len(self.discovery.identify_draft_websockets())}")
        
        # Show discovered endpoints
        if summary['endpoints']:
            print("\n🔗 Discovered WebSocket Endpoints:")
            for endpoint in summary['endpoints']:
                print(f"   • {endpoint}")
                
        # Show identified draft WebSockets
        draft_websockets = self.discovery.identify_draft_websockets()
        if draft_websockets:
            print("\n🎯 Draft-Related WebSockets:")
            for ws in draft_websockets:
                print(f"   • {ws}")
                
        # Show message type analysis
        schemas = self.discovery.extract_message_schemas()
        if schemas:
            print(f"\n📋 Message Types Identified: {len(schemas)}")
            for msg_type, schema in schemas.items():
                print(f"   • {msg_type}: {schema['sample_count']} samples, {len(schema['common_fields'])} fields")
                
        print(f"\n💾 Reports saved:")
        print(f"   • Raw messages: {message_log_file}")
        print(f"   • Analysis: {discovery_report_file}")
        
        await self.monitor.close()


async def main():
    parser = argparse.ArgumentParser(description="Discover ESPN Draft WebSocket Protocol")
    parser.add_argument("--headless", action="store_true", 
                       help="Run browser in headless mode")
    parser.add_argument("--duration", type=int, default=300,
                       help="Monitoring duration in seconds (default: 300)")
    
    args = parser.parse_args()
    
    discovery = ESPNProtocolDiscovery(headless=args.headless)
    
    try:
        await discovery.discover_mock_draft_protocol(duration=args.duration)
    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    print("""
    🏈 ESPN Draft WebSocket Protocol Discovery Tool
    ============================================
    
    This tool will:
    1. Open ESPN mock draft lobby in a browser
    2. Monitor WebSocket connections automatically  
    3. Capture and analyze draft-related messages
    4. Generate detailed protocol analysis reports
    
    Instructions:
    - If browser opens, navigate to and join a mock draft
    - Let the script run during the draft to capture events
    - Check the 'reports' folder for generated analysis
    
    """)
    
    asyncio.run(main())