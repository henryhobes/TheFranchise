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
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
from src.websocket_protocol.state.integration import DraftStateManager


class LoggingOutput:
    """Custom output handler that separates console and file logging."""
    
    def __init__(self, log_file):
        self.log_file = log_file
        
    def print_both(self, message):
        """Print to both console and log file (for important messages)."""
        print(message)
        self._log_to_file(message)
        
    def print_console_only(self, message):
        """Print only to console (for user interaction)."""
        print(message)
        
    def log_only(self, message):
        """Write only to log file (for detailed logging)."""
        self._log_to_file(message)
        
    def _log_to_file(self, message):
        """Write message to log file."""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")
            f.flush()


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
        
        # Track player name updates
        self._displayed_picks: Dict[str, str] = {}  # player_id -> displayed_name
        
        # Setup logging to both console and file
        self.log_file = self.setup_logging()
        self.output = LoggingOutput(self.log_file)
        
    def setup_logging(self):
        """Configure separate console and file logging."""
        # Create logs directory
        log_dir = Path("test_logs")
        log_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for unique log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"draft_monitor_test_{timestamp}.log"
        
        # Create separate formatters
        detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        # File handler for detailed logging
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler for critical messages only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)  # Only show errors on console
        console_handler.setFormatter(console_formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Reduce noise from external libraries (in file only)
        logging.getLogger('playwright').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)
        
        print(f"Detailed logs saved to: {log_file}")
        return log_file
        
    def print_header(self):
        """Print application header."""
        header = f"""
==========================================================
DRAFTOPS DRAFT MONITOR - Live Draft Tracking
==========================================================
League: {self.league_id} | Team: {self.team_id} 
Draft: {self.team_count} teams, {self.rounds} rounds
Started: {datetime.now().strftime('%H:%M:%S')}
==========================================================
"""
        self.output.print_both(header)
        self.output.log_only(f"Full session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
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
        
        # Use display team name for user-friendly output
        display_team = pick_data.get('display_team_name', f"Team {pick_data.get('team_id', 'Unknown')}")
        player_name = pick_data.get('player_name', f"Player #{pick_data.get('player_id', 'Unknown')}")
        
        # Format: "Pick 1.01: Team 1 → Justin Jefferson"
        if isinstance(pick_in_round, int):
            formatted_pick = f"{pick_in_round:02d}"
        else:
            formatted_pick = pick_in_round
        return f"Pick {round_num}.{formatted_pick}: {display_team} → **{player_name}**"
        
    def setup_callbacks(self):
        """Setup event callbacks for draft monitoring."""
        
        def on_pick_processed(pick_data: dict):
            """Handle pick made events."""
            player_id = pick_data.get('player_id', '')
            current_name = pick_data.get('player_name', f"Player #{player_id}")
            
            # Check if this is a name update for an existing pick
            if player_id in self._displayed_picks:
                previous_name = self._displayed_picks[player_id]
                if previous_name != current_name and not current_name.startswith("Player #"):
                    # This is a name resolution update
                    message = self.format_pick_message(pick_data)
                    self.output.print_console_only(f"   ↳ Name resolved: {message}")
                    self.output.log_only(f"NAME_UPDATE: {player_id} -> {current_name}")
                    self._displayed_picks[player_id] = current_name
                    return
            
            # This is a new pick
            self.pick_count += 1
            message = self.format_pick_message(pick_data)
            self._displayed_picks[player_id] = current_name
            
            # Check if it's our team's pick - show prominently
            if pick_data.get('team_id') == self.team_id:
                self.output.print_both(f"*** {message} ***")
                self.output.print_both(f"    >>> YOUR PICK <<<")
            else:
                # Other teams' picks - console only
                self.output.print_console_only(f"   {message}")
                
            # Always log detailed pick info to file
            self.output.log_only(f"PICK_DETAIL: {pick_data}")
                
        def on_state_updated(state_summary: dict):
            """Handle state update events."""
            current_pick = state_summary.get('current_pick', 0)
            on_clock = state_summary.get('on_the_clock')
            time_left = state_summary.get('time_remaining', 0)
            
            # Always log state updates to file
            self.output.log_only(f"STATE_UPDATE: Pick {current_pick}, On clock: {on_clock}, Time: {time_left}s")
            
            # Only show critical notifications on console
            if on_clock == self.team_id:
                self.output.print_both(f">>> YOU ARE ON THE CLOCK! <<<")
                if time_left > 0:
                    self.output.print_both(f"    {time_left:.0f} seconds remaining")
                    
        def on_draft_completed():
            """Handle draft completion."""
            self.draft_complete = True
            completion_msg = f"""
*** DRAFT COMPLETED! ***
Total picks: {self.pick_count}"""
            if self.start_time:
                duration = datetime.now() - self.start_time
                completion_msg += f"\nDuration: {duration}"
                
            self.output.print_both(completion_msg)
            self.output.print_both("=" * 50)
            
        def on_error(error_msg: str):
            """Handle errors."""
            # Errors go to both console and file
            self.output.print_both(f"ERROR: {error_msg}")
            self.output.log_only(f"ERROR_DETAIL: {error_msg}")
            
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
                rounds=self.rounds,
                headless=False  # Show browser for manual drafting
            )
            
            success = await self.manager.initialize()
            if success:
                self.setup_callbacks()
                self.output.print_console_only("Draft monitor initialized")
                self.output.log_only("[SUCCESS] Draft monitor initialized successfully")
                return True
            else:
                self.output.print_both("Failed to initialize draft monitor")
                return False
                
        except Exception as e:
            self.output.print(f"[ERROR] Initialization error: {e}")
            return False
            
    async def connect_to_draft(self, draft_url: str) -> bool:
        """Connect to ESPN draft room."""
        if not self.manager:
            return False
            
        try:
            self.output.log_only(f"[INFO] Connecting to draft: {draft_url}")
            self.output.print_console_only("Connecting to draft...")
            
            success = await self.manager.connect_to_draft(draft_url)
            
            if success:
                self.output.print_both("Connected to draft room")
                self.output.print_console_only("Monitoring draft picks...\n")
                self.output.log_only("[SUCCESS] Connected to draft room and began monitoring")
                return True
            else:
                self.output.print_both("Failed to connect to draft room")
                return False
                
        except Exception as e:
            self.output.print_both(f"Connection error: {e}")
            self.output.log_only(f"[ERROR] Connection error details: {e}")
            return False
            
    async def start_monitoring(self):
        """Start the draft monitoring loop."""
        resolution_task = None
        try:
            self.running = True
            self.start_time = datetime.now()
            
            self.output.print_console_only("Press Ctrl+C to stop monitoring")
            self.output.print_console_only("" + "-" * 50)
            self.output.log_only("[INFO] Started draft monitoring loop")
            
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
                        self.output.print_both("\nAll picks completed!")
                        self.output.log_only(f"[INFO] Draft completed - {total_picks}/{expected_picks} picks")
                        self.draft_complete = True
                        
        except asyncio.CancelledError:
            self.output.print_console_only("\nMonitoring stopped")
            self.output.log_only("[INFO] Monitoring stopped by user (CancelledError)")
        except Exception as e:
            self.output.print_both(f"\nMonitoring error: {e}")
            self.output.log_only(f"[ERROR] Monitoring error details: {e}")
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
                        self.output.log_only(f"[INFO] Resolved {resolved} player names")
                        # Only show on console if many players resolved at once
                        if resolved > 5:
                            self.output.print_console_only(f"Resolved {resolved} player names")
                        
                await asyncio.sleep(2)  # Resolve every 2 seconds
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.output.log_only(f"[ERROR] Player resolution error: {e}")
            # Only show on console if it's a critical resolution error
            if "critical" in str(e).lower() or "timeout" in str(e).lower():
                self.output.print_console_only(f"WARNING: Player resolution issue - check logs")
            
    def print_final_summary(self):
        """Print final monitoring summary."""
        if not self.manager:
            return
            
        state_summary = self.manager.get_state_summary()
        performance = state_summary.get('performance', {})
        
        summary = f"""
SESSION SUMMARY
{'-' * 30}
Picks logged: {self.pick_count}
Messages processed: {performance.get('messages_processed', 0)}
Players resolved: {performance.get('player_resolutions', 0)}
Avg processing time: {performance.get('avg_processing_time_ms', 0):.1f}ms"""
        
        if performance.get('errors', 0) > 0:
            summary += f"\nErrors: {performance['errors']}"
            
        self.output.print_both(summary)
            
    async def shutdown(self):
        """Graceful shutdown."""
        self.output.print_console_only("\nShutting down...")
        self.output.log_only("[INFO] Graceful shutdown initiated")
        
        self.running = False
        
        if self.manager:
            await self.manager.close()
            
        self.print_final_summary()
        self.output.print_console_only("Shutdown complete")
        self.output.print_console_only(f"Complete log: {self.log_file}")
        self.output.log_only("[SUCCESS] Shutdown completed successfully")
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print("\n[WARNING] Interrupt received, shutting down...")
            self.running = False
            # Raise KeyboardInterrupt to properly interrupt async operations
            raise KeyboardInterrupt()
            
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
            console.output.print_console_only("Failed to initialize. Exiting.")
            sys.exit(1)
            
        # Connect
        if not await console.connect_to_draft(draft_url):
            console.output.print_console_only("Failed to connect to draft. Exiting.")
            sys.exit(1)
            
        if args.mock:
            console.output.print_console_only("NOTE: For mock drafts, manually join a draft room in the browser")
            console.output.print_console_only("")
            
        # Start monitoring
        await console.start_monitoring()
        
    except KeyboardInterrupt:
        console.output.print_console_only("\nInterrupted by user")
        console.output.log_only("[INFO] Application interrupted by user (KeyboardInterrupt)")
    except Exception as e:
        console.output.print_both(f"\nUnexpected error: {e}")
        console.output.log_only(f"[ERROR] Unexpected error details: {e}")
        sys.exit(1)
    finally:
        await console.shutdown()


if __name__ == "__main__":
    asyncio.run(main())