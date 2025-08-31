#!/usr/bin/env python3
"""
DraftOps Monitor Console Script - Sprint 1 Deliverable

End-to-end draft monitoring console application that provides real-time pick logging
and draft state tracking for ESPN fantasy football drafts.

Usage:
    python run_draft_monitor.py --url https://fantasy.espn.com/draft/...
    python run_draft_monitor.py --league 12345 --team team_1
    python run_draft_monitor.py --mock  # Join first available mock draft
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
from src.websocket_protocol.state.integration import DraftStateManager


class DraftMonitorConsole:
    """
    Console application for real-time draft monitoring.
    
    Features:
    - Real-time pick logging with player names
    - Draft state tracking and validation
    - On-the-clock notifications
    - Connection recovery
    - Graceful shutdown
    """
    
    def __init__(self, league_id: str = "unknown", team_id: str = "unknown", 
                 team_count: int = 12, rounds: int = 16):
        self.league_id = league_id
        self.team_id = team_id
        self.team_count = team_count
        self.rounds = rounds
        
        self.manager: Optional[DraftStateManager] = None
        self.running = False
        self.draft_complete = False
        
        # Track picks for summary
        self.pick_count = 0
        self.start_time: Optional[datetime] = None
        
        # Setup logging to console
        self.setup_logging()
        
    def setup_logging(self):
        """Configure console logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Reduce noise from external libraries
        logging.getLogger('playwright').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
    def print_header(self):
        """Print application header."""
        print("=" * 60)
        print("DRAFTOPS DRAFT MONITOR - Sprint 1")
        print("=" * 60)
        print(f"League ID: {self.league_id}")
        print(f"Team ID: {self.team_id}")
        print(f"Draft Config: {self.team_count} teams, {self.rounds} rounds")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
    def format_pick_message(self, pick_data: dict) -> str:
        """Format pick data for console output."""
        pick_num = pick_data.get('pick_number', 0)
        
        try:
            pick_num = int(pick_num)
            if pick_num > 0:
                round_num = ((pick_num - 1) // self.team_count) + 1
                pick_in_round = ((pick_num - 1) % self.team_count) + 1
            else:
                round_num = '?'
                pick_in_round = '?'
        except (ValueError, TypeError):
            round_num = '?'
            pick_in_round = '?'
        
        team_id = pick_data.get('team_id', 'Unknown')
        player_name = pick_data.get('player_name', f"Player #{pick_data.get('player_id', 'Unknown')}")
        
        # Format: "Pick 1.01: Team A selected Justin Jefferson (WR, MIN)"
        if isinstance(pick_in_round, int):
            formatted_pick = f"{pick_in_round:02d}"
        else:
            formatted_pick = pick_in_round
        return f"Pick {round_num}.{formatted_pick}: Team {team_id} selected **{player_name}**"
        
    def setup_callbacks(self):
        """Setup event callbacks for draft monitoring."""
        
        def on_pick_processed(pick_data: dict):
            """Handle pick made events."""
            self.pick_count += 1
            message = self.format_pick_message(pick_data)
            print(f"[PICK] {message}")
            
            # Check if it's our team's pick
            if pick_data.get('team_id') == self.team_id:
                print(f">>> YOUR TEAM drafted {pick_data.get('player_name', 'Unknown Player')} <<<")
                
        def on_state_updated(state_summary: dict):
            """Handle state update events."""
            current_pick = state_summary.get('current_pick', 0)
            on_clock = state_summary.get('on_the_clock')
            time_left = state_summary.get('time_remaining', 0)
            
            # Notify when our team is on the clock
            if on_clock == self.team_id:
                print(f">>> YOU ARE NOW ON THE CLOCK! <<<")
                if time_left > 0:
                    print(f"    Time remaining: {time_left:.0f}s")
                    
        def on_draft_completed():
            """Handle draft completion."""
            self.draft_complete = True
            print()
            print("=" * 60)
            print("DRAFT COMPLETED!")
            print(f"Total picks logged: {self.pick_count}")
            if self.start_time:
                duration = datetime.now() - self.start_time
                print(f"Draft duration: {duration}")
            print("=" * 60)
            
        def on_error(error_msg: str):
            """Handle errors."""
            print(f"[ERROR] {error_msg}")
            
        # Set callbacks on manager
        if self.manager:
            self.manager.on_pick_processed = on_pick_processed
            self.manager.on_state_updated = on_state_updated
            self.manager.on_draft_completed = on_draft_completed
            self.manager.on_error = on_error
            
    async def initialize(self) -> bool:
        """Initialize the draft manager."""
        try:
            self.manager = DraftStateManager(
                league_id=self.league_id,
                team_id=self.team_id,
                team_count=self.team_count,
                rounds=self.rounds
            )
            
            success = await self.manager.initialize()
            if success:
                self.setup_callbacks()
                print("[SUCCESS] Draft monitor initialized successfully")
                return True
            else:
                print("[ERROR] Failed to initialize draft monitor")
                return False
                
        except Exception as e:
            print(f"[ERROR] Initialization error: {e}")
            return False
            
    async def connect_to_draft(self, draft_url: str) -> bool:
        """Connect to ESPN draft room."""
        if not self.manager:
            return False
            
        try:
            print(f"[INFO] Connecting to draft: {draft_url}")
            success = await self.manager.connect_to_draft(draft_url)
            
            if success:
                print("[SUCCESS] Connected to draft room")
                print("📡 Waiting for draft events...")
                print()
                return True
            else:
                print("[ERROR] Failed to connect to draft room")
                return False
                
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            return False
            
    async def start_monitoring(self):
        """Start the draft monitoring loop."""
        resolution_task = None
        try:
            self.running = True
            self.start_time = datetime.now()
            
            print("[INFO] Monitoring draft in progress...")
            print("   - Press Ctrl+C to stop monitoring")
            print("   - Pick events will appear below:")
            print("-" * 60)
            
            # Create background task for player resolution
            resolution_task = asyncio.create_task(self._resolution_loop())
            
            # Monitor until draft completes or stopped
            while self.running and not self.draft_complete:
                await asyncio.sleep(1)
                
                # Check if draft is still active (simple check for now)
                if self.manager:
                    state_summary = self.manager.get_state_summary()
                    total_picks = state_summary.get('total_picks', 0)
                    expected_picks = self.team_count * self.rounds
                    
                    if total_picks >= expected_picks:
                        print("\n[INFO] All picks completed!")
                        self.draft_complete = True
                        
        except asyncio.CancelledError:
            print("\n[INFO] Monitoring stopped by user")
        except Exception as e:
            print(f"\n[ERROR] Monitoring error: {e}")
        finally:
            self.running = False
            # Always cancel resolution task to prevent resource leaks
            if resolution_task:
                resolution_task.cancel()
            
    async def _resolution_loop(self):
        """Background loop for resolving player names."""
        try:
            while self.running and not self.draft_complete:
                if self.manager:
                    resolved = await self.manager.resolve_queued_players()
                    if resolved > 0:
                        print(f"[INFO] Resolved {resolved} player names")
                        
                await asyncio.sleep(2)  # Resolve every 2 seconds
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ERROR] Player resolution error: {e}")
            
    def print_final_summary(self):
        """Print final monitoring summary."""
        if not self.manager:
            return
            
        state_summary = self.manager.get_state_summary()
        performance = state_summary.get('performance', {})
        
        print()
        print("SESSION SUMMARY")
        print("-" * 30)
        print(f"Picks logged: {self.pick_count}")
        print(f"Messages processed: {performance.get('messages_processed', 0)}")
        print(f"Players resolved: {performance.get('player_resolutions', 0)}")
        print(f"Avg processing time: {performance.get('avg_processing_time_ms', 0):.1f}ms")
        
        if performance.get('errors', 0) > 0:
            print(f"Errors encountered: {performance['errors']}")
            
    async def shutdown(self):
        """Graceful shutdown."""
        print("\n[INFO] Shutting down...")
        
        self.running = False
        
        if self.manager:
            await self.manager.close()
            
        self.print_final_summary()
        print("[SUCCESS] Shutdown complete")
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print("\n[WARNING] Interrupt received, shutting down...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DraftOps Draft Monitor - Real-time ESPN draft tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_draft_monitor.py --url https://fantasy.espn.com/draft/123
  python run_draft_monitor.py --league 12345 --team team_1 --teams 10
  python run_draft_monitor.py --mock --teams 12 --rounds 15
        """
    )
    
    # Connection options
    connection_group = parser.add_mutually_exclusive_group(required=True)
    connection_group.add_argument('--url', help='Direct ESPN draft room URL')
    connection_group.add_argument('--league', help='ESPN league ID')
    connection_group.add_argument('--mock', action='store_true', 
                                help='Join first available mock draft')
    
    # Draft configuration
    parser.add_argument('--team', default='team_1', help='Your team ID (default: team_1)')
    parser.add_argument('--teams', type=int, default=12, help='Number of teams (default: 12)')
    parser.add_argument('--rounds', type=int, default=16, help='Number of rounds (default: 16)')
    
    # Options
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Determine draft URL
    draft_url = None
    league_id = "unknown"
    
    if args.url:
        draft_url = args.url
        # Try to extract league ID from URL
        if '/leagues/' in args.url:
            try:
                league_id = args.url.split('/leagues/')[1].split('/')[0]
            except:
                league_id = "url_league"
    elif args.league:
        league_id = args.league
        draft_url = f"https://fantasy.espn.com/football/draft?leagueId={args.league}"
    elif args.mock:
        # For mock drafts, use a placeholder URL - user will need to navigate
        league_id = "mock_draft"
        draft_url = "https://fantasy.espn.com/football/draft"
        
    # Create console application
    console = DraftMonitorConsole(
        league_id=league_id,
        team_id=args.team,
        team_count=args.teams,
        rounds=args.rounds
    )
    
    console.setup_signal_handlers()
    console.print_header()
    
    try:
        # Initialize
        if not await console.initialize():
            print("[ERROR] Failed to initialize. Exiting.")
            sys.exit(1)
            
        # Connect
        if not await console.connect_to_draft(draft_url):
            print("[ERROR] Failed to connect to draft. Exiting.")
            sys.exit(1)
            
        if args.mock:
            print("[NOTE] For mock drafts, you may need to manually join a draft room")
            print("   in the browser window that opened.")
            print()
            
        # Start monitoring
        await console.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
    finally:
        await console.shutdown()


if __name__ == "__main__":
    asyncio.run(main())