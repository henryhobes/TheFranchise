#!/usr/bin/env python3
"""
Draft Strategist Demo

Demonstrates usage of the Draft Strategist for position allocation.
Shows how the Scout/GM nodes would consume the strategist output.
"""

import sys
from pathlib import Path

# Add modules to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from draftOps.src.ai.core.draft_strategist import DraftStrategist, StrategistConfig
from draftOps.data_loader import Player


def create_sample_draft_state():
    """Create a sample draft state for demonstration."""
    # Use minimal DraftState for demo
    class DemoState:
        def __init__(self):
            self.current_pick = 48
            self.picks_until_next = 3
            self.team_count = 12
            self.rounds = 16
            self.my_roster = {
                'QB': [],
                'RB': ['player_123'],  # We have 1 RB
                'WR': ['player_456', 'player_789'],  # We have 2 WRs
                'TE': [],
                'DST': [],
                'K': []
            }
            self.pick_history = [
                {'pick_number': i, 'position': 'RB' if i % 5 == 0 else 'WR'}
                for i in range(1, 48)
            ]
    
    return DemoState()


def create_sample_players():
    """Create sample player pool."""
    players = []
    
    # QB players (ADP 1-60)
    for i in range(15):
        players.append(Player(
            name=f"QB{i+1}", team="TEST", position="QB",
            adp_rank=i*4 + 1, position_rank=i+1,
            adp_avg=float(i*4 + 1), adp_std=2.0,
            fantasy_points=250 - i*5
        ))
    
    # RB players (high value, limited supply)
    for i in range(30):
        players.append(Player(
            name=f"RB{i+1}", team="TEST", position="RB", 
            adp_rank=i*2 + 5, position_rank=i+1,
            adp_avg=float(i*2 + 5), adp_std=3.0,
            fantasy_points=200 - i*3
        ))
    
    # WR players (deep position)
    for i in range(40):
        players.append(Player(
            name=f"WR{i+1}", team="TEST", position="WR",
            adp_rank=i*3 + 10, position_rank=i+1, 
            adp_avg=float(i*3 + 10), adp_std=2.5,
            fantasy_points=180 - i*2
        ))
    
    # TE players (scarce after top tier)
    for i in range(12):
        players.append(Player(
            name=f"TE{i+1}", team="TEST", position="TE",
            adp_rank=i*8 + 20, position_rank=i+1,
            adp_avg=float(i*8 + 20), adp_std=4.0,
            fantasy_points=120 - i*8
        ))
    
    # DST players
    for i in range(12):
        players.append(Player(
            name=f"DST{i+1}", team="TEST", position="DST",
            adp_rank=150 + i*2, position_rank=i+1,
            adp_avg=float(150 + i*2), adp_std=5.0,
            fantasy_points=100 - i
        ))
    
    # K players  
    for i in range(12):
        players.append(Player(
            name=f"K{i+1}", team="TEST", position="K",
            adp_rank=170 + i*2, position_rank=i+1,
            adp_avg=float(170 + i*2), adp_std=3.0,
            fantasy_points=90 - i
        ))
    
    return players


def demo_strategist_usage():
    """Demonstrate Draft Strategist usage."""
    print("=== Draft Strategist Demo ===")
    print()
    
    # Create draft context
    draft_state = create_sample_draft_state()
    players = create_sample_players()
    
    print(f"Current Draft Situation:")
    print(f"  Pick: {draft_state.current_pick}")
    print(f"  Picks until next: {draft_state.picks_until_next}")
    print(f"  My roster: {dict((k,len(v)) for k,v in draft_state.my_roster.items() if v)}")
    print(f"  Available players: {len(players)}")
    print()
    
    # Create strategist with default config
    config = StrategistConfig(selection_budget=15)
    strategist = DraftStrategist(config)
    
    print(f"Strategist Configuration:")
    print(f"  Selection budget: {config.selection_budget}")
    print(f"  Weights: {config.weights}")
    print(f"  Late draft rule enabled: {not config.allow_dst_k_early}")
    print()
    
    # Get allocation
    result = strategist.get_allocation(draft_state, players)
    
    print("=== STRATEGIST OUTPUT ===")
    print()
    print("Position Allocation (for Scout consumption):")
    for pos, count in result["player_lookup"].items():
        if count > 0:
            print(f"  {pos}: {count} players")
    print()
    
    total = sum(result["player_lookup"].values())
    print(f"Total allocation: {total}")
    print()
    
    print("Strategy Rationale:")
    print(f"  \"{result['pick_strategy']}\"")
    print()
    
    # Show how Scout would use this
    print("=== HOW SCOUT WOULD USE THIS ===")
    print("Scout node would now:")
    
    for pos, count in result["player_lookup"].items():
        if count > 0:
            pos_players = [p for p in players if p.position == pos]
            pos_players.sort(key=lambda p: p.adp_rank)
            candidates = pos_players[:count]
            
            print(f"  {pos} ({count} slots):")
            for player in candidates:
                print(f"    - {player.name} (ADP {player.adp_rank})")
    print()
    
    print("Scout would merge all candidates into a single list")
    print("for GM node to rank and select from.")
    print()
    
    # Show JSON output (what gets passed to next sprint)
    print("=== RAW JSON OUTPUT ===")
    import json
    print(json.dumps(result, indent=2))


def demo_different_scenarios():
    """Show how strategist adapts to different scenarios."""
    print("\n=== SCENARIO TESTING ===")
    print()
    
    players = create_sample_players()
    config = StrategistConfig(selection_budget=15)
    
    scenarios = [
        {
            "name": "Early Draft (round 2)",
            "pick": 24,
            "until_next": 1,
            "roster": {'QB': [], 'RB': [], 'WR': [], 'TE': [], 'DST': [], 'K': []}
        },
        {
            "name": "Mid Draft (round 7)", 
            "pick": 84,
            "until_next": 4,
            "roster": {'QB': ['qb1'], 'RB': ['rb1', 'rb2'], 'WR': ['wr1', 'wr2'], 'TE': [], 'DST': [], 'K': []}
        },
        {
            "name": "Late Draft (round 13)",
            "pick": 156,
            "until_next": 8,
            "roster": {'QB': ['qb1'], 'RB': ['rb1', 'rb2', 'rb3'], 'WR': ['wr1', 'wr2', 'wr3', 'wr4'], 'TE': ['te1'], 'DST': [], 'K': []}
        }
    ]
    
    for scenario in scenarios:
        class ScenarioState:
            def __init__(self, scenario):
                self.current_pick = scenario["pick"]
                self.picks_until_next = scenario["until_next"] 
                self.team_count = 12
                self.rounds = 16
                self.my_roster = scenario["roster"]
                self.pick_history = []
        
        state = ScenarioState(scenario)
        strategist = DraftStrategist(config)
        result = strategist.get_allocation(state, players)
        
        print(f"{scenario['name']}:")
        print(f"  Allocation: {result['player_lookup']}")
        print(f"  Strategy: \"{result['pick_strategy']}\"")
        print()


if __name__ == "__main__":
    demo_strategist_usage()
    demo_different_scenarios()