#!/usr/bin/env python3
"""
Draft State Integration Layer

Connects the draft state management system with existing WebSocket monitoring
and player resolution infrastructure from Sprint 0.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from ..monitor.espn_draft_monitor import ESPNDraftMonitor
from ..scripts.player_resolver import PlayerResolver, ResolvedPlayer
from .draft_state import DraftState
from .event_processor import DraftEventProcessor
from .state_handlers import StateUpdateHandlers


class DraftStateManager:
    """
    Integrated draft state management system.
    
    Combines Sprint 0's WebSocket monitoring and player resolution with
    Sprint 1's real-time state tracking to provide a complete solution.
    
    Features:
    - WebSocket message processing with sub-200ms state updates
    - Automatic player ID resolution to names
    - State consistency validation and recovery
    - Comprehensive logging and monitoring
    - Event callbacks for external systems
    """
    
    def __init__(self, league_id: str, team_id: str, 
                 team_count: int = 12, rounds: int = 16,
                 player_cache_db: Optional[str] = None):
        """
        Initialize draft state manager.
        
        Args:
            league_id: ESPN league ID
            team_id: User's team ID
            team_count: Number of teams in draft
            rounds: Number of draft rounds
            player_cache_db: Path to player resolution cache database
        """
        self.league_id = league_id
        self.team_id = team_id
        
        # Core components
        self.draft_state = DraftState(league_id, team_id, team_count, rounds)
        self.event_processor = DraftEventProcessor(self.draft_state)
        self.state_handlers = StateUpdateHandlers(self.draft_state)
        
        # External integrations
        self.monitor: Optional[ESPNDraftMonitor] = None
        self.player_resolver: Optional[PlayerResolver] = None
        self.player_cache_db = player_cache_db or f"draft_cache_{league_id}.db"
        
        # Resolved player caches
        self._player_names: Dict[str, str] = {}
        self._player_positions: Dict[str, str] = {}
        self._resolution_queue: List[str] = []
        
        # Event callbacks
        self.on_pick_processed: Optional[Callable] = None
        self.on_state_updated: Optional[Callable] = None
        self.on_draft_completed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Performance tracking
        self.performance_stats = {
            'messages_processed': 0,
            'state_updates': 0,
            'player_resolutions': 0,
            'errors': 0,
            'avg_processing_time_ms': 0.0,
            'last_message_time': None
        }
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized DraftStateManager for league {league_id}")
        
    async def initialize(self) -> bool:
        """
        Initialize all components and connections.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize player resolver with proper async context management
            self.player_resolver = PlayerResolver(cache_db_path=self.player_cache_db)
            try:
                await self.player_resolver.__aenter__()
            except Exception as e:
                self.logger.error(f"Failed to initialize player resolver: {e}")
                self.player_resolver = None
                raise
            
            # Initialize monitor
            self.monitor = ESPNDraftMonitor(headless=True)
            await self.monitor.start_browser()
            
            # Set up event processor callbacks
            self._setup_event_callbacks()
            
            # Set up position resolver for better roster management
            self.event_processor.set_position_resolver(self._resolve_player_position)
            
            self.logger.info("DraftStateManager initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DraftStateManager: {e}")
            return False
            
    async def connect_to_draft(self, draft_url: str) -> bool:
        """
        Connect to ESPN draft room and start monitoring.
        
        Args:
            draft_url: ESPN draft room URL
            
        Returns:
            bool: True if connected successfully
        """
        if not self.monitor:
            raise RuntimeError("Manager not initialized. Call initialize() first.")
            
        try:
            # Connect to draft
            success = await self.monitor.connect_to_draft(draft_url)
            if not success:
                return False
                
            # Set up WebSocket message handler
            self.monitor.on_message_received = self._handle_websocket_message
            
            # Wait for WebSocket connections
            websocket_ready = await self.monitor.wait_for_websockets(timeout=30)
            if not websocket_ready:
                self.logger.error("No WebSocket connections established")
                return False
                
            self.logger.info(f"Successfully connected to draft: {draft_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to draft: {e}")
            return False
            
    async def initialize_player_pool(self, player_ids: Optional[List[str]] = None) -> bool:
        """
        Initialize available player pool.
        
        Args:
            player_ids: Optional list of player IDs. If None, will use ESPN API
            
        Returns:
            bool: True if initialized successfully
        """
        try:
            if player_ids:
                self.draft_state.initialize_player_pool(player_ids)
            else:
                # TODO: Fetch player pool from ESPN API
                # For now, just initialize empty - players will be added as discovered
                self.draft_state.initialize_player_pool([])
                
            self.logger.info("Player pool initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize player pool: {e}")
            return False
            
    def set_draft_order(self, team_order: List[str]) -> None:
        """
        Set draft order for snake draft calculations.
        
        Args:
            team_order: List of team IDs in draft order
        """
        self.draft_state.set_draft_order(team_order)
        self.logger.info(f"Draft order set: {team_order}")
        
    def _setup_event_callbacks(self):
        """Set up callbacks for event processor."""
        self.event_processor.on_pick_made = self._handle_pick_made
        self.event_processor.on_team_selecting = self._handle_team_selecting
        self.event_processor.on_clock_update = self._handle_clock_update
        
    async def _handle_websocket_message(self, direction: str, websocket, payload: str):
        """
        Handle incoming WebSocket messages.
        
        Args:
            direction: 'sent' or 'received'
            websocket: WebSocket instance
            payload: Message payload
        """
        if direction != 'received':
            return
            
        start_time = datetime.now()
        self.performance_stats['messages_processed'] += 1
        self.performance_stats['last_message_time'] = start_time.isoformat()
        
        try:
            # Process message through event processor
            success = self.event_processor.process_websocket_message(payload, websocket.url)
            
            if success:
                self.performance_stats['state_updates'] += 1
                
                # Trigger state updated callback
                if self.on_state_updated:
                    self.on_state_updated(self.get_state_summary())
                    
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_avg_processing_time(processing_time)
            
        except Exception as e:
            self.performance_stats['errors'] += 1
            self.logger.error(f"Error handling WebSocket message: {e}")
            
            if self.on_error:
                self.on_error(f"WebSocket message processing error: {e}")
                
    def _handle_pick_made(self, pick_data: Dict[str, Any]):
        """Handle pick made event."""
        player_id = pick_data['player_id']
        
        # Queue player for name resolution
        if player_id not in self._player_names:
            self._resolution_queue.append(player_id)
            
        # Trigger callback
        if self.on_pick_processed:
            self.on_pick_processed({
                **pick_data,
                'player_name': self._player_names.get(player_id, f"Player #{player_id}")
            })
            
    def _handle_team_selecting(self, selection_data: Dict[str, Any]):
        """Handle team selecting event."""
        self.logger.info(f"Team {selection_data['team_id']} now selecting (pick {selection_data['pick_number']})")
        
    def _handle_clock_update(self, clock_data: Dict[str, Any]):
        """Handle clock update event."""
        time_remaining = clock_data['time_remaining']
        if time_remaining <= 5.0 and time_remaining > 0:
            self.logger.warning(f"Pick clock running low: {time_remaining:.1f}s remaining")
            
    def _resolve_player_position(self, player_id: str) -> str:
        """
        Resolve player position for roster placement (synchronous).
        
        This method needs to be synchronous as it's called during message processing.
        It checks the position cache first, then queues for async resolution.
        
        Args:
            player_id: ESPN player ID
            
        Returns:
            Position string (QB, RB, WR, TE, K, DST, FLEX, BENCH)
        """
        # Check position cache first for fast synchronous lookup
        if player_id in self._player_positions:
            return self._player_positions[player_id]
            
        # Queue player for async resolution if not already queued
        if player_id not in self._resolution_queue:
            self._resolution_queue.append(player_id)
            
        # Return default position to avoid blocking message processing
        # Position will be updated after async resolution completes
        return "BENCH"
        
    async def resolve_queued_players(self) -> int:
        """
        Resolve player names and positions from queue.
        
        Returns:
            Number of players resolved
        """
        if not self._resolution_queue or not self.player_resolver:
            return 0
            
        try:
            # Batch resolve queued players
            player_ids = self._resolution_queue.copy()
            self._resolution_queue.clear()
            
            resolved_players = await self.player_resolver.batch_resolve_ids(player_ids)
            
            # Cache resolved names and positions
            resolved_count = 0
            for player_id, player in resolved_players.items():
                if player:
                    self._player_names[player_id] = player.full_name
                    self._player_positions[player_id] = player.position or "BENCH"
                    resolved_count += 1
                    
            self.performance_stats['player_resolutions'] += resolved_count
            self.logger.debug(f"Resolved {resolved_count} player names and positions")
            return resolved_count
            
        except Exception as e:
            self.logger.error(f"Error resolving player names: {e}")
            return 0
            
    def get_player_name(self, player_id: str) -> str:
        """
        Get player name by ID.
        
        Args:
            player_id: ESPN player ID
            
        Returns:
            Player name or fallback
        """
        return self._player_names.get(player_id, f"Player #{player_id}")
        
    def get_enriched_roster(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get roster with player names resolved.
        
        Returns:
            Dictionary of positions to player info
        """
        enriched = {}
        for position, player_ids in self.draft_state.my_roster.items():
            enriched[position] = [
                {
                    'player_id': pid,
                    'player_name': self.get_player_name(pid)
                }
                for pid in player_ids
            ]
        return enriched
        
    def validate_current_state(self) -> Dict[str, Any]:
        """
        Validate current draft state.
        
        Returns:
            Validation results with details
        """
        validation = self.state_handlers.validate_draft_consistency()
        
        return {
            'is_valid': validation.is_valid,
            'errors': validation.errors,
            'warnings': validation.warnings,
            'suggestions': validation.suggestions,
            'timestamp': datetime.now().isoformat()
        }
        
    def get_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state summary."""
        base_summary = self.state_handlers.get_state_summary()
        
        return {
            **base_summary,
            'performance': self.performance_stats,
            'resolved_players': len(self._player_names),
            'resolution_queue_size': len(self._resolution_queue),
            'websocket_connections': len(self.monitor.websockets) if self.monitor else 0
        }
        
    def _update_avg_processing_time(self, processing_time_ms: float):
        """Update average processing time."""
        current_avg = self.performance_stats['avg_processing_time_ms']
        total_messages = self.performance_stats['messages_processed']
        
        if total_messages == 1:
            self.performance_stats['avg_processing_time_ms'] = processing_time_ms
        else:
            # Running average
            self.performance_stats['avg_processing_time_ms'] = (
                (current_avg * (total_messages - 1) + processing_time_ms) / total_messages
            )
            
    async def monitor_draft(self, duration_seconds: Optional[int] = None):
        """
        Monitor draft for specified duration.
        
        Args:
            duration_seconds: Duration to monitor, or None for indefinite
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"Starting draft monitoring (duration: {duration_seconds or 'indefinite'}s)")
            
            if duration_seconds:
                await asyncio.sleep(duration_seconds)
            else:
                # Monitor indefinitely - wait for draft completion or manual stop
                while self.draft_state.draft_status.value != "COMPLETED":
                    await asyncio.sleep(1)
                    
                    # Periodically resolve queued players
                    if len(self._resolution_queue) > 0:
                        await self.resolve_queued_players()
                        
        except asyncio.CancelledError:
            self.logger.info("Draft monitoring cancelled")
        except Exception as e:
            self.logger.error(f"Error during draft monitoring: {e}")
        finally:
            self.logger.info(f"Draft monitoring completed")
            
    async def close(self):
        """Clean up resources."""
        try:
            if self.player_resolver:
                try:
                    await self.player_resolver.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.warning(f"Error during player resolver cleanup: {e}")
                
            if self.monitor:
                try:
                    await self.monitor.close()
                except Exception as e:
                    self.logger.warning(f"Error during monitor cleanup: {e}")
                
            self.logger.info("DraftStateManager closed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


async def create_draft_state_manager(league_id: str, team_id: str, 
                                   team_count: int = 12, rounds: int = 16,
                                   player_cache_db: Optional[str] = None) -> DraftStateManager:
    """
    Factory function to create and initialize a DraftStateManager.
    
    Args:
        league_id: ESPN league ID
        team_id: User's team ID
        team_count: Number of teams
        rounds: Number of rounds
        player_cache_db: Player cache database path
        
    Returns:
        Initialized DraftStateManager
    """
    manager = DraftStateManager(league_id, team_id, team_count, rounds, player_cache_db)
    
    success = await manager.initialize()
    if not success:
        raise RuntimeError("Failed to initialize DraftStateManager")
        
    return manager