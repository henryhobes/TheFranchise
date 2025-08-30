#!/usr/bin/env python3
"""
Cross-Reference Validator

Validates player IDs extracted from WebSocket messages by cross-referencing
them with ESPN's API data to ensure consistency and accuracy.

Part of Sprint 0 Player ID System Reverse Engineering.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field

from utils.player_id_extractor import PlayerIdExtractor, PlayerIdExtraction
from api.espn_api_client import ESPNApiClient, ESPNPlayer


@dataclass
class CrossReferenceResult:
    """Result of cross-referencing a WebSocket player ID with API data."""
    player_id: str
    websocket_extraction: PlayerIdExtraction
    api_player: Optional[ESPNPlayer]
    validation_status: str  # "VALIDATED", "NOT_FOUND", "MISMATCH", "ERROR"
    confidence_score: float
    discrepancies: List[str] = field(default_factory=list)
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CrossReferenceValidator:
    """
    Validates player IDs from WebSocket messages against ESPN API data.
    
    This helps ensure that our player ID extraction is accurate and that
    the IDs we collect from draft messages can be reliably used for
    player name resolution.
    """
    
    def __init__(self, api_client: Optional[ESPNApiClient] = None):
        self.api_client = api_client
        self.validation_results: List[CrossReferenceResult] = []
        self.validated_ids: Set[str] = set()
        
        self.logger = logging.getLogger(__name__)
        
    async def validate_extractions(self, extractions: List[PlayerIdExtraction],
                                 api_client: Optional[ESPNApiClient] = None) -> List[CrossReferenceResult]:
        """
        Validate a list of player ID extractions against API data.
        
        Args:
            extractions: List of player ID extractions from WebSocket messages
            api_client: ESPN API client (uses self.api_client if not provided)
            
        Returns:
            List of cross-reference results
        """
        client = api_client or self.api_client
        if not client:
            raise ValueError("No API client available for validation")
            
        # Get unique player IDs from extractions
        unique_ids = list(set(e.player_id for e in extractions))
        
        self.logger.info(f"Validating {len(unique_ids)} unique player IDs from {len(extractions)} extractions")
        
        # Batch fetch from API
        api_results = await client.batch_get_players(unique_ids)
        
        # Create validation results
        results = []
        for extraction in extractions:
            api_player = api_results.get(extraction.player_id)
            result = self._create_validation_result(extraction, api_player)
            results.append(result)
            
        self.validation_results.extend(results)
        self.validated_ids.update(unique_ids)
        
        return results
        
    def _create_validation_result(self, extraction: PlayerIdExtraction, 
                                api_player: Optional[ESPNPlayer]) -> CrossReferenceResult:
        """Create a cross-reference result from extraction and API data."""
        discrepancies = []
        
        if api_player is None:
            # Player not found in API
            status = "NOT_FOUND"
            confidence = 0.0
            discrepancies.append("Player ID not found in ESPN API")
            
        else:
            # Player found - check for consistency
            status = "VALIDATED"
            confidence = extraction.confidence
            
            # Check if context data matches API data
            if extraction.context_fields:
                context = extraction.context_fields
                
                # Check name consistency
                if 'name' in context or 'fullName' in context:
                    context_name = context.get('name', context.get('fullName', '')).strip().lower()
                    api_name = api_player.full_name.strip().lower()
                    
                    if context_name and context_name != api_name:
                        discrepancies.append(f"Name mismatch: '{context_name}' vs '{api_name}'")
                        confidence *= 0.8
                        
                # Check position consistency
                if 'position' in context or 'pos' in context:
                    context_pos = context.get('position', context.get('pos', '')).strip().upper()
                    api_pos = api_player.position.strip().upper()
                    
                    if context_pos and context_pos != api_pos:
                        discrepancies.append(f"Position mismatch: '{context_pos}' vs '{api_pos}'")
                        confidence *= 0.9
                        
                # Check team consistency
                if 'team' in context or 'nflTeam' in context:
                    context_team = context.get('team', context.get('nflTeam', '')).strip().upper()
                    api_team = api_player.nfl_team.strip().upper()
                    
                    if context_team and api_team and context_team != api_team:
                        discrepancies.append(f"Team mismatch: '{context_team}' vs '{api_team}'")
                        confidence *= 0.9
                        
            # Determine final status
            if discrepancies:
                status = "MISMATCH" if confidence < 0.6 else "VALIDATED"
                
        return CrossReferenceResult(
            player_id=extraction.player_id,
            websocket_extraction=extraction,
            api_player=api_player,
            validation_status=status,
            confidence_score=confidence,
            discrepancies=discrepancies
        )
        
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary statistics about validation results."""
        if not self.validation_results:
            return {"total_validations": 0}
            
        total = len(self.validation_results)
        validated = len([r for r in self.validation_results if r.validation_status == "VALIDATED"])
        not_found = len([r for r in self.validation_results if r.validation_status == "NOT_FOUND"])
        mismatch = len([r for r in self.validation_results if r.validation_status == "MISMATCH"])
        
        # Calculate confidence distribution
        confidences = [r.confidence_score for r in self.validation_results]
        high_conf = len([c for c in confidences if c >= 0.8])
        medium_conf = len([c for c in confidences if 0.5 <= c < 0.8])
        low_conf = len([c for c in confidences if c < 0.5])
        
        # Get successfully validated players
        validated_players = []
        for result in self.validation_results:
            if result.validation_status == "VALIDATED" and result.api_player:
                validated_players.append({
                    "id": result.player_id,
                    "name": result.api_player.full_name,
                    "position": result.api_player.position,
                    "team": result.api_player.nfl_team,
                    "confidence": result.confidence_score
                })
                
        return {
            "total_validations": total,
            "validation_breakdown": {
                "validated": validated,
                "not_found": not_found,
                "mismatch": mismatch
            },
            "confidence_distribution": {
                "high_confidence": high_conf,
                "medium_confidence": medium_conf,
                "low_confidence": low_conf
            },
            "success_rate": validated / total if total > 0 else 0,
            "validated_players": validated_players[:10],  # Sample of validated players
            "total_validated_players": len(validated_players)
        }
        
    def get_problematic_ids(self) -> List[Dict[str, Any]]:
        """Get player IDs that failed validation or have issues."""
        problematic = []
        
        for result in self.validation_results:
            if result.validation_status in ["NOT_FOUND", "MISMATCH"]:
                problematic.append({
                    "player_id": result.player_id,
                    "status": result.validation_status,
                    "discrepancies": result.discrepancies,
                    "confidence": result.confidence_score,
                    "websocket_context": result.websocket_extraction.context_fields
                })
                
        return problematic
        
    def save_validation_results(self, filename: str):
        """Save all validation results to a JSON file."""
        data = {
            "validation_timestamp": datetime.now().isoformat(),
            "summary": self.get_validation_summary(),
            "problematic_ids": self.get_problematic_ids(),
            "detailed_results": [
                {
                    "player_id": r.player_id,
                    "validation_status": r.validation_status,
                    "confidence_score": r.confidence_score,
                    "discrepancies": r.discrepancies,
                    "websocket_data": {
                        "timestamp": r.websocket_extraction.timestamp,
                        "message_type": r.websocket_extraction.message_type,
                        "context_fields": r.websocket_extraction.context_fields,
                        "original_confidence": r.websocket_extraction.confidence
                    },
                    "api_data": {
                        "full_name": r.api_player.full_name if r.api_player else None,
                        "position": r.api_player.position if r.api_player else None,
                        "nfl_team": r.api_player.nfl_team if r.api_player else None,
                        "status": r.api_player.status if r.api_player else None
                    } if r.api_player else None
                }
                for r in self.validation_results
            ]
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Validation results saved to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save validation results: {e}")


async def validate_websocket_extractions(websocket_log_file: str, 
                                       output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Utility function to validate player IDs from a WebSocket log file.
    
    Args:
        websocket_log_file: Path to file containing WebSocket message log
        output_file: Optional path to save validation results
        
    Returns:
        Validation summary dictionary
    """
    print(f"Loading WebSocket messages from {websocket_log_file}...")
    
    # Load WebSocket messages
    try:
        with open(websocket_log_file, 'r') as f:
            messages = json.load(f)
    except Exception as e:
        print(f"Error loading WebSocket log: {e}")
        return {"error": str(e)}
        
    # Extract player IDs
    extractor = PlayerIdExtractor()
    all_extractions = []
    
    print(f"Processing {len(messages)} WebSocket messages...")
    for msg in messages:
        payload = msg.get('payload', '')
        websocket_url = msg.get('websocket_url', '')
        extractions = extractor.extract_from_message(payload, websocket_url)
        all_extractions.extend(extractions)
        
    print(f"Found {len(all_extractions)} player ID extractions")
    
    if not all_extractions:
        return {"error": "No player IDs found in WebSocket messages"}
        
    # Validate against API
    print("Validating against ESPN API...")
    async with ESPNApiClient() as api_client:
        validator = CrossReferenceValidator()
        results = await validator.validate_extractions(all_extractions, api_client)
        
    print(f"Validation complete. Processed {len(results)} extractions.")
    
    # Get summary
    summary = validator.get_validation_summary()
    
    # Save results if requested
    if output_file:
        validator.save_validation_results(output_file)
        print(f"Detailed results saved to {output_file}")
        
    return summary


async def test_cross_reference_validator():
    """Test the cross-reference validator with sample data."""
    print("Testing Cross-Reference Validator...")
    
    # Create sample extractions (simulating WebSocket data)
    from utils.player_id_extractor import PlayerIdExtraction
    
    test_extractions = [
        PlayerIdExtraction(
            player_id="4241457",
            timestamp=datetime.now().isoformat(),
            message_type="PICK_MADE",
            websocket_url="ws://test",
            raw_message='{"type":"PICK_MADE","playerId":4241457}',
            context_fields={"name": "Najee Harris", "pos": "RB"},
            confidence=0.9
        ),
        PlayerIdExtraction(
            player_id="3916387",
            timestamp=datetime.now().isoformat(),
            message_type="PICK_MADE",
            websocket_url="ws://test",
            raw_message='{"type":"PICK_MADE","playerId":3916387}',
            context_fields={"fullName": "Josh Allen", "position": "QB"},
            confidence=0.85
        ),
        PlayerIdExtraction(
            player_id="9999999",  # Non-existent ID
            timestamp=datetime.now().isoformat(),
            message_type="PICK_MADE",
            websocket_url="ws://test",
            raw_message='{"type":"PICK_MADE","playerId":9999999}',
            context_fields={},
            confidence=0.7
        )
    ]
    
    # Validate
    async with ESPNApiClient() as api_client:
        validator = CrossReferenceValidator()
        results = await validator.validate_extractions(test_extractions, api_client)
        
    # Print results
    print(f"\nValidation Results:")
    for result in results:
        print(f"  Player ID {result.player_id}: {result.validation_status}")
        if result.api_player:
            print(f"    API: {result.api_player.full_name} ({result.api_player.position})")
        if result.discrepancies:
            print(f"    Issues: {result.discrepancies}")
        print(f"    Confidence: {result.confidence_score:.2f}")
        
    # Print summary
    summary = validator.get_validation_summary()
    print(f"\nValidation Summary:")
    print(f"  Success rate: {summary['success_rate']:.2%}")
    print(f"  Validated: {summary['validation_breakdown']['validated']}")
    print(f"  Not found: {summary['validation_breakdown']['not_found']}")
    print(f"  Mismatches: {summary['validation_breakdown']['mismatch']}")


if __name__ == "__main__":
    asyncio.run(test_cross_reference_validator())