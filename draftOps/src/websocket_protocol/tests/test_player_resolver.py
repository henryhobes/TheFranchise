#!/usr/bin/env python3
"""
Test the Player Resolver functionality.
"""

import asyncio
from pathlib import Path
from ..scripts.player_resolver import PlayerResolver


async def test_player_resolver():
    """Test the PlayerResolver with sample data."""
    print("Testing ESPN Player Resolver...")
    print("=" * 60)
    
    # Use a test database in the tests folder
    test_db = Path(__file__).parent / "test_player_resolver.db"
    
    async with PlayerResolver(cache_db_path=str(test_db)) as resolver:
        # Test single ID resolution
        print("\n1. Testing single ID resolution:")
        print("-" * 40)
        test_ids = ["4241457", "3916387", "4362628"]
        
        for player_id in test_ids:
            player = await resolver.resolve_espn_id(player_id)
            if player:
                print(f"  {player_id}: {player.full_name}")
                print(f"    Position: {player.position}")
                print(f"    Team: {player.nfl_team}")
                print(f"    Resolution: {player.resolution_method}")
                print(f"    Confidence: {player.confidence_score}")
            else:
                print(f"  {player_id}: Not found")
        
        # Test batch resolution
        print("\n2. Testing batch resolution:")
        print("-" * 40)
        batch_results = await resolver.batch_resolve_ids(test_ids)
        for player_id, player in batch_results.items():
            if player:
                print(f"  {player_id}: {player.full_name} ({player.position}, {player.nfl_team})")
            else:
                print(f"  {player_id}: Not found")
        
        # Test WebSocket message extraction and resolution
        print("\n3. Testing WebSocket message processing:")
        print("-" * 40)
        test_messages = [
            '{"type":"PICK_MADE","playerId":4241457,"teamId":1}',
            '{"event":"draft_pick","player":{"id":3916387,"name":"Josh Allen"}}',
            '{"data":{"selectedPlayer":{"playerId":"4362628"}}}'
        ]
        
        for i, msg in enumerate(test_messages, 1):
            print(f"\nMessage {i}: {msg[:50]}...")
            player_ids = resolver.extract_player_ids_from_message(msg)
            if player_ids:
                print(f"  Extracted IDs: {player_ids}")
                players = await resolver.batch_resolve_ids(player_ids)
                for pid, player in players.items():
                    if player:
                        print(f"  -> {player.full_name} ({player.position})")
                    else:
                        print(f"  -> Player ID {pid} not resolved")
            else:
                print("  No player IDs found")
        
        # Test fuzzy name search
        print("\n4. Testing fuzzy name search:")
        print("-" * 40)
        test_names = ["Josh", "Harris", "Jefferson"]
        
        for name in test_names:
            print(f"\nSearching for '{name}':")
            search_results = resolver.fuzzy_match_name(name, limit=3)
            if search_results:
                for player in search_results:
                    print(f"  - {player.full_name} ({player.position}, {player.nfl_team})")
            else:
                print(f"  No results found")
        
        # Test fallback name generation
        print("\n5. Testing fallback name generation:")
        print("-" * 40)
        unknown_id = "9999999"
        fallback_name = resolver.get_fallback_name(unknown_id)
        print(f"  Fallback for ID {unknown_id}: {fallback_name}")
        
        # Print statistics
        stats = resolver.get_stats()
        print("\n6. Performance Statistics:")
        print("-" * 40)
        print(f"  Total resolutions: {stats['total_resolutions']}")
        print(f"  Cache hits: {stats['cache_hits']}")
        print(f"  API calls: {stats['api_calls']}")
        print(f"  Failed resolutions: {stats['failed_resolutions']}")
        print(f"  Cache hit rate: {stats['cache_hit_rate']:.2%}")
        print(f"  Success rate: {stats['success_rate']:.2%}")
        print(f"  Memory cache size: {stats['memory_cache_size']}")
        print(f"  Database cache size: {resolver.get_cached_player_count()}")
        
        print("\n[SUCCESS] Player Resolver test completed!")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    asyncio.run(test_player_resolver())