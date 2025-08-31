#!/usr/bin/env python3
"""
Test ESPN Draft Text Protocol Parsing
Tests the new text protocol parsing with real data captured from live test.
"""

import asyncio
from ..utils.player_id_extractor import PlayerIdExtractor
from ..scripts.player_resolver import PlayerResolver


def test_espn_text_protocol():
    """Test the ESPN text protocol parsing with real captured data."""
    print("Testing ESPN Draft Text Protocol Parsing")
    print("=" * 60)
    
    # Real messages captured from live test
    test_messages = [
        "SELECTED 1 4430807 2 {F00CC66D-9B1C-4FC1-9C18-5ACF60B83CCC}",  # Pick 1, RB
        "SELECTED 2 4362628 4 {A59C5B68-2A04-4309-857A-9A57A15AFE2B}",  # Pick 2, WR (Justin Jefferson!)
        "SELECTED 3 3929630 2 {2D76B249-034E-47A7-B6B2-49034E57A704}",  # Pick 3, RB  
        "SELECTED 4 3117251 2 {6CEA75BD-50DB-48B5-A8A6-503154C8FF55}",  # Pick 4, RB
        "SELECTED 5 4241389 4 {6D2794A0-5179-4927-ABB0-51C3A7BBEB94}",  # Pick 5, WR
        "SELECTED 6 4262921 4 {4DDD546C-40D8-11D2-9B2C-00A0C9862BBB}",  # Pick 6, WR
        "SELECTED 7 4890973 2 {3F54F436-FF9F-44B7-94F4-36FF9F54B7FA}",  # Pick 7, RB
        "SELECTED 8 4429795 2 {9B093AF3-D046-4FAE-893A-F3D046DFAE99}",  # Pick 8, RB
        "SELECTED 9 4595348 4 {80F06FE2-9BBF-46F7-A07F-4F2D92764922}",  # Pick 9, WR
        "SELECTED 10 4426515 4",  # Pick 10, WR (no team GUID)
        "AUTODRAFT 5 false",  # Non-player message
        "AUTODRAFT 7 true",   # Non-player message
    ]
    
    extractor = PlayerIdExtractor()
    
    print("1. Testing ESPN Text Protocol Detection:")
    print("-" * 40)
    
    all_extractions = []
    for i, message in enumerate(test_messages, 1):
        print(f"\nMessage {i}: {message}")
        
        extractions = extractor.extract_from_message(
            message, 
            "wss://fantasydraft.espn.com/test"
        )
        
        if extractions:
            for extraction in extractions:
                print(f"  [FOUND] Player ID: {extraction.player_id}")
                print(f"     Position Code: {extraction.context_fields.get('position_code', 'N/A')}")
                print(f"     Pick #: {extraction.context_fields.get('pick_number', 'N/A')}")
                print(f"     Confidence: {extraction.confidence:.2f}")
                all_extractions.append(extraction)
        else:
            if message.startswith("SELECTED"):
                print(f"  [FAILED] Failed to extract player ID")
            else:
                print(f"  [OK] No player ID expected (correct)")
    
    print(f"\n2. Extraction Summary:")
    print("-" * 40)
    summary = extractor.get_extraction_summary()
    print(f"Total extractions: {summary['total_extractions']}")
    print(f"Unique player IDs: {summary['unique_players']}")
    print(f"High confidence: {summary['confidence_breakdown']['high_confidence']}")
    
    expected_player_ids = {
        "4430807", "4362628", "3929630", "3117251", "4241389",
        "4262921", "4890973", "4429795", "4595348", "4426515"
    }
    
    extracted_ids = set(summary['unique_player_ids'])
    
    print(f"\n3. Validation Against Expected Data:")
    print("-" * 40)
    print(f"Expected IDs: {len(expected_player_ids)}")
    print(f"Extracted IDs: {len(extracted_ids)}")
    
    missing = expected_player_ids - extracted_ids
    extra = extracted_ids - expected_player_ids
    
    if not missing and not extra:
        print("[SUCCESS] All expected player IDs extracted correctly!")
    else:
        if missing:
            print(f"[MISSING] Missing IDs: {missing}")
        if extra:
            print(f"[EXTRA] Extra IDs: {extra}")
    
    return len(extracted_ids) == len(expected_player_ids) and not missing and not extra


async def test_integration_with_resolver():
    """Test integration with PlayerResolver using real captured IDs."""
    print("\n\n4. Testing Integration with PlayerResolver:")
    print("-" * 40)
    
    test_message = "SELECTED 2 4362628 4 {A59C5B68-2A04-4309-857A-9A57A15AFE2B}"
    
    async with PlayerResolver(cache_db_path="test_espn_protocol.db") as resolver:
        # Test extraction
        player_ids = resolver.extract_player_ids_from_message(test_message)
        print(f"Extracted player IDs: {player_ids}")
        
        if player_ids:
            # Test resolution  
            players = await resolver.batch_resolve_ids(player_ids)
            for pid, player in players.items():
                if player:
                    print(f"[RESOLVED] {pid} -> {player.full_name} ({player.position})")
                else:
                    print(f"[FAILED] Failed to resolve: {pid}")
        
        # Test stats
        stats = resolver.get_stats()
        print(f"\nResolver stats:")
        print(f"  Total resolutions: {stats['total_resolutions']}")
        print(f"  Success rate: {stats['success_rate']:.2%}")


if __name__ == "__main__":
    success = test_espn_text_protocol()
    
    if success:
        print("\n[PASSED] ESPN Text Protocol Test: PASSED")
        print("Ready for live testing!")
        
        # Test integration
        asyncio.run(test_integration_with_resolver())
    else:
        print("\n[FAILED] ESPN Text Protocol Test: FAILED")
        print("Fixes needed before live testing.")