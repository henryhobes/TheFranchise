#!/usr/bin/env python3
"""
Tests for GM Node Implementation

Tests the core functionality of the GM agent including:
- Final decision making from Scout recommendations
- Input validation
- JSON schema compliance
- Error handling and fallback behavior
"""

import pytest
import json
from unittest.mock import Mock, patch
from typing import List, Dict, Any

import sys
import os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.gm import GM, GMDecision


class TestGM:
    """Test cases for GM node."""
    
    @pytest.fixture
    def mock_openai_key(self, monkeypatch):
        """Mock OpenAI API key for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        
    @pytest.fixture
    def sample_scout_recommendations(self) -> List[Dict[str, Any]]:
        """Sample Scout recommendations for testing."""
        return [
            {
                "suggested_player_id": "12345",
                "suggested_player_name": "Christian McCaffrey",
                "position": "RB",
                "reason": "Elite RB1 talent with proven production.",
                "score_hint": 0.95
            },
            {
                "suggested_player_id": "23456", 
                "suggested_player_name": "Cooper Kupp",
                "position": "WR",
                "reason": "WR depth needed and excellent value here.",
                "score_hint": 0.85
            },
            {
                "suggested_player_id": "34567",
                "suggested_player_name": "Mark Andrews", 
                "position": "TE",
                "reason": "Elite TE1 fills positional scarcity need.",
                "score_hint": 0.80
            },
            {
                "suggested_player_id": "45678",
                "suggested_player_name": "Josh Allen",
                "position": "QB", 
                "reason": "Top QB available with strong ceiling.",
                "score_hint": 0.75
            },
            {
                "suggested_player_id": "56789",
                "suggested_player_name": "Derrick Henry",
                "position": "RB",
                "reason": "RB depth with goal line upside.",
                "score_hint": 0.70
            },
            {
                "suggested_player_id": "67890",
                "suggested_player_name": "Davante Adams",
                "position": "WR",
                "reason": "WR1 talent falling due to tier break.",
                "score_hint": 0.88
            },
            {
                "suggested_player_id": "78901",
                "suggested_player_name": "Travis Kelce",
                "position": "TE",
                "reason": "Best TE available before cliff.",
                "score_hint": 0.82
            },
            {
                "suggested_player_id": "89012",
                "suggested_player_name": "Lamar Jackson",
                "position": "QB",
                "reason": "Dual-threat QB with high ceiling.",
                "score_hint": 0.77
            },
            {
                "suggested_player_id": "90123",
                "suggested_player_name": "Nick Chubb",
                "position": "RB",
                "reason": "Reliable RB2 with upside in good offense.",
                "score_hint": 0.72
            },
            {
                "suggested_player_id": "01234",
                "suggested_player_name": "Stefon Diggs",
                "position": "WR", 
                "reason": "Consistent WR1 production expected.",
                "score_hint": 0.78
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
        
    def test_gm_initialization(self, mock_openai_key):
        """Test GM agent initializes correctly."""
        gm = GM()
        
        assert gm.model_name == "gpt-5-2025-08-07"
        assert gm.temperature == 0.8
        assert gm.api_key == "test-key"
        
    def test_gm_custom_params(self, mock_openai_key):
        """Test GM with custom parameters."""
        gm = GM(model_name="gpt-4o", temperature=0.5)
        
        assert gm.model_name == "gpt-4o"
        assert gm.temperature == 0.5
        
    def test_missing_api_key(self, monkeypatch):
        """Test GM raises error with missing API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
            GM()
            
    @patch('ai.core.gm.ChatOpenAI')
    def test_make_decision_success(self, mock_chat, mock_openai_key, 
                                 sample_scout_recommendations, sample_draft_state, sample_strategy):
        """Test successful decision making."""
        # Mock LLM response - GM chooses highest-confidence Scout recommendation
        mock_response = Mock()
        mock_response.content = json.dumps({
            "selected_player_id": "12345",
            "selected_player_name": "Christian McCaffrey", 
            "position": "RB",
            "reason": "Highest confidence Scout recommendation with elite talent. Fills RB need with proven production ceiling.",
            "score_hint": 0.95
        })
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        gm = GM()
        decision = gm.make_decision(
            sample_scout_recommendations, sample_strategy, sample_draft_state
        )
        
        assert isinstance(decision, GMDecision)
        assert decision.selected_player_id == "12345"
        assert decision.selected_player_name == "Christian McCaffrey"
        assert decision.position == "RB"
        assert "Highest confidence" in decision.reason
        assert decision.score_hint == 0.95
        
    @patch('ai.core.gm.ChatOpenAI')
    def test_make_decision_different_choice(self, mock_chat, mock_openai_key,
                                          sample_scout_recommendations, sample_draft_state, sample_strategy):
        """Test GM choosing different Scout recommendation based on context."""
        # Mock response choosing WR based on strategy
        mock_response = Mock()
        mock_response.content = json.dumps({
            "selected_player_id": "67890",
            "selected_player_name": "Davante Adams",
            "position": "WR", 
            "reason": "Strategy emphasizes WR depth and Adams has high confidence score. Addresses roster need at WR position.",
            "score_hint": 0.88
        })
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        gm = GM()
        decision = gm.make_decision(
            sample_scout_recommendations, sample_strategy, sample_draft_state
        )
        
        assert decision.selected_player_id == "67890"
        assert decision.selected_player_name == "Davante Adams"
        assert decision.position == "WR"
        assert "WR depth" in decision.reason
        
    @patch('ai.core.gm.ChatOpenAI')
    def test_invalid_json_response(self, mock_chat, mock_openai_key,
                                 sample_scout_recommendations, sample_draft_state, sample_strategy):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.content = "This is not valid JSON"
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        gm = GM()
        decision = gm.make_decision(
            sample_scout_recommendations, sample_strategy, sample_draft_state
        )
        
        # Should return fallback decision (highest confidence Scout)
        assert isinstance(decision, GMDecision)
        assert decision.selected_player_id == "12345"  # Highest score_hint (0.95)
        assert "Fallback selection" in decision.reason
        
    @patch('ai.core.gm.ChatOpenAI')  
    def test_invalid_player_selection(self, mock_chat, mock_openai_key,
                                    sample_scout_recommendations, sample_draft_state, sample_strategy):
        """Test handling when GM selects player not in Scout recommendations."""
        mock_response = Mock()
        mock_response.content = json.dumps({
            "selected_player_id": "99999",  # Not in Scout recommendations
            "selected_player_name": "Invalid Player",
            "position": "QB",
            "reason": "This player is not in Scout recommendations.",
            "score_hint": 0.0
        })
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        gm = GM()
        decision = gm.make_decision(
            sample_scout_recommendations, sample_strategy, sample_draft_state
        )
        
        # Should return fallback decision
        assert isinstance(decision, GMDecision)
        assert decision.selected_player_id == "12345"  # Highest confidence
        assert "Fallback selection" in decision.reason
        
    def test_validate_inputs_success(self, mock_openai_key, sample_scout_recommendations, 
                                   sample_draft_state, sample_strategy):
        """Test input validation with valid inputs."""
        gm = GM()
        
        # Should not raise any exceptions
        assert gm.validate_inputs(sample_scout_recommendations, sample_strategy, sample_draft_state) is True
        
    def test_validate_inputs_empty_recommendations(self, mock_openai_key):
        """Test validation fails with empty Scout recommendations."""
        gm = GM()
        
        with pytest.raises(ValueError, match="scout_recommendations cannot be empty"):
            gm.validate_inputs([], "strategy", {})
            
    def test_validate_inputs_invalid_recommendation_format(self, mock_openai_key):
        """Test validation fails with invalid recommendation format."""
        gm = GM()
        
        invalid_recommendations = [{"player_name": "Player", "position": "QB"}]  # Missing required fields
        
        with pytest.raises(ValueError, match="missing required field"):
            gm.validate_inputs(invalid_recommendations, "strategy", {})
            
    def test_validate_inputs_empty_strategy(self, mock_openai_key, sample_scout_recommendations):
        """Test validation fails with empty strategy."""
        gm = GM()
        
        with pytest.raises(ValueError, match="pick_strategy cannot be empty"):
            gm.validate_inputs(sample_scout_recommendations, "", {})
            
    def test_validate_inputs_invalid_draft_state(self, mock_openai_key, sample_scout_recommendations):
        """Test validation fails with invalid draft state."""
        gm = GM()
        
        with pytest.raises(ValueError, match="draft_state must be a dictionary"):
            gm.validate_inputs(sample_scout_recommendations, "strategy", "not a dict")
            
    @patch('ai.core.gm.ChatOpenAI')
    def test_build_prompt_structure(self, mock_chat, mock_openai_key,
                                   sample_scout_recommendations, sample_draft_state, sample_strategy):
        """Test that prompts are built with correct structure."""
        gm = GM()
        prompt = gm._build_prompt(sample_scout_recommendations, sample_strategy, sample_draft_state)
        
        # Check key components are in prompt
        assert "You are the GENERAL MANAGER" in prompt
        assert "choose exactly ONE player" in prompt
        assert "SCOUT_RECOMMENDATIONS:" in prompt
        assert "PICK_STRATEGY:" in prompt
        assert "DRAFT_STATE:" in prompt
        assert sample_strategy in prompt
        
        # Check JSON schema is specified
        assert "selected_player_id" in prompt
        assert "selected_player_name" in prompt
        assert "position" in prompt
        assert "reason" in prompt
        
    def test_parse_response_valid_json(self, mock_openai_key, sample_scout_recommendations):
        """Test parsing valid JSON response."""
        gm = GM()
        
        response_text = json.dumps({
            "selected_player_id": "23456",
            "selected_player_name": "Cooper Kupp",
            "position": "WR", 
            "reason": "Great value pick with strategic fit for WR depth.",
            "score_hint": 0.85
        })
        
        decision = gm._parse_response(response_text, sample_scout_recommendations)
        
        assert decision.selected_player_id == "23456"
        assert decision.selected_player_name == "Cooper Kupp"
        assert decision.position == "WR"
        assert decision.score_hint == 0.85
        
    def test_parse_response_with_extra_text(self, mock_openai_key, sample_scout_recommendations):
        """Test parsing JSON response with extra text around it."""
        gm = GM()
        
        response_text = '''Based on the Scout recommendations, here is my final decision:
        
        {
            "selected_player_id": "12345",
            "selected_player_name": "Christian McCaffrey",
            "position": "RB",
            "reason": "Elite talent with highest Scout confidence.",
            "score_hint": 0.95
        }
        
        This should provide excellent value for the team.'''
        
        decision = gm._parse_response(response_text, sample_scout_recommendations)
        
        assert decision.selected_player_id == "12345"
        assert decision.selected_player_name == "Christian McCaffrey"
        
    def test_fallback_decision(self, mock_openai_key, sample_scout_recommendations):
        """Test fallback decision generation."""
        gm = GM()
        
        fallback = gm._get_fallback_decision(sample_scout_recommendations)
        
        assert isinstance(fallback, GMDecision)
        assert fallback.selected_player_id == "12345"  # Highest score_hint (0.95)
        assert fallback.selected_player_name == "Christian McCaffrey"
        assert "Fallback selection" in fallback.reason
        assert fallback.score_hint == 0.5
        
    def test_fallback_decision_empty_recommendations(self, mock_openai_key):
        """Test fallback fails with empty recommendations."""
        gm = GM()
        
        with pytest.raises(ValueError, match="No Scout recommendations available"):
            gm._get_fallback_decision([])
            
    def test_validate_inputs_too_many_recommendations(self, mock_openai_key, sample_draft_state, sample_strategy):
        """Test handling of more than 10 Scout recommendations."""
        gm = GM()
        
        # Create 15 recommendations (more than spec limit of 10)
        many_recommendations = []
        for i in range(15):
            many_recommendations.append({
                "suggested_player_id": f"id_{i}",
                "suggested_player_name": f"Player {i}",
                "position": "RB",
                "reason": f"Good player {i}",
                "score_hint": 0.5
            })
        
        # Should validate but log warning (flexibility for real usage)
        assert gm.validate_inputs(many_recommendations, sample_strategy, sample_draft_state) is True
        
    def test_reason_length_validation(self, mock_openai_key, sample_scout_recommendations):
        """Test validation of reason length constraint."""
        gm = GM()
        
        # Response with long reason (>2 sentences)
        response_text = json.dumps({
            "selected_player_id": "12345",
            "selected_player_name": "Christian McCaffrey",
            "position": "RB", 
            "reason": "This is sentence one. This is sentence two. This is sentence three that exceeds the limit.",
            "score_hint": 0.95
        })
        
        # Should still parse but log warning
        decision = gm._parse_response(response_text, sample_scout_recommendations)
        assert decision.selected_player_id == "12345"
        assert "sentence three" in decision.reason


class TestGMDecision:
    """Test the GMDecision dataclass."""
    
    def test_gm_decision_creation(self):
        """Test GMDecision creation and attributes."""
        decision = GMDecision(
            selected_player_id="12345",
            selected_player_name="Test Player",
            position="QB",
            reason="Good QB pick for team needs.",
            score_hint=0.75
        )
        
        assert decision.selected_player_id == "12345"
        assert decision.selected_player_name == "Test Player" 
        assert decision.position == "QB"
        assert decision.reason == "Good QB pick for team needs."
        assert decision.score_hint == 0.75
        
    def test_gm_decision_default_score(self):
        """Test GMDecision with default score_hint."""
        decision = GMDecision(
            selected_player_id="67890",
            selected_player_name="Another Player",
            position="WR",
            reason="WR depth needed."
        )
        
        assert decision.score_hint == 0.0  # Default value


if __name__ == "__main__":
    pytest.main([__file__])