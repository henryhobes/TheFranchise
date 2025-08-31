#!/usr/bin/env python3
"""
State Update Handlers

Specialized handlers for draft state updates with comprehensive validation
and error recovery mechanisms.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from .draft_state import DraftState, DraftStatus


@dataclass
class ValidationResult:
    """Result of state validation check."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    def has_critical_errors(self) -> bool:
        """Check if validation found critical errors."""
        critical_keywords = ['corruption', 'inconsistent', 'missing', 'duplicate']
        return any(keyword in error.lower() for error in self.errors 
                  for keyword in critical_keywords)


class StateUpdateHandlers:
    """
    Specialized handlers for draft state updates with validation and recovery.
    
    Provides higher-level handlers that combine multiple state operations
    with comprehensive validation and error handling.
    """
    
    def __init__(self, draft_state: DraftState):
        """
        Initialize state handlers.
        
        Args:
            draft_state: DraftState instance to manage
        """
        self.draft_state = draft_state
        self.logger = logging.getLogger(__name__)
        
        # Handler statistics
        self.stats = {
            'picks_processed': 0,
            'picks_failed': 0,
            'clock_updates': 0,
            'validation_checks': 0,
            'validation_failures': 0,
            'state_recoveries': 0
        }
        
    def handle_pick_with_validation(self, player_id: str, team_id: str, 
                                  pick_number: int, position: str = "BENCH",
                                  validate_before: bool = True,
                                  validate_after: bool = True) -> Tuple[bool, ValidationResult]:
        """
        Handle pick with comprehensive validation.
        
        Args:
            player_id: ESPN player ID selected
            team_id: Team making the pick
            pick_number: Overall pick number
            position: Roster position 
            validate_before: Validate state before applying pick
            validate_after: Validate state after applying pick
            
        Returns:
            Tuple of (success, validation_result)
        """
        self.stats['picks_processed'] += 1
        
        validation_result = ValidationResult(True, [], [], [])
        
        try:
            # Pre-pick validation
            if validate_before:
                pre_validation = self.validate_pick_eligibility(player_id, team_id, pick_number)
                validation_result.errors.extend(pre_validation.errors)
                validation_result.warnings.extend(pre_validation.warnings)
                
                if not pre_validation.is_valid:
                    self.stats['picks_failed'] += 1
                    self.logger.warning(f"Pick validation failed: {pre_validation.errors}")
                    return False, validation_result
                    
            # Apply the pick
            success = self.draft_state.apply_pick(player_id, team_id, pick_number, position)
            
            if not success:
                self.stats['picks_failed'] += 1
                validation_result.is_valid = False
                validation_result.errors.append("Failed to apply pick to draft state")
                return False, validation_result
                
            # Post-pick validation
            if validate_after:
                post_validation = self.validate_draft_consistency()
                validation_result.errors.extend(post_validation.errors)
                validation_result.warnings.extend(post_validation.warnings)
                validation_result.suggestions.extend(post_validation.suggestions)
                
                if not post_validation.is_valid and post_validation.has_critical_errors():
                    self.logger.error(f"Critical state corruption detected: {post_validation.errors}")
                    # Attempt recovery
                    recovery_success = self._attempt_state_recovery()
                    if recovery_success:
                        self.stats['state_recoveries'] += 1
                        validation_result.suggestions.append("State automatically recovered from corruption")
                    else:
                        validation_result.errors.append("Failed to recover from state corruption")
                        
            self.logger.info(f"Successfully processed pick: {player_id} to team {team_id}")
            return True, validation_result
            
        except Exception as e:
            self.stats['picks_failed'] += 1
            validation_result.is_valid = False
            validation_result.errors.append(f"Exception handling pick: {e}")
            self.logger.error(f"Error in handle_pick_with_validation: {e}")
            return False, validation_result
            
    def handle_clock_change_with_validation(self, team_id: str, pick_number: int,
                                          time_limit: float) -> Tuple[bool, ValidationResult]:
        """
        Handle team going on clock with validation.
        
        Args:
            team_id: Team now picking
            pick_number: Pick number starting
            time_limit: Time limit in seconds
            
        Returns:
            Tuple of (success, validation_result)
        """
        self.stats['clock_updates'] += 1
        validation_result = ValidationResult(True, [], [], [])
        
        try:
            # Validate pick sequence
            expected_pick = self.draft_state.current_pick + 1
            if pick_number != expected_pick:
                validation_result.warnings.append(
                    f"Pick sequence warning: Expected {expected_pick}, got {pick_number}"
                )
                
            # Validate team order (if we have draft order info)
            if hasattr(self.draft_state, '_draft_order') and self.draft_state._draft_order:
                expected_team = self._calculate_expected_team(pick_number)
                if expected_team and expected_team != team_id:
                    validation_result.warnings.append(
                        f"Team order warning: Expected {expected_team}, got {team_id}"
                    )
                    
            # Apply clock change
            success = self.draft_state.start_new_pick(pick_number, team_id, time_limit)
            
            if not success:
                validation_result.is_valid = False
                validation_result.errors.append("Failed to update draft clock state")
                return False, validation_result
                
            self.logger.debug(f"Clock updated: Pick {pick_number}, team {team_id}")
            return True, validation_result
            
        except Exception as e:
            validation_result.is_valid = False
            validation_result.errors.append(f"Exception handling clock change: {e}")
            self.logger.error(f"Error in handle_clock_change_with_validation: {e}")
            return False, validation_result
            
    def validate_pick_eligibility(self, player_id: str, team_id: str, 
                                pick_number: int) -> ValidationResult:
        """
        Validate if a pick is eligible/legal.
        
        Args:
            player_id: Player being picked
            team_id: Team making pick
            pick_number: Pick number
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Check if player already drafted
        if player_id in self.draft_state.drafted_players:
            errors.append(f"Player {player_id} already drafted")
            
        # Check if player is in available pool
        if player_id not in self.draft_state.available_players:
            warnings.append(f"Player {player_id} not in available pool (may be valid if pool not initialized)")
            
        # Check pick sequence
        expected_pick = self.draft_state.current_pick + 1
        if pick_number != expected_pick:
            if pick_number < expected_pick:
                errors.append(f"Pick number {pick_number} is in the past (current: {self.draft_state.current_pick})")
            else:
                warnings.append(f"Pick number {pick_number} skips ahead (expected: {expected_pick})")
                
        # Check if team is on clock
        if self.draft_state.on_the_clock and self.draft_state.on_the_clock != team_id:
            warnings.append(f"Team {team_id} picking but {self.draft_state.on_the_clock} is on clock")
            
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, suggestions)
        
    def validate_draft_consistency(self) -> ValidationResult:
        """
        Comprehensive draft state consistency validation.
        
        Returns:
            ValidationResult with detailed analysis
        """
        self.stats['validation_checks'] += 1
        
        errors = []
        warnings = []
        suggestions = []
        
        # Use DraftState's built-in validation
        is_valid, state_errors = self.draft_state.validate_state()
        errors.extend(state_errors)
        
        # Additional consistency checks
        
        # Check roster size limits
        for team_id, roster in self.draft_state.other_rosters.items():
            total_players = sum(len(position_players) for position_players in roster.values())
            expected_picks = sum(1 for pick in self.draft_state.pick_history 
                               if pick['team_id'] == team_id)
            if total_players != expected_picks:
                errors.append(f"Team {team_id} roster count mismatch: {total_players} vs {expected_picks}")
                
        # Check our roster
        my_total = sum(len(players) for players in self.draft_state.my_roster.values())
        my_expected = sum(1 for pick in self.draft_state.pick_history 
                         if pick['team_id'] == self.draft_state.my_team_id)
        if my_total != my_expected:
            errors.append(f"Our roster count mismatch: {my_total} vs {my_expected}")
            
        # Check for duplicate players in rosters
        all_roster_players = set()
        for roster in self.draft_state.other_rosters.values():
            for position_players in roster.values():
                for player_id in position_players:
                    if player_id in all_roster_players:
                        errors.append(f"Duplicate player {player_id} found in multiple rosters")
                    all_roster_players.add(player_id)
                    
        # Add our roster players
        for position_players in self.draft_state.my_roster.values():
            for player_id in position_players:
                if player_id in all_roster_players:
                    errors.append(f"Duplicate player {player_id} found in our roster and others")
                all_roster_players.add(player_id)
                
        # Check that all roster players are in drafted set
        drafted_but_not_rostered = self.draft_state.drafted_players - all_roster_players
        if drafted_but_not_rostered:
            warnings.append(f"Players drafted but not in rosters: {drafted_but_not_rostered}")
            
        rostered_but_not_drafted = all_roster_players - self.draft_state.drafted_players
        if rostered_but_not_drafted:
            errors.append(f"Players in rosters but not drafted: {rostered_but_not_drafted}")
            
        # Performance suggestions
        if len(self.draft_state.available_players) > 1000:
            suggestions.append("Consider pruning available player pool for performance")
            
        if len(self.draft_state.pick_history) > 200:
            suggestions.append("Draft approaching completion, consider state cleanup")
            
        validation_is_valid = len(errors) == 0 and is_valid
        if not validation_is_valid:
            self.stats['validation_failures'] += 1
            
        return ValidationResult(validation_is_valid, errors, warnings, suggestions)
        
    def _calculate_expected_team(self, pick_number: int) -> Optional[str]:
        """
        Calculate which team should be picking based on snake draft order.
        
        Args:
            pick_number: Overall pick number (1-based)
            
        Returns:
            Expected team ID or None if can't calculate
        """
        if not hasattr(self.draft_state, '_draft_order') or not self.draft_state._draft_order:
            return None
            
        team_count = len(self.draft_state._draft_order)
        if team_count == 0:
            return None
            
        # Snake draft calculation
        round_num = (pick_number - 1) // team_count  # 0-based round
        position_in_round = (pick_number - 1) % team_count  # 0-based position
        
        if round_num % 2 == 0:  # Even round (0-based): normal order
            team_index = position_in_round
        else:  # Odd round: reverse order
            team_index = team_count - 1 - position_in_round
            
        return self.draft_state._draft_order[team_index]
        
    def _attempt_state_recovery(self) -> bool:
        """
        Attempt to recover from state corruption using snapshots.
        
        Returns:
            bool: True if recovery successful
        """
        try:
            # Try to rollback to the most recent valid snapshot
            for i in range(len(self.draft_state._state_snapshots) - 1, -1, -1):
                snapshot = self.draft_state.get_snapshot(i)
                if snapshot:
                    # Test if this snapshot is valid by creating temporary state
                    # For now, just rollback to most recent snapshot
                    success = self.draft_state.rollback_to_snapshot(i)
                    if success:
                        self.logger.info(f"State recovered using snapshot {i}")
                        return True
                        
            self.logger.error("No valid snapshots found for recovery")
            return False
            
        except Exception as e:
            self.logger.error(f"State recovery failed: {e}")
            return False
            
    def handle_draft_completion(self) -> ValidationResult:
        """
        Handle draft completion with final validation.
        
        Returns:
            ValidationResult with final draft analysis
        """
        self.draft_state.complete_draft()
        
        # Final validation
        validation = self.validate_draft_consistency()
        
        # Additional completion checks
        expected_total_picks = self.draft_state.team_count * self.draft_state.rounds
        actual_picks = len(self.draft_state.pick_history)
        
        if actual_picks != expected_total_picks:
            validation.warnings.append(
                f"Draft pick count mismatch: {actual_picks} vs expected {expected_total_picks}"
            )
            
        # Check that all teams have appropriate roster sizes
        for team_id, roster in self.draft_state.other_rosters.items():
            total_picks = sum(len(pos_players) for pos_players in roster.values())
            if total_picks != self.draft_state.rounds:
                validation.warnings.append(f"Team {team_id} has {total_picks} picks (expected {self.draft_state.rounds})")
                
        self.logger.info(f"Draft completion handled. Final validation: {validation.is_valid}")
        return validation
        
    def get_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state summary."""
        base_stats = self.draft_state.get_stats()
        handler_stats = self.get_stats()
        
        return {
            **base_stats,
            'handler_stats': handler_stats,
            'last_validation': datetime.now().isoformat(),
            'state_health': 'good' if handler_stats['validation_failures'] == 0 else 'warnings'
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        picks_processed = max(self.stats['picks_processed'], 0)
        picks_failed = max(self.stats['picks_failed'], 0)
        validation_checks = max(self.stats['validation_checks'], 0)
        validation_failures = max(self.stats['validation_failures'], 0)
        
        # Calculate success rates with proper bounds checking
        pick_success_rate = 1.0 if picks_processed == 0 else max(0.0, min(1.0, (picks_processed - picks_failed) / picks_processed))
        validation_success_rate = 1.0 if validation_checks == 0 else max(0.0, min(1.0, (validation_checks - validation_failures) / validation_checks))
        
        return {
            **self.stats,
            'pick_success_rate': pick_success_rate,
            'validation_success_rate': validation_success_rate
        }