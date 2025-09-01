#!/usr/bin/env python3
"""
Debug GM Node API Response

Simple test to debug the JSON parsing issue with GPT-5 responses.
"""

import json
import sys
import os

# Add project root to path and load environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

from core.gm import GM


def debug_gm_response():
    """Debug the raw response from GPT-5."""
    print("Debugging GM Node API Response")
    print("=" * 40)
    
    # Simple test data
    scout_recommendations = [
        {
            "suggested_player_id": "123",
            "suggested_player_name": "Test Player",
            "position": "RB",
            "reason": "Good player for testing.",
            "score_hint": 0.8
        }
    ]
    
    draft_state = {"round": 1, "pick": 1}
    strategy = "Pick the best player available."
    
    try:
        print("Creating GM instance...")
        gm = GM(model_name="gpt-5", temperature=0.8)
        
        print("Building prompt...")
        prompt = gm._build_prompt(scout_recommendations, strategy, draft_state)
        print(f"Prompt length: {len(prompt)} characters")
        print("\nPrompt preview:")
        print(prompt[:500] + "...\n")
        
        print("Making API call...")
        response = gm.llm.invoke([{"role": "user", "content": prompt}])
        
        print("Raw API response:")
        print(f"Type: {type(response.content)}")
        print(f"Length: {len(response.content)} characters")
        print("Content:")
        print("-" * 40)
        print(response.content)
        print("-" * 40)
        
        # Try to find JSON in the response
        print("\nLooking for JSON...")
        json_start = response.content.find('{')
        json_end = response.content.rfind('}') + 1
        
        print(f"JSON start position: {json_start}")
        print(f"JSON end position: {json_end}")
        
        if json_start != -1 and json_end > json_start:
            json_text = response.content[json_start:json_end]
            print(f"\nExtracted JSON ({len(json_text)} chars):")
            print(json_text)
            
            try:
                parsed = json.loads(json_text)
                print("\nSuccessfully parsed JSON:")
                print(json.dumps(parsed, indent=2))
                return True
            except json.JSONDecodeError as e:
                print(f"\nJSON parsing failed: {e}")
                return False
        else:
            print("\nNo JSON found in response!")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = debug_gm_response()
    if success:
        print("\n[SUCCESS] GM API response debugging completed")
    else:
        print("\n[ERROR] GM API response debugging failed")