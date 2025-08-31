#!/usr/bin/env python3
"""
ESPN Draft State Management

Core DraftState class that maintains accurate real-time state of an ESPN 
fantasy football draft based on WebSocket messages.

Implements the DraftState data structure specified in Sprint 1 with
immutable state updates and comprehensive validation.
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import copy


class DraftStatus(Enum):
    """Draft status enumeration."""
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS" 
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"


@dataclass(frozen=True)
class DraftStateSnapshot:
    """Immutable snapshot of draft state at a point in time."""
    timestamp: str
    drafted_players: frozenset[str]
    available_players: tuple[str, ...]
    my_roster: Dict[str, tuple[str, ...]]
    other_rosters: Dict[str, Dict[str, tuple[str, ...]]]
    current_pick: int
    picks_until_next: int
    time_remaining: float
    on_the_clock: str
    draft_status: DraftStatus
    pick_history: tuple[Dict[str, Any], ...]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for serialization."""
        return {
            'timestamp': self.timestamp,
            'drafted_players': list(self.drafted_players),
            'available_players': list(self.available_players),
            'my_roster': {pos: list(players) for pos, players in self.my_roster.items()},
            'other_rosters': {
                team: {pos: list(players) for pos, players in roster.items()}
                for team, roster in self.other_rosters.items()
            },
            'current_pick': self.current_pick,
            'picks_until_next': self.picks_until_next,
            'time_remaining': self.time_remaining,
            'on_the_clock': self.on_the_clock,
            'draft_status': self.draft_status.value,
            'pick_history': list(self.pick_history)
        }


