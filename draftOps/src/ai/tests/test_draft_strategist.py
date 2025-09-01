#!/usr/bin/env python3
"""
Tests for Draft Strategist

Essential tests focusing on:
1. Core allocation logic works correctly
2. Budget constraints are met
3. Output format matches contract
4. Basic signal calculations function
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from draftOps.src.ai.core.draft_strategist import DraftStrategist, StrategistConfig
from draftOps.src.websocket_protocol.state.draft_state import DraftState
from draftOps.data_loader import Player


class TestDraftStrategist:
    """Test cases for Draft Strategist core functionality."""
    
    @pytest.fixture
    def basic_config(self):
        """Basic test configuration."""
        return StrategistConfig(selection_budget=15)
    
    @pytest.fixture
    def draft_state(self):
        """Mock draft state for testing."""
        state = DraftState("test_league", "team1", team_count=12, rounds=16)
        
        # Set some basic state
        state._current_pick = 24
        state._picks_until_next = 5
        state.set_draft_order([f"team{i}" for i in range(1, 13)])
        
        return state
    
    @pytest.fixture
    def sample_players(self):
        """Sample player pool for testing."""
        players = []
        
        # Create some test players for each position
        positions = ["QB", "RB", "WR", "TE", "DST", "K"]
        
        for pos_idx, pos in enumerate(positions):
            for i in range(10):  # 10 players per position
                rank = pos_idx * 10 + i + 1
                player = Player(
                    name=f"{pos}{i+1}",
                    team="TEST",
                    position=pos,
                    adp_rank=rank,
                    position_rank=i+1,
                    adp_avg=float(rank),
                    adp_std=2.0,
                    fantasy_points=100.0 - rank
                )
                players.append(player)
                
        return players
    
    def test_basic_allocation_creation(self, basic_config, draft_state, sample_players):
        """Test that basic allocation can be created."""
        strategist = DraftStrategist(basic_config)
        result = strategist.get_allocation(draft_state, sample_players)
        
        # Check contract compliance
        assert "player_lookup" in result
        assert "pick_strategy" in result
        
        # Check player_lookup structure
        player_lookup = result["player_lookup"]
        assert isinstance(player_lookup, dict)
        
        # Check all positions present
        expected_positions = ["QB", "RB", "WR", "TE", "DST", "K"]
        for pos in expected_positions:
            assert pos in player_lookup
            assert isinstance(player_lookup[pos], int)
            assert player_lookup[pos] >= 0
    
    def test_budget_constraint_met(self, basic_config, draft_state, sample_players):
        """Test that allocation always sums to selection budget."""
        strategist = DraftStrategist(basic_config)
        result = strategist.get_allocation(draft_state, sample_players)
        
        total_allocation = sum(result["player_lookup"].values())
        assert total_allocation == basic_config.selection_budget
    
    def test_different_budget_sizes(self, draft_state, sample_players):
        """Test allocation works with different budget sizes."""
        budgets = [5, 10, 15, 20, 30]
        
        for budget in budgets:
            config = StrategistConfig(selection_budget=budget)
            strategist = DraftStrategist(config)
            result = strategist.get_allocation(draft_state, sample_players)
            
            total_allocation = sum(result["player_lookup"].values())
            assert total_allocation == budget, f"Budget {budget} not met"
    
    def test_pick_strategy_format(self, basic_config, draft_state, sample_players):
        """Test that pick strategy is properly formatted."""
        strategist = DraftStrategist(basic_config)
        result = strategist.get_allocation(draft_state, sample_players)
        
        strategy = result["pick_strategy"]
        assert isinstance(strategy, str)
        assert len(strategy.strip()) > 0
        assert len(strategy) < 500  # Reasonable length limit
    
    def test_roster_need_calculation(self, basic_config, draft_state, sample_players):
        """Test roster need signal responds to roster gaps."""
        strategist = DraftStrategist(basic_config)
        
        # Test with empty roster (high need)
        need_empty = strategist._compute_roster_need("RB", draft_state)
        assert need_empty > 0.5  # Should show significant need
        
        # Add some RBs to roster
        draft_state._my_roster["RB"] = ["rb1", "rb2", "rb3"]
        need_filled = strategist._compute_roster_need("RB", draft_state)
        assert need_filled < need_empty  # Should show less need
    
    def test_late_draft_rule(self, draft_state, sample_players):
        """Test that DST/K are withheld until late rounds."""
        config = StrategistConfig(selection_budget=15, allow_dst_k_early=False)
        strategist = DraftStrategist(config)
        
        # Early in draft
        draft_state._current_pick = 24  # Round 2
        result = strategist.get_allocation(draft_state, sample_players)
        
        # DST/K should have minimal allocation early
        assert result["player_lookup"]["DST"] <= 1
        assert result["player_lookup"]["K"] <= 1
    
    def test_deterministic_output(self, basic_config, draft_state, sample_players):
        """Test that identical inputs produce identical outputs."""
        strategist1 = DraftStrategist(basic_config)
        strategist2 = DraftStrategist(basic_config)
        
        result1 = strategist1.get_allocation(draft_state, sample_players)
        result2 = strategist2.get_allocation(draft_state, sample_players)
        
        assert result1["player_lookup"] == result2["player_lookup"]
        assert result1["pick_strategy"] == result2["pick_strategy"]
    
    def test_signal_calculations_return_valid_ranges(self, basic_config, draft_state, sample_players):
        """Test that all signals return values in [0,1] range."""
        strategist = DraftStrategist(basic_config)
        signals = strategist._compute_all_signals(draft_state, sample_players)
        
        for pos in ["QB", "RB", "WR", "TE", "DST", "K"]:
            pos_signals = signals[pos]
            for signal_name, value in pos_signals.items():
                assert 0.0 <= value <= 1.0, f"{signal_name} for {pos} out of range: {value}"
    
    def test_fallback_allocation_valid(self, basic_config):
        """Test that fallback allocation meets contract requirements."""
        strategist = DraftStrategist(basic_config)
        result = strategist._get_fallback_allocation()
        
        # Check contract compliance
        assert "player_lookup" in result
        assert "pick_strategy" in result
        
        total_allocation = sum(result["player_lookup"].values())
        assert total_allocation == basic_config.selection_budget
    
    def test_edge_case_empty_player_pool(self, basic_config, draft_state):
        """Test behavior with empty player pool."""
        strategist = DraftStrategist(basic_config)
        result = strategist.get_allocation(draft_state, [])
        
        # Should still return valid contract
        assert "player_lookup" in result
        assert "pick_strategy" in result
        total_allocation = sum(result["player_lookup"].values())
        assert total_allocation == basic_config.selection_budget
    
    def test_weight_configuration(self, draft_state, sample_players):
        """Test that different weight configurations affect allocation."""
        # Config heavily weighting RosterNeed
        config1 = StrategistConfig(
            selection_budget=15,
            weights={
                'RosterNeed': 0.90,
                'TierUrgency': 0.02,
                'ValueGap': 0.02,
                'RunPressure': 0.03,
                'Scarcity': 0.03
            }
        )
        
        # Config heavily weighting Scarcity  
        config2 = StrategistConfig(
            selection_budget=15,
            weights={
                'RosterNeed': 0.05,
                'TierUrgency': 0.05,
                'ValueGap': 0.05,
                'RunPressure': 0.05,
                'Scarcity': 0.80
            }
        )
        
        strategist1 = DraftStrategist(config1)
        strategist2 = DraftStrategist(config2)
        
        result1 = strategist1.get_allocation(draft_state, sample_players)
        result2 = strategist2.get_allocation(draft_state, sample_players)
        
        # Results should be different due to different weightings
        assert result1["player_lookup"] != result2["player_lookup"]


if __name__ == "__main__":
    # Run basic smoke test if executed directly
    config = StrategistConfig(selection_budget=15)
    strategist = DraftStrategist(config)
    
    # Create minimal test data
    state = DraftState("test", "team1")
    state._current_pick = 12
    state._picks_until_next = 3
    
    players = [
        Player("TestQB", "TEST", "QB", 1, 1, 10.0, 1.0, 200.0),
        Player("TestRB", "TEST", "RB", 2, 1, 15.0, 2.0, 180.0),
        Player("TestWR", "TEST", "WR", 3, 1, 20.0, 2.5, 160.0)
    ]
    
    result = strategist.get_allocation(state, players)
    print(f"Smoke test passed: {result}")