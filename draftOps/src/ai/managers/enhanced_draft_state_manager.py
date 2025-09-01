#!/usr/bin/env python3
"""
Enhanced Draft State Manager with LangGraph AI Integration

Extends the existing DraftStateManager to include LangGraph Supervisor
for AI-driven draft decision making. This integration provides:

- Real-time AI recommendations based on draft context
- Contextual AI responses that consider current draft state
- Non-blocking async AI calls that don't interfere with WebSocket monitoring
- Automatic context injection from DraftState to LangGraph
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_protocol.state.integration import DraftStateManager
from ..core.draft_supervisor import DraftSupervisor


class EnhancedDraftStateManager(DraftStateManager):
    """
    Enhanced Draft State Manager with AI capabilities.
    
    Extends the base DraftStateManager with LangGraph Supervisor integration
    to provide AI-driven draft recommendations while maintaining all existing
    WebSocket monitoring and state management functionality.
    """
    
    def __init__(self, league_id: str, team_id: str, 
                 team_count: int = 12, rounds: int = 16,
                 player_cache_db: Optional[str] = None,
                 headless: bool = True,
                 ai_enabled: bool = True,
                 ai_thread_id: Optional[str] = None):
        """
        Initialize enhanced draft state manager with AI capabilities.
        
        Args:
            league_id: ESPN league ID
            team_id: User's team ID
            team_count: Number of teams in draft
            rounds: Number of draft rounds
            player_cache_db: Path to player resolution cache database
            headless: Run browser in headless mode
            ai_enabled: Enable AI supervisor functionality
            ai_thread_id: Custom thread ID for AI conversations (defaults to league_id)
        """
        # Initialize base manager
        super().__init__(league_id, team_id, team_count, rounds, player_cache_db, headless)
        
        # AI integration
        self.ai_enabled = ai_enabled
        self.ai_thread_id = ai_thread_id or f"draft_{league_id}"
        self.supervisor: Optional[DraftSupervisor] = None
        
        # AI callbacks
        self.on_ai_recommendation: Optional[Callable] = None
        self.on_ai_response: Optional[Callable] = None
        self.on_ai_error: Optional[Callable] = None
        
        # AI state tracking
        self.ai_stats = {
            'recommendations_generated': 0,
            'queries_processed': 0,
            'ai_errors': 0,
            'last_recommendation_time': None,
            'avg_ai_response_time_ms': 0.0
        }
        
        self.logger.info(f"Enhanced DraftStateManager initialized (AI enabled: {ai_enabled})")
        
    async def initialize(self) -> bool:
        """
        Initialize all components including AI supervisor.
        
        Returns:
            bool: True if initialization successful
        """
        # Initialize base components first
        if not await super().initialize():
            return False
            
        # Initialize AI supervisor if enabled
        if self.ai_enabled:
            try:
                self.supervisor = DraftSupervisor()
                
                # Test AI connectivity
                test_result = await self.supervisor.test_connection()
                if not test_result['success']:
                    self.logger.error(f"AI supervisor connectivity test failed: {test_result.get('error')}")
                    return False
                    
                self.logger.info(f"AI supervisor initialized successfully (model: {test_result.get('model')})")
                
                # Set up enhanced callbacks that include AI
                self._setup_ai_enhanced_callbacks()
                
            except Exception as e:
                self.logger.error(f"Failed to initialize AI supervisor: {e}")
                if not self.ai_enabled:  # Allow degraded mode without AI
                    self.logger.warning("Continuing without AI capabilities")
                else:
                    return False
                    
        self.logger.info("Enhanced DraftStateManager initialization complete")
        return True
        
    def _setup_ai_enhanced_callbacks(self):
        """Set up enhanced callbacks that trigger AI analysis."""
        # Store original callbacks
        original_pick_callback = self.on_pick_processed
        original_state_callback = self.on_state_updated
        
        # Wrap callbacks to include AI analysis
        def enhanced_pick_callback(pick_data: Dict[str, Any]):
            # Call original callback first
            if original_pick_callback:
                original_pick_callback(pick_data)
                
            # Trigger AI analysis for significant picks
            if self.ai_enabled and self.supervisor:
                asyncio.create_task(self._analyze_pick_with_ai(pick_data))
                
        def enhanced_state_callback(state_summary: Dict[str, Any]):
            # Call original callback first
            if original_state_callback:
                original_state_callback(state_summary)
                
            # Trigger AI analysis for state changes
            if self.ai_enabled and self.supervisor:
                asyncio.create_task(self._analyze_state_with_ai(state_summary))
                
        # Set enhanced callbacks
        self.on_pick_processed = enhanced_pick_callback
        self.on_state_updated = enhanced_state_callback
        
    async def _analyze_pick_with_ai(self, pick_data: Dict[str, Any]):
        """
        Analyze a draft pick with AI and potentially generate recommendations.
        
        Args:
            pick_data: Information about the pick that was made
        """
        try:
            # Only analyze significant picks (not every pick)
            pick_number = pick_data.get('pick_number', 0)
            picks_until_next = self.draft_state.picks_until_next
            
            # Generate AI analysis for picks close to our turn
            if picks_until_next <= 3 and picks_until_next > 0:
                context = self.supervisor.update_draft_context(self.draft_state)
                
                query = f"Pick {pick_number} just happened: {pick_data.get('player_name', 'Unknown player')} was selected by {pick_data.get('display_team_name', 'Unknown team')}. How does this affect our strategy for our upcoming pick?"
                
                start_time = datetime.now()
                result = await self.supervisor.invoke_async(
                    query, 
                    draft_context=context,
                    thread_id=self.ai_thread_id
                )
                
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_ai_processing_time(processing_time)
                
                if result['success']:
                    self.ai_stats['recommendations_generated'] += 1
                    self.ai_stats['last_recommendation_time'] = datetime.now().isoformat()
                    
                    # Trigger AI recommendation callback
                    if self.on_ai_recommendation:
                        self.on_ai_recommendation({
                            'type': 'pick_analysis',
                            'trigger_pick': pick_data,
                            'recommendation': result.get('recommendation', ''),
                            'reasoning': result.get('reasoning', ''),
                            'messages': result.get('messages', []),
                            'timestamp': datetime.now().isoformat()
                        })
                else:
                    self.ai_stats['ai_errors'] += 1
                    self.logger.warning(f"AI pick analysis failed: {result.get('error')}")
                    
        except Exception as e:
            self.ai_stats['ai_errors'] += 1
            self.logger.error(f"Error in AI pick analysis: {e}")
            
    async def _analyze_state_with_ai(self, state_summary: Dict[str, Any]):
        """
        Analyze draft state changes with AI for strategic insights.
        
        Args:
            state_summary: Current draft state summary
        """
        try:
            # Only analyze when we're on the clock
            if state_summary.get('on_the_clock') == self.team_id:
                context = self.supervisor.update_draft_context(self.draft_state)
                
                query = "I'm on the clock! What should I do right now? Give me a specific recommendation based on the current draft situation."
                
                start_time = datetime.now()
                result = await self.supervisor.invoke_async(
                    query,
                    draft_context=context,
                    thread_id=self.ai_thread_id
                )
                
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_ai_processing_time(processing_time)
                
                if result['success']:
                    self.ai_stats['recommendations_generated'] += 1
                    self.ai_stats['last_recommendation_time'] = datetime.now().isoformat()
                    
                    # Trigger urgent AI recommendation callback
                    if self.on_ai_recommendation:
                        self.on_ai_recommendation({
                            'type': 'urgent_recommendation',
                            'state': state_summary,
                            'recommendation': result.get('recommendation', ''),
                            'reasoning': result.get('reasoning', ''),
                            'messages': result.get('messages', []),
                            'timestamp': datetime.now().isoformat(),
                            'priority': 'high'
                        })
                else:
                    self.ai_stats['ai_errors'] += 1
                    self.logger.warning(f"AI state analysis failed: {result.get('error')}")
                    
        except Exception as e:
            self.ai_stats['ai_errors'] += 1
            self.logger.error(f"Error in AI state analysis: {e}")
            
    async def query_ai(self, user_input: str, include_context: bool = True) -> Dict[str, Any]:
        """
        Query the AI supervisor with custom input.
        
        Args:
            user_input: User's question or instruction
            include_context: Whether to include current draft context
            
        Returns:
            AI response with success status
        """
        if not self.ai_enabled or not self.supervisor:
            return {
                'success': False,
                'error': 'AI supervisor not available',
                'timestamp': datetime.now().isoformat()
            }
            
        try:
            start_time = datetime.now()
            self.ai_stats['queries_processed'] += 1
            
            # Include draft context if requested
            context = None
            if include_context:
                context = self.supervisor.update_draft_context(self.draft_state)
                
            result = await self.supervisor.invoke_async(
                user_input,
                draft_context=context,
                thread_id=self.ai_thread_id
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_ai_processing_time(processing_time)
            
            if result['success'] and self.on_ai_response:
                self.on_ai_response({
                    'type': 'user_query',
                    'query': user_input,
                    'response': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            return result
            
        except Exception as e:
            self.ai_stats['ai_errors'] += 1
            self.logger.error(f"Error querying AI: {e}")
            
            error_result = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            if self.on_ai_error:
                self.on_ai_error(error_result)
                
            return error_result
            
    async def get_draft_recommendation(self) -> Dict[str, Any]:
        """
        Get immediate AI recommendation based on current draft state.
        
        Returns:
            AI recommendation with context
        """
        if not self.ai_enabled or not self.supervisor:
            return {
                'success': False,
                'error': 'AI supervisor not available',
                'timestamp': datetime.now().isoformat()
            }
            
        try:
            context = self.supervisor.update_draft_context(self.draft_state)
            picks_until_next = self.draft_state.picks_until_next
            
            if picks_until_next == 0:
                query = "I'm on the clock right now! What specific player or position should I target immediately?"
            elif picks_until_next <= 2:
                query = f"I pick in {picks_until_next} picks. What should I be thinking about and preparing for?"
            else:
                query = "What's our current draft strategy and what positions should we be targeting in upcoming rounds?"
                
            result = await self.query_ai(query, include_context=True)
            
            if result['success']:
                return {
                    **result,
                    'context_summary': self._get_context_summary(),
                    'urgency': 'high' if picks_until_next == 0 else 'medium' if picks_until_next <= 2 else 'low'
                }
            else:
                return result
                
        except Exception as e:
            self.logger.error(f"Error getting draft recommendation: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def _get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of current draft context for AI responses."""
        return {
            'current_pick': self.draft_state.current_pick,
            'picks_until_next': self.draft_state.picks_until_next,
            'time_remaining': self.draft_state.time_remaining,
            'my_roster_counts': {pos: len(players) for pos, players in self.draft_state.my_roster.items()},
            'total_picks_made': len(self.draft_state.pick_history),
            'draft_status': self.draft_state.draft_status.value
        }
        
    def _update_ai_processing_time(self, processing_time_ms: float):
        """Update average AI processing time."""
        current_avg = self.ai_stats['avg_ai_response_time_ms']
        total_queries = self.ai_stats['queries_processed'] + self.ai_stats['recommendations_generated']
        
        if total_queries <= 1:
            # First query or single query - use the processing time directly
            self.ai_stats['avg_ai_response_time_ms'] = processing_time_ms
        else:
            # Running average
            self.ai_stats['avg_ai_response_time_ms'] = (
                (current_avg * (total_queries - 1) + processing_time_ms) / total_queries
            )
            
    def get_ai_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get AI conversation history for this draft session.
        
        Returns:
            List of conversation messages
        """
        if not self.supervisor:
            return []
            
        return self.supervisor.get_conversation_history(self.ai_thread_id)
        
    def clear_ai_conversation(self) -> bool:
        """
        Clear AI conversation history.
        
        Returns:
            True if cleared successfully
        """
        if not self.supervisor:
            return False
            
        return self.supervisor.clear_conversation(self.ai_thread_id)
        
    def get_enhanced_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state summary including AI metrics."""
        base_summary = super().get_state_summary()
        
        return {
            **base_summary,
            'ai_enabled': self.ai_enabled,
            'ai_stats': self.ai_stats,
            'ai_conversation_length': len(self.get_ai_conversation_history()),
            'ai_thread_id': self.ai_thread_id
        }
        
    async def close(self):
        """Clean up resources including AI supervisor."""
        try:
            # Clear AI conversation before closing
            if self.supervisor:
                self.clear_ai_conversation()
                
            # Call base cleanup
            await super().close()
            
            self.logger.info("Enhanced DraftStateManager closed")
            
        except Exception as e:
            self.logger.error(f"Error during enhanced cleanup: {e}")


async def create_enhanced_draft_state_manager(league_id: str, team_id: str, 
                                            team_count: int = 12, rounds: int = 16,
                                            player_cache_db: Optional[str] = None,
                                            ai_enabled: bool = True,
                                            ai_thread_id: Optional[str] = None) -> EnhancedDraftStateManager:
    """
    Factory function to create and initialize an Enhanced DraftStateManager.
    
    Args:
        league_id: ESPN league ID
        team_id: User's team ID
        team_count: Number of teams
        rounds: Number of rounds
        player_cache_db: Player cache database path
        ai_enabled: Enable AI supervisor functionality
        ai_thread_id: Custom AI thread ID
        
    Returns:
        Initialized EnhancedDraftStateManager
    """
    manager = EnhancedDraftStateManager(
        league_id, team_id, team_count, rounds, 
        player_cache_db, ai_enabled=ai_enabled, ai_thread_id=ai_thread_id
    )
    
    success = await manager.initialize()
    if not success:
        raise RuntimeError("Failed to initialize EnhancedDraftStateManager")
        
    return manager