class DraftState:
    """
    Real-time ESPN draft state management.
    
    Maintains complete draft state including picked players, team rosters,
    draft position, and timing information. Updates state based on WebSocket
    messages from ESPN draft room.
    
    Features:
    - Immutable state updates with rollback capability
    - Real-time pick tracking with sub-200ms updates
    - Snake draft position calculation
    - Comprehensive state validation
    - Pick history with full audit trail
    """
    
    def __init__(self, league_id: str, team_id: str, team_count: int = 12, 
                 rounds: int = 16, my_team_id: Optional[str] = None):
        """
        Initialize draft state.
        
        Args:
            league_id: ESPN league identifier
            team_id: Current user's team identifier
            team_count: Number of teams in draft
            rounds: Number of draft rounds
            my_team_id: Team ID we're tracking (defaults to team_id)
        """
        self.league_id = league_id
        self.team_id = team_id
        self.my_team_id = my_team_id or team_id
        self.team_count = team_count
        self.rounds = rounds
        
        # Core state - mutable for performance, immutable updates via methods
        self._drafted_players: Set[str] = set()
        self._available_players: List[str] = []
        self._my_roster: Dict[str, List[str]] = {
            'QB': [], 'RB': [], 'WR': [], 'TE': [], 'K': [], 'DST': [], 'FLEX': [], 'BENCH': []
        }
        self._other_rosters: Dict[str, Dict[str, List[str]]] = {}
        
        # Draft position state
        self._current_pick: int = 0
        self._picks_until_next: int = 0
        self._time_remaining: float = 0.0
        self._on_the_clock: str = ""
        
        # Draft metadata
        self._draft_status: DraftStatus = DraftStatus.WAITING
        self._pick_history: List[Dict[str, Any]] = []
        
        # Snake draft order calculation
        self._draft_order: List[str] = []  # Team IDs in draft order
        self._my_pick_positions: List[int] = []  # Our pick positions
        
        # State management
        self._state_snapshots: List[DraftStateSnapshot] = []
        self._max_snapshots: int = 100
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized DraftState for league {league_id}, team {team_id}")
        
    @property
    def drafted_players(self) -> Set[str]:
        """Get set of drafted player IDs."""
        return self._drafted_players.copy()
        
    @property
    def available_players(self) -> List[str]:
        """Get list of available player IDs."""
        return self._available_players.copy()
        
    @property
    def my_roster(self) -> Dict[str, List[str]]:
        """Get our team's roster."""
        return copy.deepcopy(self._my_roster)
        
    @property 
    def other_rosters(self) -> Dict[str, Dict[str, List[str]]]:
        """Get other teams' rosters."""
        return copy.deepcopy(self._other_rosters)
        
    @property
    def current_pick(self) -> int:
        """Get current overall pick number (1-based)."""
        return self._current_pick
        
    @property
    def picks_until_next(self) -> int:
        """Get picks until our next turn."""
        return self._picks_until_next
        
    @property
    def time_remaining(self) -> float:
        """Get time remaining on pick clock in seconds."""
        return self._time_remaining
        
    @property
    def on_the_clock(self) -> str:
        """Get team ID currently on the clock."""
        return self._on_the_clock
        
    @property
    def draft_status(self) -> DraftStatus:
        """Get current draft status."""
        return self._draft_status
        
    @property
    def pick_history(self) -> List[Dict[str, Any]]:
        """Get complete pick history."""
        return copy.deepcopy(self._pick_history)
        
    def initialize_player_pool(self, player_ids: List[str]) -> None:
        """
        Initialize available player pool.
        
        Args:
            player_ids: List of all draftable player IDs
        """
        self._available_players = player_ids.copy()
        self.logger.info(f"Initialized player pool with {len(player_ids)} players")
        
    def set_draft_order(self, draft_order: List[str]) -> None:
        """
        Set draft order and calculate our pick positions.
        
        Args:
            draft_order: List of team IDs in draft order
        """
        self._draft_order = draft_order.copy()
        
        # Calculate snake draft pick positions for our team
        if self.my_team_id in draft_order:
            my_position = draft_order.index(self.my_team_id)
            self._my_pick_positions = []
            
            for round_num in range(self.rounds):
                if round_num % 2 == 0:  # Even rounds (0-indexed): normal order
                    pick = round_num * self.team_count + my_position + 1
                else:  # Odd rounds: reverse order
                    pick = round_num * self.team_count + (self.team_count - my_position)
                self._my_pick_positions.append(pick)
                
        self.logger.info(f"Set draft order, our picks: {self._my_pick_positions}")
        
    def apply_pick(self, player_id: str, team_id: str, pick_number: int,
                   position: str = "BENCH") -> bool:
        """
        Apply a draft pick to state.
        
        Args:
            player_id: ESPN player ID that was selected
            team_id: Team that made the pick
            pick_number: Overall pick number
            position: Roster position (QB, RB, etc.)
            
        Returns:
            bool: True if pick was applied successfully
        """
        try:
            # Validation
            if player_id in self._drafted_players:
                self.logger.warning(f"Player {player_id} already drafted")
                return False
                
            if player_id not in self._available_players:
                self.logger.warning(f"Player {player_id} not in available pool")
                
            # Take snapshot before change (for rollback capability)
            self._take_snapshot()
            
            # Update state
            self._drafted_players.add(player_id)
            if player_id in self._available_players:
                self._available_players.remove(player_id)
                
            # Update roster
            if team_id == self.my_team_id:
                self._my_roster[position].append(player_id)
            else:
                if team_id not in self._other_rosters:
                    self._other_rosters[team_id] = {
                        'QB': [], 'RB': [], 'WR': [], 'TE': [], 'K': [], 'DST': [], 'FLEX': [], 'BENCH': []
                    }
                self._other_rosters[team_id][position].append(player_id)
                
            # Update pick tracking
            self._current_pick = pick_number
            self._update_picks_until_next()
            
            # Add to history
            pick_record = {
                'pick_number': pick_number,
                'player_id': player_id,
                'team_id': team_id,
                'position': position,
                'timestamp': datetime.now().isoformat()
            }
            self._pick_history.append(pick_record)
            
            self.logger.info(f"Applied pick {pick_number}: Player {player_id} to team {team_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying pick: {e}")
            return False
            
    def start_new_pick(self, pick_number: int, team_id: str, time_limit: float = 90.0) -> bool:
        """
        Start a new pick (team goes on the clock).
        
        Args:
            pick_number: Overall pick number starting
            team_id: Team that is now on the clock
            time_limit: Time limit for pick in seconds
            
        Returns:
            bool: True if state updated successfully
        """
        try:
            self._take_snapshot()
            
            self._current_pick = pick_number
            self._on_the_clock = team_id
            self._time_remaining = time_limit
            
            # Update picks until our next turn
            self._update_picks_until_next()
            
            # Update draft status
            if self._draft_status == DraftStatus.WAITING:
                self._draft_status = DraftStatus.IN_PROGRESS
                
            self.logger.info(f"Pick {pick_number} started, team {team_id} on clock")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting pick: {e}")
            return False
            
    def update_clock(self, time_remaining: float) -> bool:
        """
        Update pick clock time remaining.
        
        Args:
            time_remaining: Seconds remaining on pick clock
            
        Returns:
            bool: True if updated successfully
        """
        try:
            self._time_remaining = max(0.0, time_remaining)
            return True
        except Exception as e:
            self.logger.error(f"Error updating clock: {e}")
            return False
            
    def _update_picks_until_next(self) -> None:
        """Calculate picks remaining until our next turn."""
        if not self._my_pick_positions or self._current_pick >= max(self._my_pick_positions):
            self._picks_until_next = 0
            return
            
        # Find next pick position
        for pick_pos in self._my_pick_positions:
            if pick_pos > self._current_pick:
                self._picks_until_next = pick_pos - self._current_pick
                return
                
        self._picks_until_next = 0
        
    def complete_draft(self) -> None:
        """Mark draft as completed."""
        self._take_snapshot()
        self._draft_status = DraftStatus.COMPLETED
        self._on_the_clock = ""
        self._time_remaining = 0.0
        
        self.logger.info("Draft marked as completed")
        
    def validate_state(self) -> Tuple[bool, List[str]]:
        """
        Validate current draft state consistency.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Basic consistency checks
        if len(self._drafted_players) != len(self._pick_history):
            errors.append(f"Drafted players count ({len(self._drafted_players)}) != pick history ({len(self._pick_history)})")
            
        # Pick number should match completed picks (not in-progress picks)
        completed_picks = len(self._drafted_players)
        if completed_picks > 0 or self._current_pick > 0:
            # Current pick should be either equal to completed picks (no pick in progress)
            # or exactly one more (pick in progress)
            if self._current_pick < completed_picks:
                errors.append(f"Current pick ({self._current_pick}) is behind completed picks ({completed_picks})")
            elif self._current_pick > completed_picks + 1:
                errors.append(f"Current pick ({self._current_pick}) is too far ahead of completed picks ({completed_picks})")
            
        # All drafted players should be out of available pool
        overlap = self._drafted_players.intersection(set(self._available_players))
        if overlap:
            errors.append(f"Players in both drafted and available: {overlap}")
            
        # Roster counts should be reasonable
        total_my_picks = sum(len(players) for players in self._my_roster.values())
        expected_my_picks = sum(1 for pick in self._pick_history if pick['team_id'] == self.my_team_id)
        if total_my_picks != expected_my_picks:
            errors.append(f"My roster count ({total_my_picks}) != expected picks ({expected_my_picks})")
            
        is_valid = len(errors) == 0
        if not is_valid:
            self.logger.warning(f"State validation failed: {errors}")
        else:
            self.logger.debug("State validation passed")
            
        return is_valid, errors
        
    def _take_snapshot(self) -> None:
        """Take immutable snapshot of current state."""
        snapshot = DraftStateSnapshot(
            timestamp=datetime.now().isoformat(),
            drafted_players=frozenset(self._drafted_players),
            available_players=tuple(self._available_players),
            my_roster={pos: tuple(players) for pos, players in self._my_roster.items()},
            other_rosters={
                team: {pos: tuple(players) for pos, players in roster.items()}
                for team, roster in self._other_rosters.items()
            },
            current_pick=self._current_pick,
            picks_until_next=self._picks_until_next,
            time_remaining=self._time_remaining,
            on_the_clock=self._on_the_clock,
            draft_status=self._draft_status,
            pick_history=tuple(self._pick_history)
        )
        
        self._state_snapshots.append(snapshot)
        
        # Limit snapshot history with efficient cleanup
        if len(self._state_snapshots) > self._max_snapshots:
            self._state_snapshots = self._state_snapshots[1:]
            
    def get_snapshot(self, index: int = -1) -> Optional[DraftStateSnapshot]:
        """
        Get state snapshot by index.
        
        Args:
            index: Snapshot index (-1 for latest)
            
        Returns:
            DraftStateSnapshot or None if invalid index
        """
        try:
            return self._state_snapshots[index]
        except (IndexError, TypeError):
            return None
            
    def rollback_to_snapshot(self, index: int) -> bool:
        """
        Rollback state to a previous snapshot.
        
        Args:
            index: Snapshot index to rollback to
            
        Returns:
            bool: True if rollback successful
        """
        try:
            if index >= len(self._state_snapshots) or index < -len(self._state_snapshots):
                return False
                
            snapshot = self._state_snapshots[index]
            
            # Restore state from snapshot
            self._drafted_players = set(snapshot.drafted_players)
            self._available_players = list(snapshot.available_players)
            self._my_roster = {pos: list(players) for pos, players in snapshot.my_roster.items()}
            self._other_rosters = {
                team: {pos: list(players) for pos, players in roster.items()}
                for team, roster in snapshot.other_rosters.items()
            }
            self._current_pick = snapshot.current_pick
            self._picks_until_next = snapshot.picks_until_next
            self._time_remaining = snapshot.time_remaining
            self._on_the_clock = snapshot.on_the_clock
            self._draft_status = snapshot.draft_status
            self._pick_history = list(snapshot.pick_history)
            
            # Remove snapshots after rollback point
            self._state_snapshots = self._state_snapshots[:index + 1]
            
            self.logger.info(f"Rolled back to snapshot {index}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error rolling back: {e}")
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """Get draft state statistics."""
        total_picks = len(self._pick_history)
        total_available = len(self._available_players)
        my_picks = sum(1 for pick in self._pick_history if pick['team_id'] == self.my_team_id)
        
        return {
            'league_id': self.league_id,
            'team_id': self.team_id,
            'draft_status': self._draft_status.value,
            'current_pick': self._current_pick,
            'total_picks': total_picks,
            'my_picks': my_picks,
            'picks_until_next': self._picks_until_next,
            'available_players': total_available,
            'time_remaining': self._time_remaining,
            'on_the_clock': self._on_the_clock,
            'snapshots_count': len(self._state_snapshots),
            'my_roster_counts': {pos: len(players) for pos, players in self._my_roster.items()}
        }