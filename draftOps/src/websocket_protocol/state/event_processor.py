#!/usr/bin/env python3
"""
Draft Event Processor

Processes ESPN WebSocket messages and translates them into DraftState updates.
Based on Sprint 0's protocol discovery showing text-based command structure.
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import re

from .draft_state import DraftState


class MessageParseError(Exception):
    """Error parsing WebSocket message."""
    pass


class DraftEventProcessor:
    """
    Processes ESPN draft WebSocket messages and updates DraftState.
    
    Based on Sprint 0 protocol discovery:
    - SELECTED {teamId} {playerId} {overallPick} {memberId}
    - SELECTING {teamId} {timeMs}
    - CLOCK {teamId} {timeRemainingMs} {round?}
    - AUTODRAFT {teamId} {boolean}
    - Plus session management (TOKEN, JOINED, PING/PONG)
    """
    
    def __init__(self, draft_state: DraftState):
        """
        Initialize event processor.
        
        Args:
            draft_state: DraftState instance to update
        """
        self.draft_state = draft_state
        self.logger = logging.getLogger(__name__)
        
        # Message processing callbacks
        self.on_pick_made: Optional[Callable] = None
        self.on_team_selecting: Optional[Callable] = None 
        self.on_clock_update: Optional[Callable] = None
        self.on_autodraft_change: Optional[Callable] = None
        
        # Processing statistics
        self.stats = {
            'total_messages': 0,
            'selected_messages': 0,
            'selecting_messages': 0,
            'clock_messages': 0,
            'parse_errors': 0,
            'state_update_errors': 0
        }
        
        # Message validation patterns
        self._member_id_pattern = re.compile(r'^\{[A-F0-9-]{36}\}$')
        
    def process_websocket_message(self, message: str, websocket_url: str = "") -> bool:
        """
        Process a WebSocket message and update draft state.
        
        Args:
            message: Raw WebSocket message text
            websocket_url: Source WebSocket URL for logging
            
        Returns:
            bool: True if message was processed successfully
        """
        self.stats['total_messages'] += 1
        
        try:
            # Parse the message
            parsed = self._parse_message(message)
            
            if parsed['type'] == 'UNKNOWN':
                self.logger.debug(f"Unrecognized message: {message}")
                return True  # Not an error, just not handled
                
            # Route to appropriate handler
            success = self._route_message(parsed, message)
            
            if not success:
                self.stats['state_update_errors'] += 1
                self.logger.error(f"Failed to update state for message: {message}")
                
            return success
            
        except Exception as e:
            self.stats['parse_errors'] += 1
            self.logger.error(f"Error processing message '{message}': {e}")
            return False
            
    def _parse_message(self, message: str) -> Dict[str, Any]:
        """
        Parse WebSocket message text into structured data.
        
        Based on Sprint 0 protocol discovery:
        - SELECTED {teamId} {playerId} {overallPick} {memberId}
        - SELECTING {teamId} {timeMs}
        - CLOCK {teamId} {timeRemainingMs} {round?}
        - AUTODRAFT {teamId} {boolean}
        
        Args:
            message: Raw message text
            
        Returns:
            Dictionary with parsed message data
        """
        try:
            parts = message.strip().split()
            if not parts:
                return {"type": "UNKNOWN", "raw": message}
                
            command = parts[0].upper()
            
            if command == "SELECTED" and len(parts) >= 5:
                return {
                    "type": "SELECTED",
                    "team_id": parts[1],
                    "player_id": parts[2],
                    "overall_pick": int(parts[3]),
                    "member_id": parts[4],
                    "raw": message
                }
                
            elif command == "SELECTING" and len(parts) >= 3:
                return {
                    "type": "SELECTING", 
                    "team_id": parts[1],
                    "time_ms": int(parts[2]),
                    "raw": message
                }
                
            elif command == "CLOCK" and len(parts) >= 3:
                return {
                    "type": "CLOCK",
                    "team_id": parts[1], 
                    "time_remaining_ms": int(parts[2]),
                    "round": int(parts[3]) if len(parts) > 3 else None,
                    "raw": message
                }
                
            elif command == "AUTODRAFT" and len(parts) >= 3:
                return {
                    "type": "AUTODRAFT",
                    "team_id": parts[1],
                    "enabled": parts[2].lower() == "true",
                    "raw": message
                }
                
            elif command in ["TOKEN", "JOINED", "LEFT", "PING", "PONG"]:
                return {
                    "type": command,
                    "raw": message,
                    "parts": parts[1:]  # Additional data varies
                }
                
            else:
                return {"type": "UNKNOWN", "raw": message}
                
        except (ValueError, IndexError) as e:
            raise MessageParseError(f"Failed to parse message '{message}': {e}")
            
    def _route_message(self, parsed: Dict[str, Any], raw_message: str) -> bool:
        """
        Route parsed message to appropriate handler.
        
        Args:
            parsed: Parsed message data
            raw_message: Original message text
            
        Returns:
            bool: True if handled successfully
        """
        message_type = parsed['type']
        
        try:
            if message_type == "SELECTED":
                return self._handle_selected(parsed)
            elif message_type == "SELECTING":
                return self._handle_selecting(parsed)
            elif message_type == "CLOCK":
                return self._handle_clock(parsed)
            elif message_type == "AUTODRAFT":
                return self._handle_autodraft(parsed)
            elif message_type in ["TOKEN", "JOINED", "LEFT", "PING", "PONG"]:
                return self._handle_session_message(parsed)
            else:
                return True  # Unknown messages are not errors
                
        except Exception as e:
            self.logger.error(f"Error in message handler for {message_type}: {e}")
            return False
            
    def _handle_selected(self, parsed: Dict[str, Any]) -> bool:
        """
        Handle SELECTED message (pick made).
        
        Message: SELECTED {teamId} {playerId} {overallPick} {memberId}
        Updates: Add player to drafted list, remove from available, update rosters
        """
        self.stats['selected_messages'] += 1
        
        team_id = parsed['team_id']
        player_id = parsed['player_id'] 
        pick_number = parsed['overall_pick']
        
        self.logger.info(f"Processing pick: Team {team_id} selected player {player_id} (pick {pick_number})")
        
        # Apply pick to draft state with position detection
        position = self._resolve_position(player_id)
        success = self.draft_state.apply_pick(
            player_id=player_id,
            team_id=team_id, 
            pick_number=pick_number,
            position=position
        )
        
        # Trigger callback if registered
        if self.on_pick_made and success:
            try:
                self.on_pick_made({
                    'team_id': team_id,
                    'player_id': player_id,
                    'pick_number': pick_number,
                    'member_id': parsed['member_id']
                })
            except Exception as e:
                self.logger.error(f"Error in pick_made callback: {e}")
                
        return success
        
    def _handle_selecting(self, parsed: Dict[str, Any]) -> bool:
        """
        Handle SELECTING message (team on clock).
        
        Message: SELECTING {teamId} {timeMs}
        Updates: Set current pick, team on clock, reset timer
        """
        self.stats['selecting_messages'] += 1
        
        team_id = parsed['team_id']
        time_limit_ms = parsed['time_ms']
        time_limit_seconds = time_limit_ms / 1000.0
        
        # Calculate next pick number (current pick + 1)
        next_pick = self.draft_state.current_pick + 1
        
        self.logger.info(f"Team {team_id} now selecting (pick {next_pick}, {time_limit_seconds}s)")
        
        # Update draft state
        success = self.draft_state.start_new_pick(
            pick_number=next_pick,
            team_id=team_id,
            time_limit=time_limit_seconds
        )
        
        # Trigger callback if registered
        if self.on_team_selecting and success:
            try:
                self.on_team_selecting({
                    'team_id': team_id,
                    'pick_number': next_pick,
                    'time_limit': time_limit_seconds
                })
            except Exception as e:
                self.logger.error(f"Error in team_selecting callback: {e}")
                
        return success
        
    def _handle_clock(self, parsed: Dict[str, Any]) -> bool:
        """
        Handle CLOCK message (timer update).
        
        Message: CLOCK {teamId} {timeRemainingMs} {round?}
        Updates: Update countdown timer
        """
        self.stats['clock_messages'] += 1
        
        time_remaining_ms = parsed['time_remaining_ms']
        time_remaining_seconds = max(0, time_remaining_ms / 1000.0)
        
        # Update timer in draft state
        success = self.draft_state.update_clock(time_remaining_seconds)
        
        # Trigger callback if registered
        if self.on_clock_update and success:
            try:
                self.on_clock_update({
                    'team_id': parsed['team_id'],
                    'time_remaining': time_remaining_seconds,
                    'round': parsed.get('round')
                })
            except Exception as e:
                self.logger.error(f"Error in clock_update callback: {e}")
                
        return success
        
    def _handle_autodraft(self, parsed: Dict[str, Any]) -> bool:
        """
        Handle AUTODRAFT message (autodraft status change).
        
        Message: AUTODRAFT {teamId} {boolean}
        Updates: Log autodraft status (not currently tracked in DraftState)
        """
        team_id = parsed['team_id']
        enabled = parsed['enabled']
        
        self.logger.info(f"Team {team_id} autodraft: {'enabled' if enabled else 'disabled'}")
        
        # Trigger callback if registered
        if self.on_autodraft_change:
            try:
                self.on_autodraft_change({
                    'team_id': team_id,
                    'enabled': enabled
                })
            except Exception as e:
                self.logger.error(f"Error in autodraft_change callback: {e}")
                
        return True
        
    def _handle_session_message(self, parsed: Dict[str, Any]) -> bool:
        """
        Handle session management messages.
        
        Messages: TOKEN, JOINED, LEFT, PING, PONG
        Updates: Log for debugging, maintain connection health
        """
        message_type = parsed['type']
        
        if message_type in ["PING", "PONG"]:
            self.logger.debug(f"Heartbeat: {message_type}")
        else:
            self.logger.info(f"Session message: {parsed['raw']}")
            
        return True
        
    def set_position_resolver(self, position_resolver: Callable[[str], str]):
        """
        Set function to resolve player positions.
        
        Args:
            position_resolver: Function that takes player_id and returns position
        """
        self._position_resolver = position_resolver
        
    def _resolve_position(self, player_id: str) -> str:
        """
        Resolve player position for roster placement.
        
        Args:
            player_id: ESPN player ID
            
        Returns:
            Position string (QB, RB, WR, TE, K, DST, FLEX, BENCH)
        """
        if hasattr(self, '_position_resolver'):
            try:
                return self._position_resolver(player_id)
            except Exception as e:
                self.logger.warning(f"Position resolver failed for {player_id}: {e}")
                
        return "BENCH"  # Default fallback
        
    def get_stats(self) -> Dict[str, Any]:
        """Get event processing statistics."""
        total = self.stats['total_messages']
        
        # Prevent division by zero with proper guards
        if total == 0:
            return {
                **self.stats,
                'success_rate': 1.0,
                'parse_error_rate': 0.0,
                'state_error_rate': 0.0
            }
        
        return {
            **self.stats,
            'success_rate': (total - self.stats['parse_errors'] - self.stats['state_update_errors']) / total,
            'parse_error_rate': self.stats['parse_errors'] / total,
            'state_error_rate': self.stats['state_update_errors'] / total
        }
        
    def reset_stats(self):
        """Reset processing statistics."""
        for key in self.stats:
            self.stats[key] = 0