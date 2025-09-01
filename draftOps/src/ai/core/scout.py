#!/usr/bin/env python3
"""
Scout Node - AI-driven pick recommendation agent

Implements the Scout node specification for Sprint 2.
Selects exactly one player from a provided shortlist using draft context and strategy.
Runs GPT-5 with high temperature for diverse recommendations.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass 
class ScoutRecommendation:
    """Single scout recommendation output."""
    suggested_player_id: str
    suggested_player_name: str
    position: str
    reason: str
    score_hint: float = 0.0


class Scout:
    """
    Scout node for AI-driven pick recommendations.
    
    Takes a shortlist of candidates from the Strategist and selects exactly one player
    using GPT-5 with draft context and strategy. Designed to run multiple times
    with different seeds for diverse recommendations.
    """
    
    def __init__(self, model_name: str = "gpt-5", temperature: float = 1.0):
        """
        Initialize Scout agent.
        
        Args:
            model_name: OpenAI model to use (default: gpt-5)
            temperature: High temperature for diversity (default: 1.0)
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
        
        self.logger.info(f"Scout initialized with model {model_name}, temp {temperature}")
        
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
            self.logger.debug(f"Scout LLM initialized: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Scout LLM: {e}")
            raise
            
    def get_recommendation(self, pick_candidates: List[Dict[str, Any]], 
                          pick_strategy: str, draft_state: Dict[str, Any],
                          seed: Optional[int] = None) -> ScoutRecommendation:
        """
        Generate a single pick recommendation from the candidate list.
        
        Args:
            pick_candidates: List of player objects (from Strategist)
            pick_strategy: Strategy string from Strategist
            draft_state: Current draft context
            seed: Random seed for reproducibility (optional)
            
        Returns:
            ScoutRecommendation object with the selected player and reasoning
            
        Raises:
            ValueError: If no valid recommendation can be generated
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(pick_candidates, pick_strategy, draft_state)
            
            # Set seed if provided (for deterministic testing)
            llm_to_use = self.llm
            if seed is not None:
                llm_to_use = ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=self.api_key,
                    max_tokens=10000,
                    timeout=30.0,
                    model_kwargs={"seed": seed}
                )
            
            # Get response from GPT-5
            response = llm_to_use.invoke([{"role": "user", "content": prompt}])
            
            # Parse JSON response
            recommendation = self._parse_response(response.content, pick_candidates)
            
            self.logger.debug(f"Scout recommendation: {recommendation.suggested_player_name}")
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error generating scout recommendation: {e}")
            # Return fallback recommendation
            return self._get_fallback_recommendation(pick_candidates)
            
    async def get_multiple_recommendations(self, pick_candidates: List[Dict[str, Any]], 
                                         pick_strategy: str, draft_state: Dict[str, Any],
                                         num_recommendations: int = 10) -> List[ScoutRecommendation]:
        """
        Generate multiple diverse recommendations by running Scout in parallel.
        
        Args:
            pick_candidates: List of player objects (from Strategist)
            pick_strategy: Strategy string from Strategist  
            draft_state: Current draft context
            num_recommendations: Number of parallel recommendations (default: 10)
            
        Returns:
            List of ScoutRecommendation objects
        """
        try:
            # Create tasks for parallel execution with different seeds
            tasks = []
            for i in range(num_recommendations):
                seed = 101 + i  # Seeds 101-110 per spec
                task = self._get_recommendation_async(
                    pick_candidates, pick_strategy, draft_state, seed
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            recommendations = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and return valid recommendations
            valid_recommendations = []
            for rec in recommendations:
                if isinstance(rec, ScoutRecommendation):
                    valid_recommendations.append(rec)
                else:
                    self.logger.warning(f"Invalid recommendation received: {rec}")
                    
            self.logger.info(f"Generated {len(valid_recommendations)}/{num_recommendations} valid recommendations")
            return valid_recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating multiple recommendations: {e}")
            # Return at least one fallback
            return [self._get_fallback_recommendation(pick_candidates)]
            
    async def _get_recommendation_async(self, pick_candidates: List[Dict[str, Any]], 
                                      pick_strategy: str, draft_state: Dict[str, Any],
                                      seed: int) -> ScoutRecommendation:
        """Async wrapper for get_recommendation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.get_recommendation, pick_candidates, pick_strategy, draft_state, seed
        )
        
    def _build_prompt(self, pick_candidates: List[Dict[str, Any]], 
                     pick_strategy: str, draft_state: Dict[str, Any]) -> str:
        """Build the system + user prompt for the Scout."""
        
        system_prompt = """You are the SCOUT. Select exactly ONE player from the shortlist.

Use the draft strategy and state to justify the pick in ≤2 sentences. Cite relevant factors:
- need (roster gaps)  
- tier (tier break urgency)
- ADP/value (players falling vs expected position)
- run (position run pressure)
- stack (team stacking opportunities)
- risk (injury/consistency concerns)

If players are close, break ties by: need > tier > ADP > projection > lower risk.

Return ONLY valid JSON matching this schema:
{
  "suggested_player_id": "<player_id>",
  "suggested_player_name": "<player_name>", 
  "position": "<position>",
  "reason": "<concise justification (≤2 sentences)>",
  "score_hint": 0.0
}"""

        # Format the user input
        candidates_json = json.dumps(pick_candidates, indent=2)
        draft_state_json = json.dumps(draft_state, indent=2)
        
        user_prompt = f"""PICK_STRATEGY: {pick_strategy}

DRAFT_STATE: {draft_state_json}

PICK_CANDIDATES (size={len(pick_candidates)}): {candidates_json}"""

        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return full_prompt
        
    def _parse_response(self, response_text: str, pick_candidates: List[Dict[str, Any]]) -> ScoutRecommendation:
        """Parse and validate the JSON response from GPT-5."""
        try:
            # Extract JSON from response (handle any extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
                
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['suggested_player_id', 'suggested_player_name', 'position', 'reason']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Validate player selection is from candidates
            suggested_id = data['suggested_player_id']
            valid_ids = [str(c.get('player_id', '')) for c in pick_candidates]
            
            if suggested_id not in valid_ids:
                raise ValueError(f"Selected player {suggested_id} not in candidate list")
                
            # Validate reason length (≤2 sentences approximately)
            reason = data['reason'].strip()
            if len(reason) == 0:
                raise ValueError("Empty reason provided")
                
            sentence_count = reason.count('.') + reason.count('!') + reason.count('?')
            if sentence_count > 2:
                self.logger.warning(f"Reason may exceed 2 sentences: {sentence_count} detected")
                
            # Create recommendation object
            return ScoutRecommendation(
                suggested_player_id=suggested_id,
                suggested_player_name=data['suggested_player_name'],
                position=data['position'],
                reason=reason,
                score_hint=float(data.get('score_hint', 0.0))
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse scout response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            raise ValueError(f"Invalid scout response: {e}")
            
    def _get_fallback_recommendation(self, pick_candidates: List[Dict[str, Any]]) -> ScoutRecommendation:
        """Return a safe fallback recommendation if main logic fails."""
        if not pick_candidates:
            raise ValueError("No candidates available for fallback recommendation")
            
        # Select the highest-ranked player (lowest ADP) as fallback
        best_candidate = min(pick_candidates, key=lambda p: p.get('adp', float('inf')))
        
        return ScoutRecommendation(
            suggested_player_id=str(best_candidate.get('player_id', '')),
            suggested_player_name=best_candidate.get('name', 'Unknown Player'),
            position=best_candidate.get('position', 'Unknown'),
            reason="Fallback selection: highest-ranked available player by ADP.",
            score_hint=0.5
        )
        
    def validate_inputs(self, pick_candidates: List[Dict[str, Any]], 
                       pick_strategy: str, draft_state: Dict[str, Any]) -> bool:
        """
        Validate inputs meet Scout node requirements.
        
        Args:
            pick_candidates: List of player candidates
            pick_strategy: Strategy string
            draft_state: Draft context
            
        Returns:
            True if inputs are valid
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate pick_candidates
        if not isinstance(pick_candidates, list):
            raise ValueError("pick_candidates must be a list")
            
        if len(pick_candidates) == 0:
            raise ValueError("pick_candidates cannot be empty")
            
        # Check each candidate has required fields
        required_candidate_fields = ['player_id', 'name', 'position', 'adp']
        for i, candidate in enumerate(pick_candidates):
            if not isinstance(candidate, dict):
                raise ValueError(f"Candidate {i} must be a dictionary")
                
            for field in required_candidate_fields:
                if field not in candidate:
                    raise ValueError(f"Candidate {i} missing required field: {field}")
                    
        # Validate pick_strategy
        if not isinstance(pick_strategy, str):
            raise ValueError("pick_strategy must be a string")
            
        if len(pick_strategy.strip()) == 0:
            raise ValueError("pick_strategy cannot be empty")
            
        # Validate draft_state
        if not isinstance(draft_state, dict):
            raise ValueError("draft_state must be a dictionary")
            
        return True