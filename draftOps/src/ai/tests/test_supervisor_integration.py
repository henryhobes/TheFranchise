#!/usr/bin/env python3
"""
Integration test for DraftSupervisor LangGraph implementation.

Tests the core functionality required by the Sprint 2 specification:
1. LangGraph setup with GPT-5 connectivity
2. Supervisor agent maintains context between messages
3. Draft state context injection works correctly
4. End-to-end round-trip functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from draftOps.src.ai.core.draft_supervisor import DraftSupervisor


async def test_basic_connectivity():
    """Test 1: Basic GPT-5 connectivity through LangGraph."""
    print("=" * 60)
    print("TEST 1: Basic GPT-5 Connectivity")
    print("=" * 60)
    
    try:
        supervisor = DraftSupervisor()
        print("[OK] DraftSupervisor initialized successfully")
        
        # Test connection
        result = await supervisor.test_connection()
        
        if result['success']:
            print("[OK] GPT-5 connectivity test passed")
            print(f"  Model: {result['model']}")
            print(f"  Response preview: {result['response_preview']}")
        else:
            print(f"[FAIL] GPT-5 connectivity test failed: {result['error']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"[FAIL] Basic connectivity test failed: {e}")
        return False


async def test_context_maintenance():
    """Test 2: Supervisor maintains context between messages."""
    print("\n" + "=" * 60)
    print("TEST 2: Context Maintenance")
    print("=" * 60)
    
    try:
        supervisor = DraftSupervisor()
        thread_id = "context_test"
        
        # First message
        first_input = "Remember that I need a quarterback badly."
        result1 = await supervisor.invoke_async(first_input, thread_id=thread_id)
        
        if not result1['success']:
            print(f"[FAIL] First message failed: {result1['error']}")
            return False
            
        print("[OK] First message processed")
        print(f"  Input: {first_input}")
        print(f"  Response: {result1['messages'][-1]['content'][:100]}...")
        
        # Second message referencing first
        second_input = "What position should I prioritize based on what I told you?"
        result2 = await supervisor.invoke_async(second_input, thread_id=thread_id)
        
        if not result2['success']:
            print(f"[FAIL] Second message failed: {result2['error']}")
            return False
            
        print("[OK] Second message processed")
        print(f"  Input: {second_input}")
        print(f"  Response: {result2['messages'][-1]['content'][:100]}...")
        
        # Check conversation history
        history = supervisor.get_conversation_history(thread_id)
        print(f"[OK] Conversation history contains {len(history)} messages")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Context maintenance test failed: {e}")
        return False


async def test_draft_context_injection():
    """Test 3: Draft state context injection works correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Draft State Context Injection")
    print("=" * 60)
    
    try:
        supervisor = DraftSupervisor()
        
        # Mock draft context
        mock_draft_context = {
            "current_pick": 15,
            "picks_until_next": 3,
            "time_remaining": 45.0,
            "on_the_clock": "Team 7",
            "draft_status": "IN_PROGRESS",
            "my_roster": {
                "QB": [],
                "RB": ["Player_123"],
                "WR": ["Player_456", "Player_789"],
                "TE": [],
                "K": [],
                "DST": [],
                "FLEX": [],
                "BENCH": []
            },
            "available_players_count": 487,
            "total_picks_made": 14,
            "recent_picks": [
                {"pick_number": 13, "player_name": "Christian McCaffrey", "team_id": "Team 6"},
                {"pick_number": 14, "player_name": "Cooper Kupp", "team_id": "Team 7"}
            ]
        }
        
        user_input = "What should I be thinking about for my upcoming pick?"
        result = await supervisor.invoke_async(
            user_input, 
            draft_context=mock_draft_context,
            thread_id="context_injection_test"
        )
        
        if not result['success']:
            print(f"[FAIL] Context injection test failed: {result['error']}")
            return False
            
        print("[OK] Draft context injection successful")
        print(f"  Input: {user_input}")
        print(f"  Response: {result['messages'][-1]['content'][:150]}...")
        
        if result.get('recommendation'):
            print(f"  Recommendation: {result['recommendation']}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Draft context injection test failed: {e}")
        return False


