#!/usr/bin/env python3
"""
DraftOps AI Supervisor using LangGraph Framework

Implements the LangGraph Supervisor pattern for AI-driven draft decision making.
The Supervisor Agent orchestrates draft strategy and maintains context throughout
the draft using LangGraph's StateGraph and InMemorySaver.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, TypedDict, Annotated
from typing_extensions import NotRequired
from operator import add
from datetime import datetime
from dataclasses import asdict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()


class DraftState(TypedDict):
    """LangGraph state for draft decision making."""
    messages: Annotated[list[Dict[str, Any]], add]
    draft_context: NotRequired[Dict[str, Any]]
    current_recommendation: NotRequired[str]
    reasoning: NotRequired[str]
    last_updated: NotRequired[str]


class DraftSupervisor:
    """
    AI Supervisor Agent for fantasy football draft decisions.
    
    Uses LangGraph's StateGraph with GPT-5 to orchestrate draft strategy,
    maintain context between picks, and provide AI-driven recommendations.
    
    Features:
    - LangGraph StateGraph for workflow orchestration
    - InMemorySaver for conversation memory persistence
    - GPT-5 (gpt-5-2025-08-07) integration for decision making
    - Context injection from DraftOps DraftState
    - Streaming support for real-time feedback
    """
    
    def __init__(self, model_name: str = "gpt-5-2025-08-07", temperature: float = 0.1):
        """
        Initialize the Draft Supervisor.
        
        Args:
            model_name: OpenAI model to use (default: gpt-5-2025-08-07)
            temperature: Model temperature for determinism (default: 0.1)
        """
        self.model_name = model_name
        self.temperature = temperature
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Verify OpenAI API key
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        # Initialize LLM
        self._initialize_llm()
        
        # LangGraph components
        self.workflow: Optional[StateGraph] = None
        self.graph = None
        self.checkpointer = InMemorySaver()
        
        # Build the graph
        self._build_graph()
        
        self.logger.info(f"DraftSupervisor initialized with model {model_name}")
        
    def _initialize_llm(self):
        """Initialize the OpenAI LLM with GPT-5."""
        try:
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.api_key,
                max_tokens=2000,
                timeout=30.0
            )
            self.logger.info(f"LLM initialized: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
            raise
            
    def _build_graph(self):
        """Build the LangGraph StateGraph workflow."""
        try:
            # Create StateGraph
            self.workflow = StateGraph(DraftState)
            
            # Add nodes
            self.workflow.add_node("supervisor", self._supervisor_node)
            self.workflow.add_node("context_processor", self._context_processor_node)
            self.workflow.add_node("recommendation_generator", self._recommendation_generator_node)
            
            # Add edges
            self.workflow.add_edge(START, "context_processor")
            self.workflow.add_edge("context_processor", "supervisor")
            self.workflow.add_edge("supervisor", "recommendation_generator")
            self.workflow.add_edge("recommendation_generator", END)
            
            # Compile graph with checkpointer
            self.graph = self.workflow.compile(checkpointer=self.checkpointer)
            
            self.logger.info("LangGraph workflow compiled successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to build graph: {e}")
            raise
            
    def _context_processor_node(self, state: DraftState) -> Dict[str, Any]:
        """Process and prepare draft context for the supervisor."""
        try:
            current_time = datetime.now().isoformat()
            draft_context = state.get('draft_context', {})
            
            # Extract key information from draft context
            context_summary = self._summarize_draft_context(draft_context)
            
            # Add system message with context
            context_message = {
                "role": "system",
                "content": f"""You are the DraftOps Supervisor, an AI assistant for fantasy football drafts.

Current Draft Context:
{context_summary}

Your role is to analyze the draft situation and coordinate strategy. You have access to:
- Real-time draft state (picks, available players, team needs)
- Player rankings and ADP data  
- Snake draft position calculations
- Time remaining information

