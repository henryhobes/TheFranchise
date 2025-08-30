#!/usr/bin/env python3
"""
Test Cross-Reference Validation

Test script for the cross-reference validator that handles import paths correctly.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the websocket_protocol directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.player_id_extractor import PlayerIdExtractor, PlayerIdExtraction
from api.espn_api_client import ESPNApiClient
from utils.cross_reference_validator import CrossReferenceValidator


async def test_cross_reference_validator():
    """Test the cross-reference validator with sample data."""
    print("Testing Cross-Reference Validator...")
    
    # Create sample extractions (simulating WebSocket data)
    test_extractions = [
        PlayerIdExtraction(
            player_id="4241457",
            timestamp=datetime.now().isoformat(),
            message_type="PICK_MADE",
            websocket_url="ws://test",
            raw_message='{"type":"PICK_MADE","playerId":4241457}',
            context_fields={"name": "Najee Harris", "pos": "RB"},
            confidence=0.9
        ),
        PlayerIdExtraction(
            player_id="3916387",
            timestamp=datetime.now().isoformat(),
            message_type="PICK_MADE",
            websocket_url="ws://test",
            raw_message='{"type":"PICK_MADE","playerId":3916387}',
            context_fields={"fullName": "Josh Allen", "position": "QB"},
            confidence=0.85
        ),
        PlayerIdExtraction(
            player_id="9999999",  # Non-existent ID
            timestamp=datetime.now().isoformat(),
            message_type="PICK_MADE",
            websocket_url="ws://test",
            raw_message='{"type":"PICK_MADE","playerId":9999999}',
            context_fields={},
            confidence=0.7
        )
    ]
    
    # Validate
    async with ESPNApiClient() as api_client:
        validator = CrossReferenceValidator()
        results = await validator.validate_extractions(test_extractions, api_client)
        
    # Print results
    print(f"\nValidation Results:")
    for result in results:
        print(f"  Player ID {result.player_id}: {result.validation_status}")
        if result.api_player:
            print(f"    API: {result.api_player.full_name} ({result.api_player.position})")
        if result.discrepancies:
            print(f"    Issues: {result.discrepancies}")
        print(f"    Confidence: {result.confidence_score:.2f}")
        
    # Print summary
    summary = validator.get_validation_summary()
    print(f"\nValidation Summary:")
    print(f"  Success rate: {summary['success_rate']:.2%}")
    print(f"  Validated: {summary['validation_breakdown']['validated']}")
    print(f"  Not found: {summary['validation_breakdown']['not_found']}")
    print(f"  Mismatches: {summary['validation_breakdown']['mismatch']}")
    
    # Test with mock sample data
    print("\nTesting validation with mock samples...")
    
    # Create a simple extractor test
    extractor = PlayerIdExtractor()
    mock_messages = [
        '{"type":"PICK_MADE","playerId":4241457,"teamId":1,"pickNumber":12}',
        '{"event":"draft_pick","player":{"id":3916387,"name":"Josh Allen","pos":"QB"}}',
        '{"data":{"selectedPlayer":{"playerId":"4362628","fullName":"Justin Jefferson"}}}'
    ]
    
    all_extractions = []
    for i, msg in enumerate(mock_messages):
        extractions = extractor.extract_from_message(msg, f"mock_ws_{i}")
        all_extractions.extend(extractions)
        
    print(f"Extracted {len(all_extractions)} player IDs from mock messages")
    
    # Validate mock extractions
    validator2 = CrossReferenceValidator()
    mock_results = await validator2.validate_extractions(all_extractions, api_client)
    
    print(f"Mock validation results:")
    for result in mock_results:
        status_marker = "OK" if result.validation_status == "VALIDATED" else "FAIL"
        print(f"  {status_marker} {result.player_id}: {result.validation_status}")
        if result.api_player:
            print(f"    {result.api_player.full_name} ({result.api_player.position}, {result.api_player.nfl_team})")
            
    mock_summary = validator2.get_validation_summary()
    print(f"\nMock Validation Summary:")
    print(f"  Total validated players: {mock_summary['total_validated_players']}")
    print(f"  Success rate: {mock_summary['success_rate']:.2%}")


if __name__ == "__main__":
    asyncio.run(test_cross_reference_validator())