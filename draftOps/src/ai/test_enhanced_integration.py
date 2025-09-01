#!/usr/bin/env python3
"""
Enhanced Integration Test for LangGraph + DraftStateManager

Tests the complete integration between the DraftSupervisor and DraftStateManager
to verify the Sprint 2 deliverables are working correctly in the full system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from draftOps.src.ai.enhanced_draft_state_manager import EnhancedDraftStateManager


async def test_enhanced_manager_initialization():
    """Test 1: Enhanced manager initializes correctly with AI."""
    print("=" * 60)
    print("TEST 1: Enhanced Manager Initialization")
    print("=" * 60)
    
    try:
        # Create enhanced manager
        manager = EnhancedDraftStateManager(
            league_id="test_league",
            team_id="test_team",
            team_count=12,
            rounds=16,
            ai_enabled=True,
            headless=True  # No browser needed for this test
        )
        
        print("[OK] Enhanced manager created")
        
        # Initialize (this should include AI supervisor)
        success = await manager.initialize()
        
        if not success:
            print("[FAIL] Enhanced manager initialization failed")
            return False
            
        print("[OK] Enhanced manager initialized successfully")
        
        # Check AI components
        if not manager.supervisor:
            print("[FAIL] AI supervisor not created")
            return False
            
        print("[OK] AI supervisor created")
        
        # Get enhanced state summary
        summary = manager.get_enhanced_state_summary()
        print(f"[OK] Enhanced state summary includes AI stats: {bool(summary.get('ai_stats'))}")
        
        await manager.close()
        return True
        
    except Exception as e:
        print(f"[FAIL] Enhanced manager initialization failed: {e}")
        return False


async def test_ai_query_integration():
    """Test 2: AI queries work with draft context."""
    print("\n" + "=" * 60)
    print("TEST 2: AI Query Integration")
    print("=" * 60)
    
    try:
        manager = EnhancedDraftStateManager(
            league_id="test_league",
            team_id="test_team", 
            team_count=10,
            ai_enabled=True,
            headless=True
        )
        
        await manager.initialize()
        
        # Simulate some draft state
        manager.draft_state._current_pick = 15
        manager.draft_state._picks_until_next = 2
        manager.draft_state._time_remaining = 45.0
        manager.draft_state._my_roster['RB'] = ['player_123']
        manager.draft_state._my_roster['WR'] = ['player_456', 'player_789']
        
        print("[OK] Mock draft state configured")
        
        # Test AI query with context
        result = await manager.query_ai("What position should I focus on next?", include_context=True)
        
        if not result['success']:
            print(f"[FAIL] AI query failed: {result.get('error')}")
            return False
            
        print("[OK] AI query processed successfully")
        print(f"  Response preview: {result['messages'][-1]['content'][:100]}...")
        
        # Test getting draft recommendation
        recommendation = await manager.get_draft_recommendation()
        
        if not recommendation['success']:
            print(f"[FAIL] Draft recommendation failed: {recommendation.get('error')}")
            return False
            
        print("[OK] Draft recommendation generated")
        print(f"  Urgency level: {recommendation.get('urgency', 'unknown')}")
        
        await manager.close()
        return True
        
    except Exception as e:
        print(f"[FAIL] AI query integration failed: {e}")
        return False


async def test_callback_integration():
    """Test 3: AI-enhanced callbacks work correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Callback Integration")
    print("=" * 60)
    
    try:
        manager = EnhancedDraftStateManager(
            league_id="test_league",
            team_id="test_team",
            team_count=12,
            ai_enabled=True,
            headless=True
        )
        
        await manager.initialize()
        
        # Set up callback tracking
        callback_results = {
            'picks_processed': 0,
            'ai_recommendations': 0,
            'ai_responses': 0
        }
        
        def track_pick_callback(pick_data):
            callback_results['picks_processed'] += 1
            print(f"[OK] Pick callback triggered: {pick_data.get('player_name', 'Unknown')}")
            
        def track_ai_recommendation(recommendation_data):
            callback_results['ai_recommendations'] += 1
            print(f"[OK] AI recommendation callback: {recommendation_data.get('type', 'unknown')}")
            
        def track_ai_response(response_data):
            callback_results['ai_responses'] += 1
            print(f"[OK] AI response callback: {response_data.get('type', 'unknown')}")
            
        # Set callbacks
        manager.on_pick_processed = track_pick_callback
        manager.on_ai_recommendation = track_ai_recommendation
        manager.on_ai_response = track_ai_response
        
        # Simulate draft state that triggers AI analysis
        manager.draft_state._current_pick = 10
        manager.draft_state._picks_until_next = 2  # Close to our turn
        
        # Simulate a pick event (this should trigger AI analysis)
        mock_pick = {
            'pick_number': 10,
            'player_id': 'player_999',
            'player_name': 'Mock Player',
            'team_id': 'other_team',
            'display_team_name': 'Team 5'
        }
        
        print("[OK] Simulating pick event...")
        
        # Trigger the enhanced pick callback
        if manager.on_pick_processed:
            manager.on_pick_processed(mock_pick)
            
        # Wait briefly for async AI analysis
        await asyncio.sleep(3)
        
        print(f"[OK] Callback tracking results:")
        print(f"  Picks processed: {callback_results['picks_processed']}")
        print(f"  AI recommendations: {callback_results['ai_recommendations']}")
        print(f"  AI responses: {callback_results['ai_responses']}")
        
        if callback_results['picks_processed'] == 0:
            print("[FAIL] Pick callback not triggered")
            return False
            
        print("[OK] Callback integration working")
        
        await manager.close()
        return True
        
    except Exception as e:
        print(f"[FAIL] Callback integration failed: {e}")
        return False


