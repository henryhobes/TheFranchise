#!/usr/bin/env python3
"""
Player ID Extraction Utility

Extracts and analyzes player identifiers from ESPN draft WebSocket messages.
Part of Sprint 0 Player ID System Reverse Engineering.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class PlayerIdExtraction:
    """Represents an extracted player ID from a WebSocket message."""
    player_id: str
    timestamp: str
    message_type: str
    websocket_url: str
    raw_message: str
    context_fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # How confident we are this is a valid player ID


class PlayerIdExtractor:
    """
    Utility for extracting player IDs from ESPN draft WebSocket messages.
    
    Focuses on identifying player identifiers in various message formats
    and building a comprehensive dataset for reverse engineering ESPN's
    player identification system.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.extracted_ids: List[PlayerIdExtraction] = []
        self.unique_player_ids: Set[str] = set()
        self.message_patterns: Dict[str, int] = {}
        
        # Known field patterns that likely contain player IDs
        self.player_id_fields = [
            "playerId", "player_id", "playerID", "id", "espnId", "espn_id",
            "athleteId", "athlete_id", "selectedPlayerId", "draftedPlayerId"
        ]
        
        # Context fields that help understand the player selection
        self.context_fields = [
            "teamId", "team_id", "pickNumber", "pick_number", "round",
            "position", "pos", "name", "fullName", "firstName", "lastName",
            "team", "nflTeam", "status", "injuryStatus"
        ]
        
    def extract_from_message(self, payload: str, websocket_url: str, 
                           message_type: str = "unknown") -> List[PlayerIdExtraction]:
        """
        Extract player IDs from a WebSocket message payload.
        
        Args:
            payload: Raw WebSocket message payload
            websocket_url: Source WebSocket URL
            message_type: Type of message (if known)
            
        Returns:
            List of extracted player ID information
        """
        extractions = []
        timestamp = datetime.now().isoformat()
        
        try:
            # Try to parse as JSON
            data = json.loads(payload)
            extractions.extend(self._extract_from_json(
                data, payload, websocket_url, message_type, timestamp
            ))
        except json.JSONDecodeError:
            # Try pattern-based extraction for non-JSON messages
            extractions.extend(self._extract_from_text(
                payload, websocket_url, message_type, timestamp
            ))
            
        # Store extractions
        self.extracted_ids.extend(extractions)
        for extraction in extractions:
            self.unique_player_ids.add(extraction.player_id)
            
        return extractions
        
    def _extract_from_json(self, data: Any, raw_message: str, websocket_url: str,
                          message_type: str, timestamp: str) -> List[PlayerIdExtraction]:
        """Extract player IDs from parsed JSON data."""
        extractions = []
        
        if isinstance(data, dict):
            extractions.extend(self._extract_from_dict(
                data, raw_message, websocket_url, message_type, timestamp
            ))
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    extractions.extend(self._extract_from_dict(
                        item, raw_message, websocket_url, message_type, timestamp
                    ))
                    
        return extractions
        
    def _extract_from_dict(self, data: Dict[str, Any], raw_message: str,
                          websocket_url: str, message_type: str, 
                          timestamp: str) -> List[PlayerIdExtraction]:
        """Extract player IDs from a dictionary, recursively searching nested structures."""
        extractions = []
        
        # Direct field matching
        for field in self.player_id_fields:
            if field in data:
                player_id = str(data[field])
                if self._is_valid_player_id(player_id):
                    context = self._extract_context(data)
                    
                    extraction = PlayerIdExtraction(
                        player_id=player_id,
                        timestamp=timestamp,
                        message_type=message_type,
                        websocket_url=websocket_url,
                        raw_message=raw_message,
                        context_fields=context,
                        confidence=self._calculate_confidence(field, context)
                    )
                    extractions.append(extraction)
                    
        # Recursive search in nested structures
        for key, value in data.items():
            if isinstance(value, dict):
                extractions.extend(self._extract_from_dict(
                    value, raw_message, websocket_url, message_type, timestamp
                ))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        extractions.extend(self._extract_from_dict(
                            item, raw_message, websocket_url, message_type, timestamp
                        ))
                        
        return extractions
        
    def _extract_from_text(self, payload: str, websocket_url: str,
                          message_type: str, timestamp: str) -> List[PlayerIdExtraction]:
        """Extract player IDs from non-JSON text using pattern matching."""
        extractions = []
        
        # Pattern for numeric IDs (common ESPN format)
        numeric_patterns = [
            r'"playerId["\s]*:\s*["\s]*(\d+)["\s]*',
            r'"player_id["\s]*:\s*["\s]*(\d+)["\s]*',
            r'"id["\s]*:\s*["\s]*(\d+)["\s]*',
            r'playerId[=:]\s*(\d+)',
            r'player[_\s]*id[=:]\s*(\d+)'
        ]
        
        for pattern in numeric_patterns:
            matches = re.finditer(pattern, payload, re.IGNORECASE)
            for match in matches:
                player_id = match.group(1)
                if self._is_valid_player_id(player_id):
                    extraction = PlayerIdExtraction(
                        player_id=player_id,
                        timestamp=timestamp,
                        message_type=message_type,
                        websocket_url=websocket_url,
                        raw_message=payload,
                        context_fields={},
                        confidence=0.7  # Lower confidence for pattern matching
                    )
                    extractions.append(extraction)
                    
        return extractions
        
    def _is_valid_player_id(self, candidate: str) -> bool:
        """
        Validate whether a candidate string looks like a valid ESPN player ID.
        
        Based on research findings, ESPN player IDs appear to be numeric
        and typically 6-7 digits long.
        """
        try:
            # Must be numeric
            int_id = int(candidate)
            
            # Reasonable range for ESPN player IDs (based on research examples)
            # ESPN IDs seem to be in the millions (e.g., 4241457 for Najee Harris)
            if 1000 <= int_id <= 99999999:
                return True
                
        except (ValueError, TypeError):
            pass
            
        return False
        
    def _extract_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contextual information that helps understand the player."""
        context = {}
        
        for field in self.context_fields:
            if field in data:
                context[field] = data[field]
                
        return context
        
    def _calculate_confidence(self, field_name: str, context: Dict[str, Any]) -> float:
        """Calculate confidence score for a player ID extraction."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for explicit player ID fields
        if field_name.lower() in ["playerid", "player_id"]:
            confidence += 0.3
        elif field_name.lower() in ["espnid", "espn_id", "athleteid", "athlete_id"]:
            confidence += 0.2
        elif field_name.lower() == "id":
            confidence += 0.1  # Generic "id" field is less certain
            
        # Boost confidence if we have supporting context
        if context.get("name") or context.get("fullName"):
            confidence += 0.1
        if context.get("position") or context.get("pos"):
            confidence += 0.05
        if context.get("team") or context.get("nflTeam"):
            confidence += 0.05
            
        return min(confidence, 1.0)
        
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get summary statistics about extracted player IDs."""
        if not self.extracted_ids:
            return {"total_extractions": 0, "unique_players": 0}
            
        # Group by confidence levels
        high_confidence = [e for e in self.extracted_ids if e.confidence >= 0.8]
        medium_confidence = [e for e in self.extracted_ids if 0.5 <= e.confidence < 0.8]
        low_confidence = [e for e in self.extracted_ids if e.confidence < 0.5]
        
        # Group by message type
        by_message_type = {}
        for extraction in self.extracted_ids:
            msg_type = extraction.message_type
            if msg_type not in by_message_type:
                by_message_type[msg_type] = 0
            by_message_type[msg_type] += 1
            
        return {
            "total_extractions": len(self.extracted_ids),
            "unique_players": len(self.unique_player_ids),
            "confidence_breakdown": {
                "high_confidence": len(high_confidence),
                "medium_confidence": len(medium_confidence), 
                "low_confidence": len(low_confidence)
            },
            "by_message_type": by_message_type,
            "unique_player_ids": list(self.unique_player_ids)
        }
        
    def get_high_confidence_ids(self) -> Set[str]:
        """Get player IDs with high confidence scores."""
        return {
            e.player_id for e in self.extracted_ids 
            if e.confidence >= 0.8
        }
        
    def save_extractions(self, filename: str):
        """Save all extractions to a JSON file for analysis."""
        data = {
            "extraction_timestamp": datetime.now().isoformat(),
            "summary": self.get_extraction_summary(),
            "extractions": [
                {
                    "player_id": e.player_id,
                    "timestamp": e.timestamp,
                    "message_type": e.message_type,
                    "websocket_url": e.websocket_url,
                    "context_fields": e.context_fields,
                    "confidence": e.confidence,
                    "raw_message": e.raw_message[:500]  # Truncate for readability
                }
                for e in self.extracted_ids
            ]
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Player ID extractions saved to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save extractions: {e}")


def analyze_draft_message_for_players(payload: str, websocket_url: str = "") -> List[str]:
    """
    Quick utility function to extract player IDs from a single message.
    
    Args:
        payload: WebSocket message payload
        websocket_url: Source URL (optional)
        
    Returns:
        List of extracted player ID strings
    """
    extractor = PlayerIdExtractor()
    extractions = extractor.extract_from_message(payload, websocket_url)
    return [e.player_id for e in extractions if e.confidence >= 0.5]


if __name__ == "__main__":
    # Example usage and testing
    print("ESPN Player ID Extractor - Test Mode")
    
    # Test with sample JSON that might come from ESPN
    test_messages = [
        '{"type":"PICK_MADE","playerId":4241457,"teamId":1,"pickNumber":12}',
        '{"event":"draft_pick","player":{"id":3916387,"name":"Josh Allen","pos":"QB"}}',
        '{"data":{"selectedPlayer":{"playerId":"4362628","fullName":"Justin Jefferson"}}}'
    ]
    
    extractor = PlayerIdExtractor()
    
    for i, msg in enumerate(test_messages):
        print(f"\nTesting message {i+1}: {msg}")
        extractions = extractor.extract_from_message(msg, f"test_ws_{i}")
        for extraction in extractions:
            print(f"  Found player ID: {extraction.player_id} (confidence: {extraction.confidence})")
            
    print(f"\nSummary: {extractor.get_extraction_summary()}")