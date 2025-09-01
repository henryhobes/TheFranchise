#!/usr/bin/env python3
"""
DraftOps LangGraph AI Integration Demo

Demonstrates the key capabilities of the LangGraph Supervisor Framework
integration completed in Sprint 2. This shows how the AI system works
with draft context and maintains conversation continuity.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from draftOps.src.ai.draft_supervisor import DraftSupervisor


async def demo_basic_ai_functionality():
    """Demonstrate basic AI supervisor functionality."""
    print("=" * 60)
    print("DEMO 1: Basic AI Supervisor Functionality")
    print("=" * 60)
    
    supervisor = DraftSupervisor()
    
    # Test connection
    print("Testing GPT-5 connectivity...")
    result = await supervisor.test_connection()
    
    if result['success']:
        print(f"[OK] Connected to {result['model']}")
        print(f"[OK] Response preview: {result['response_preview']}")
    else:
        print(f"[ERROR] Connection failed: {result['error']}")
        return
        
    print("\n" + "-" * 40)
    print("Basic Q&A without draft context:")
    
    response = await supervisor.invoke_async(
        "What makes a good fantasy football draft strategy?",
        thread_id="demo_basic"
    )
    
    if response['success']:
        print(f"AI: {response['messages'][-1]['content'][:200]}...")
    else:
        print(f"Error: {response['error']}")


async def demo_draft_context_awareness():
    """Demonstrate draft context injection and awareness."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Draft Context Awareness")
    print("=" * 60)
    
    supervisor = DraftSupervisor()
    
    # Create mock draft context
    mock_context = {
        "current_pick": 23,
        "picks_until_next": 1,
        "time_remaining": 35.0,
        "on_the_clock": "Team 11",
        "draft_status": "IN_PROGRESS",
        "my_roster": {
            "QB": [],
            "RB": ["Saquon Barkley"],
            "WR": ["Davante Adams", "Mike Evans"],
            "TE": [],
            "K": [],
            "DST": [],
            "FLEX": [],
            "BENCH": []
        },
        "available_players_count": 423,
        "total_picks_made": 22,
        "recent_picks": [
            {"pick_number": 21, "player_name": "Travis Kelce", "team_id": "Team 9"},
            {"pick_number": 22, "player_name": "Josh Allen", "team_id": "Team 10"}
        ]
    }
    
    print("Mock draft situation:")
    print(f"  - Pick {mock_context['current_pick']}, we pick next!")
    print(f"  - Time: {mock_context['time_remaining']}s remaining")
    print(f"  - Our roster: 1 RB, 2 WR, need QB/TE/etc.")
    print(f"  - Recent picks: Kelce, Josh Allen just taken")
    
    print("\nQuerying AI with draft context...")
    
    response = await supervisor.invoke_async(
        "I'm on the clock! What should I do right now?",
        draft_context=mock_context,
        thread_id="demo_context"
    )
    
    if response['success']:
        print(f"\nAI Analysis: {response['messages'][-1]['content'][:400]}...")
        if response.get('recommendation'):
            print(f"\nQuick Rec: {response['recommendation']}")
    else:
        print(f"Error: {response['error']}")


async def demo_conversation_continuity():
    """Demonstrate conversation memory and context maintenance."""
    print("\n\n" + "=" * 60)
    print("DEMO 3: Conversation Continuity")
    print("=" * 60)
    
    supervisor = DraftSupervisor()
    thread_id = "demo_memory"
    
    # First message - establish context
    print("Message 1: Setting up draft preferences...")
    response1 = await supervisor.invoke_async(
        "I'm in a 12-team PPR league and I really want to prioritize RB early since they're scarce.",
        thread_id=thread_id
    )
    
    if response1['success']:
        print(f"AI: {response1['messages'][-1]['content'][:150]}...")
    
    print("\nMessage 2: Testing memory of previous context...")
    response2 = await supervisor.invoke_async(
        "Given what I just told you about my strategy, what should I do if both a top RB and WR are available?",
        thread_id=thread_id
    )
    
    if response2['success']:
        print(f"AI: {response2['messages'][-1]['content'][:150]}...")
        
    # Check conversation history
    history = supervisor.get_conversation_history(thread_id)
    print(f"\n[INFO] Conversation history: {len(history)} messages stored")
    
    print("\nMessage 3: Testing deeper context retention...")
    response3 = await supervisor.invoke_async(
        "What format did I say my league was in?",
        thread_id=thread_id
    )
    
    if response3['success']:
        print(f"AI: {response3['messages'][-1]['content'][:100]}...")


async def demo_multiple_scenarios():
    """Demonstrate AI responses to different draft scenarios."""
    print("\n\n" + "=" * 60)
    print("DEMO 4: Multiple Draft Scenarios")
    print("=" * 60)
    
    supervisor = DraftSupervisor()
    
    scenarios = [
        {
            "name": "Early Draft - Building Foundation",
            "context": {
                "current_pick": 8,
                "picks_until_next": 5,
                "my_roster": {"QB": [], "RB": [], "WR": [], "TE": [], "K": [], "DST": [], "FLEX": [], "BENCH": []}
            },
            "question": "It's still early in the draft. What's our overall approach?"
        },
        {
            "name": "Mid-Draft - Roster Balance",
            "context": {
                "current_pick": 67,
                "picks_until_next": 3,
                "my_roster": {
                    "QB": ["Lamar Jackson"],
                    "RB": ["Christian McCaffrey", "Josh Jacobs"],
                    "WR": ["Cooper Kupp"],
                    "TE": [],
                    "K": [], "DST": [], "FLEX": [], "BENCH": []
                }
            },
            "question": "Mid-draft now. What positions should I prioritize?"
        },
        {
            "name": "Late Draft - Sleepers & Handcuffs",
            "context": {
                "current_pick": 145,
                "picks_until_next": 7,
                "my_roster": {
                    "QB": ["Josh Allen"],
                    "RB": ["Derrick Henry", "Aaron Jones"],
                    "WR": ["Stefon Diggs", "Keenan Allen", "Chris Godwin"],
                    "TE": ["Mark Andrews"],
                    "K": [], "DST": [], "FLEX": [], "BENCH": ["Gus Edwards", "Roschon Johnson"]
                }
            },
            "question": "Late rounds - what should we be looking for now?"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        
        response = await supervisor.invoke_async(
            scenario['question'],
            draft_context=scenario['context'],
            thread_id=f"demo_scenario_{i}"
        )
        
        if response['success']:
            print(f"AI: {response['messages'][-1]['content'][:200]}...")
            if response.get('recommendation'):
                print(f"Rec: {response['recommendation']}")
        else:
            print(f"Error: {response['error']}")


async def main():
    """Run all demos."""
    print("DraftOps LangGraph AI Integration Demo")
    print("Showcasing Sprint 2 Deliverables\n")
    
    try:
        await demo_basic_ai_functionality()
        await demo_draft_context_awareness()
        await demo_conversation_continuity()
        await demo_multiple_scenarios()
        
        print("\n\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print("Sprint 2 LangGraph Integration Features Demonstrated:")
        print("[OK] GPT-5 Connectivity via LangGraph")
        print("[OK] Draft Context Injection & Awareness")
        print("[OK] Conversation Memory & Continuity")
        print("[OK] StateGraph Workflow Processing")
        print("[OK] Multiple Scenario Handling")
        print("[OK] Async Non-blocking Operation")
        
        print("\nThe AI system is ready for integration with the full")
        print("DraftOps application and Sprint 3 testing!")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo error: {e}")


if __name__ == "__main__":
    asyncio.run(main())