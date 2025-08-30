#!/usr/bin/env python3
"""
Enhanced ESPN Draft Monitor with Player Resolution

Integrates the PlayerResolver system with WebSocket monitoring to provide
real-time player name resolution during ESPN fantasy football drafts.

This represents the complete Sprint 0 deliverable combining all components:
- WebSocket monitoring
- Player ID extraction
- ESPN API integration
- Player resolution with caching
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from monitor.espn_draft_monitor import ESPNDraftMonitor
from player_resolver import PlayerResolver, ResolvedPlayer


class EnhancedDraftMonitor:
    """
    Enhanced draft monitor with integrated player resolution.
    
    Combines WebSocket monitoring with the PlayerResolver to provide
    human-readable draft events in real-time.
    """
    
    def __init__(self, headless: bool = False, cache_db_path: Optional[str] = None):
        self.monitor = ESPNDraftMonitor(headless=headless)
        self.player_resolver: Optional[PlayerResolver] = None
        self.cache_db_path = cache_db_path or "draft_player_cache.db"
        
        # Enhanced event tracking
        self.resolved_picks = []
        self.unresolved_picks = []
        self.draft_events = []
        
        # Performance tracking
        self.session_stats = {
            "start_time": None,
            "total_messages": 0,
            "draft_messages": 0,
            "player_ids_extracted": 0,
            "players_resolved": 0,
            "resolution_failures": 0
        }
        
        self.logger = logging.getLogger(__name__)
        self.setup_callbacks()
        
    def setup_callbacks(self):
        """Set up WebSocket event callbacks with player resolution."""
        
        def on_websocket_opened(websocket):
            print(f"Connected to WebSocket: {websocket.url}")
            self.logger.info(f"WebSocket connected: {websocket.url}")
            
        async def on_message_received(direction, websocket, payload):
            await self._process_message(direction, websocket, payload)
            
        self.monitor.on_websocket_opened = on_websocket_opened
        # Note: We'll handle the async callback differently
        self._original_callback = on_message_received
        
    async def start_resolver(self):
        """Initialize the PlayerResolver."""
        self.player_resolver = PlayerResolver(cache_db_path=self.cache_db_path)
        await self.player_resolver.__aenter__()
        self.logger.info("PlayerResolver initialized")
        
    async def stop_resolver(self):
        """Clean up the PlayerResolver."""
        if self.player_resolver:
            await self.player_resolver.__aexit__(None, None, None)
            self.logger.info("PlayerResolver closed")
            
    async def _process_message(self, direction: str, websocket, payload: str):
        """Process WebSocket message with player resolution."""
        self.session_stats["total_messages"] += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Extract player IDs from message
        player_ids = []
        if self.player_resolver:
            player_ids = self.player_resolver.extract_player_ids_from_message(
                payload, websocket.url
            )
            
        if player_ids:
            self.session_stats["player_ids_extracted"] += len(player_ids)
            
        # Check if this is a draft-related message
        is_draft_event = self._is_draft_message(payload)
        
        if is_draft_event:
            self.session_stats["draft_messages"] += 1
            message_type = self._categorize_message(payload)
            
            print(f"[{timestamp}] DRAFT EVENT: {message_type}")
            
            # Store the event
            event_data = {
                "timestamp": timestamp,
                "direction": direction,
                "websocket": websocket.url,
                "message_type": message_type,
                "raw_payload": payload,
                "extracted_player_ids": player_ids
            }
            
            if player_ids:
                print(f"  Player IDs detected: {len(player_ids)}")
                
                # Resolve player names
                if self.player_resolver:
                    resolved_players = await self.player_resolver.batch_resolve_ids(player_ids)
                    
                    resolved_info = []
                    for player_id, player in resolved_players.items():
                        if player:
                            self.session_stats["players_resolved"] += 1
                            resolved_info.append({
                                "id": player_id,
                                "name": player.full_name,
                                "position": player.position,
                                "team": player.nfl_team,
                                "confidence": player.confidence_score
                            })
                            print(f"    {player.full_name} ({player.position}, {player.nfl_team})")
                        else:
                            self.session_stats["resolution_failures"] += 1
                            fallback_name = self.player_resolver.get_fallback_name(player_id)
                            resolved_info.append({
                                "id": player_id,
                                "name": fallback_name,
                                "position": "UNKNOWN",
                                "team": "UNKNOWN",
                                "confidence": 0.0
                            })
                            print(f"    {fallback_name} (resolution failed)")
                            
                    event_data["resolved_players"] = resolved_info
                    
                    # Track picks specifically
                    if "pick" in message_type.lower() and resolved_info:
                        pick_data = {
                            "timestamp": timestamp,
                            "players": resolved_info,
                            "message_type": message_type,
                            "raw_message": payload[:200]  # Truncated
                        }
                        
                        if any(p["confidence"] > 0 for p in resolved_info):
                            self.resolved_picks.append(pick_data)
                        else:
                            self.unresolved_picks.append(pick_data)
                            
            self.draft_events.append(event_data)
            
            # Display parsed message
            try:
                parsed = json.loads(payload)
                print(f"  Raw data: {json.dumps(parsed, indent=2)[:300]}...")
            except:
                print(f"  Raw data: {payload[:100]}...")
                
        else:
            # Non-draft message
            if player_ids:
                print(f"[{timestamp}] Non-draft message with {len(player_ids)} player ID(s)")
            else:
                print(f"[{timestamp}] {direction}: {len(payload)} bytes")
                
    def _is_draft_message(self, payload: str) -> bool:
        """Enhanced draft message detection."""
        payload_lower = payload.lower()
        
        # Primary indicators
        draft_keywords = [
            "pick", "draft", "player", "selected", "drafted", "roster",
            "pick_made", "on_the_clock", "roster_update"
        ]
        
        if any(keyword in payload_lower for keyword in draft_keywords):
            return True
            
        # Check for JSON with player-like structure
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                # Look for ESPN-specific fields
                espn_fields = ["playerid", "player_id", "teamid", "picknumber"]
                if any(field in str(data).lower() for field in espn_fields):
                    return True
        except:
            pass
            
        return False
        
    def _categorize_message(self, payload: str) -> str:
        """Categorize draft message type."""
        payload_lower = payload.lower()
        
        if any(keyword in payload_lower for keyword in ["pick_made", "pickmade"]):
            return "PICK_MADE"
        elif any(keyword in payload_lower for keyword in ["on_the_clock", "ontheclock"]):
            return "ON_THE_CLOCK"
        elif "roster" in payload_lower and "update" in payload_lower:
            return "ROSTER_UPDATE"
        elif "draft" in payload_lower and "status" in payload_lower:
            return "DRAFT_STATUS"
        elif any(keyword in payload_lower for keyword in ["player", "selected", "drafted"]):
            return "PLAYER_EVENT"
        else:
            return "DRAFT_MISC"
            
    async def run_enhanced_monitoring(self, duration: int = 600):
        """
        Run enhanced draft monitoring with player resolution.
        
        Args:
            duration: Monitoring duration in seconds
        """
        print("Enhanced ESPN Draft Monitor with Player Resolution")
        print("=" * 60)
        print("Features:")
        print("- Real-time WebSocket monitoring")
        print("- Automatic player ID extraction")
        print("- ESPN API player resolution")
        print("- SQLite caching for performance")
        print("- Human-readable draft events")
        print()
        
        self.session_stats["start_time"] = datetime.now()
        
        try:
            # Initialize player resolver
            await self.start_resolver()
            
            # Set up the async message handler
            def sync_message_handler(direction, websocket, payload):
                # Create a new event loop task for the async handler
                asyncio.create_task(self._original_callback(direction, websocket, payload))
                
            self.monitor.on_message_received = sync_message_handler
            
            # Connect to ESPN
            mock_draft_url = "https://fantasy.espn.com/football/mockdraftlobby"
            print(f"Connecting to ESPN mock draft lobby...")
            
            success = await self.monitor.connect_to_draft(mock_draft_url)
            if not success:
                print("Failed to connect to ESPN")
                return
                
            print("Connected to ESPN")
            print()
            print("INSTRUCTIONS:")
            print("1. Navigate to and join a mock draft in the browser")
            print("2. Watch for real-time player name resolution")
            print("3. Observe draft events with human-readable names")
            print("4. Press Ctrl+C to stop and generate report")
            print()
            
            # Wait for WebSocket connections
            print("Waiting for WebSocket connections...")
            found_websockets = await self.monitor.wait_for_websockets(timeout=120)
            
            if found_websockets:
                print(f"Monitoring {len(self.monitor.websockets)} WebSocket connection(s)")
                print("Enhanced monitoring active - player resolution enabled")
                print()
                
                # Start stats display task
                stats_task = asyncio.create_task(self._display_realtime_stats())
                
                try:
                    await self.monitor.monitor_for_duration(duration)
                except KeyboardInterrupt:
                    print("\nMonitoring stopped by user")
                finally:
                    stats_task.cancel()
                    
            else:
                print("No WebSocket connections found")
                print("Make sure you joined a draft room")
                
        except Exception as e:
            print(f"Error during monitoring: {e}")
            self.logger.error(f"Monitoring error: {e}")
            
        finally:
            await self.save_enhanced_results()
            await self.stop_resolver()
            
    async def _display_realtime_stats(self):
        """Display real-time statistics during monitoring."""
        try:
            while True:
                await asyncio.sleep(15)  # Update every 15 seconds
                
                runtime = datetime.now() - self.session_stats["start_time"]
                
                print(f"\nReal-time Stats (Runtime: {runtime}):")
                print(f"  Messages: {self.session_stats['total_messages']} | "
                      f"Draft Events: {self.session_stats['draft_messages']} | "
                      f"Players Resolved: {self.session_stats['players_resolved']}")
                      
                if self.player_resolver:
                    resolver_stats = self.player_resolver.get_stats()
                    print(f"  Cache Hit Rate: {resolver_stats['cache_hit_rate']:.1%} | "
                          f"Success Rate: {resolver_stats['success_rate']:.1%} | "
                          f"Cached Players: {self.player_resolver.get_cached_player_count()}")
                      
        except asyncio.CancelledError:
            pass
            
    async def save_enhanced_results(self):
        """Save comprehensive monitoring results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create enhanced reports directory
        reports_dir = Path("reports/enhanced_monitoring")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Save resolved picks
        picks_file = reports_dir / f"resolved_picks_{timestamp}.json"
        try:
            with open(picks_file, 'w') as f:
                json.dump({
                    "session_info": {
                        "timestamp": timestamp,
                        "duration": str(datetime.now() - self.session_stats["start_time"]),
                        "stats": self.session_stats
                    },
                    "resolved_picks": self.resolved_picks,
                    "unresolved_picks": self.unresolved_picks
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to save picks: {e}")
            
        # Save all draft events
        events_file = reports_dir / f"draft_events_{timestamp}.json"
        try:
            with open(events_file, 'w') as f:
                json.dump(self.draft_events, f, indent=2)
        except Exception as e:
            print(f"Failed to save events: {e}")
            
        # Save full WebSocket log
        full_log_file = reports_dir / f"websocket_log_{timestamp}.json"
        self.monitor.save_message_log(str(full_log_file))
        
        # Generate summary report
        await self._generate_summary_report(reports_dir, timestamp)
        
        # Print final summary
        self._print_final_summary(timestamp)
        
        await self.monitor.close()
        
    async def _generate_summary_report(self, reports_dir: Path, timestamp: str):
        """Generate comprehensive summary report."""
        summary_file = reports_dir / f"monitoring_summary_{timestamp}.json"
        
        # Get resolver stats if available
        resolver_stats = {}
        if self.player_resolver:
            resolver_stats = self.player_resolver.get_stats()
            
        summary_data = {
            "session_info": {
                "timestamp": timestamp,
                "start_time": self.session_stats["start_time"].isoformat(),
                "duration": str(datetime.now() - self.session_stats["start_time"]),
                "cache_database": self.cache_db_path
            },
            "session_stats": self.session_stats,
            "resolver_stats": resolver_stats,
            "draft_summary": {
                "total_events": len(self.draft_events),
                "resolved_picks": len(self.resolved_picks),
                "unresolved_picks": len(self.unresolved_picks),
                "success_rate": (
                    self.session_stats["players_resolved"] / 
                    max(self.session_stats["player_ids_extracted"], 1)
                )
            },
            "websocket_info": self.monitor.get_websocket_info(),
            "files_generated": [
                f"resolved_picks_{timestamp}.json",
                f"draft_events_{timestamp}.json", 
                f"websocket_log_{timestamp}.json",
                f"monitoring_summary_{timestamp}.json"
            ]
        }
        
        try:
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save summary: {e}")
            
    def _print_final_summary(self, timestamp: str):
        """Print final monitoring summary."""
        runtime = datetime.now() - self.session_stats["start_time"]
        
        print("\n" + "=" * 60)
        print("ENHANCED DRAFT MONITORING COMPLETE")
        print("=" * 60)
        
        print(f"Session Summary:")
        print(f"  Runtime: {runtime}")
        print(f"  Total messages: {self.session_stats['total_messages']}")
        print(f"  Draft events: {self.session_stats['draft_messages']}")
        print(f"  Player IDs extracted: {self.session_stats['player_ids_extracted']}")
        print(f"  Players resolved: {self.session_stats['players_resolved']}")
        
        if self.session_stats['player_ids_extracted'] > 0:
            resolution_rate = (
                self.session_stats['players_resolved'] / 
                self.session_stats['player_ids_extracted']
            )
            print(f"  Resolution rate: {resolution_rate:.1%}")
            
        print(f"\nDraft Picks:")
        print(f"  Resolved picks: {len(self.resolved_picks)}")
        print(f"  Unresolved picks: {len(self.unresolved_picks)}")
        
        if self.resolved_picks:
            print(f"\nSample Resolved Picks:")
            for i, pick in enumerate(self.resolved_picks[:5], 1):
                players_str = ", ".join([
                    f"{p['name']} ({p['position']})" 
                    for p in pick['players']
                ])
                print(f"  {i}. [{pick['timestamp']}] {players_str}")
                
        if self.player_resolver:
            cached_count = self.player_resolver.get_cached_player_count()
            print(f"\nPlayer Resolution:")
            print(f"  Players cached: {cached_count}")
            print(f"  Cache database: {self.cache_db_path}")
            
        print(f"\nFiles saved in reports/enhanced_monitoring/:")
        print(f"  - resolved_picks_{timestamp}.json")
        print(f"  - draft_events_{timestamp}.json")
        print(f"  - websocket_log_{timestamp}.json")
        print(f"  - monitoring_summary_{timestamp}.json")
        
        if len(self.resolved_picks) > 0:
            print("\nSUCCESS: Player resolution system working!")
            print("Ready for Sprint 1 integration.")
        else:
            print("\nNOTE: No resolved picks detected.")
            print("Try joining an active draft for full testing.")


async def main():
    """Main entry point for enhanced monitoring."""
    monitor = EnhancedDraftMonitor(headless=False)
    await monitor.run_enhanced_monitoring(duration=600)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("""
    Enhanced ESPN Draft Monitor with Player Resolution
    ================================================
    
    This enhanced monitor combines WebSocket monitoring with real-time
    player name resolution using the PlayerResolver system.
    
    Features:
    - Real-time WebSocket draft monitoring
    - Automatic player ID extraction from messages
    - ESPN API integration for player resolution
    - SQLite caching for performance
    - Human-readable draft events
    - Comprehensive analytics and reporting
    
    INSTRUCTIONS:
    1. Script will open ESPN mock draft lobby
    2. Navigate to and JOIN a mock draft in the browser
    3. Watch for real-time player name resolution
    4. Observe enhanced draft events with player names
    5. Press Ctrl+C to stop and generate reports
    
    Results saved in 'reports/enhanced_monitoring/' folder
    
    Ready to start enhanced monitoring!
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Error: {e}")