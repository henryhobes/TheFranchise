#!/usr/bin/env python3
"""
Enhanced ESPN Draft Logger - Player ID Focus

Enhanced version of the POC draft logger specifically designed to capture
and analyze player identifiers from ESPN draft WebSocket messages.
Part of Sprint 0 Player ID System Reverse Engineering.

Usage:
    python player_id_logger.py
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from ..monitor.espn_draft_monitor import ESPNDraftMonitor
from ..utils.player_id_extractor import PlayerIdExtractor


class PlayerIdDraftLogger:
    """Enhanced draft logger focused on player ID extraction and analysis."""
    
    def __init__(self, headless: bool = False):
        self.monitor = ESPNDraftMonitor(headless=headless)
        self.player_id_extractor = PlayerIdExtractor()
        self.draft_events = []
        self.player_picks = []  # Specific tracking for player selection events
        self.session_stats = {
            "start_time": None,
            "total_messages": 0,
            "draft_messages": 0,
            "player_ids_found": 0
        }
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.setup_callbacks()
        
    def setup_callbacks(self):
        """Set up enhanced event callbacks with player ID extraction."""
        
        def on_websocket_opened(websocket):
            print(f"[CONNECTED] WebSocket: {websocket.url}")
            self.logger.info(f"WebSocket connected: {websocket.url}")
            
        def on_message_received(direction, websocket, payload):
            self.session_stats["total_messages"] += 1
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Extract player IDs from every message
            extractions = self.player_id_extractor.extract_from_message(
                payload, websocket.url, message_type="auto_detected"
            )
            
            # Categorize message type
            message_type = self._categorize_message(payload)
            is_draft_event = self.is_potential_draft_event(payload)
            
            if is_draft_event:
                self.session_stats["draft_messages"] += 1
                print(f"[DRAFT] [{timestamp}] {message_type}")
                
                # Store the event
                event_data = {
                    "timestamp": timestamp,
                    "direction": direction,
                    "websocket": websocket.url,
                    "payload": payload,
                    "message_type": message_type,
                    "player_extractions": len(extractions)
                }
                self.draft_events.append(event_data)
                
                # If we found player IDs, this is likely a pick event
                if extractions:
                    self.session_stats["player_ids_found"] += len(extractions)
                    print(f"   [PLAYER] Found {len(extractions)} ID(s):")
                    
                    for extraction in extractions:
                        print(f"      - Player ID: {extraction.player_id} "
                             f"(confidence: {extraction.confidence:.2f})")
                        if extraction.context_fields:
                            print(f"        Context: {extraction.context_fields}")
                            
                    # Track this as a potential pick
                    pick_data = {
                        "timestamp": timestamp,
                        "extractions": extractions,
                        "message_type": message_type,
                        "raw_payload": payload
                    }
                    self.player_picks.append(pick_data)
                
                # Display parsed message nicely
                try:
                    parsed = json.loads(payload)
                    print(f"   [DATA] {json.dumps(parsed, indent=4)}")
                except:
                    print(f"   [DATA] {payload[:200]}...")
                    
            else:
                # Still check for player IDs in non-draft messages
                if extractions:
                    print(f"   [{timestamp}] Non-draft message with {len(extractions)} player ID(s)")
                else:
                    # Only show every 10th non-draft message to avoid spam
                    if self.session_stats["total_messages"] % 10 == 0:
                        print(f"   [{timestamp}] Monitoring... ({self.session_stats['total_messages']} messages, waiting for draft to start)")
                    
        self.monitor.on_websocket_opened = on_websocket_opened
        self.monitor.on_message_received = on_message_received
        
    def _categorize_message(self, payload: str) -> str:
        """Attempt to categorize the message type based on content."""
        payload_stripped = payload.strip()
        payload_lower = payload.lower()
        
        # Check for ESPN draft text protocol first (discovered from live test)
        if payload_stripped.startswith('SELECTED '):
            return "PLAYER_SELECTED"
        elif payload_stripped.startswith('AUTODRAFT '):
            return "AUTODRAFT_STATUS"
        elif payload_stripped.startswith(('CLOCK ', 'ONTHECLOCK ')):
            return "DRAFT_TIMER"
        
        # Look for JSON-based ESPN message patterns
        elif any(keyword in payload_lower for keyword in ["pick_made", "pickmade", "draft_pick"]):
            return "PICK_MADE"
        elif any(keyword in payload_lower for keyword in ["on_the_clock", "ontheclock", "clock"]):
            return "ON_THE_CLOCK"
        elif any(keyword in payload_lower for keyword in ["roster_update", "rosterupdate"]):
            return "ROSTER_UPDATE"
        elif "draft" in payload_lower and "status" in payload_lower:
            return "DRAFT_STATUS"
        elif any(keyword in payload_lower for keyword in ["player", "selected", "drafted"]):
            return "PLAYER_EVENT"
        elif "heartbeat" in payload_lower or "ping" in payload_lower:
            return "HEARTBEAT"
        else:
            return "UNKNOWN"
        
    def is_potential_draft_event(self, payload: str) -> bool:
        """Enhanced draft event detection with ESPN text protocol support."""
        payload_stripped = payload.strip()
        payload_lower = payload.lower()
        
        # Check for ESPN draft text protocol first (discovered from live test)
        if (payload_stripped.startswith('SELECTED ') or 
            payload_stripped.startswith('AUTODRAFT ') or
            payload_stripped.startswith('CLOCK ') or
            payload_stripped.startswith('ONTHECLOCK ')):
            return True
        
        # Primary draft keywords (expanded)
        draft_keywords = [
            "pick", "draft", "player", "selected", "drafted",
            "pick_made", "on_the_clock", "roster_update", "roster",
            "team", "turn", "available", "autopick", "auto_pick",
            "fantasy", "league", "draftroom", "pick_timer", "timer",
            "round", "selection", "choose", "taken"
        ]
        
        # Secondary indicators (less certain)
        secondary_keywords = [
            "clock", "timer", "round", "position"
        ]
        
        # High priority patterns
        if any(keyword in payload_lower for keyword in draft_keywords):
            return True
            
        # Check for JSON with player-like structure
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                # Look for player-related fields
                player_fields = ["playerid", "player_id", "playername", "position", "team"]
                if any(field in str(data).lower() for field in player_fields):
                    return True
        except:
            pass
            
        return False
        
    async def run_player_id_analysis(self, duration: int = 600):
        """
        Run the enhanced draft logger focused on player ID analysis.
        
        Args:
            duration: How long to run in seconds (default 20 minutes)
        """
        print("ESPN Player ID Analysis - Enhanced Draft Logger")
        print("=" * 60)
        print("This enhanced logger will:")
        print("1. Monitor ESPN draft WebSocket traffic")
        print("2. Extract and analyze player identifiers")
        print("3. Categorize message types")
        print("4. Build player ID mapping dataset")
        print("5. Generate comprehensive analysis reports")
        print()
        
        self.session_stats["start_time"] = datetime.now()
        
        try:
            # Connect to ESPN mock draft
            mock_draft_url = "https://fantasy.espn.com/football/mockdraftlobby"
            print(f"[INFO] Opening ESPN mock draft lobby...")
            
            success = await self.monitor.connect_to_draft(mock_draft_url)
            if not success:
                print("[ERROR] Failed to connect")
                return
                
            print("[SUCCESS] Connected to ESPN")
            print()
            print("INSTRUCTIONS:")
            print("   1. Navigate to and join a mock draft in the browser")
            print("   2. Watch this console for player ID extractions")
            print("   3. Let several picks happen for better analysis")
            print("   4. Press Ctrl+C to stop and generate report")
            print()
            
            # Wait for WebSocket connections (longer timeout for draft to start)
            print("[WAITING] Looking for WebSocket connections...")
            print("   TIP: The draft needs to START first - wait for the timer to reach 0")
            print("   TIP: Once you're in the draft room, WebSocket connections will be detected")
            found_websockets = await self.monitor.wait_for_websockets(timeout=1200)
            
            if found_websockets:
                print(f"[ACTIVE] Monitoring {len(self.monitor.websockets)} WebSocket connection(s)")
                print("[ANALYZING] Processing messages for player IDs...")
                print()
                
                # Start real-time stats display
                stats_task = asyncio.create_task(self._display_realtime_stats())
                
                # Monitor for the specified duration
                try:
                    await self.monitor.monitor_for_duration(duration)
                except KeyboardInterrupt:
                    print("\n[STOPPED] Analysis stopped by user")
                finally:
                    stats_task.cancel()
                    
            else:
                print("[ERROR] No WebSocket connections found")
                print("   Make sure you joined a draft room")
                
        except Exception as e:
            print(f"[ERROR] {e}")
            self.logger.error(f"Error during analysis: {e}")
            
        finally:
            await self.save_enhanced_results()
            
    async def _display_realtime_stats(self):
        """Display real-time statistics during monitoring."""
        try:
            while True:
                await asyncio.sleep(10)  # Update every 10 seconds
                
                runtime = datetime.now() - self.session_stats["start_time"]
                unique_ids = len(self.player_id_extractor.unique_player_ids)
                
                print(f"\n[STATS] Runtime: {runtime}")
                print(f"   Messages: {self.session_stats['total_messages']} | "
                      f"Draft Events: {self.session_stats['draft_messages']} | "
                      f"Player IDs: {unique_ids}")
                      
        except asyncio.CancelledError:
            pass
            
    async def save_enhanced_results(self):
        """Save comprehensive analysis results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create reports directory
        reports_dir = Path("reports/player_id_analysis")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Save player ID extractions
        extractions_file = reports_dir / f"player_id_extractions_{timestamp}.json"
        self.player_id_extractor.save_extractions(str(extractions_file))
        
        # Save draft events
        events_file = reports_dir / f"draft_events_{timestamp}.json"
        try:
            with open(events_file, 'w') as f:
                json.dump(self.draft_events, f, indent=2)
        except Exception as e:
            print(f"Failed to save draft events: {e}")
            
        # Save player picks specifically
        picks_file = reports_dir / f"player_picks_{timestamp}.json"
        try:
            picks_data = []
            for pick in self.player_picks:
                pick_data = {
                    "timestamp": pick["timestamp"],
                    "message_type": pick["message_type"],
                    "player_ids": [e.player_id for e in pick["extractions"]],
                    "extractions_detail": [
                        {
                            "player_id": e.player_id,
                            "confidence": e.confidence,
                            "context": e.context_fields
                        }
                        for e in pick["extractions"]
                    ],
                    "raw_payload": pick["raw_payload"][:500]  # Truncate
                }
                picks_data.append(pick_data)
                
            with open(picks_file, 'w') as f:
                json.dump(picks_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save player picks: {e}")
            
        # Save full message log
        full_log_file = reports_dir / f"full_websocket_log_{timestamp}.json"
        self.monitor.save_message_log(str(full_log_file))
        
        # Generate analysis summary
        await self._generate_analysis_summary(reports_dir, timestamp)
        
        # Print comprehensive summary
        self._print_final_summary(reports_dir, timestamp)
        
        await self.monitor.close()
        
    async def _generate_analysis_summary(self, reports_dir: Path, timestamp: str):
        """Generate a comprehensive analysis summary."""
        summary_file = reports_dir / f"analysis_summary_{timestamp}.json"
        
        extraction_summary = self.player_id_extractor.get_extraction_summary()
        
        summary_data = {
            "analysis_timestamp": datetime.now().isoformat(),
            "session_duration": str(datetime.now() - self.session_stats["start_time"]) if self.session_stats["start_time"] else "0:00:00",
            "session_stats": {k: v for k, v in self.session_stats.items() if k != "start_time"},
            "player_id_analysis": extraction_summary,
            "websocket_info": self.monitor.get_websocket_info(),
            "files_generated": [
                f"player_id_extractions_{timestamp}.json",
                f"draft_events_{timestamp}.json",
                f"player_picks_{timestamp}.json",
                f"full_websocket_log_{timestamp}.json"
            ]
        }
        
        try:
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save analysis summary: {e}")
            
    def _print_final_summary(self, reports_dir: Path, timestamp: str):
        """Print final analysis summary to console."""
        runtime = datetime.now() - self.session_stats["start_time"]
        extraction_summary = self.player_id_extractor.get_extraction_summary()
        
        print("\n" + "=" * 60)
        print("PLAYER ID ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"Session Summary:")
        print(f"   Runtime: {runtime}")
        print(f"   Total WebSocket messages: {self.session_stats['total_messages']}")
        print(f"   Draft-related messages: {self.session_stats['draft_messages']}")
        print(f"   Player picks detected: {len(self.player_picks)}")
        print()
        print(f"Player ID Analysis:")
        print(f"   Total player ID extractions: {extraction_summary['total_extractions']}")
        print(f"   Unique player IDs found: {extraction_summary['unique_players']}")
        print(f"   High confidence IDs: {extraction_summary['confidence_breakdown']['high_confidence']}")
        print(f"   Medium confidence IDs: {extraction_summary['confidence_breakdown']['medium_confidence']}")
        
        if extraction_summary['unique_player_ids']:
            print(f"\nSample Player IDs Found:")
            sample_ids = list(extraction_summary['unique_player_ids'])[:10]
            for i, player_id in enumerate(sample_ids, 1):
                print(f"   {i}. {player_id}")
            if len(extraction_summary['unique_player_ids']) > 10:
                print(f"   ... and {len(extraction_summary['unique_player_ids']) - 10} more")
                
        print(f"\nFiles Generated in reports/player_id_analysis/:")
        print(f"   - player_id_extractions_{timestamp}.json - Detailed extraction data")
        print(f"   - draft_events_{timestamp}.json - All draft-related messages")
        print(f"   - player_picks_{timestamp}.json - Specific player selection events")
        print(f"   - full_websocket_log_{timestamp}.json - Complete message log")
        print(f"   - analysis_summary_{timestamp}.json - Session summary")
        
        if extraction_summary['unique_players'] > 0:
            print("\n[SUCCESS] Player IDs detected! Ready for Phase 2 (ESPN API integration)")
        else:
            print("\n[WARNING] No player IDs found. May need to join an active draft.")


async def main():
    """Main entry point."""
    logger = PlayerIdDraftLogger(headless=False)
    await logger.run_player_id_analysis(duration=600)  # Run for 10 minutes


if __name__ == "__main__":
    print("""
    ESPN Player ID Analysis - Enhanced Draft Logger
    ================================================
    
    This enhanced tool focuses on extracting and analyzing player identifiers
    from ESPN draft WebSocket messages to build the foundation for player
    name resolution.
    
    INSTRUCTIONS:
    1. Script will open ESPN mock draft lobby
    2. Navigate to and JOIN a mock draft in the browser
    3. Watch for player ID extractions in real-time
    4. Let several picks happen for comprehensive analysis
    5. Press Ctrl+C to stop and generate detailed reports
    
    Results will be saved in 'reports/player_id_analysis/' folder
    
    Ready? Press Ctrl+C anytime to stop and analyze results.
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Analysis stopped. Generating final reports...")
    except Exception as e:
        print(f"Error: {e}")