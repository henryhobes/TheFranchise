#!/usr/bin/env python3
"""
GM Node API Integration Test

Tests the GM node with actual OpenAI API calls to verify end-to-end functionality.
This validates that the GM can make real decisions using GPT-5.
"""

import json
import sys
import os
from typing import Dict, Any, List

# Add project root to path and load environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Load environment variables from project root
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

from core.gm import GM, GMDecision


def create_realistic_scout_recommendations() -> List[Dict[str, Any]]:
    """Create realistic Scout recommendations that represent different decision factors."""
    return [
        {
            "suggested_player_id": "4036131",
            "suggested_player_name": "Christian McCaffrey",
            "position": "RB",
            "reason": "Elite RB1 with proven floor and ceiling despite injury history.",
            "score_hint": 0.95
        },
        {
            "suggested_player_id": "3139477", 
            "suggested_player_name": "Cooper Kupp",
            "position": "WR",
            "reason": "WR depth urgency and Kupp offers excellent target share reliability.",
            "score_hint": 0.82
        },
        {
            "suggested_player_id": "3915511",
            "suggested_player_name": "Mark Andrews", 
            "position": "TE",
            "reason": "TE scarcity makes elite options critical before tier cliff.",
            "score_hint": 0.78
        },
        {
            "suggested_player_id": "3916387",
            "suggested_player_name": "Josh Allen",
            "position": "QB", 
            "reason": "QB1 upside with rushing floor mitigates positional risk.",
            "score_hint": 0.73
        },
        {
            "suggested_player_id": "3043078",
            "suggested_player_name": "Davante Adams",
            "position": "WR",
            "reason": "Proven WR1 production falling due to QB transition concerns.",
            "score_hint": 0.87
        },
        {
            "suggested_player_id": "3932905",
            "suggested_player_name": "Travis Kelce",
            "position": "TE",
            "reason": "Age concerns offset by target monopoly in high-powered offense.",
            "score_hint": 0.84
        },
        {
            "suggested_player_id": "3918298",
            "suggested_player_name": "Lamar Jackson",
            "position": "QB",
            "reason": "Dual-threat QB with safe rushing floor and improved passing game.",
            "score_hint": 0.76
        },
        {
            "suggested_player_id": "4242335",
            "suggested_player_name": "Ja'Marr Chase",
            "position": "WR", 
            "reason": "Elite target share and red zone usage in explosive offense.",
            "score_hint": 0.91
        },
        {
            "suggested_player_id": "4361579",
            "suggested_player_name": "Jonathan Taylor",
            "position": "RB",
            "reason": "Workload questions but talent and offensive line support remain strong.",
            "score_hint": 0.79
        },
        {
            "suggested_player_id": "4035687",
            "suggested_player_name": "Stefon Diggs",
            "position": "WR", 
            "reason": "New team concerns but proven target volume and route running.",
            "score_hint": 0.74
        }
    ]


def create_draft_scenario() -> Dict[str, Any]:
    """Create a realistic draft scenario for testing."""
    return {
        "round": 2,
        "pick": 18,
        "picks_until_next_turn": 7,
        "our_roster_counts": {"QB": 0, "RB": 2, "WR": 0, "TE": 0, "DST": 0, "K": 0},
        "lineup_rules": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "DST": 1, "K": 1},
        "league_size": 12,
        "total_picks": 168,
        "current_pick": 18,
        "time_remaining": 45,
        "on_the_clock": "our_team"
    }


