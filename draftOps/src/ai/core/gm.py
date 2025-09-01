#!/usr/bin/env python3
"""
GM Node - Final Draft Decision Agent

Implements the GM node specification for Sprint 2.
Takes 10 Scout recommendations, strategy, and draft state to select exactly one final player.
Runs GPT-5 with moderate temperature for consistent final decisions.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class GMDecision:
    """Final GM decision output."""
    selected_player_id: str
    selected_player_name: str
    position: str
    reason: str
    score_hint: float = 0.0


class GM:
    """
    GM node for final draft decision making.
    
    Takes 10 Scout recommendations, strategy from Draft Strategist, and current draft state
    to select exactly one player to draft. Uses GPT-5 with consistent temperature for
    final decision aggregation.
    """
    
    def __init__(self, model_name: str = "gpt-5", temperature: float = 0.8):
        """
        Initialize GM agent.
        
        Args:
            model_name: OpenAI model to use (default: gpt-5-2025-08-07)
            temperature: Moderate temperature for consistency (default: 0.8)
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
        
        self.logger.info(f"GM initialized with model {model_name}, temp {temperature}")
        
    def _initialize_llm(self):
        """Initialize the OpenAI LLM with GPT-5."""
        try:
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.api_key,
                max_tokens=10000,  # Large limit for GPT-5 reasoning tokens
                timeout=30.0
            )
            self.logger.debug(f"GM LLM initialized: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize GM LLM: {e}")
            raise
            
    def make_decision(self, scout_recommendations: List[Dict[str, Any]], 
                     pick_strategy: str, draft_state: Dict[str, Any]) -> GMDecision:
        """
        Make final draft decision from Scout recommendations.
        
        Args:
            scout_recommendations: List of 10 Scout recommendation objects
            pick_strategy: Strategy string from Draft Strategist
            draft_state: Current draft context
            
        Returns:
            GMDecision object with selected player and reasoning
            
        Raises:
            ValueError: If no valid decision can be generated
        """
        try:
            # Validate inputs
            self.validate_inputs(scout_recommendations, pick_strategy, draft_state)
            
            # Build the prompt
            prompt = self._build_prompt(scout_recommendations, pick_strategy, draft_state)
            
            # Get response from GPT-5
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            
            # Parse JSON response
            decision = self._parse_response(response.content, scout_recommendations)
            
            self.logger.debug(f"GM decision: {decision.selected_player_name}")
            return decision
            
        except Exception as e:
            self.logger.error(f"Error making GM decision: {e}")
            # Return fallback decision
            return self._get_fallback_decision(scout_recommendations)
            
    def _build_prompt(self, scout_recommendations: List[Dict[str, Any]], 
                     pick_strategy: str, draft_state: Dict[str, Any]) -> str:
        """Build the system + user prompt for the GM."""
        
        system_prompt = """You are the GENERAL MANAGER (GM). From the 10 candidate recommendations and the given strategy and state, choose exactly ONE player to draft.

Use context (roster needs, strategy, tier runs, ADP, etc.) to justify the pick in 2 sentences or less. Consider:
- Roster need gaps
- Best value/ADP opportunities  
- Position scarcity and urgency
- Tier breaks and runs
- Scout confidence scores

If candidates are close, prefer the one with higher score_hint or clearer strategic fit.

Return ONLY valid JSON matching this schema:
{
  "selected_player_id": "<player_id>",
  "selected_player_name": "<player_name>",
  "position": "<position>",
  "reason": "<concise justification (2 sentences or less)>",
  "score_hint": 0.0
}"""

        # Format the user input
        recommendations_json = json.dumps(scout_recommendations, indent=2)
        draft_state_json = json.dumps(draft_state, indent=2)
        
        user_prompt = f"""SCOUT_RECOMMENDATIONS: {recommendations_json}

PICK_STRATEGY: {pick_strategy}

DRAFT_STATE: {draft_state_json}"""

        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return full_prompt
        
    def _parse_response(self, response_text: str, scout_recommendations: List[Dict[str, Any]]) -> GMDecision:
        """Parse and validate the JSON response from GPT-5."""
        try:
            # Handle markdown code blocks if present
            if '```json' in response_text:
                start_marker = response_text.find('```json') + 7
                end_marker = response_text.find('```', start_marker)
                if end_marker != -1:
                    json_text = response_text[start_marker:end_marker].strip()
                else:
                    # Fallback to finding JSON braces
                    json_start = response_text.find('{', start_marker)
                    json_end = response_text.rfind('}') + 1
                    json_text = response_text[json_start:json_end]
            else:
                # Extract JSON from response (handle any extra text)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise ValueError("No JSON found in response")
                    
                json_text = response_text[json_start:json_end]
                
            data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['selected_player_id', 'selected_player_name', 'position', 'reason']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Validate player selection is from Scout recommendations
            selected_id = data['selected_player_id']
            valid_ids = [str(rec.get('suggested_player_id', '')) for rec in scout_recommendations]
            
            if selected_id not in valid_ids:
                raise ValueError(f"Selected player {selected_id} not in Scout recommendations")
                
            # Validate reason length (2 sentences or less approximately)
            reason = data['reason'].strip()
            if len(reason) == 0:
                raise ValueError("Empty reason provided")
                
            sentence_count = reason.count('.') + reason.count('!') + reason.count('?')
            if sentence_count > 2:
                self.logger.warning(f"Reason may exceed 2 sentences: {sentence_count} detected")
                
            # Create decision object
            return GMDecision(
                selected_player_id=selected_id,
                selected_player_name=data['selected_player_name'],
                position=data['position'],
                reason=reason,
                score_hint=float(data.get('score_hint', 0.0))
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse GM response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            raise ValueError(f"Invalid GM response: {e}")
            
    def _get_fallback_decision(self, scout_recommendations: List[Dict[str, Any]]) -> GMDecision:
        """Return a safe fallback decision if main logic fails."""
        if not scout_recommendations:
            raise ValueError("No Scout recommendations available for fallback decision")
            
        # Select the Scout recommendation with highest confidence score
        best_recommendation = max(scout_recommendations, key=lambda r: r.get('score_hint', 0.0))
        
        return GMDecision(
            selected_player_id=str(best_recommendation.get('suggested_player_id', '')),
            selected_player_name=best_recommendation.get('suggested_player_name', 'Unknown Player'),
            position=best_recommendation.get('position', 'Unknown'),
            reason="Fallback selection: highest-confidence Scout recommendation.",
            score_hint=0.5
        )
        
    def validate_inputs(self, scout_recommendations: List[Dict[str, Any]], 
                       pick_strategy: str, draft_state: Dict[str, Any]) -> bool:
        """
        Validate inputs meet GM node requirements.
        
        Args:
            scout_recommendations: List of Scout recommendations
            pick_strategy: Strategy string
            draft_state: Draft context
            
        Returns:
            True if inputs are valid
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate scout_recommendations
        if not isinstance(scout_recommendations, list):
            raise ValueError("scout_recommendations must be a list")
            
        if len(scout_recommendations) == 0:
            raise ValueError("scout_recommendations cannot be empty")
            
        # Ideally should have 10 recommendations per spec, but be flexible
        if len(scout_recommendations) > 10:
            self.logger.warning(f"More than 10 Scout recommendations provided: {len(scout_recommendations)}")
            
        # Check each recommendation has required fields
        required_rec_fields = ['suggested_player_id', 'suggested_player_name', 'position', 'reason']
        for i, rec in enumerate(scout_recommendations):
            if not isinstance(rec, dict):
                raise ValueError(f"Scout recommendation {i} must be a dictionary")
                
            for field in required_rec_fields:
                if field not in rec:
                    raise ValueError(f"Scout recommendation {i} missing required field: {field}")
                    
        # Validate pick_strategy
        if not isinstance(pick_strategy, str):
            raise ValueError("pick_strategy must be a string")
            
        if len(pick_strategy.strip()) == 0:
            raise ValueError("pick_strategy cannot be empty")
            
        # Validate draft_state
        if not isinstance(draft_state, dict):
            raise ValueError("draft_state must be a dictionary")
            
        return True