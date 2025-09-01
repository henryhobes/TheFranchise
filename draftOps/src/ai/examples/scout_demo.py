#!/usr/bin/env python3
"""
Scout Node Integration Demo

Demonstrates how the Scout node integrates with the existing DraftOps architecture.
Shows the complete flow from Strategist allocation to Scout recommendations.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add the parent directories to path for imports
current_dir = Path(__file__).parent
ai_dir = current_dir.parent
sys.path.insert(0, str(ai_dir))

# Set up environment
os.environ.setdefault('OPENAI_API_KEY', 'demo-key-for-testing')

from core.scout import Scout, ScoutRecommendation


def create_sample_draft_context():
    """Create sample draft context similar to what DraftState would provide."""
    return {
        "league_id": "123456", 
        "team_id": "user_team",
        "current_pick": 25,
        "round": 3,
        "picks_until_next_turn": 7,
        "time_remaining": 45.0,
        "on_the_clock": "Other Team",
        "my_roster": {
            "QB": ["Josh Allen"],
            "RB": ["Christian McCaffrey", "Derrick Henry"], 
            "WR": [],
            "TE": [],
            "DST": [],
            "K": []
        },
        "lineup_rules": {
            "QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "DST": 1, "K": 1
        },
        "recent_picks": [
            {"pick_number": 22, "player_name": "Travis Kelce", "position": "TE"},
            {"pick_number": 23, "player_name": "Davante Adams", "position": "WR"},
            {"pick_number": 24, "player_name": "Nick Chubb", "position": "RB"}
        ]
    }


def create_strategist_output():
    """Create sample output from Draft Strategist (what would feed into Scout)."""
    
    # These would come from the actual Strategist allocation
    pick_candidates = [
        {
            "player_id": "wr_001",
            "name": "Tyreek Hill",
            "position": "WR", 
            "adp": 18.3,
            "position_rank": 5,
            "projection": 267.8,
            "tier": 2,
            "value_over_baseline": 45.2,
            "team": "MIA",
            "bye_week": 10,
            "injury_status": "Healthy",
            "risk_flag": "Low"
        },
        {
            "player_id": "wr_002", 
            "name": "Stefon Diggs",
            "position": "WR",
            "adp": 22.1,
            "position_rank": 7,
            "projection": 252.4,
            "tier": 2, 
            "value_over_baseline": 38.7,
            "team": "HOU",
            "bye_week": 14,
            "injury_status": "Healthy",
            "risk_flag": "Low"
        },
        {
            "player_id": "rb_003",
            "name": "Alvin Kamara", 
            "position": "RB",
            "adp": 24.8,
            "position_rank": 8,
            "projection": 245.6,
            "tier": 3,
            "value_over_baseline": 42.1,
            "team": "NO",
            "bye_week": 12,
            "injury_status": "Healthy", 
            "risk_flag": "Medium"
        },
        {
            "player_id": "te_001",
            "name": "Mark Andrews",
            "position": "TE",
            "adp": 26.9,
            "position_rank": 2,
            "projection": 195.3,
            "tier": 1,
            "value_over_baseline": 55.8,
            "team": "BAL",
            "bye_week": 14,
            "injury_status": "Healthy",
            "risk_flag": "Low"
        },
        {
            "player_id": "wr_003",
            "name": "Mike Evans",
            "position": "WR", 
            "adp": 28.2,
            "position_rank": 9,
            "projection": 238.9,
            "tier": 3,
            "value_over_baseline": 35.1,
            "team": "TB",
            "bye_week": 11,
            "injury_status": "Healthy",
            "risk_flag": "Medium"
        }
    ]
    
    pick_strategy = "WR depth critical with zero WR on roster and tier urgency before position run accelerates"
    
    return pick_candidates, pick_strategy


def demonstrate_single_recommendation():
    """Demo single Scout recommendation."""
    print("=" * 60)
    print("SCOUT NODE SINGLE RECOMMENDATION DEMO")
    print("=" * 60)
    
    # Get sample data
    pick_candidates, pick_strategy = create_strategist_output()
    draft_state = create_sample_draft_context()
    
    print("\n1. DRAFT CONTEXT:")
    print(f"   Round: {draft_state['round']}, Pick: {draft_state['current_pick']}")
    print(f"   Picks until next turn: {draft_state['picks_until_next_turn']}")
    print(f"   Current roster: {draft_state['my_roster']}")
    
    print(f"\n2. STRATEGIST OUTPUT:")
    print(f"   Strategy: {pick_strategy}")
    print(f"   Candidates: {len(pick_candidates)} players")
    for i, candidate in enumerate(pick_candidates, 1):
        print(f"      {i}. {candidate['name']} ({candidate['position']}) - ADP {candidate['adp']}")
    
    try:
        print(f"\n3. SCOUT RECOMMENDATION:")
        scout = Scout(temperature=0.8)  # Slightly lower temp for demo consistency
        
        # Mock the actual OpenAI call for demo purposes
        from unittest.mock import patch, Mock
        
        with patch('core.scout.ChatOpenAI') as mock_chat:
            # Create a realistic recommendation
            mock_response = Mock()
            mock_response.content = json.dumps({
                "suggested_player_id": "wr_001",
                "suggested_player_name": "Tyreek Hill",
                "position": "WR",
                "reason": "Critical WR need with zero WR on roster and Hill offers elite tier-2 value at current ADP. Must act before WR run accelerates in this range.",
                "score_hint": 0.92
            })
            mock_chat.return_value.invoke.return_value = mock_response
            
            recommendation = scout.get_recommendation(
                pick_candidates, pick_strategy, draft_state, seed=42
            )
            
            print(f"   Selected: {recommendation.suggested_player_name}")
            print(f"   Position: {recommendation.position}")
            print(f"   Reasoning: {recommendation.reason}")
            print(f"   Confidence: {recommendation.score_hint:.2f}")
            
    except Exception as e:
        print(f"   ERROR: {e}")
        print("   (Note: This demo uses mocked OpenAI calls)")
        
    return True


async def demonstrate_multiple_recommendations():
    """Demo multiple parallel Scout recommendations."""
    print("\n\n" + "=" * 60)
    print("SCOUT NODE PARALLEL RECOMMENDATIONS DEMO")
    print("=" * 60)
    
    # Get sample data
    pick_candidates, pick_strategy = create_strategist_output()
    draft_state = create_sample_draft_context()
    
    print(f"\n1. GENERATING 10 PARALLEL RECOMMENDATIONS:")
    print("   (Using different seeds for diversity)")
    
    try:
        scout = Scout(temperature=1.0)  # High temp for diversity
        
        # Mock multiple diverse responses
        from unittest.mock import patch, Mock
        
        def create_mock_response(player_idx):
            players = [
                ("wr_001", "Tyreek Hill", "WR", "Elite speed and target share make him WR1 upside. Zero WR on roster creates urgent need."),
                ("te_001", "Mark Andrews", "TE", "Tier-1 TE at great value with positional scarcity advantage. Fill scarce position while available."),
                ("wr_002", "Stefon Diggs", "WR", "Proven WR1 production in new offense with target opportunity. WR need is critical priority."),
                ("rb_003", "Alvin Kamara", "RB", "RB depth for injury protection with pass-catching upside. Good value at current ADP."),
                ("wr_003", "Mike Evans", "WR", "Red zone target magnet with TD upside fills WR void. Consistent WR2 floor production.")
            ]
            
            player = players[player_idx % len(players)]
            mock_response = Mock()
            mock_response.content = json.dumps({
                "suggested_player_id": player[0],
                "suggested_player_name": player[1], 
                "position": player[2],
                "reason": player[3],
                "score_hint": 0.8 + (player_idx * 0.02)
            })
            return mock_response
        
        with patch('core.scout.ChatOpenAI') as mock_chat:
            # Create a side effect that returns different responses
            mock_chat.return_value.invoke.side_effect = lambda _: create_mock_response(
                len(mock_chat.return_value.invoke.call_args_list) - 1
            )
            
            recommendations = await scout.get_multiple_recommendations(
                pick_candidates, pick_strategy, draft_state, num_recommendations=10
            )
            
            print(f"\n2. RESULTS ({len(recommendations)} recommendations):")
            
            # Group by player for analysis
            player_counts = {}
            for rec in recommendations:
                player_counts[rec.suggested_player_name] = player_counts.get(rec.suggested_player_name, 0) + 1
            
            print("\n   Player Selection Distribution:")
            for player, count in sorted(player_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"      {player}: {count} selections")
                
            print(f"\n   Sample Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"      {i}. {rec.suggested_player_name} ({rec.position})")
                print(f"         Reason: {rec.reason}")
                print(f"         Score: {rec.score_hint:.2f}")
                print()
            
    except Exception as e:
        print(f"   ERROR: {e}")
        print("   (Note: This demo uses mocked OpenAI calls)")
        
    return True


def demonstrate_validation_and_error_handling():
    """Demo input validation and error handling."""
    print("\n" + "=" * 60)
    print("SCOUT NODE VALIDATION & ERROR HANDLING DEMO")
    print("=" * 60)
    
    scout = Scout()
    
    print("\n1. TESTING INPUT VALIDATION:")
    
    # Test valid inputs
    pick_candidates, pick_strategy = create_strategist_output()
    draft_state = create_sample_draft_context()
    
    try:
        scout.validate_inputs(pick_candidates, pick_strategy, draft_state)
        print("   Valid inputs: PASSED")
    except Exception as e:
        print(f"   Valid inputs: FAILED - {e}")
        
    # Test invalid inputs
    test_cases = [
        ([], pick_strategy, draft_state, "Empty candidates"),
        (pick_candidates, "", draft_state, "Empty strategy"),
        (pick_candidates, pick_strategy, "not a dict", "Invalid draft state"),
        ([{"name": "Player"}], pick_strategy, draft_state, "Missing required fields")
    ]
    
    for candidates, strategy, state, description in test_cases:
        try:
            scout.validate_inputs(candidates, strategy, state)
            print(f"   {description}: FAILED (should have raised error)")
        except Exception as e:
            print(f"   {description}: PASSED (correctly raised error)")
    
    print("\n2. TESTING FALLBACK BEHAVIOR:")
    
    # Test fallback recommendation
    try:
        fallback = scout._get_fallback_recommendation(pick_candidates)
        print(f"   Fallback player: {fallback.suggested_player_name}")
        print(f"   Fallback reason: {fallback.reason}")
        print("   Fallback generation: PASSED")
    except Exception as e:
        print(f"   Fallback generation: FAILED - {e}")
    
    return True


async def main():
    """Run all Scout node demonstrations."""
    print("SCOUT NODE INTEGRATION DEMONSTRATION")
    print("Showing how Scout integrates with DraftOps architecture")
    
    # Run demonstrations
    demonstrate_single_recommendation()
    await demonstrate_multiple_recommendations()
    demonstrate_validation_and_error_handling()
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\nKEY FEATURES DEMONSTRATED:")
    print("1. Single recommendation with detailed reasoning")
    print("2. Parallel diverse recommendations (10 concurrent calls)")
    print("3. Input validation and error handling")
    print("4. Integration with Strategist output format")
    print("5. Fallback behavior for error conditions")
    print("\nThe Scout node is ready for integration with the GM node.")


if __name__ == "__main__":
    asyncio.run(main())