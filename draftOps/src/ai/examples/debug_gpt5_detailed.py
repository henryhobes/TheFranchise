#!/usr/bin/env python3
"""
Detailed GPT-5 Debugging

Debug script to understand why gpt-5 is returning empty responses.
Tests various aspects of the OpenAI API call.
"""

import json
import sys
import os
from typing import Dict, Any

# Add project root to path and load environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

from langchain_openai import ChatOpenAI
import openai


def test_api_key():
    """Test if API key is properly loaded."""
    print("Testing API Key...")
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"  API Key found: {api_key[:10]}...{api_key[-5:]}")
        return api_key
    else:
        print("  [ERROR] No API key found")
        return None


def test_openai_client_direct():
    """Test OpenAI client directly without LangChain."""
    print("\nTesting Direct OpenAI Client...")
    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Test simple completion
        print("  Making simple completion request...")
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "user", "content": "Say 'Hello World' in JSON format with a 'message' field."}
            ],
            max_tokens=10000,
            temperature=0.5
        )
        
        print(f"  Response object type: {type(response)}")
        print(f"  Response choices: {len(response.choices) if response.choices else 0}")
        
        if response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            print(f"  First choice: {choice}")
            print(f"  Message: {choice.message}")
            print(f"  Content: '{choice.message.content}'")
            print(f"  Content length: {len(choice.message.content) if choice.message.content else 0}")
            return choice.message.content
        else:
            print("  [ERROR] No choices in response")
            return None
            
    except Exception as e:
        print(f"  [ERROR] Direct OpenAI client failed: {e}")
        print(f"  Error type: {type(e)}")
        return None


def test_langchain_different_models():
    """Test LangChain with different model names."""
    print("\nTesting LangChain with Different Models...")
    
    models_to_test = [
        "gpt-5",
        "gpt-4o", 
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4"
    ]
    
    api_key = os.getenv('OPENAI_API_KEY')
    simple_prompt = "Respond with exactly: {'test': 'success'}"
    
    for model in models_to_test:
        print(f"\n  Testing model: {model}")
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=0.5,
                api_key=api_key,
                max_tokens=10000,
                timeout=30.0
            )
            
            response = llm.invoke([{"role": "user", "content": simple_prompt}])
            
            print(f"    Response type: {type(response)}")
            print(f"    Response content type: {type(response.content)}")
            print(f"    Response length: {len(response.content) if response.content else 0}")
            print(f"    Response preview: '{response.content[:100] if response.content else '[EMPTY]'}{'...' if response.content and len(response.content) > 100 else ''}'")
            
        except Exception as e:
            print(f"    [ERROR] {model} failed: {e}")
            print(f"    Error type: {type(e)}")


def test_gpt5_with_verbose_logging():
    """Test GPT-5 with maximum verbosity."""
    print("\nTesting GPT-5 with Verbose Logging...")
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        print(f"  Using API key: {api_key[:10]}...{api_key[-5:]}")
        
        # Enable verbose logging
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        llm = ChatOpenAI(
            model="gpt-5",
            temperature=0.8,
            api_key=api_key,
            max_tokens=10000,
            timeout=30.0,
            verbose=True
        )
        
        print("  LangChain ChatOpenAI instance created successfully")
        print(f"  Model: {llm.model_name}")
        print(f"  Temperature: {llm.temperature}")
        print(f"  Max tokens: {llm.max_tokens}")
        
        simple_message = [{"role": "user", "content": "Hello, respond with a simple JSON object containing 'status': 'working'"}]
        print(f"  Sending message: {simple_message}")
        
        print("  Making API call...")
        response = llm.invoke(simple_message)
        
        print("  API call completed")
        print(f"  Response object: {response}")
        print(f"  Response type: {type(response)}")
        print(f"  Response attributes: {dir(response)}")
        
        if hasattr(response, 'content'):
            print(f"  Content: '{response.content}'")
            print(f"  Content type: {type(response.content)}")
            print(f"  Content length: {len(response.content) if response.content else 0}")
            
            if response.content is None:
                print("  [WARNING] Content is None!")
            elif response.content == "":
                print("  [WARNING] Content is empty string!")
            else:
                print("  [SUCCESS] Got content from GPT-5")
                return response.content
        else:
            print("  [ERROR] Response has no 'content' attribute")
            
        return None
        
    except Exception as e:
        print(f"  [ERROR] GPT-5 verbose test failed: {e}")
        print(f"  Error type: {type(e)}")
        import traceback
        print(f"  Traceback: {traceback.format_exc()}")
        return None


def main():
    """Run all debug tests."""
    print("Detailed GPT-5 Debugging")
    print("=" * 50)
    
    # Test 1: API Key
    api_key = test_api_key()
    if not api_key:
        print("\n[ABORT] Cannot proceed without API key")
        return
    
    # Test 2: Direct OpenAI Client
    direct_result = test_openai_client_direct()
    
    # Test 3: LangChain with different models
    test_langchain_different_models()
    
    # Test 4: GPT-5 with verbose logging
    verbose_result = test_gpt5_with_verbose_logging()
    
    # Summary
    print("\n" + "=" * 50)
    print("DEBUGGING SUMMARY:")
    print(f"  Direct OpenAI client (gpt-5): {'SUCCESS' if direct_result else 'FAILED'}")
    print(f"  LangChain verbose (gpt-5): {'SUCCESS' if verbose_result else 'FAILED'}")
    
    if not direct_result and not verbose_result:
        print("\n[CONCLUSION] GPT-5 is not responding through either method")
        print("Possible causes:")
        print("  1. GPT-5 model not available with current API key")
        print("  2. GPT-5 requires different API endpoint")
        print("  3. GPT-5 name is incorrect (should be different)")
        print("  4. Account doesn't have GPT-5 access")
        print("  5. Rate limiting or API issues")
    elif direct_result and not verbose_result:
        print("\n[CONCLUSION] GPT-5 works with direct client but not LangChain")
        print("Possible LangChain configuration issue")
    elif not direct_result and verbose_result:
        print("\n[CONCLUSION] GPT-5 works with LangChain but not direct client")
        print("Unusual - might be configuration difference")
    else:
        print("\n[CONCLUSION] GPT-5 is working properly")
        print("The empty response issue might be in the GM implementation")


if __name__ == "__main__":
    main()