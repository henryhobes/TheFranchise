#!/usr/bin/env python3
"""
Simple integration test for Scout Node

Tests basic functionality without complex imports that cause issues.
"""

import os
import sys
import json
from unittest.mock import Mock, patch

# Add the parent directory to path to import scout
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, '..')
sys.path.insert(0, parent_dir)

# Set up mock environment
os.environ['OPENAI_API_KEY'] = 'test-key'

# Import after setting up environment
from core.scout import Scout, ScoutRecommendation


def test_scout_basic_functionality():
    """Test basic Scout functionality with mocked OpenAI."""
    
    # Sample test data
    sample_candidates = [
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
        }
    ]
    
    sample_draft_state = {
        "round": 2,
        "pick": 15,
        "picks_until_next_turn": 5,
        "our_roster_counts": {"QB": 1, "RB": 1, "WR": 0, "TE": 0}
    }
    
    sample_strategy = "Target WR depth with tier urgency before position run develops"
    
    # Mock the ChatOpenAI response
    with patch('core.scout.ChatOpenAI') as mock_chat:
        mock_response = Mock()
        mock_response.content = json.dumps({
            "suggested_player_id": "23456",
            "suggested_player_name": "Cooper Kupp", 
            "position": "WR",
            "reason": "We need WR depth and Kupp represents excellent value at this ADP. Tier urgency suggests acting now before the position run.",
            "score_hint": 0.85
        })
        
        mock_chat.return_value.invoke.return_value = mock_response
        
        # Test Scout initialization
        scout = Scout()
        assert scout.model_name == "gpt-5"
        assert scout.temperature == 1.0
        
        # Test input validation
        try:
            scout.validate_inputs(sample_candidates, sample_strategy, sample_draft_state)
            print("[PASS] Input validation passed")
        except Exception as e:
            print(f"[FAIL] Input validation failed: {e}")
            return False
        
        # Test recommendation generation
        try:
            recommendation = scout.get_recommendation(
                sample_candidates, sample_strategy, sample_draft_state
            )
            
            assert isinstance(recommendation, ScoutRecommendation)
            assert recommendation.suggested_player_id == "23456"
            assert recommendation.suggested_player_name == "Cooper Kupp"
            assert recommendation.position == "WR"
            assert "WR depth" in recommendation.reason
            assert recommendation.score_hint == 0.85
            print("[PASS] Recommendation generation passed")
            
        except Exception as e:
            print(f"[FAIL] Recommendation generation failed: {e}")
            return False
        
        # Test fallback recommendation
        try:
            fallback = scout._get_fallback_recommendation(sample_candidates)
            assert isinstance(fallback, ScoutRecommendation)
            assert fallback.suggested_player_id == "12345"  # Lowest ADP
            assert "Fallback selection" in fallback.reason
            print("[PASS] Fallback recommendation passed")
            
        except Exception as e:
            print(f"[FAIL] Fallback recommendation failed: {e}")
            return False
        
        print("[PASS] All Scout tests passed!")
        return True


def test_scout_prompt_building():
    """Test prompt building functionality."""
    
    sample_candidates = [{"player_id": "123", "name": "Test Player", "position": "QB", "adp": 50}]
    sample_strategy = "Test strategy"
    sample_draft_state = {"round": 1, "pick": 5}
    
    with patch('core.scout.ChatOpenAI'):
        scout = Scout()
        prompt = scout._build_prompt(sample_candidates, sample_strategy, sample_draft_state)
        
        # Check key components
        assert "You are the SCOUT" in prompt
        assert "Select exactly ONE player" in prompt
        assert "PICK_STRATEGY:" in prompt
        assert "DRAFT_STATE:" in prompt
        assert "Test strategy" in prompt
        
        print("[PASS] Prompt building test passed!")
        return True


def test_json_parsing():
    """Test JSON response parsing."""
    
    sample_candidates = [
        {"player_id": "123", "name": "Test Player", "position": "QB", "adp": 50}
    ]
    
    with patch('core.scout.ChatOpenAI'):
        scout = Scout()
        
        # Test valid JSON
        valid_json = json.dumps({
            "suggested_player_id": "123",
            "suggested_player_name": "Test Player",
            "position": "QB",
            "reason": "Good QB choice for team needs.",
            "score_hint": 0.7
        })
        
        try:
            rec = scout._parse_response(valid_json, sample_candidates)
            assert rec.suggested_player_id == "123"
            assert rec.suggested_player_name == "Test Player"
            assert rec.position == "QB"
            print("[PASS] JSON parsing test passed!")
            return True
            
        except Exception as e:
            print(f"[FAIL] JSON parsing failed: {e}")
            return False


if __name__ == "__main__":
    print("Running Scout Node Integration Tests...")
    print("=" * 50)
    
    success = True
    
    print("\n1. Testing basic functionality...")
    success &= test_scout_basic_functionality()
    
    print("\n2. Testing prompt building...")  
    success &= test_scout_prompt_building()
    
    print("\n3. Testing JSON parsing...")
    success &= test_json_parsing()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: All tests passed! Scout implementation is working correctly.")
    else:
        print("FAILURE: Some tests failed. Check the implementation.")
    
    sys.exit(0 if success else 1)