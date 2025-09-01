#!/usr/bin/env python3
"""
Draft Strategist - Position Count Allocation

Implements the Draft Strategist logic specified for Sprint 2.
Produces position-count allocation and rationale for Scout/GM consumption.

Core functionality:
- Computes 5 signals per position (RosterNeed, TierUrgency, ValueGap, RunPressure, Scarcity)
- Allocates SELECTION_BUDGET across positions using weighted scoring
- Returns JSON contract: {player_lookup: {pos: count}, pick_strategy: "rationale"}
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import math

# Import DraftState for context and Player for data analysis
try:
    from ....websocket_protocol.state.draft_state import DraftState
    from ....data_loader import Player
except ImportError:
    # Fallback for direct execution or testing
    try:
        from state.draft_state import DraftState
        from data_loader import Player
    except ImportError:
        # Define minimal classes for testing
        class DraftState:
            def __init__(self, league_id, team_id, team_count=12, rounds=16):
                self.league_id = league_id
                self.team_id = team_id
                self.team_count = team_count
                self.rounds = rounds
                self.current_pick = 0
                self.picks_until_next = 0
                self.my_roster = {'QB': [], 'RB': [], 'WR': [], 'TE': [], 'DST': [], 'K': []}
                self.pick_history = []
        
        class Player:
            def __init__(self, name, team, position, adp_rank, position_rank, adp_avg, adp_std, fantasy_points):
                self.name = name
                self.team = team
                self.position = position
                self.adp_rank = adp_rank
                self.position_rank = position_rank
                self.adp_avg = adp_avg
                self.adp_std = adp_std
                self.fantasy_points = fantasy_points


@dataclass
class StrategistConfig:
    """Configuration for Draft Strategist."""
    selection_budget: int = 15
    weights: Dict[str, float] = None
    secondary_sort: str = "projection"
    late_draft_rounds: int = 2
    allow_dst_k_early: bool = False
    min_per_pos: Dict[str, int] = None
    max_per_pos: Dict[str, int] = None
    
    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                'RosterNeed': 0.40,
                'TierUrgency': 0.25,
                'ValueGap': 0.20,
                'RunPressure': 0.10,
                'Scarcity': 0.05
            }
        if self.min_per_pos is None:
            self.min_per_pos = {}
        if self.max_per_pos is None:
            self.max_per_pos = {}


class DraftStrategist:
    """
    Draft Strategist for position-count allocation.
    
    Analyzes current draft context and produces allocation recommendations
    for the Scout node to consume. Implements the 5-signal scoring system
    with configurable weights and budget allocation.
    """
    
    def __init__(self, config: Optional[StrategistConfig] = None):
        """
        Initialize Draft Strategist.
        
        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or StrategistConfig()
        self.logger = logging.getLogger(__name__)
        
        # Position order for consistent processing
        self.positions = ["QB", "RB", "WR", "TE", "DST", "K"]
        
        self.logger.info(f"DraftStrategist initialized with budget: {self.config.selection_budget}")
        
    def get_allocation(self, draft_state: DraftState, players: List[Player]) -> Dict[str, Any]:
        """
        Generate position allocation based on current draft state.
        
        Args:
            draft_state: Current draft state with roster/pick information
            players: Available player pool with rankings/projections
            
        Returns:
            Dict with player_lookup and pick_strategy as per contract
        """
        try:
            # Compute signals for each position
            signals = self._compute_all_signals(draft_state, players)
            
            # Calculate weighted scores
            scores = self._calculate_scores(signals)
            
            # Allocate budget across positions
            allocation = self._allocate_budget(scores, draft_state)
            
            # Generate strategy rationale
            strategy = self._generate_strategy(signals, allocation, draft_state)
            
            # Construct final contract
            result = {
                "player_lookup": allocation,
                "pick_strategy": strategy
            }
            
            # Validate contract compliance
            if not self._validate_contract(result):
                raise ValueError("Generated allocation does not meet contract requirements")
                
            self.logger.info(f"Allocation generated: {allocation}, Strategy: {strategy[:50]}...")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating allocation: {e}")
            # Return fallback allocation
            return self._get_fallback_allocation()
            
    def _compute_all_signals(self, draft_state: DraftState, players: List[Player]) -> Dict[str, Dict[str, float]]:
        """Compute all 5 signals for each position."""
        signals = {}
        
        for pos in self.positions:
            signals[pos] = {
                'RosterNeed': self._compute_roster_need(pos, draft_state),
                'TierUrgency': self._compute_tier_urgency(pos, draft_state, players),
                'ValueGap': self._compute_value_gap(pos, draft_state, players),
                'RunPressure': self._compute_run_pressure(pos, draft_state),
                'Scarcity': self._compute_scarcity(pos, players)
            }
            
        return signals
        
    def _compute_roster_need(self, position: str, draft_state: DraftState) -> float:
        """
        Compute RosterNeed signal: deficit vs ideal starters + bench plan.
        
        Returns value in [0,1] where 1 = maximum need
        """
        my_roster = draft_state.my_roster
        current_count = len(my_roster.get(position, []))
        
        # Define ideal targets per position (starter + depth)
        ideal_targets = {
            'QB': 2,   # 1 starter + 1 backup
            'RB': 5,   # 2-3 starters + 2-3 depth (high variance position)
            'WR': 6,   # 2-3 starters + 3 depth (lots of targets needed)
            'TE': 2,   # 1 starter + 1 backup
            'DST': 1,  # 1 starter only
            'K': 1     # 1 starter only
        }
        
        ideal = ideal_targets.get(position, 1)
        deficit = max(0, ideal - current_count)
        
        # Normalize to [0,1] - max deficit is the ideal count
        need_score = min(1.0, deficit / ideal)
        
        return need_score
        
    def _compute_tier_urgency(self, position: str, draft_state: DraftState, players: List[Player]) -> float:
        """
        Compute TierUrgency signal: risk a tier cliff occurs before our next pick.
        
        Returns value in [0,1] where 1 = maximum urgency
        """
        picks_until_next = draft_state.picks_until_next
        
        if picks_until_next <= 1:
            return 0.0  # No urgency if we're picking soon
            
        # Get available players at position sorted by ADP
        pos_players = [p for p in players if p.position == position]
        pos_players.sort(key=lambda p: p.adp_rank)
        
        if len(pos_players) < 2:
            return 0.0  # Not enough players to assess tiers
            
        # Look for ADP gaps that suggest tier breaks
        # Check if there's a large ADP gap within the next 'picks_until_next' players
        check_depth = min(picks_until_next + 2, len(pos_players))
        max_gap = 0
        
        for i in range(1, check_depth):
            gap = pos_players[i].adp_rank - pos_players[i-1].adp_rank
            max_gap = max(max_gap, gap)
            
        # Normalize gap to urgency score
        # A gap of 10+ ADP ranks suggests a tier break
        urgency = min(1.0, max_gap / 15.0)
        
        return urgency
        
    def _compute_value_gap(self, position: str, draft_state: DraftState, players: List[Player]) -> float:
        """
        Compute ValueGap signal: best available ADP vs expected slot (fallers).
        
        Returns value in [0,1] where 1 = maximum value opportunity
        """
        current_pick = draft_state.current_pick
        
        if current_pick <= 0:
            return 0.0
            
        # Get best available player at position
        pos_players = [p for p in players if p.position == position]
        if not pos_players:
            return 0.0
            
        best_available = min(pos_players, key=lambda p: p.adp_rank)
        
        # Calculate value gap: how much better is this than expected at current pick
        expected_adp = current_pick + 10  # Add buffer for pick timing
        actual_adp = best_available.adp_rank
        
        if actual_adp >= expected_adp:
            return 0.0  # No value, player going at or after expected time
            
        gap = expected_adp - actual_adp
        value_score = min(1.0, gap / 30.0)  # Normalize with max gap of 30
        
        return value_score
        
    def _compute_run_pressure(self, position: str, draft_state: DraftState) -> float:
        """
        Compute RunPressure signal: recent picks concentrated at position.
        
        Returns value in [0,1] where 1 = maximum run pressure
        """
        pick_history = draft_state.pick_history
        
        if len(pick_history) < 3:
            return 0.0  # Need some history to detect runs
            
        # Look at last 5 picks for position concentration
        recent_picks = pick_history[-5:]
        position_picks = len([p for p in recent_picks if p.get('position') == position])
        
        # If 2+ of last 5 picks were this position, there's run pressure
        run_intensity = position_picks / len(recent_picks)
        
        # High pressure if 40%+ of recent picks are this position
        pressure = min(1.0, run_intensity / 0.4)
        
        return pressure
        
    def _compute_scarcity(self, position: str, players: List[Player]) -> float:
        """
        Compute Scarcity signal: structural scarcity (e.g., elite TE).
        
        Returns value in [0,1] where 1 = maximum scarcity
        """
        # Get available players at position
        pos_players = [p for p in players if p.position == position]
        
        if not pos_players:
            return 1.0  # Maximum scarcity if no players available
            
        # Position scarcity factors based on typical draft patterns
        scarcity_factors = {
            'QB': 0.2,   # Many viable QBs available late
            'RB': 0.6,   # RBs become scarce quickly
            'WR': 0.4,   # Decent WR depth typically
            'TE': 0.8,   # Very scarce after top few TEs
            'DST': 0.1,  # Many similar DSTs available
            'K': 0.0     # All kickers roughly equivalent
        }
        
        base_scarcity = scarcity_factors.get(position, 0.5)
        
        # Adjust based on available pool size
        total_available = len(pos_players)
        if total_available <= 3:
            scarcity_adjustment = 0.5  # Boost for very thin position
        elif total_available <= 8:
            scarcity_adjustment = 0.2  # Moderate boost
        else:
            scarcity_adjustment = 0.0  # No adjustment for deep positions
            
        scarcity = min(1.0, base_scarcity + scarcity_adjustment)
        
        return scarcity
        
    def _calculate_scores(self, signals: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate weighted scores for each position."""
        scores = {}
        
        for pos in self.positions:
            pos_signals = signals[pos]
            score = 0.0
            
            for signal_name, weight in self.config.weights.items():
                signal_value = pos_signals.get(signal_name, 0.0)
                score += weight * signal_value
                
            scores[pos] = score
            
        return scores
        
    def _allocate_budget(self, scores: Dict[str, float], draft_state: DraftState) -> Dict[str, int]:
        """Allocate selection budget across positions based on scores."""
        
        # Normalize scores to proportions
        total_score = sum(scores.values())
        if total_score == 0:
            # Fallback to equal distribution
            proportions = {pos: 1.0/len(self.positions) for pos in self.positions}
        else:
            proportions = {pos: score/total_score for pos, score in scores.items()}
            
        # Calculate raw allocations
        raw_allocations = {}
        for pos in self.positions:
            raw = proportions[pos] * self.config.selection_budget
            raw_allocations[pos] = raw
            
        # Floor allocations and track remainders
        allocations = {}
        remainders = {}
        total_allocated = 0
        
        for pos in self.positions:
            floor_val = int(raw_allocations[pos])
            allocations[pos] = floor_val
            remainders[pos] = raw_allocations[pos] - floor_val
            total_allocated += floor_val
            
        # Distribute remaining budget by largest remainders
        remaining_budget = self.config.selection_budget - total_allocated
        
        # Sort positions by remainder size (stable sort for determinism)
        remainder_order = sorted(self.positions, key=lambda p: (remainders[p], p), reverse=True)
        
        for i in range(remaining_budget):
            pos = remainder_order[i % len(self.positions)]
            allocations[pos] += 1
            
        # Apply late-draft rule for DST/K
        allocations = self._apply_late_draft_rule(allocations, draft_state)
        
        # Apply min/max clamps if configured
        allocations = self._apply_clamps(allocations)
        
        # Final validation and rebalancing
        current_total = sum(allocations.values())
        if current_total != self.config.selection_budget:
            allocations = self._rebalance_allocation(allocations)
            
        return allocations
        
    def _apply_late_draft_rule(self, allocations: Dict[str, int], draft_state: DraftState) -> Dict[str, int]:
        """Apply late-draft rule: withhold DST/K until late rounds unless allowed early."""
        
        if self.config.allow_dst_k_early:
            return allocations
            
        current_pick = draft_state.current_pick
        total_picks = draft_state.team_count * draft_state.rounds
        picks_remaining = total_picks - current_pick
        
        # If we're in final few rounds, must include DST/K
        in_late_rounds = picks_remaining <= (self.config.late_draft_rounds * draft_state.team_count)
        
        if not in_late_rounds:
            # Redistribute DST/K allocation to other positions
            dst_allocation = allocations['DST']
            k_allocation = allocations['K']
            total_to_redistribute = dst_allocation + k_allocation
            
            allocations['DST'] = 0
            allocations['K'] = 0
            
            # Redistribute proportionally to skill positions
            skill_positions = ['QB', 'RB', 'WR', 'TE']
            skill_total = sum(allocations[pos] for pos in skill_positions)
            
            if skill_total > 0:
                for pos in skill_positions:
                    proportion = allocations[pos] / skill_total
                    additional = int(proportion * total_to_redistribute)
                    allocations[pos] += additional
                    total_to_redistribute -= additional
                    
                # Give any remainder to RB (highest variance position)
                allocations['RB'] += total_to_redistribute
        else:
            # In late rounds, ensure at least 1 each for DST/K if we need them
            my_roster = draft_state.my_roster
            if len(my_roster.get('DST', [])) == 0 and allocations['DST'] == 0:
                allocations['DST'] = 1
            if len(my_roster.get('K', [])) == 0 and allocations['K'] == 0:
                allocations['K'] = 1
                
        return allocations
        
    def _apply_clamps(self, allocations: Dict[str, int]) -> Dict[str, int]:
        """Apply min/max per position clamps if configured."""
        
        for pos in self.positions:
            min_val = self.config.min_per_pos.get(pos, 0)
            max_val = self.config.max_per_pos.get(pos, self.config.selection_budget)
            
            allocations[pos] = max(min_val, min(max_val, allocations[pos]))
            
        return allocations
        
    def _rebalance_allocation(self, allocations: Dict[str, int]) -> Dict[str, int]:
        """Rebalance allocation to meet exact budget requirement."""
        
        current_total = sum(allocations.values())
        target_total = self.config.selection_budget
        difference = target_total - current_total
        
        if difference == 0:
            return allocations
            
        # Adjust by adding/removing from positions with highest allocations
        positions_by_allocation = sorted(self.positions, key=lambda p: allocations[p], reverse=True)
        
        if difference > 0:
            # Need to add counts
            for i in range(difference):
                pos = positions_by_allocation[i % len(self.positions)]
                allocations[pos] += 1
        else:
            # Need to remove counts
            for i in range(abs(difference)):
                pos = positions_by_allocation[i % len(self.positions)]
                if allocations[pos] > 0:
                    allocations[pos] -= 1
                    
        return allocations
        
    def _generate_strategy(self, signals: Dict[str, Dict[str, float]], 
                          allocation: Dict[str, int], draft_state: DraftState) -> str:
        """Generate 1-3 sentence strategy rationale."""
        
        # Find primary drivers (highest weighted signal contributions)
        primary_reasons = []
        
        # Check for high-allocation positions and their primary drivers
        top_positions = sorted(allocation.items(), key=lambda x: x[1], reverse=True)[:2]
        
        for pos, count in top_positions:
            if count > 3:  # Significant allocation
                pos_signals = signals[pos]
                
                # Find dominant signal for this position
                max_signal = max(pos_signals.items(), key=lambda x: x[1] * self.config.weights.get(x[0], 0))
                signal_name, signal_value = max_signal
                
                if signal_value > 0.5:  # Significant signal
                    primary_reasons.append(self._get_signal_explanation(pos, signal_name, signal_value))
                    
        # Check for late draft considerations
        current_pick = draft_state.current_pick
        total_picks = draft_state.team_count * draft_state.rounds if draft_state.rounds > 0 else 192
        remaining_rounds = max(1, (total_picks - current_pick) // draft_state.team_count)
        
        if remaining_rounds <= 3 and (allocation['DST'] > 0 or allocation['K'] > 0):
            primary_reasons.append("beginning shortlist DST/K so you're not scraping at the end")
        
        # Construct strategy message
        if len(primary_reasons) >= 2:
            strategy = f"{primary_reasons[0]} and {primary_reasons[1]}."
        elif len(primary_reasons) == 1:
            strategy = f"{primary_reasons[0]}."
        else:
            # Fallback strategy based on allocation
            max_pos = max(allocation.items(), key=lambda x: x[1])
            strategy = f"Focus on {max_pos[0]} depth with balanced coverage across other positions."
            
        return strategy
        
    def _get_signal_explanation(self, position: str, signal_name: str, signal_value: float) -> str:
        """Get human-readable explanation for a signal."""
        
        explanations = {
            'RosterNeed': f"{position} roster gaps need filling",
            'TierUrgency': f"{position} tier cliff approaching before next pick",
            'ValueGap': f"value opportunity with {position} fallers available",
            'RunPressure': f"{position} run detected, may need to react",
            'Scarcity': f"{position} structural scarcity requires early attention"
        }
        
        return explanations.get(signal_name, f"{position} showing {signal_name} signal")
        
    def _validate_contract(self, result: Dict[str, Any]) -> bool:
        """Validate that result meets API contract requirements."""
        
        # Check required fields
        if 'player_lookup' not in result or 'pick_strategy' not in result:
            return False
            
        player_lookup = result['player_lookup']
        pick_strategy = result['pick_strategy']
        
        # Check player_lookup structure
        if not isinstance(player_lookup, dict):
            return False
            
        # Check all required position keys
        for pos in self.positions:
            if pos not in player_lookup:
                return False
            if not isinstance(player_lookup[pos], int) or player_lookup[pos] < 0:
                return False
                
        # Check budget constraint
        total_allocation = sum(player_lookup.values())
        if total_allocation != self.config.selection_budget:
            return False
            
        # Check pick_strategy
        if not isinstance(pick_strategy, str) or len(pick_strategy.strip()) == 0:
            return False
            
        return True
        
    def _get_fallback_allocation(self) -> Dict[str, Any]:
        """Return safe fallback allocation if main logic fails."""
        
        # Simple fallback: distribute budget evenly with bias toward skill positions
        fallback_weights = {'QB': 1, 'RB': 3, 'WR': 4, 'TE': 1, 'DST': 0, 'K': 0}
        total_weight = sum(fallback_weights.values())
        
        allocation = {}
        total_allocated = 0
        
        for pos in self.positions:
            count = int((fallback_weights[pos] / total_weight) * self.config.selection_budget)
            allocation[pos] = count
            total_allocated += count
            
        # Distribute remainder to WR
        remaining = self.config.selection_budget - total_allocated
        allocation['WR'] += remaining
        
        return {
            "player_lookup": allocation,
            "pick_strategy": "Balanced approach focusing on WR depth with RB coverage and essential positions filled."
        }