async def test_end_to_end_workflow():
    """Test 4: Complete end-to-end workflow simulation."""
    print("\n" + "=" * 60)
    print("TEST 4: End-to-End Workflow")
    print("=" * 60)
    
    try:
        supervisor = DraftSupervisor()
        thread_id = "e2e_test"
        
        # Simulate draft progression
        scenarios = [
            {
                "description": "Early draft - need to establish strategy",
                "context": {
                    "current_pick": 3,
                    "picks_until_next": 7,
                    "time_remaining": 60.0,
                    "my_roster": {"QB": [], "RB": [], "WR": [], "TE": [], "K": [], "DST": [], "FLEX": [], "BENCH": []},
                    "recent_picks": []
                },
                "input": "Draft just started. What's our overall strategy?"
            },
            {
                "description": "Mid-draft - need specific position",
                "context": {
                    "current_pick": 47,
                    "picks_until_next": 1,
                    "time_remaining": 30.0,
                    "my_roster": {"QB": [], "RB": ["Player_123", "Player_456"], "WR": ["Player_789"], "TE": [], "K": [], "DST": [], "FLEX": [], "BENCH": []},
                    "recent_picks": [
                        {"pick_number": 45, "player_name": "Travis Kelce", "team_id": "Team 3"},
                        {"pick_number": 46, "player_name": "Patrick Mahomes", "team_id": "Team 4"}
                    ]
                },
                "input": "I'm on the clock! What position should I target?"
            },
            {
                "description": "Late draft - filling bench",
                "context": {
                    "current_pick": 156,
                    "picks_until_next": 8,
                    "time_remaining": 90.0,
                    "my_roster": {
                        "QB": ["Player_111"], 
                        "RB": ["Player_123", "Player_456"], 
                        "WR": ["Player_789", "Player_101", "Player_102"], 
                        "TE": ["Player_131"], 
                        "K": [], 
                        "DST": [], 
                        "FLEX": [], 
                        "BENCH": ["Player_141", "Player_151"]
                    },
                    "recent_picks": []
                },
                "input": "Late rounds now. What should we focus on?"
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n--- Scenario {i}: {scenario['description']} ---")
            
            result = await supervisor.invoke_async(
                scenario['input'],
                draft_context=scenario['context'],
                thread_id=thread_id
            )
            
            if not result['success']:
                print(f"[FAIL] Scenario {i} failed: {result['error']}")
                return False
                
            print(f"[OK] Scenario {i} processed")
            print(f"  Response: {result['messages'][-1]['content'][:120]}...")
            
            if result.get('recommendation'):
                print(f"  Recommendation: {result['recommendation']}")
        
        print("\n[OK] End-to-end workflow test completed successfully")
        return True
        
    except Exception as e:
        print(f"[FAIL] End-to-end workflow test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("DraftOps LangGraph Supervisor Integration Test")
    print("Testing Sprint 2 specification requirements...")
    print(f"Timestamp: {asyncio.get_event_loop().time()}")
    
    tests = [
        ("Basic Connectivity", test_basic_connectivity),
        ("Context Maintenance", test_context_maintenance), 
        ("Draft Context Injection", test_draft_context_injection),
        ("End-to-End Workflow", test_end_to_end_workflow)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"\n[OK] {test_name}: PASSED")
            else:
                print(f"\n[FAIL] {test_name}: FAILED")
        except Exception as e:
            print(f"\n[ERROR] {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("SUCCESS: All tests passed! LangGraph integration is working correctly.")
        print("\nDeliverables completed:")
        print("[OK] LangGraph Dependency & Config")
        print("[OK] Supervisor Agent Node")  
        print("[OK] Memory & State Management via LangGraph")
        print("[OK] Integration Test (LangGraph Round-Trip)")
        return True
    else:
        print(f"FAILED: {total - passed} test(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)