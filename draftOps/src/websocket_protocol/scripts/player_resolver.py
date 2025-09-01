#!/usr/bin/env python3
"""
ESPN Player Resolver

Core player resolution system that combines WebSocket player ID extraction
with ESPN API lookups to provide reliable player name resolution for
DraftOps draft monitoring.

This is the main deliverable of Sprint 0 Player ID System Reverse Engineering.
"""

import asyncio
import sqlite3
import json
import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib

from ..api.espn_api_client import ESPNApiClient, ESPNPlayer
from ..utils.player_id_extractor import PlayerIdExtractor, PlayerIdExtraction
from ..utils.cross_reference_validator import CrossReferenceValidator


@dataclass
class ResolvedPlayer:
    """A fully resolved player with all available information."""
    player_id: str
    full_name: str
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    nfl_team: str = ""
    jersey_number: Optional[int] = None
    status: str = "ACTIVE"
    
    # Resolution metadata
    resolution_method: str = "API"  # "API", "CACHE", "FALLBACK", "MANUAL"
    confidence_score: float = 1.0
    last_updated: str = ""
    resolution_source: str = "ESPN API"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_espn_player(cls, espn_player: ESPNPlayer, resolution_method: str = "API") -> 'ResolvedPlayer':
        """Create ResolvedPlayer from ESPNPlayer."""
        return cls(
            player_id=espn_player.player_id,
            full_name=espn_player.full_name,
            first_name=espn_player.first_name,
            last_name=espn_player.last_name,
            position=espn_player.position,
            nfl_team=espn_player.nfl_team,
            jersey_number=espn_player.jersey_number,
            status=espn_player.status,
            resolution_method=resolution_method,
            confidence_score=1.0,
            last_updated=datetime.now().isoformat(),
            resolution_source=espn_player.source_api
        )