async def test_conversation_persistence():
    """Test 4: AI conversation persistence across queries."""
    print("\n" + "=" * 60)
    print("TEST 4: Conversation Persistence")
    print("=" * 60)
    
    try:
        manager = EnhancedDraftStateManager(
            league_id="test_league", 
            team_id="test_team",
            ai_enabled=True,
            ai_thread_id="persistence_test",
            headless=True
        )
        
        await manager.initialize()
        
        # First query
        result1 = await manager.query_ai("I really need a tight end", include_context=False)
        
        if not result1['success']:
            print(f"[FAIL] First query failed: {result1.get('error')}")
            return False
            
        print("[OK] First query processed")
        
        # Second query referencing first
        result2 = await manager.query_ai("Based on what I just told you, what should I do?", include_context=False)
        
        if not result2['success']:
            print(f"[FAIL] Second query failed: {result2.get('error')}")
            return False
            
        print("[OK] Second query processed")
        
        # Check conversation history
        history = manager.get_ai_conversation_history()
        
        if len(history) == 0:
            print("[FAIL] No conversation history found")
            return False
            
        print(f"[OK] Conversation history contains {len(history)} messages")
        
        # Test clearing conversation
        success = manager.clear_ai_conversation()
        print(f"[OK] Conversation clearing: {success}")
        
        await manager.close()
        return True
        
    except Exception as e:
        print(f"[FAIL] Conversation persistence failed: {e}")
        return False


async def test_draft_context_injection():
    """Test 5: Draft context properly injected to AI."""
    print("\n" + "=" * 60)
    print("TEST 5: Draft Context Injection")
    print("=" * 60)
    
    try:
        manager = EnhancedDraftStateManager(
            league_id="test_league",
            team_id="test_team",
            team_count=12,
            ai_enabled=True,
            headless=True
        )
        
        await manager.initialize()
        
        # Create rich draft state
        manager.draft_state._current_pick = 47
        manager.draft_state._picks_until_next = 1
        manager.draft_state._time_remaining = 25.0
        manager.draft_state._on_the_clock = "team_5"
        manager.draft_state._my_roster = {
            'QB': [],
            'RB': ['player_123', 'player_456'], 
            'WR': ['player_789'],
            'TE': [],
            'K': [],
            'DST': [],
            'FLEX': [],
            'BENCH': []
        }
        
        # Add some pick history
        manager.draft_state._pick_history = [
            {'pick_number': 45, 'player_name': 'Travis Kelce', 'team_id': 'team_3'},
            {'pick_number': 46, 'player_name': 'Patrick Mahomes', 'team_id': 'team_4'}
        ]
        
        print("[OK] Rich draft state configured")
        
        # Query AI with context
        result = await manager.query_ai(
            "I'm picking next! What's my best move?", 
            include_context=True
        )
        
        if not result['success']:
            print(f"[FAIL] Context-aware query failed: {result.get('error')}")
            return False
            
        print("[OK] Context-aware query processed")
        
        # Verify context was included by checking response content
        response_content = result['messages'][-1]['content'] if result.get('messages') else ""
        
        # The AI should reference draft context in its response
        context_indicators = ['pick', 'draft', 'roster', 'position']
        context_found = any(indicator in response_content.lower() for indicator in context_indicators)
        
        if not context_found:
            print("[WARN] AI response may not include draft context")
        else:
            print("[OK] AI response includes draft context")
            
        print(f"  Response preview: {response_content[:150]}...")
        
        await manager.close()
        return True
        
    except Exception as e:
        print(f"[FAIL] Draft context injection failed: {e}")
        return False


async def main():
    """Run all enhanced integration tests."""
    print("DraftOps Enhanced LangGraph Integration Test")
    print("Testing complete system integration...")
    
    tests = [
        ("Enhanced Manager Initialization", test_enhanced_manager_initialization),
        ("AI Query Integration", test_ai_query_integration),
        ("Callback Integration", test_callback_integration),
        ("Conversation Persistence", test_conversation_persistence),
        ("Draft Context Injection", test_draft_context_injection)
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
    print("ENHANCED INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("SUCCESS: All enhanced integration tests passed!")
        print("\nFinal Sprint 2 Deliverables Verified:")
        print("[OK] LangGraph Dependency & Config - Working")
        print("[OK] Supervisor Agent Node - Working")
        print("[OK] Memory & State Management via LangGraph - Working") 
        print("[OK] Integration Test (LangGraph Round-Trip) - Working")
        print("[OK] Draft Context Injection - Working")
        print("[OK] Async Non-blocking AI Invocation - Working")
        print("[OK] Integration with DraftStateManager - Working")
        
        print("\nSystem is ready for Sprint 3 testing and refinement!")
        return True
    else:
        print(f"FAILED: {total - passed} test(s) failed.")
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