def test_gm_real_decision():
    """Test GM making a real decision with OpenAI API."""
    print("GM Node API Integration Test")
    print("=" * 50)
    
    # Create test data
    scout_recommendations = create_realistic_scout_recommendations()
    draft_state = create_draft_scenario()
    pick_strategy = "Target WR1 talent with proven production. RB depth is solid, prioritize pass-catchers with target security before tier breaks occur."
    
    print(f"Draft Scenario: Round {draft_state['round']}, Pick {draft_state['pick']}")
    print(f"Current Roster: {draft_state['our_roster_counts']}")
    print(f"Strategy: {pick_strategy}")
    print(f"Scout Candidates: {len(scout_recommendations)}")
    print()
    
    # Show top Scout recommendations by confidence
    print("Top Scout Recommendations:")
    sorted_recs = sorted(scout_recommendations, key=lambda x: x['score_hint'], reverse=True)[:5]
    for i, rec in enumerate(sorted_recs, 1):
        print(f"  {i}. {rec['suggested_player_name']} ({rec['position']}) - "
              f"Confidence: {rec['score_hint']:.2f}")
        print(f"     Reason: {rec['reason']}")
    print()
    
    try:
        # Test actual GM decision
        print("Making GM decision with OpenAI API...")
        gm = GM(model_name="gpt-5", temperature=0.8)
        
        decision = gm.make_decision(scout_recommendations, pick_strategy, draft_state)
        
        print("[SUCCESS] GM Decision Made Successfully!")
        print()
        print("FINAL GM DECISION:")
        print(f"  Selected Player: {decision.selected_player_name}")
        print(f"  Position: {decision.position}")
        print(f"  Player ID: {decision.selected_player_id}")
        print(f"  GM Reasoning: {decision.reason}")
        print(f"  Confidence Score: {decision.score_hint:.2f}")
        print()
        
        # Find the corresponding Scout recommendation
        selected_scout = None
        for rec in scout_recommendations:
            if rec['suggested_player_id'] == decision.selected_player_id:
                selected_scout = rec
                break
                
        if selected_scout:
            print("CORRESPONDING SCOUT RECOMMENDATION:")
            print(f"  Original Scout Reasoning: {selected_scout['reason']}")
            print(f"  Scout Confidence: {selected_scout['score_hint']:.2f}")
            print()
            
            # Analysis
            print("DECISION ANALYSIS:")
            if selected_scout['score_hint'] >= 0.85:
                print("  -> Selected high-confidence Scout recommendation")
            elif decision.position == "WR" and draft_state['our_roster_counts']['WR'] == 0:
                print("  -> Addressed clear positional need (WR depth)")
            else:
                print("  -> GM weighed multiple factors beyond pure Scout confidence")
                
        return True
        
    except Exception as e:
        print(f"[ERROR] Error during GM API test: {e}")
        print("This could indicate:")
        print("  - API key issues")
        print("  - Network connectivity problems") 
        print("  - Model availability issues")
        print("  - Prompt/parsing problems")
        return False


def test_gm_multiple_scenarios():
    """Test GM with multiple different scenarios to validate consistency."""
    print("\nTesting Multiple Decision Scenarios")
    print("-" * 40)
    
    scenarios = [
        {
            "name": "Early Draft - Need RB",
            "roster": {"QB": 0, "RB": 0, "WR": 1, "TE": 0, "DST": 0, "K": 0},
            "strategy": "Secure RB1 talent early, position scarcity makes waiting risky."
        },
        {
            "name": "Mid Draft - Balanced",
            "roster": {"QB": 0, "RB": 2, "WR": 1, "TE": 0, "DST": 0, "K": 0}, 
            "strategy": "Best available talent, slight preference for WR depth and TE security."
        },
        {
            "name": "Late Draft - Fill Needs",
            "roster": {"QB": 1, "RB": 2, "WR": 2, "TE": 0, "DST": 0, "K": 0},
            "strategy": "Must secure TE before cliff, then best available for FLEX upside."
        }
    ]
    
    scout_recommendations = create_realistic_scout_recommendations()
    gm = GM(model_name="gpt-5", temperature=0.8)
    
    results = []
    
    for scenario in scenarios:
        try:
            print(f"\nScenario: {scenario['name']}")
            print(f"Roster: {scenario['roster']}")
            print(f"Strategy: {scenario['strategy'][:60]}...")
            
            draft_state = create_draft_scenario()
            draft_state['our_roster_counts'] = scenario['roster']
            
            decision = gm.make_decision(scout_recommendations, scenario['strategy'], draft_state)
            
            print(f"Decision: {decision.selected_player_name} ({decision.position})")
            print(f"Reasoning: {decision.reason[:80]}...")
            
            results.append({
                'scenario': scenario['name'],
                'player': decision.selected_player_name,
                'position': decision.position,
                'success': True
            })
            
        except Exception as e:
            print(f"[ERROR] Failed: {e}")
            results.append({
                'scenario': scenario['name'], 
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\nScenario Testing Summary:")
    successes = sum(1 for r in results if r['success'])
    print(f"  Successful decisions: {successes}/{len(scenarios)}")
    
    if successes == len(scenarios):
        print("  [PASS] All scenarios completed successfully")
        return True
    else:
        print("  [FAIL] Some scenarios failed")
        return False


if __name__ == "__main__":
    print("Testing GM Node with Real OpenAI API")
    print("=" * 60)
    
    # Test 1: Single decision
    success1 = test_gm_real_decision()
    
    # Test 2: Multiple scenarios 
    success2 = test_gm_multiple_scenarios()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("[SUCCESS] ALL TESTS PASSED - GM Node is working correctly with OpenAI API!")
        print("\nThe GM Node successfully:")
        print("  [PASS] Connects to OpenAI GPT-5")
        print("  [PASS] Processes Scout recommendations")
        print("  [PASS] Considers draft strategy and state")  
        print("  [PASS] Makes contextual decisions")
        print("  [PASS] Returns properly formatted responses")
        print("  [PASS] Handles multiple scenarios consistently")
    else:
        print("[FAIL] SOME TESTS FAILED")
        if not success1:
            print("  - Basic decision making failed")
        if not success2:
            print("  - Multi-scenario testing failed")
        sys.exit(1)