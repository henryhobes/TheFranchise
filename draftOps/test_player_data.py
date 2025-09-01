#!/usr/bin/env python3
"""
Unit tests for player data loading and integration.
"""

import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_loader import Player, PlayerDataLoader, load_player_data
from src.websocket_protocol.state.draft_state import DraftState


class TestPlayerDataLoading(unittest.TestCase):
    """Test player data loading functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Load player data once for all tests."""
        cls.players = load_player_data("playerData")
        
    def test_player_data_loaded(self):
        """Test that player data loads successfully."""
        self.assertGreater(len(self.players), 0)
        self.assertLessEqual(len(self.players), 400)  # Reasonable upper bound
        
    def test_player_object_structure(self):
        """Test that Player objects have required fields."""
        player = self.players[0]
        
        # Required fields
        self.assertIsInstance(player.name, str)
        self.assertIsInstance(player.team, str)
        self.assertIsInstance(player.position, str)
        self.assertIsInstance(player.adp_rank, int)
        self.assertIsInstance(player.position_rank, int)
        self.assertIsInstance(player.adp_avg, float)
        self.assertIsInstance(player.adp_std, float)
        self.assertIsInstance(player.fantasy_points, float)
        
    def test_positions_loaded(self):
        """Test that all expected positions are present."""
        positions = set(p.position for p in self.players)
        expected_positions = {'QB', 'RB', 'WR', 'TE', 'K', 'DST'}
        
        for pos in expected_positions:
            self.assertIn(pos, positions, f"Missing position: {pos}")
            
    def test_top_players_have_low_adp(self):
        """Test that top-ranked players have low ADP values."""
        top_5 = sorted(self.players, key=lambda p: p.adp_rank)[:5]
        
        for player in top_5:
            self.assertLess(player.adp_avg, 20.0, f"{player.name} should have low ADP")
            
    def test_fantasy_points_projections(self):
        """Test that most players have fantasy point projections."""
        players_with_projections = [p for p in self.players if p.fantasy_points > 0]
        projection_rate = len(players_with_projections) / len(self.players)
        
        self.assertGreater(projection_rate, 0.8, "Most players should have projections")
        
    def test_specific_top_players(self):
        """Test that specific top players are loaded correctly."""
        player_lookup = {p.name: p for p in self.players}
        
        # Test some known top players
        expected_top_players = ["Ja'Marr Chase", "Bijan Robinson", "CeeDee Lamb"]
        
        for name in expected_top_players:
            self.assertIn(name, player_lookup, f"{name} should be in player data")
            player = player_lookup[name]
            self.assertLess(player.adp_avg, 10.0, f"{name} should have very low ADP")
            

class TestDraftStateIntegration(unittest.TestCase):
    """Test DraftState integration with player data."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.players = load_player_data("playerData")
        self.draft_state = DraftState("test_league", "team1", 12, 16)
        self.draft_state.load_player_database(self.players)
        
    def test_player_database_loaded(self):
        """Test that player database is loaded into DraftState."""
        self.assertEqual(len(self.draft_state._player_database), len(self.players))
        
    def test_player_lookup_by_name(self):
        """Test that players can be found by name."""
        test_name = "Josh Allen"
        player = self.draft_state.get_player(test_name)
        
        self.assertIsNotNone(player)
        self.assertEqual(player.name, test_name)
        self.assertEqual(player.position, "QB")
        
    def test_positional_queries(self):
        """Test querying players by position."""
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        
        for pos in positions:
            players = self.draft_state.get_available_players_by_position(pos)
            self.assertGreater(len(players), 0, f"Should find {pos} players")
            
            for player in players:
                self.assertEqual(player.position, pos)
                
    def test_top_available_players(self):
        """Test getting top available players."""
        top_players = self.draft_state.get_top_available_players(10)
        
        self.assertEqual(len(top_players), 10)
        
        # Should be sorted by ADP rank
        for i in range(1, len(top_players)):
            self.assertLessEqual(
                top_players[i-1].adp_rank, 
                top_players[i].adp_rank,
                "Players should be sorted by ADP rank"
            )
            
    def test_draft_pick_tracking(self):
        """Test ESPN draft pick tracking."""
        # Initialize with mock ESPN IDs
        espn_ids = [f"espn_{i}" for i in range(100)]
        self.draft_state.initialize_player_pool(espn_ids)
        
        # Apply a pick
        success = self.draft_state.apply_pick("espn_1", "team1", 1, "BENCH")
        self.assertTrue(success)
        
        # Check state
        self.assertIn("espn_1", self.draft_state.drafted_players)
        self.assertNotIn("espn_1", self.draft_state.available_players)
        

class TestPlayerDataValidation(unittest.TestCase):
    """Test data validation and consistency."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.players = load_player_data("playerData")
        
    def test_no_duplicate_names(self):
        """Test that there are no duplicate player names."""
        names = [p.name for p in self.players]
        unique_names = set(names)
        
        self.assertEqual(len(names), len(unique_names), "No duplicate player names allowed")
        
    def test_position_ranks_sequential(self):
        """Test that position ranks are reasonable."""
        for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DST']:
            pos_players = [p for p in self.players if p.position == pos]
            pos_players.sort(key=lambda p: p.position_rank)
            
            ranks = [p.position_rank for p in pos_players]
            
            # First player should be rank 1
            if ranks:
                self.assertEqual(ranks[0], 1, f"First {pos} should be rank 1")
                
            # Ranks should be reasonable (not huge gaps)
            self.assertLessEqual(max(ranks), len(ranks) + 20, f"{pos} ranks should be reasonable")
            
    def test_adp_values_reasonable(self):
        """Test that ADP values are in reasonable ranges."""
        for player in self.players:
            self.assertGreater(player.adp_avg, 0, f"{player.name} ADP should be positive")
            self.assertLess(player.adp_avg, 500, f"{player.name} ADP should be reasonable")
            self.assertGreaterEqual(player.adp_std, 0, f"{player.name} ADP std dev should be non-negative")


if __name__ == '__main__':
    # Set up logging to reduce noise during tests
    import logging
    logging.basicConfig(level=logging.ERROR)
    
    unittest.main()