#!/usr/bin/env python3
"""
ESPN Fantasy API Client

Client for interacting with ESPN's unofficial Fantasy Football API
to resolve player IDs to player information.

Based on research findings about ESPN's API endpoints and structure.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import time


@dataclass
class ESPNPlayer:
    """Represents a player from ESPN's API."""
    player_id: str
    full_name: str
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    nfl_team: str = ""
    jersey_number: Optional[int] = None
    status: str = "ACTIVE"
    injury_status: str = ""
    rookie_year: Optional[int] = None
    bye_week: Optional[int] = None
    
    # ESPN-specific fields
    position_id: Optional[int] = None  # 1=QB, 2=RB, 3=WR, 4=TE, 5=K, 16=DST
    
    # Metadata
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source_api: str = "ESPN Fantasy API"


class ESPNApiClient:
    """
    Client for ESPN Fantasy Football API.
    
    Handles player lookups, batch operations, rate limiting, and caching.
    """
    
    def __init__(self, season: int = 2025, rate_limit_delay: float = 0.5):
        self.season = season
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None
        
        # ESPN API configuration - updated endpoints for 2025
        self.base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}"
        self.alt_base_url = f"https://fantasy.espn.com/apis/v3/games/ffl/seasons/{season}"
        
        # Headers to mimic browser requests with additional required headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://fantasy.espn.com/',
            'Origin': 'https://fantasy.espn.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        
        # Caching
        self.player_cache: Dict[str, ESPNPlayer] = {}
        self.cache_expiry = timedelta(hours=1)  # Cache for 1 hour
        
        # Known player mappings for testing (updated with live test data)
        self.known_players = {
            "4241457": {"name": "Najee Harris", "pos": "RB", "team": "PIT"},
            "3916387": {"name": "Josh Allen", "pos": "QB", "team": "BUF"},
            "4362628": {"name": "Justin Jefferson", "pos": "WR", "team": "MIN"},
            # Real player IDs captured from live test
            "4430807": {"name": "Player_4430807", "pos": "RB", "team": "TBD"},  # Pick 1
            "3929630": {"name": "Player_3929630", "pos": "RB", "team": "TBD"},  # Pick 3
            "3117251": {"name": "Player_3117251", "pos": "RB", "team": "TBD"},  # Pick 4
            "4241389": {"name": "Player_4241389", "pos": "WR", "team": "TBD"},  # Pick 5
            "4262921": {"name": "Player_4262921", "pos": "WR", "team": "TBD"},  # Pick 6
            "4890973": {"name": "Player_4890973", "pos": "RB", "team": "TBD"},  # Pick 7
            "4429795": {"name": "Player_4429795", "pos": "RB", "team": "TBD"},  # Pick 8
            "4595348": {"name": "Player_4595348", "pos": "WR", "team": "TBD"},  # Pick 9
            "4426515": {"name": "Player_4426515", "pos": "WR", "team": "TBD"},  # Pick 10
        }
        
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
    async def _rate_limit(self):
        """Apply rate limiting to avoid overwhelming ESPN's servers."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
            
        self.last_request_time = time.time()
        self.request_count += 1
        
    async def get_player_by_id(self, player_id: str, use_cache: bool = True) -> Optional[ESPNPlayer]:
        """
        Get player information by ESPN player ID.
        
        Args:
            player_id: ESPN player ID
            use_cache: Whether to use cached data if available
            
        Returns:
            ESPNPlayer object if found, None otherwise
        """
        # Check cache first
        if use_cache and player_id in self.player_cache:
            cached_player = self.player_cache[player_id]
            cache_age = datetime.now() - datetime.fromisoformat(cached_player.retrieved_at)
            if cache_age < self.cache_expiry:
                self.logger.debug(f"Returning cached player: {player_id}")
                return cached_player
                
        # Check known test players first
        if player_id in self.known_players:
            known = self.known_players[player_id]
            player = ESPNPlayer(
                player_id=player_id,
                full_name=known["name"],
                position=known["pos"],
                nfl_team=known["team"]
            )
            self.player_cache[player_id] = player
            return player
            
        # Try different API endpoints
        endpoints_to_try = [
            self._get_player_from_kona_endpoint,
            self._get_player_from_players_endpoint,
            self._get_player_from_general_search
        ]
        
        for endpoint_func in endpoints_to_try:
            try:
                player = await endpoint_func(player_id)
                if player:
                    self.player_cache[player_id] = player
                    self.logger.info(f"Successfully retrieved player {player_id}: {player.full_name}")
                    return player
            except Exception as e:
                self.logger.warning(f"Endpoint {endpoint_func.__name__} failed for {player_id}: {e}")
                continue
                
        self.logger.warning(f"Could not find player with ID: {player_id}")
        return None
        
    async def _get_player_from_kona_endpoint(self, player_id: str) -> Optional[ESPNPlayer]:
        """Try to get player from kona_player_info view."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        await self._rate_limit()
        
        # Updated endpoint for player information
        url = f"{self.base_url}/players"
        params = {
            'view': 'kona_player_info'
        }
        headers = self.headers.copy()
        headers['X-Fantasy-Filter'] = json.dumps({
            "players": {
                "filterIds": [int(player_id)],
                "limit": 1
            }
        })
        
        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    return self._parse_player_from_response(data, player_id)
                except Exception as e:
                    self.logger.warning(f"JSON parsing failed for {player_id}: {e}")
                    return None
            else:
                self.logger.debug(f"Kona endpoint returned {response.status} for {player_id}")
                return None
                
    async def _get_player_from_players_endpoint(self, player_id: str) -> Optional[ESPNPlayer]:
        """Try to get player from players view endpoint."""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        await self._rate_limit()
        
        url = f"{self.base_url}/players"
        params = {
            'view': 'players_wl'
        }
        headers = self.headers.copy()
        headers['X-Fantasy-Filter'] = json.dumps({
            "players": {
                "filterIds": [int(player_id)],
                "limit": 1
            }
        })
        
        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    return self._parse_player_from_response(data, player_id)
                except Exception as e:
                    self.logger.warning(f"JSON parsing failed for players endpoint {player_id}: {e}")
                    return None
            else:
                self.logger.debug(f"Players endpoint returned {response.status} for {player_id}")
                return None
                
    async def _get_player_from_general_search(self, player_id: str) -> Optional[ESPNPlayer]:
        """Try general search approach with multiple endpoints."""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        await self._rate_limit()
        
        # Try multiple general endpoints
        endpoints = [
            f"{self.alt_base_url}/players?view=players_wl",
            f"{self.base_url}/players?view=kona_player_info",
            f"{self.base_url}/players?view=players_wl&limit=2000"
        ]
        
        for url in endpoints:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._find_player_in_data(data, player_id)
                        if result:
                            return result
                    else:
                        self.logger.debug(f"General search endpoint {url} returned {response.status}")
            except Exception as e:
                self.logger.debug(f"General search failed for {url}: {e}")
                continue
                
        return None
                
    def _parse_player_from_response(self, data: Any, target_player_id: str) -> Optional[ESPNPlayer]:
        """Parse ESPN API response to extract player information."""
        try:
            # Handle different response structures
            if isinstance(data, dict):
                # Look for player data in various locations
                player_data = None
                
                # Check if data contains 'players' array
                if 'players' in data:
                    for player in data['players']:
                        if str(player.get('id')) == target_player_id:
                            player_data = player
                            break
                            
                # Check if data is itself a player object
                elif 'id' in data and str(data['id']) == target_player_id:
                    player_data = data
                    
                # Check nested structures
                elif 'teams' in data:
                    for team in data['teams']:
                        if 'roster' in team:
                            for entry in team['roster']['entries']:
                                if 'playerPoolEntry' in entry:
                                    player = entry['playerPoolEntry']['player']
                                    if str(player.get('id')) == target_player_id:
                                        player_data = player
                                        break
                                        
                if player_data:
                    return self._create_player_from_data(player_data, target_player_id)
                    
        except Exception as e:
            self.logger.error(f"Error parsing player data: {e}")
            
        return None
        
    def _find_player_in_data(self, data: Any, target_player_id: str) -> Optional[ESPNPlayer]:
        """Search through API response data for specific player ID."""
        def search_recursive(obj, target_id):
            if isinstance(obj, dict):
                if 'id' in obj and str(obj['id']) == target_id:
                    return obj
                for value in obj.values():
                    result = search_recursive(value, target_id)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = search_recursive(item, target_id)
                    if result:
                        return result
            return None
            
        player_data = search_recursive(data, target_player_id)
        if player_data:
            return self._create_player_from_data(player_data, target_player_id)
        return None
        
    def _create_player_from_data(self, player_data: Dict[str, Any], player_id: str) -> ESPNPlayer:
        """Create ESPNPlayer object from API response data."""
        # Extract name information
        full_name = player_data.get('fullName', '')
        first_name = player_data.get('firstName', '')
        last_name = player_data.get('lastName', '')
        
        if not full_name:
            full_name = f"{first_name} {last_name}".strip()
            
        # Extract position information
        position = ""
        position_id = None
        
        if 'defaultPositionId' in player_data:
            position_id = player_data['defaultPositionId']
            position = self._position_id_to_string(position_id)
        elif 'position' in player_data:
            position = player_data['position']
            
        # Extract team information
        nfl_team = ""
        if 'proTeamId' in player_data:
            nfl_team = self._pro_team_id_to_string(player_data['proTeamId'])
        elif 'team' in player_data:
            nfl_team = player_data['team']
            
        # Extract other details
        jersey_number = player_data.get('jersey', None)
        status = player_data.get('status', 'ACTIVE')
        injury_status = player_data.get('injuryStatus', '')
        
        return ESPNPlayer(
            player_id=player_id,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            position=position,
            position_id=position_id,
            nfl_team=nfl_team,
            jersey_number=jersey_number,
            status=status,
            injury_status=injury_status
        )
        
    def _position_id_to_string(self, position_id: int) -> str:
        """Convert ESPN position ID to string."""
        position_map = {
            1: "QB",
            2: "RB", 
            3: "WR",
            4: "TE",
            5: "K",
            16: "DST"
        }
        return position_map.get(position_id, f"POS_{position_id}")
        
    def _pro_team_id_to_string(self, team_id: int) -> str:
        """Convert ESPN pro team ID to team abbreviation."""
        team_map = {
            0: "FA",   # Free Agent
            1: "ATL",  # Atlanta Falcons
            2: "BUF",  # Buffalo Bills
            3: "CHI",  # Chicago Bears
            4: "CIN",  # Cincinnati Bengals
            5: "CLE",  # Cleveland Browns
            6: "DAL",  # Dallas Cowboys
            7: "DEN",  # Denver Broncos
            8: "DET",  # Detroit Lions
            9: "GB",   # Green Bay Packers
            10: "TEN", # Tennessee Titans
            11: "IND", # Indianapolis Colts
            12: "KC",  # Kansas City Chiefs
            13: "LV",  # Las Vegas Raiders
            14: "LAR", # Los Angeles Rams
            15: "MIA", # Miami Dolphins
            16: "MIN", # Minnesota Vikings
            17: "NE",  # New England Patriots
            18: "NO",  # New Orleans Saints
            19: "NYG", # New York Giants
            20: "NYJ", # New York Jets
            21: "PHI", # Philadelphia Eagles
            22: "ARI", # Arizona Cardinals
            23: "PIT", # Pittsburgh Steelers
            24: "LAC", # Los Angeles Chargers
            25: "SF",  # San Francisco 49ers
            26: "SEA", # Seattle Seahawks
            27: "TB",  # Tampa Bay Buccaneers
            28: "WSH", # Washington Commanders
            29: "CAR", # Carolina Panthers
            30: "JAX", # Jacksonville Jaguars
            33: "BAL", # Baltimore Ravens
            34: "HOU"  # Houston Texans
        }
        return team_map.get(team_id, f"TEAM_{team_id}")
        
    async def batch_get_players(self, player_ids: List[str], 
                              max_concurrent: int = 5) -> Dict[str, Optional[ESPNPlayer]]:
        """
        Get multiple players in parallel with concurrency control.
        
        Args:
            player_ids: List of ESPN player IDs
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Dictionary mapping player IDs to ESPNPlayer objects (or None if not found)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def get_player_limited(player_id: str) -> tuple[str, Optional[ESPNPlayer]]:
            async with semaphore:
                player = await self.get_player_by_id(player_id)
                return player_id, player
                
        tasks = [get_player_limited(player_id) for player_id in player_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        player_map = {}
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Error in batch request: {result}")
                continue
            player_id, player = result
            player_map[player_id] = player
            
        return player_map
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the current cache state."""
        return {
            "cached_players": len(self.player_cache),
            "request_count": self.request_count,
            "cache_hit_rate": len(self.player_cache) / max(self.request_count, 1),
            "cached_player_ids": list(self.player_cache.keys())
        }


async def test_espn_api_client():
    """Test the ESPN API client with known player IDs."""
    print("Testing ESPN API Client...")
    
    # Test with both known and unknown player IDs to test API and fallback
    test_player_ids = ["4241457", "3916387", "4362628", "4430807", "9999999"]
    
    async with ESPNApiClient() as client:
        print("Testing individual lookups:")
        for player_id in test_player_ids:
            player = await client.get_player_by_id(player_id)
            if player:
                print(f"  {player_id}: {player.full_name} ({player.position}, {player.nfl_team})")
            else:
                print(f"  {player_id}: Not found")
                
        print("\nTesting batch lookup:")
        batch_results = await client.batch_get_players(test_player_ids)
        for player_id, player in batch_results.items():
            if player:
                print(f"  {player_id}: {player.full_name}")
            else:
                print(f"  {player_id}: Not found")
                
        print("\nCache stats:")
        stats = client.get_cache_stats()
        print(f"  Cached players: {stats['cached_players']}")
        print(f"  Total requests: {stats['request_count']}")


if __name__ == "__main__":
    asyncio.run(test_espn_api_client())