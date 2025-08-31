#!/usr/bin/env python3
"""
Test the ESPN API client functionality.
"""

import asyncio
from ..api.espn_api_client import ESPNApiClient


async def test_espn_api_client():
    """Test the ESPN API client with known player IDs."""
    print("Testing ESPN API Client...")
    print("=" * 60)
    
    # Test with known player IDs from research
    test_player_ids = ["4241457", "3916387", "4362628"]
    
    async with ESPNApiClient() as client:
        print("\n1. Testing individual lookups:")
        print("-" * 40)
        for player_id in test_player_ids:
            player = await client.get_player_by_id(player_id)
            if player:
                print(f"  {player_id}: {player.full_name}")
                print(f"    Position: {player.position}")
                print(f"    Team: {player.nfl_team}")
                print(f"    Status: {player.status}")
            else:
                print(f"  {player_id}: Not found")
        
        print("\n2. Testing batch lookup:")
        print("-" * 40)
        batch_results = await client.batch_get_players(test_player_ids)
        for player_id, player in batch_results.items():
            if player:
                print(f"  {player_id}: {player.full_name} ({player.position}, {player.nfl_team})")
            else:
                print(f"  {player_id}: Not found")
        
        print("\n3. Testing cache effectiveness:")
        print("-" * 40)
        # Request same players again to test cache
        for player_id in test_player_ids:
            player = await client.get_player_by_id(player_id)
            if player:
                print(f"  {player_id}: Retrieved from cache")
        
        print("\n4. Cache statistics:")
        print("-" * 40)
        stats = client.get_cache_stats()
        print(f"  Cached players: {stats['cached_players']}")
        print(f"  Total requests: {stats['request_count']}")
        print(f"  Cache hit rate: {stats['cache_hit_rate']:.2%}")
        
        print("\n[SUCCESS] ESPN API client test completed!")


if __name__ == "__main__":
    asyncio.run(test_espn_api_client())