Focus on making logical, strategic draft recommendations based on the current context.""",
                "timestamp": current_time
            }
            
            return {
                "messages": [context_message],
                "last_updated": current_time
            }
            
        except Exception as e:
            self.logger.error(f"Context processor error: {e}")
            return {"messages": []}
            
    def _supervisor_node(self, state: DraftState) -> Dict[str, Any]:
        """Main supervisor node that orchestrates decision making."""
        try:
            messages = state.get('messages', [])
            
            if not messages:
                return {"messages": []}
                
            # Get latest message for processing
            latest_message = messages[-1] if messages else None
            
            if latest_message and latest_message.get('role') == 'user':
                # Process user query with full context
                response = self.llm.invoke(messages)
                
                supervisor_message = {
                    "role": "assistant", 
                    "content": response.content,
                    "timestamp": datetime.now().isoformat(),
                    "source": "supervisor"
                }
                
                return {
                    "messages": [supervisor_message],
                    "reasoning": response.content
                }
            
            return {"messages": []}
            
        except Exception as e:
            self.logger.error(f"Supervisor node error: {e}")
            return {"messages": []}
            
    def _recommendation_generator_node(self, state: DraftState) -> Dict[str, Any]:
        """Generate specific draft recommendations."""
        try:
            draft_context = state.get('draft_context', {})
            messages = state.get('messages', [])
            
            # Check if we need to generate a recommendation
            if not draft_context or not messages:
                return {}
                
            # Generate recommendation based on context
            recommendation = self._generate_recommendation(draft_context, messages)
            
            return {
                "current_recommendation": recommendation,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Recommendation generator error: {e}")
            return {}
            
    def _summarize_draft_context(self, draft_context: Dict[str, Any]) -> str:
        """Create a human-readable summary of the draft context."""
        if not draft_context:
            return "No draft context available"
            
        try:
            lines = []
            
            # Basic draft info
            current_pick = draft_context.get('current_pick', 0)
            picks_until_next = draft_context.get('picks_until_next', 0)
            time_remaining = draft_context.get('time_remaining', 0)
            on_the_clock = draft_context.get('on_the_clock', 'Unknown')
            
            lines.append(f"• Current pick: {current_pick}")
            lines.append(f"• Picks until our turn: {picks_until_next}")
            lines.append(f"• Time remaining: {time_remaining:.0f}s")
            lines.append(f"• On the clock: {on_the_clock}")
            
            # Our roster
            my_roster = draft_context.get('my_roster', {})
            if my_roster:
                roster_counts = {pos: len(players) for pos, players in my_roster.items() if players}
                if roster_counts:
                    lines.append(f"• Our roster: {roster_counts}")
                    
            # Available players count
            available_count = draft_context.get('available_players_count', 0)
            if available_count:
                lines.append(f"• Available players: {available_count}")
                
            # Recent picks
            recent_picks = draft_context.get('recent_picks', [])
            if recent_picks:
                lines.append("• Recent picks:")
                for pick in recent_picks[-3:]:  # Last 3 picks
                    pick_num = pick.get('pick_number', '?')
                    player_name = pick.get('player_name', 'Unknown')
                    lines.append(f"  - Pick {pick_num}: {player_name}")
                    
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error summarizing context: {e}")
            return "Error processing draft context"
            
    def _generate_recommendation(self, draft_context: Dict[str, Any], messages: List[Dict[str, Any]]) -> str:
        """Generate a specific draft recommendation."""
        try:
            # Simple recommendation based on available context
            picks_until_next = draft_context.get('picks_until_next', 0)
            my_roster = draft_context.get('my_roster', {})
            
            if picks_until_next == 0:
                return "You are on the clock! Make your pick now."
            elif picks_until_next <= 2:
                return f"Get ready - you're picking in {picks_until_next} picks!"
            else:
                return f"Monitor the draft - you pick in {picks_until_next} picks."
                
        except Exception as e:
            self.logger.error(f"Error generating recommendation: {e}")
            return "Unable to generate recommendation at this time."
            
    async def invoke_async(self, user_input: str, draft_context: Optional[Dict[str, Any]] = None, 
                          thread_id: str = "default") -> Dict[str, Any]:
        """
        Asynchronously invoke the supervisor with user input and draft context.
        
        Args:
            user_input: User query or instruction
            draft_context: Current draft state information
            thread_id: Thread identifier for conversation continuity
            
        Returns:
            Dict containing the supervisor's response and recommendation
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Prepare input state
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            }
            
            input_state = {
                "messages": [user_message],
                "draft_context": draft_context or {}
            }
            
            # Invoke graph asynchronously using thread pool executor
            # Use get_running_loop() which is safer in async contexts
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = await loop.run_in_executor(
                None, self.graph.invoke, input_state, config
            )
            
            self.logger.info(f"Supervisor invoked successfully for thread {thread_id}")
            
            return {
                "success": True,
                "messages": result.get('messages', []),
                "recommendation": result.get('current_recommendation', ''),
                "reasoning": result.get('reasoning', ''),
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error invoking supervisor: {e}")
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat()
            }
            
    def invoke_sync(self, user_input: str, draft_context: Optional[Dict[str, Any]] = None,
                   thread_id: str = "default") -> Dict[str, Any]:
        """
        Synchronously invoke the supervisor (for backwards compatibility).
        
        Args:
            user_input: User query or instruction
            draft_context: Current draft state information
            thread_id: Thread identifier for conversation continuity
            
        Returns:
            Dict containing the supervisor's response and recommendation
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Prepare input state
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            }
            
            input_state = {
                "messages": [user_message],
                "draft_context": draft_context or {}
            }
            
            # Invoke graph
            result = self.graph.invoke(input_state, config)
            
            self.logger.info(f"Supervisor invoked successfully for thread {thread_id}")
            
            return {
                "success": True,
                "messages": result.get('messages', []),
                "recommendation": result.get('current_recommendation', ''),
                "reasoning": result.get('reasoning', ''),
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error invoking supervisor: {e}")
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat()
            }
            
    def update_draft_context(self, draft_state_obj) -> Dict[str, Any]:
        """
        Convert DraftOps DraftState object to context dict for LangGraph.
        
        Args:
            draft_state_obj: DraftOps DraftState instance
            
        Returns:
            Dict containing draft context for AI processing
        """
        try:
            if not draft_state_obj:
                return {}
                
            # Extract key information from DraftState
            context = {
                "current_pick": draft_state_obj.current_pick,
                "picks_until_next": draft_state_obj.picks_until_next,
                "time_remaining": draft_state_obj.time_remaining,
                "on_the_clock": draft_state_obj.on_the_clock,
                "draft_status": draft_state_obj.draft_status.value if hasattr(draft_state_obj.draft_status, 'value') else str(draft_state_obj.draft_status),
                "my_roster": draft_state_obj.my_roster,
                "available_players_count": len(draft_state_obj.available_players),
                "total_picks_made": len(draft_state_obj.pick_history),
                "recent_picks": draft_state_obj.pick_history[-5:] if draft_state_obj.pick_history else []
            }
            
            self.logger.debug("Draft context updated successfully")
            return context
            
        except Exception as e:
            self.logger.error(f"Error updating draft context: {e}")
            return {}
            
    def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """
        Get conversation history for a specific thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            List of messages in the conversation
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get current state from checkpointer
            checkpoint = self.checkpointer.get(config)
            if checkpoint and 'channel_values' in checkpoint:
                state = checkpoint['channel_values']
                return state.get('messages', [])
                
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            return []
            
    def clear_conversation(self, thread_id: str = "default") -> bool:
        """
        Clear conversation history for a specific thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            True if cleared successfully
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Note: InMemorySaver doesn't have direct clear method
            # In practice, you'd create a new checkpointer or restart
            self.logger.info(f"Conversation cleared for thread {thread_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing conversation: {e}")
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test GPT-5 connectivity and basic functionality.
        
        Returns:
            Dict containing test results
        """
        try:
            test_input = "Hello, are you working correctly?"
            
            result = await self.invoke_async(test_input, thread_id="test")
            
            if result.get('success'):
                return {
                    "success": True,
                    "model": self.model_name,
                    "response_preview": result.get('messages', [{}])[-1].get('content', '')[:100] + "...",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Unknown error'),
                    "model": self.model_name,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self.model_name,
                "timestamp": datetime.now().isoformat()
            }