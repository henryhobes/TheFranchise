#!/usr/bin/env python3
"""
Test the Player ID Extractor functionality.
"""

import json
from ..utils.player_id_extractor import PlayerIdExtractor, analyze_draft_message_for_players


def test_player_id_extractor():
    """Test the PlayerIdExtractor with various message formats."""
    print("Testing Player ID Extractor...")
    print("=" * 60)
    
    extractor = PlayerIdExtractor()
    
    # Test messages with different structures
    test_cases = [
        {
            "description": "Simple pick made message",
            "message": '{"type":"PICK_MADE","playerId":4241457,"teamId":1,"pickNumber":12}',
            "expected_ids": ["4241457"]
        },
        {
            "description": "Player object with nested ID",
            "message": '{"event":"draft_pick","player":{"id":3916387,"name":"Josh Allen","pos":"QB"}}',
            "expected_ids": ["3916387"]
        },
        {
            "description": "Nested selectedPlayer structure",
            "message": '{"data":{"selectedPlayer":{"playerId":"4362628","fullName":"Justin Jefferson"}}}',
            "expected_ids": ["4362628"]
        },
        {
            "description": "Multiple players in roster update",
            "message": '{"roster_update":{"players":[{"id":4241457},{"id":3916387},{"id":4362628}]}}',
            "expected_ids": ["4241457", "3916387", "4362628"]
        },
        {
            "description": "ESPN-specific athleteId field",
            "message": '{"pick":{"athleteId":2976499,"position":"RB","team":"NYG"}}',
            "expected_ids": ["2976499"]
        },
        {
            "description": "Message without player ID",
            "message": '{"type":"DRAFT_STATUS","round":2,"pick":15,"timeRemaining":90}',
            "expected_ids": []
        },
        {
            "description": "Invalid/non-numeric player ID",
            "message": '{"playerId":"INVALID","name":"Test Player"}',
            "expected_ids": []
        },
        {
            "description": "Player ID outside valid range",
            "message": '{"playerId":123,"name":"Invalid ID"}',
            "expected_ids": []
        }
    ]
    
    print("\n1. Testing various message formats:")
    print("-" * 40)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"  Message: {test_case['message'][:80]}...")
        
        extractions = extractor.extract_from_message(
            test_case['message'], 
            f"test_ws_{i}"
        )
        
        extracted_ids = [e.player_id for e in extractions]
        
        # Check if we got expected IDs
        expected = set(test_case['expected_ids'])
        actual = set(extracted_ids)
        
        if expected == actual:
            print(f"  [PASS] Found expected IDs: {', '.join(extracted_ids) if extracted_ids else 'None'}")
        else:
            print(f"  [FAIL] Expected {expected}, got {actual}")
        
        # Show confidence scores
        if extractions:
            for extraction in extractions:
                print(f"    - ID: {extraction.player_id}, Confidence: {extraction.confidence:.2f}")
                if extraction.context_fields:
                    print(f"      Context: {extraction.context_fields}")
    
    # Test the utility function
    print("\n2. Testing utility function:")
    print("-" * 40)
    
    test_msg = '{"draft":{"pick":{"playerId":4241457,"round":1}}}'
    quick_ids = analyze_draft_message_for_players(test_msg)
    print(f"  Message: {test_msg}")
    print(f"  Extracted IDs: {quick_ids}")
    
    # Test extraction summary
    print("\n3. Extraction Summary:")
    print("-" * 40)
    
    summary = extractor.get_extraction_summary()
    print(f"  Total extractions: {summary['total_extractions']}")
    print(f"  Unique players: {summary['unique_players']}")
    print(f"  Confidence breakdown:")
    print(f"    High: {summary['confidence_breakdown']['high_confidence']}")
    print(f"    Medium: {summary['confidence_breakdown']['medium_confidence']}")
    print(f"    Low: {summary['confidence_breakdown']['low_confidence']}")
    
    if summary['by_message_type']:
        print(f"  By message type:")
        for msg_type, count in summary['by_message_type'].items():
            print(f"    {msg_type}: {count}")
    
    # Test high confidence IDs
    high_conf_ids = extractor.get_high_confidence_ids()
    print(f"\n  High confidence IDs: {', '.join(high_conf_ids) if high_conf_ids else 'None'}")
    
    print("\n[SUCCESS] Player ID Extractor test completed!")


if __name__ == "__main__":
    test_player_id_extractor()