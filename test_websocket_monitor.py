#!/usr/bin/env python3
"""
Test script to verify the WebSocket monitoring system works correctly.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "draftOps/src/websocket_protocol"))

async def test_import():
    """Test that all modules can be imported correctly."""
    try:
        print("Testing imports...")
        
        from monitor.espn_draft_monitor import ESPNDraftMonitor
        from utils.websocket_discovery import WebSocketDiscovery
        
        print("OK All imports successful")
        return True
        
    except ImportError as e:
        print(f"X Import error: {e}")
        return False

async def test_monitor_creation():
    """Test that monitor can be created and basic methods work."""
    try:
        print("Testing monitor creation...")
        
        from monitor.espn_draft_monitor import ESPNDraftMonitor
        
        monitor = ESPNDraftMonitor(headless=True)
        
        # Test basic methods
        assert hasattr(monitor, 'start_browser')
        assert hasattr(monitor, 'connect_to_draft')
        assert hasattr(monitor, 'get_message_log')
        
        print("OK Monitor creation successful")
        return True
        
    except Exception as e:
        print(f"X Monitor creation error: {e}")
        return False

async def test_discovery_creation():
    """Test that discovery utility works."""
    try:
        print("Testing discovery utility...")
        
        from utils.websocket_discovery import WebSocketDiscovery
        
        discovery = WebSocketDiscovery()
        
        # Test URL analysis
        test_url = "wss://draft-socket.fantasy.espn.com/draft/12345"
        analysis = discovery.analyze_websocket_url(test_url)
        
        assert analysis["service"] == "ESPN"
        assert analysis["purpose"] == "draft"
        
        # Test message categorization
        test_message = '{"type": "PICK_MADE", "player": "Josh Allen", "team": 1}'
        msg_analysis = discovery.categorize_message(test_message)
        
        assert msg_analysis["is_json"] == True
        assert msg_analysis["message_type"] == "PICK_MADE"
        assert msg_analysis["contains_draft_keywords"] == True
        
        print("OK Discovery utility working correctly")
        return True
        
    except Exception as e:
        print(f"X Discovery utility error: {e}")
        return False

async def test_browser_startup():
    """Test that browser can start up correctly."""
    try:
        print("Testing browser startup...")
        
        from monitor.espn_draft_monitor import ESPNDraftMonitor
        
        monitor = ESPNDraftMonitor(headless=True)
        await monitor.start_browser()
        
        assert monitor.browser is not None
        assert monitor.page is not None
        
        await monitor.close()
        
        print("OK Browser startup successful")
        return True
        
    except Exception as e:
        print(f"X Browser startup error: {e}")
        return False

async def run_all_tests():
    """Run all tests and report results."""
    print("[TEST] Running WebSocket Monitor Tests")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_import),
        ("Monitor Creation", test_monitor_creation),
        ("Discovery Utility", test_discovery_creation), 
        ("Browser Startup", test_browser_startup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n- {test_name}")
        print("-" * 20)
        
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"X Test failed with exception: {e}")
            
    print(f"\nRESULTS Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("OK All tests passed! System ready for use.")
        return True
    else:
        print("X Some tests failed. Check errors above.")
        return False

if __name__ == "__main__":
    print("""
    WebSocket Monitor Test Suite
    ============================
    
    This script tests that all components are working correctly
    before attempting to connect to ESPN drafts.
    
    """)
    
    try:
        success = asyncio.run(run_all_tests())
        
        if success:
            print("""
    Next Steps:
    ===========
    
    1. Run the discovery script:
       cd draftOps/src/websocket_protocol
       python discover_espn_protocol.py
       
    2. Or run the proof-of-concept logger:
       cd draftOps/src/websocket_protocol  
       python poc_draft_logger.py
       
    """)
        
    except Exception as e:
        print(f"Fatal test error: {e}")
        sys.exit(1)