class PlayerResolver:
    """
    Core player resolution system for ESPN fantasy football.
    
    Provides reliable translation from ESPN player IDs (extracted from
    WebSocket messages) to human-readable player information.
    
    Features:
    - Real-time player ID extraction from WebSocket messages
    - ESPN API integration for authoritative player data
    - SQLite caching for performance
    - Fallback mechanisms for reliability
    - Validation and confidence scoring
    """
    
    def __init__(self, cache_db_path: Optional[str] = None, season: int = 2025):
        self.season = season
        self.cache_db_path = cache_db_path or "player_cache.db"
        
        # Components
        self.api_client: Optional[ESPNApiClient] = None
        self.extractor = PlayerIdExtractor()
        self.validator = CrossReferenceValidator()
        
        # Runtime cache
        self.memory_cache: Dict[str, ResolvedPlayer] = {}
        self.cache_expiry = timedelta(hours=6)  # Memory cache expires after 6 hours
        
        # Performance tracking
        self.stats = {
            "total_resolutions": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "failed_resolutions": 0,
            "extraction_attempts": 0
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for player caching."""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    player_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    position TEXT,
                    nfl_team TEXT,
                    jersey_number INTEGER,
                    status TEXT,
                    resolution_method TEXT,
                    confidence_score REAL,
                    last_updated TEXT,
                    resolution_source TEXT,
                    data_hash TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_player_name ON players (full_name)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_position ON players (position)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_team ON players (nfl_team)
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Database initialized: {self.cache_db_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
            
    async def __aenter__(self):
        """Async context manager entry."""
        self.api_client = ESPNApiClient(season=self.season)
        await self.api_client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.api_client:
            await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
            
    def extract_player_ids_from_message(self, websocket_payload: str, 
                                      websocket_url: str = "") -> List[str]:
        """
        Extract player IDs from a WebSocket message.
        
        Args:
            websocket_payload: Raw WebSocket message payload
            websocket_url: Source WebSocket URL
            
        Returns:
            List of extracted player ID strings
        """
        self.stats["extraction_attempts"] += 1
        
        extractions = self.extractor.extract_from_message(
            websocket_payload, websocket_url
        )
        
        # Return only high-confidence IDs
        high_confidence_ids = [
            e.player_id for e in extractions 
            if e.confidence >= 0.5
        ]
        
        self.logger.debug(f"Extracted {len(high_confidence_ids)} player IDs from message")
        return high_confidence_ids
        
    async def resolve_espn_id(self, espn_id: str) -> Optional[ResolvedPlayer]:
        """
        Resolve a single ESPN player ID to player information.
        
        Args:
            espn_id: ESPN player ID string
            
        Returns:
            ResolvedPlayer object if found, None otherwise
        """
        self.stats["total_resolutions"] += 1
        
        # Check memory cache first
        if espn_id in self.memory_cache:
            cached_player = self.memory_cache[espn_id]
            if self._is_cache_valid(cached_player):
                self.stats["cache_hits"] += 1
                self.logger.debug(f"Memory cache hit for player {espn_id}")
                return cached_player
                
        # Check database cache
        db_player = self._get_from_database(espn_id)
        if db_player and self._is_cache_valid(db_player):
            self.memory_cache[espn_id] = db_player
            self.stats["cache_hits"] += 1
            self.logger.debug(f"Database cache hit for player {espn_id}")
            return db_player
            
        # Fetch from API
        if not self.api_client:
            raise RuntimeError("API client not initialized. Use async context manager.")
            
        self.stats["api_calls"] += 1
        espn_player = await self.api_client.get_player_by_id(espn_id)
        
        if espn_player:
            resolved_player = ResolvedPlayer.from_espn_player(espn_player, "API")
            
            # Cache the result
            self.memory_cache[espn_id] = resolved_player
            self._save_to_database(resolved_player)
            
            self.logger.info(f"Resolved player {espn_id}: {resolved_player.full_name}")
            return resolved_player
        else:
            # Create fallback player to ensure UI shows something meaningful
            fallback_player = self.create_fallback_player(espn_id)
            
            # Cache the fallback briefly (shorter expiry)
            self.memory_cache[espn_id] = fallback_player
            
            self.stats["failed_resolutions"] += 1
            self.logger.warning(f"Could not resolve player ID: {espn_id}, using fallback")
            return fallback_player
            
    async def batch_resolve_ids(self, espn_ids: List[str]) -> Dict[str, Optional[ResolvedPlayer]]:
        """
        Resolve multiple ESPN player IDs efficiently.
        
        Args:
            espn_ids: List of ESPN player ID strings
            
        Returns:
            Dictionary mapping player IDs to ResolvedPlayer objects (or None)
        """
        if not espn_ids:
            return {}
            
        self.logger.info(f"Batch resolving {len(espn_ids)} player IDs")
        
        results = {}
        uncached_ids = []
        
        # Check caches first
        for espn_id in espn_ids:
            # Memory cache
            if espn_id in self.memory_cache:
                cached = self.memory_cache[espn_id]
                if self._is_cache_valid(cached):
                    results[espn_id] = cached
                    self.stats["cache_hits"] += 1
                    continue
                    
            # Database cache
            db_player = self._get_from_database(espn_id)
            if db_player and self._is_cache_valid(db_player):
                results[espn_id] = db_player
                self.memory_cache[espn_id] = db_player
                self.stats["cache_hits"] += 1
                continue
                
            uncached_ids.append(espn_id)
            
        # Fetch uncached IDs from API
        if uncached_ids and self.api_client:
            self.logger.debug(f"Fetching {len(uncached_ids)} players from API")
            api_results = await self.api_client.batch_get_players(uncached_ids)
            
            for espn_id, espn_player in api_results.items():
                self.stats["api_calls"] += 1
                
                if espn_player:
                    resolved = ResolvedPlayer.from_espn_player(espn_player, "API")
                    results[espn_id] = resolved
                    self.memory_cache[espn_id] = resolved
                    self._save_to_database(resolved)
                else:
                    results[espn_id] = None
                    self.stats["failed_resolutions"] += 1
                    
        # Ensure all requested IDs are in results
        for espn_id in espn_ids:
            if espn_id not in results:
                results[espn_id] = None
                
        self.stats["total_resolutions"] += len(espn_ids)
        
        successful = len([r for r in results.values() if r is not None])
        self.logger.info(f"Batch resolution complete: {successful}/{len(espn_ids)} successful")
        
        return results
        
    def fuzzy_match_name(self, name: str, limit: int = 5) -> List[ResolvedPlayer]:
        """
        Find players by fuzzy name matching.
        
        Args:
            name: Player name to search for
            limit: Maximum number of results to return
            
        Returns:
            List of ResolvedPlayer objects matching the name
        """
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Simple LIKE search (could be enhanced with fuzzy string matching)
            search_term = f"%{name.lower()}%"
            cursor.execute('''
                SELECT * FROM players 
                WHERE LOWER(full_name) LIKE ? 
                   OR LOWER(first_name) LIKE ? 
                   OR LOWER(last_name) LIKE ?
                ORDER BY 
                    CASE WHEN LOWER(full_name) = ? THEN 1
                         WHEN LOWER(full_name) LIKE ? THEN 2
                         ELSE 3 END,
                    full_name
                LIMIT ?
            ''', (search_term, search_term, search_term, 
                  name.lower(), f"{name.lower()}%", limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                player = self._row_to_resolved_player(row)
                if player:
                    results.append(player)
                    
            self.logger.debug(f"Fuzzy search for '{name}' returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Fuzzy search failed: {e}")
            return []
            
    def get_fallback_name(self, espn_id: str) -> str:
        """
        Get a fallback display name for a player ID.
        
        Args:
            espn_id: ESPN player ID
            
        Returns:
            Fallback name string
        """
        return f"Player #{espn_id}"
    
    def create_fallback_player(self, espn_id: str) -> ResolvedPlayer:
        """
        Create a fallback ResolvedPlayer when API lookup fails.
        
        Args:
            espn_id: ESPN player ID
            
        Returns:
            ResolvedPlayer with fallback data
        """
        return ResolvedPlayer(
            player_id=espn_id,
            full_name=f"Player #{espn_id}",
            resolution_method="FALLBACK",
            confidence_score=0.1,
            last_updated=datetime.now().isoformat(),
            resolution_source="Fallback - API unavailable"
        )
        
    def _is_cache_valid(self, player: ResolvedPlayer) -> bool:
        """Check if cached player data is still valid."""
        if not player.last_updated:
            return False
            
        try:
            last_update = datetime.fromisoformat(player.last_updated)
            age = datetime.now() - last_update
            return age < self.cache_expiry
        except:
            return False
            
    def _get_from_database(self, espn_id: str) -> Optional[ResolvedPlayer]:
        """Get player from database cache."""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM players WHERE player_id = ?', (espn_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_resolved_player(row)
                
        except Exception as e:
            self.logger.error(f"Database read error: {e}")
            
        return None
        
    def _save_to_database(self, player: ResolvedPlayer):
        """Save player to database cache."""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Create data hash for change detection
            data_str = f"{player.full_name}|{player.position}|{player.nfl_team}"
            data_hash = hashlib.md5(data_str.encode()).hexdigest()
            
            cursor.execute('''
                INSERT OR REPLACE INTO players 
                (player_id, full_name, first_name, last_name, position, 
                 nfl_team, jersey_number, status, resolution_method, 
                 confidence_score, last_updated, resolution_source, data_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                player.player_id, player.full_name, player.first_name,
                player.last_name, player.position, player.nfl_team,
                player.jersey_number, player.status, player.resolution_method,
                player.confidence_score, player.last_updated,
                player.resolution_source, data_hash
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Database save error: {e}")
            
    def _row_to_resolved_player(self, row) -> Optional[ResolvedPlayer]:
        """Convert database row to ResolvedPlayer object."""
        try:
            return ResolvedPlayer(
                player_id=row[0],
                full_name=row[1],
                first_name=row[2] or "",
                last_name=row[3] or "",
                position=row[4] or "",
                nfl_team=row[5] or "",
                jersey_number=row[6],
                status=row[7] or "ACTIVE",
                resolution_method=row[8] or "UNKNOWN",
                confidence_score=row[9] or 1.0,
                last_updated=row[10] or "",
                resolution_source=row[11] or ""
            )
        except Exception as e:
            self.logger.error(f"Row conversion error: {e}")
            return None
            
    def get_stats(self) -> Dict[str, Any]:
        """Get performance and usage statistics."""
        cache_hit_rate = (
            self.stats["cache_hits"] / max(self.stats["total_resolutions"], 1)
        )
        
        success_rate = (
            (self.stats["total_resolutions"] - self.stats["failed_resolutions"]) /
            max(self.stats["total_resolutions"], 1)
        )
        
        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "success_rate": success_rate,
            "memory_cache_size": len(self.memory_cache),
            "database_path": self.cache_db_path
        }
        
    def get_cached_player_count(self) -> int:
        """Get total number of cached players in database."""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM players')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0


async def test_player_resolver():
    """Test the PlayerResolver with sample data."""
    print("Testing ESPN Player Resolver...")
    
    async with PlayerResolver(cache_db_path="test_player_cache.db") as resolver:
        # Test single ID resolution with unknown ID
        print("\nTesting single ID resolution:")
        test_ids = ["4241457", "3916387", "4362628", "9999999"]
        
        for player_id in test_ids:
            player = await resolver.resolve_espn_id(player_id)
            if player:
                print(f"  {player_id}: {player.full_name} ({player.position}, {player.nfl_team})")
            else:
                print(f"  {player_id}: Not found")
                
        # Test batch resolution
        print("\nTesting batch resolution:")
        batch_results = await resolver.batch_resolve_ids(test_ids)
        for player_id, player in batch_results.items():
            if player:
                print(f"  {player_id}: {player.full_name}")
            else:
                print(f"  {player_id}: Not found")
                
        # Test WebSocket message extraction and resolution
        print("\nTesting WebSocket message processing:")
        test_messages = [
            '{"type":"PICK_MADE","playerId":4241457,"teamId":1}',
            '{"event":"draft_pick","player":{"id":3916387,"name":"Josh Allen"}}',
            '{"data":{"selectedPlayer":{"playerId":"4362628"}}}'
        ]
        
        for i, msg in enumerate(test_messages, 1):
            print(f"  Message {i}:")
            player_ids = resolver.extract_player_ids_from_message(msg)
            if player_ids:
                players = await resolver.batch_resolve_ids(player_ids)
                for pid, player in players.items():
                    if player:
                        print(f"    Found: {player.full_name} ({player.position})")
                    else:
                        print(f"    Player ID {pid} not resolved")
            else:
                print("    No player IDs found")
                
        # Test fuzzy name search
        print("\nTesting fuzzy name search:")
        search_results = resolver.fuzzy_match_name("Josh")
        for player in search_results:
            print(f"  {player.full_name} ({player.position}, {player.nfl_team})")
            
        # Print statistics
        stats = resolver.get_stats()
        print(f"\nPerformance Statistics:")
        print(f"  Total resolutions: {stats['total_resolutions']}")
        print(f"  Cache hit rate: {stats['cache_hit_rate']:.2%}")
        print(f"  Success rate: {stats['success_rate']:.2%}")
        print(f"  Cached players: {resolver.get_cached_player_count()}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    asyncio.run(test_player_resolver())