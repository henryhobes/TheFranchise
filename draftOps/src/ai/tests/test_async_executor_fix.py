#!/usr/bin/env python3
"""
Minimal test to verify async executor fix for RuntimeError.

Tests that invoke_async() works correctly in different async contexts
where asyncio.get_event_loop() would have raised RuntimeError.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from draftOps.src.ai.core.draft_supervisor import DraftSupervisor


async def test_invoke_async_in_running_loop():
    """Test that invoke_async works in a normal async context with running loop."""
    supervisor = DraftSupervisor()
    
    # This should work without RuntimeError
    result = await supervisor.invoke_async(
        "Test query",
        thread_id="test_running_loop"
    )
    
    assert result["success"] == True
    assert "error" not in result or result.get("error") is None
    print("[PASS] invoke_async works with running event loop")


def test_invoke_from_sync_context():
    """Test that invoke_async can be called from sync context without crashing."""
    supervisor = DraftSupervisor()
    
    # Create a new event loop for this sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the async function in the loop
        result = loop.run_until_complete(
            supervisor.invoke_async(
                "Test from sync",
                thread_id="test_sync_context"
            )
        )
        
        assert result["success"] == True
        print("[PASS] invoke_async works when called from sync context")
    finally:
        loop.close()


async def test_nested_async_context():
    """Test invoke_async in nested async contexts."""
    supervisor = DraftSupervisor()
    
    async def inner_call():
        return await supervisor.invoke_async(
            "Nested test",
            thread_id="test_nested"
        )
    
    # This tests that get_running_loop() works correctly in nested contexts
    result = await inner_call()
    
    assert result["success"] == True
    print("[PASS] invoke_async works in nested async contexts")


async def run_async_tests():
    """Run async tests."""
    print("Testing async executor fix...")
    print("-" * 40)
    
    # Test 1: Normal async context
    await test_invoke_async_in_running_loop()
    
    # Test 2: Nested async contexts
    await test_nested_async_context()
    
    print("-" * 40)
    print("Async context tests passed!")


if __name__ == "__main__":
    # Run async tests
    asyncio.run(run_async_tests())
    
    # Run sync context test separately (can't run nested event loops)
    print("\nTesting sync context separately...")
    test_invoke_from_sync_context()
    
    print("\nAll tests passed! Async executor fix verified.")