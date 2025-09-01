#!/usr/bin/env python3
"""
Fixed DraftOps Monitor Console Script with proper pick ordering and team calculation.

This version fixes:
1. Out-of-order pick display - buffers picks and displays them in order
2. Wrong team assignments - calculates correct teams based on pick number and draft order
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
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


class FixedDraftMonitorConsole:
    """
    Console application for real-time draft monitoring with fixed ordering and team calculation.
    
    Key improvements:
    - Displays picks in numerical order regardless of network message order
    - Calculates correct teams based on pick number and established draft order
    - Handles snake draft logic properly
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
        
        # Fixed pick ordering system
        self._displayed_picks = {}  # player_id -> displayed_name
        self._pick_buffer = {}  # pick_number -> pick_data (for ordering)
        self._highest_displayed_pick = 0  # track what we've displayed so far
        self._pick_to_player = {}  # pick_number -> player_id (for name updates)
        self._player_to_picks = {}  # player_id -> set of pick_numbers (handles duplicates)
        
        # Setup logging
        self.log_file = self.setup_logging()
        self.output = LoggingOutput(self.log_file)
        
    def setup_logging(self):
        """Configure logging."""
        log_dir = Path("test_logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"draft_monitor_fixed_{timestamp}.log"
        
        # Configure logging
        detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(console_formatter)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        logging.getLogger('playwright').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        print(f"Detailed logs saved to: {log_file}")
        return log_file
        
    def print_header(self):
        """Print application header."""
        header = f"""
==========================================================
DRAFTOPS DRAFT MONITOR - FIXED VERSION
==========================================================
League: {self.league_id} | Team: {self.team_id} 
Draft: {self.team_count} teams, {self.rounds} rounds
Started: {datetime.now().strftime('%H:%M:%S')}
==========================================================
"""
        self.output.print_both(header)
        
    def _calculate_team_for_pick(self, pick_number: int) -> str:
        """Calculate which team should be picking based on pick number and snake draft."""
        if not self.manager or not hasattr(self.manager, '_draft_order') or not self.manager._draft_order:
            return None
            
        actual_team_count = len(self.manager._draft_order)
        if actual_team_count == 0:
            return None
            
        # Snake draft calculation
        round_num = ((pick_number - 1) // actual_team_count)  # 0-based round
        position_in_round = ((pick_number - 1) % actual_team_count)  # 0-based position
        
        if round_num % 2 == 0:  # Even round (0-based): normal order
            team_index = position_in_round
        else:  # Odd round (0-based): reverse order
            team_index = actual_team_count - 1 - position_in_round
            
        if 0 <= team_index < len(self.manager._draft_order):
            return self.manager._draft_order[team_index]
        
        return None
    
    def _correct_pick_data(self, pick_data: dict) -> dict:
        """Add display team name to pick data (no corrections needed now)."""
        if self.manager:
            team_id = pick_data.get('team_id')
            if team_id:
                corrected_data = pick_data.copy()
                corrected_data['display_team_name'] = self.manager.get_display_team_name(team_id)
                return corrected_data
        
        return pick_data

    def format_pick_message(self, pick_data: dict) -> str:
        """Format pick data for console output with correct team count."""
        pick_num = pick_data.get('pick_number', 0)
        
        # Use configured team count - draft order builds incrementally and is unreliable
        actual_team_count = self.team_count
        
        try:
            pick_num = int(pick_num)
            if pick_num > 0:
                round_num = ((pick_num - 1) // actual_team_count) + 1
                pick_in_round = ((pick_num - 1) % actual_team_count) + 1
                self.output.log_only(f"Pick {pick_num} -> Round {round_num}.{pick_in_round:02d} (team_count={actual_team_count})")
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
        return f"Pick {round_num}.{formatted_pick}: {display_team} -> **{player_name}**"
        
    def _display_buffered_picks(self):
        """Display picks in proper order from buffer."""
        # Display picks sequentially starting from where we left off
        next_pick = self._highest_displayed_pick + 1
        
        while next_pick in self._pick_buffer:
            pick_data = self._pick_buffer[next_pick]
            message = self.format_pick_message(pick_data)
            
            # Check if it's our team's pick - show prominently
            if pick_data.get('team_id') == self.team_id:
                self.output.print_both(f"*** {message} ***")
                self.output.print_both(f"    >>> YOUR PICK <<<")
            else:
                # Other teams' picks - console only
                self.output.print_console_only(f"   {message}")
            
            self.pick_count += 1
            self._highest_displayed_pick = next_pick
            next_pick += 1
        
    def setup_callbacks(self):
        """Setup event callbacks for draft monitoring."""
        
        def on_pick_processed(pick_data: dict):
            """Handle pick made events with proper ordering."""
            player_id = pick_data.get('player_id', '')
            current_name = pick_data.get('player_name', f"Player #{player_id}")
            pick_number = pick_data.get('pick_number', 0)
            
            # If pick_number is provided, this is the authoritative pick
            if pick_number > 0:
                # Log the incoming pick for debugging
                self.output.log_only(f"INCOMING_PICK: pick_number={pick_number}, player_id={player_id}, team_id={pick_data.get('team_id')}, name={current_name}")
                
                # Check if this pick slot already has a different player
                existing_player_id = self._pick_to_player.get(pick_number)
                if existing_player_id and existing_player_id != player_id:
                    self.output.log_only(f"WARNING: Pick {pick_number} player ID changed from {existing_player_id} to {player_id}")
                    # Clean up old player mapping
                    if existing_player_id in self._player_to_picks:
                        self._player_to_picks[existing_player_id].discard(pick_number)
                        self.output.log_only(f"Removed player {existing_player_id} from pick {pick_number}")
                
                # Check if this player already has other picks (shouldn't happen in a normal draft)
                if player_id in self._player_to_picks and len(self._player_to_picks[player_id]) > 0:
                    existing_picks = self._player_to_picks[player_id]
                    self.output.log_only(f"WARNING: Player {player_id} already has picks: {existing_picks}, adding pick {pick_number}")
                
                # This is either a new pick or an update to an existing pick
                corrected_pick_data = self._correct_pick_data(pick_data)
                self._pick_buffer[pick_number] = corrected_pick_data
                self._pick_to_player[pick_number] = player_id
                
                # Track player -> pick mappings (handle multiple picks per player)
                if player_id not in self._player_to_picks:
                    self._player_to_picks[player_id] = set()
                self._player_to_picks[player_id].add(pick_number)
                
                self.output.log_only(f"STORED: pick {pick_number} -> player {player_id}, player now has picks: {self._player_to_picks[player_id]}")
                
                # Check if this is a name resolution update
                previous_name = self._displayed_picks.get(player_id, "")
                is_name_update = (previous_name.startswith("Player #") and not current_name.startswith("Player #"))
                
                if is_name_update:
                    message = self.format_pick_message(corrected_pick_data)
                    self.output.print_console_only(f"   ↳ Name resolved: {message}")
                    self.output.log_only(f"NAME_UPDATE: Pick {pick_number}, {player_id} -> {current_name}")
                else:
                    # Display picks in order (will only show new ones)
                    self._display_buffered_picks()
                
                self._displayed_picks[player_id] = current_name
                
                # Always log detailed pick info to file
                self.output.log_only(f"PICK_DETAIL: {corrected_pick_data}")
            else:
                # No pick number - this might be a delayed name update
                self.output.log_only(f"WARNING: Received pick data without pick_number: {pick_data}")
                
                # Try to find ALL picks by this player_id
                if player_id in self._player_to_picks:
                    pick_numbers = sorted(self._player_to_picks[player_id])
                    self.output.log_only(f"Player {player_id} has picks: {pick_numbers}")
                    
                    for pick_num in pick_numbers:
                        if pick_num in self._pick_buffer:
                            # Update this specific pick with the new name
                            old_name = self._pick_buffer[pick_num].get('player_name', '')
                            
                            # Only update if name is actually changing to avoid duplicate messages
                            if old_name != current_name:
                                self._pick_buffer[pick_num]['player_name'] = current_name
                                corrected_pick_data = self._correct_pick_data(self._pick_buffer[pick_num])
                                
                                # Only show update if it's a real name resolution (not Player #xxx)
                                if not current_name.startswith("Player #") and old_name.startswith("Player #"):
                                    message = self.format_pick_message(corrected_pick_data)
                                    self.output.print_console_only(f"   ↳ Name resolved: {message}")
                                    self.output.log_only(f"NAME_UPDATE_DELAYED: Pick {pick_num}, {player_id} -> {current_name}")
                            
                            self._displayed_picks[player_id] = current_name
                
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
            self.output.print_both(f"ERROR: {error_msg}")
            
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
                headless=False
            )
            
            success = await self.manager.initialize()
            if success:
                self.setup_callbacks()
                self.output.print_console_only("Draft monitor initialized")
                return True
            else:
                self.output.print_both("Failed to initialize draft monitor")
                return False
                
        except Exception as e:
            self.output.print_both(f"Initialization error: {e}")
            return False
            
    async def connect_to_draft(self, draft_url: str) -> bool:
        """Connect to ESPN draft room."""
        if not self.manager:
            return False
            
        try:
            self.output.print_console_only("Connecting to draft...")
            success = await self.manager.connect_to_draft(draft_url)
            
            if success:
                self.output.print_both("Connected to draft room")
                self.output.print_console_only("Monitoring draft picks...\n")
                return True
            else:
                self.output.print_both("Failed to connect to draft room")
                return False
                
        except Exception as e:
            self.output.print_both(f"Connection error: {e}")
            return False
            
    async def start_monitoring(self):
        """Start the draft monitoring loop."""
        resolution_task = None
        try:
            self.running = True
            self.start_time = datetime.now()
            
            self.output.print_console_only("Press Ctrl+C to stop monitoring")
            self.output.print_console_only("-" * 50)
            
            # Create background task for player resolution
            resolution_task = asyncio.create_task(self._resolution_loop())
            
            # Monitor until draft completes or stopped
            while self.running and not self.draft_complete:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.output.print_console_only("\nMonitoring stopped")
        except Exception as e:
            self.output.print_both(f"\nMonitoring error: {e}")
        finally:
            self.running = False
            if resolution_task:
                resolution_task.cancel()
            
    async def _resolution_loop(self):
        """Background loop for resolving player names."""
        try:
            while self.running and not self.draft_complete:
                if self.manager:
                    resolved = await self.manager.resolve_queued_players()
                    if resolved > 0:
                        self.output.log_only(f"Resolved {resolved} player names")
                        
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.output.log_only(f"Player resolution error: {e}")
            
    async def shutdown(self):
        """Graceful shutdown."""
        self.output.print_console_only("\nShutting down...")
        self.running = False
        
        if self.manager:
            await self.manager.close()
            
        self.output.print_console_only("Shutdown complete")
        self.output.print_console_only(f"Complete log: {self.log_file}")
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print("\n[WARNING] Interrupt received, shutting down...")
            self.running = False
            raise KeyboardInterrupt()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fixed DraftOps Draft Monitor")
    
    connection_group = parser.add_mutually_exclusive_group(required=True)
    connection_group.add_argument('--url', help='Direct ESPN draft room URL')
    connection_group.add_argument('--league', help='ESPN league ID')
    connection_group.add_argument('--mock', action='store_true', help='Join first available mock draft')
    
    parser.add_argument('--team', default='team_1', help='Your team ID (default: team_1)')
    parser.add_argument('--teams', type=int, default=12, help='Number of teams (default: 12)')
    parser.add_argument('--rounds', type=int, default=16, help='Number of rounds (default: 16)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Determine draft URL
    draft_url = None
    league_id = "unknown"
    
    if args.url:
        draft_url = args.url
        if '/leagues/' in args.url:
            try:
                league_id = args.url.split('/leagues/')[1].split('/')[0]
            except:
                league_id = "url_league"
    elif args.league:
        league_id = args.league
        draft_url = f"https://fantasy.espn.com/football/draft?leagueId={args.league}"
    elif args.mock:
        league_id = "mock_draft"
        draft_url = "https://fantasy.espn.com/football/draft"
        
    # Create console application
    console = FixedDraftMonitorConsole(
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
            console.output.print_console_only("NOTE: For mock drafts, manually join a draft room in the browser\n")
            
        # Start monitoring
        await console.start_monitoring()
        
    except KeyboardInterrupt:
        console.output.print_console_only("\nInterrupted by user")
    except Exception as e:
        console.output.print_both(f"\nUnexpected error: {e}")
        sys.exit(1)
    finally:
        await console.shutdown()


if __name__ == "__main__":
    asyncio.run(main())