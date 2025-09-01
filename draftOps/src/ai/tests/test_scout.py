#!/usr/bin/env python3
"""
Tests for Scout Node Implementation

Tests the core functionality of the Scout agent including:
- Single recommendation generation
- Multiple parallel recommendations  
- Input validation
- JSON schema compliance
- Error handling and fallback behavior
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

import sys
import os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.scout import Scout, ScoutRecommendation


class TestScout:
    """Test cases for Scout node."""
    
    @pytest.fixture
    def mock_openai_key(self, monkeypatch):
        """Mock OpenAI API key for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        
    @pytest.fixture
    def sample_candidates(self) -> List[Dict[str, Any]]:
        """Sample pick candidates for testing."""
        return [
            {
                "player_id": "12345",
                "name": "Christian McCaffrey",
                "position": "RB",
                "adp": 2.1,
                "projection": 285.5,
                "tier": 1,
                "team": "SF"
            },
            {
                "player_id": "23456", 
                "name": "Cooper Kupp",
                "position": "WR",
                "adp": 15.3,
                "projection": 245.2,
                "tier": 2,
                "team": "LAR"
            },
            {
                "player_id": "34567",
                "name": "Mark Andrews", 
                "position": "TE",
                "adp": 25.7,
                "projection": 195.8,
                "tier": 1,
                "team": "BAL"
            }
        ]
        
    @pytest.fixture
    def sample_draft_state(self) -> Dict[str, Any]:
        """Sample draft state for testing."""
        return {
            "round": 2,
            "pick": 15,
            "picks_until_next_turn": 5,
            "our_roster_counts": {"QB": 1, "RB": 1, "WR": 0, "TE": 0},
            "lineup_rules": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1}
        }
        
    @pytest.fixture
    def sample_strategy(self) -> str:
        """Sample pick strategy for testing."""
        return "Target WR depth with tier urgency before position run develops"
        
    def test_scout_initialization(self, mock_openai_key):
        """Test Scout agent initializes correctly."""
        scout = Scout()
        
        assert scout.model_name == "gpt-5"
        assert scout.temperature == 1.0
        assert scout.api_key == "test-key"
        
    def test_scout_custom_params(self, mock_openai_key):
        """Test Scout with custom parameters."""
        scout = Scout(model_name="gpt-4o", temperature=0.8)
        
        assert scout.model_name == "gpt-4o"
        assert scout.temperature == 0.8
        
    def test_missing_api_key(self, monkeypatch):
        """Test Scout raises error with missing API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
            Scout()
            
    @patch('ai.core.scout.ChatOpenAI')
    def test_get_recommendation_success(self, mock_chat, mock_openai_key, 
                                      sample_candidates, sample_draft_state, sample_strategy):
        """Test successful recommendation generation."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "suggested_player_id": "23456",
            "suggested_player_name": "Cooper Kupp", 
            "position": "WR",
            "reason": "We need WR depth and Kupp represents excellent value at this ADP. Tier urgency suggests acting now before the position run.",
            "score_hint": 0.85
        })
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        scout = Scout()
        recommendation = scout.get_recommendation(
            sample_candidates, sample_strategy, sample_draft_state
        )
        
        assert isinstance(recommendation, ScoutRecommendation)
        assert recommendation.suggested_player_id == "23456"
        assert recommendation.suggested_player_name == "Cooper Kupp"
        assert recommendation.position == "WR"
        assert "WR depth" in recommendation.reason
        assert recommendation.score_hint == 0.85
        
    @patch('ai.core.scout.ChatOpenAI')
    def test_get_recommendation_with_seed(self, mock_chat, mock_openai_key,
                                        sample_candidates, sample_draft_state, sample_strategy):
        """Test recommendation generation with seed for reproducibility."""
        mock_response = Mock()
        mock_response.content = json.dumps({
            "suggested_player_id": "12345",
            "suggested_player_name": "Christian McCaffrey",
            "position": "RB", 
            "reason": "Elite RB1 talent available at good value.",
            "score_hint": 0.95
        })
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        scout = Scout()
        recommendation = scout.get_recommendation(
            sample_candidates, sample_strategy, sample_draft_state, seed=105
        )
        
        # Verify seed was passed to model_kwargs
        assert mock_chat.call_count == 2  # Initial + seeded
        seeded_call = mock_chat.call_args_list[1]
        assert seeded_call[1]['model_kwargs']['seed'] == 105
        
    @patch('ai.core.scout.ChatOpenAI')
    def test_invalid_json_response(self, mock_chat, mock_openai_key,
                                  sample_candidates, sample_draft_state, sample_strategy):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.content = "This is not valid JSON"
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        scout = Scout()
        recommendation = scout.get_recommendation(
            sample_candidates, sample_strategy, sample_draft_state
        )
        
        # Should return fallback recommendation
        assert isinstance(recommendation, ScoutRecommendation)
        assert recommendation.suggested_player_id == "12345"  # Lowest ADP
        assert "Fallback selection" in recommendation.reason
        
    @patch('ai.core.scout.ChatOpenAI')  
    def test_invalid_player_selection(self, mock_chat, mock_openai_key,
                                    sample_candidates, sample_draft_state, sample_strategy):
        """Test handling when AI selects player not in candidate list."""
        mock_response = Mock()
        mock_response.content = json.dumps({
            "suggested_player_id": "99999",  # Not in candidate list
            "suggested_player_name": "Invalid Player",
            "position": "QB",
            "reason": "This player is not in the list.",
            "score_hint": 0.0
        })
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        scout = Scout()
        recommendation = scout.get_recommendation(
            sample_candidates, sample_strategy, sample_draft_state
        )
        
        # Should return fallback recommendation
        assert isinstance(recommendation, ScoutRecommendation)
        assert recommendation.suggested_player_id in ["12345", "23456", "34567"]
        assert "Fallback selection" in recommendation.reason
        
    @patch('ai.core.scout.ChatOpenAI')
    @pytest.mark.asyncio
    async def test_multiple_recommendations(self, mock_chat, mock_openai_key,
                                          sample_candidates, sample_draft_state, sample_strategy):
        """Test generating multiple recommendations in parallel."""
        # Mock different responses for parallel calls
        def mock_invoke(messages):
            response = Mock()
            # Alternate between different players
            player_ids = ["12345", "23456", "34567"]
            player_names = ["Christian McCaffrey", "Cooper Kupp", "Mark Andrews"]
            positions = ["RB", "WR", "TE"]
            
            idx = len(mock_chat.return_value.invoke.call_args_list) % 3
            response.content = json.dumps({
                "suggested_player_id": player_ids[idx],
                "suggested_player_name": player_names[idx],
                "position": positions[idx], 
                "reason": f"Good pick for {positions[idx]} need.",
                "score_hint": 0.7 + (idx * 0.1)
            })
            return response
            
        mock_chat.return_value.invoke.side_effect = mock_invoke
        
        scout = Scout()
        recommendations = await scout.get_multiple_recommendations(
            sample_candidates, sample_strategy, sample_draft_state, num_recommendations=6
        )
        
        assert len(recommendations) == 6
        assert all(isinstance(rec, ScoutRecommendation) for rec in recommendations)
        
        # Verify we got diverse recommendations (not all the same)
        unique_players = set(rec.suggested_player_id for rec in recommendations)
        assert len(unique_players) >= 2  # Should have some diversity
        
    def test_validate_inputs_success(self, mock_openai_key, sample_candidates, 
                                   sample_draft_state, sample_strategy):
        """Test input validation with valid inputs."""
        scout = Scout()
        
        # Should not raise any exceptions
        assert scout.validate_inputs(sample_candidates, sample_strategy, sample_draft_state) is True
        
    def test_validate_inputs_empty_candidates(self, mock_openai_key):
        """Test validation fails with empty candidate list."""
        scout = Scout()
        
        with pytest.raises(ValueError, match="pick_candidates cannot be empty"):
            scout.validate_inputs([], "strategy", {})
            
    def test_validate_inputs_invalid_candidate_format(self, mock_openai_key):
        """Test validation fails with invalid candidate format."""
        scout = Scout()
        
        invalid_candidates = [{"name": "Player", "position": "QB"}]  # Missing required fields
        
        with pytest.raises(ValueError, match="missing required field"):
            scout.validate_inputs(invalid_candidates, "strategy", {})
            
    def test_validate_inputs_empty_strategy(self, mock_openai_key, sample_candidates):
        """Test validation fails with empty strategy."""
        scout = Scout()
        
        with pytest.raises(ValueError, match="pick_strategy cannot be empty"):
            scout.validate_inputs(sample_candidates, "", {})
            
    def test_validate_inputs_invalid_draft_state(self, mock_openai_key, sample_candidates):
        """Test validation fails with invalid draft state."""
        scout = Scout()
        
        with pytest.raises(ValueError, match="draft_state must be a dictionary"):
            scout.validate_inputs(sample_candidates, "strategy", "not a dict")
            
    @patch('ai.core.scout.ChatOpenAI')
    def test_build_prompt_structure(self, mock_chat, mock_openai_key,
                                   sample_candidates, sample_draft_state, sample_strategy):
        """Test that prompts are built with correct structure."""
        scout = Scout()
        prompt = scout._build_prompt(sample_candidates, sample_strategy, sample_draft_state)
        
        # Check key components are in prompt
        assert "You are the SCOUT" in prompt
        assert "Select exactly ONE player" in prompt
        assert "PICK_STRATEGY:" in prompt
        assert "DRAFT_STATE:" in prompt
        assert "PICK_CANDIDATES" in prompt
        assert sample_strategy in prompt
        
        # Check JSON schema is specified
        assert "suggested_player_id" in prompt
        assert "suggested_player_name" in prompt
        assert "position" in prompt
        assert "reason" in prompt
        
    def test_parse_response_valid_json(self, mock_openai_key, sample_candidates):
        """Test parsing valid JSON response."""
        scout = Scout()
        
        response_text = json.dumps({
            "suggested_player_id": "23456",
            "suggested_player_name": "Cooper Kupp",
            "position": "WR", 
            "reason": "Great value pick with tier urgency.",
            "score_hint": 0.8
        })
        
        recommendation = scout._parse_response(response_text, sample_candidates)
        
        assert recommendation.suggested_player_id == "23456"
        assert recommendation.suggested_player_name == "Cooper Kupp"
        assert recommendation.position == "WR"
        assert recommendation.score_hint == 0.8
        
    def test_parse_response_with_extra_text(self, mock_openai_key, sample_candidates):
        """Test parsing JSON response with extra text around it."""
        scout = Scout()
        
        response_text = '''Here is my recommendation:
        
        {
            "suggested_player_id": "12345",
            "suggested_player_name": "Christian McCaffrey",
            "position": "RB",
            "reason": "Elite RB talent available.",
            "score_hint": 0.9
        }
        
        This should work well for your team.'''
        
        recommendation = scout._parse_response(response_text, sample_candidates)
        
        assert recommendation.suggested_player_id == "12345"
        assert recommendation.suggested_player_name == "Christian McCaffrey"
        
    def test_fallback_recommendation(self, mock_openai_key, sample_candidates):
        """Test fallback recommendation generation."""
        scout = Scout()
        
        fallback = scout._get_fallback_recommendation(sample_candidates)
        
        assert isinstance(fallback, ScoutRecommendation)
        assert fallback.suggested_player_id == "12345"  # Lowest ADP (2.1)
        assert "Fallback selection" in fallback.reason
        assert fallback.score_hint == 0.5
        
    def test_fallback_recommendation_empty_candidates(self, mock_openai_key):
        """Test fallback fails with empty candidates."""
        scout = Scout()
        
        with pytest.raises(ValueError, match="No candidates available"):
            scout._get_fallback_recommendation([])


class TestScoutRecommendation:
    """Test the ScoutRecommendation dataclass."""
    
    def test_scout_recommendation_creation(self):
        """Test ScoutRecommendation creation and attributes."""
        rec = ScoutRecommendation(
            suggested_player_id="12345",
            suggested_player_name="Test Player",
            position="QB",
            reason="Good QB pick for team needs.",
            score_hint=0.75
        )
        
        assert rec.suggested_player_id == "12345"
        assert rec.suggested_player_name == "Test Player" 
        assert rec.position == "QB"
        assert rec.reason == "Good QB pick for team needs."
        assert rec.score_hint == 0.75
        
    def test_scout_recommendation_default_score(self):
        """Test ScoutRecommendation with default score_hint."""
        rec = ScoutRecommendation(
            suggested_player_id="67890",
            suggested_player_name="Another Player",
            position="WR",
            reason="WR depth needed."
        )
        
        assert rec.score_hint == 0.0  # Default value


if __name__ == "__main__":
    pytest.main([__file__])