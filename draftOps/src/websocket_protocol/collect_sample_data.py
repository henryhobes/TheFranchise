#!/usr/bin/env python3
"""
Sample Draft Data Collector

Quick utility to collect draft data samples for analysis.
Can be used to test the player ID extraction system or gather data
for ESPN API cross-referencing.

Usage:
    python collect_sample_data.py [--duration 300] [--headless]
"""

import asyncio
import argparse
import json
from pathlib import Path
from datetime import datetime

from player_id_logger import PlayerIdDraftLogger


async def collect_draft_samples(duration: int = 300, headless: bool = False):
    """
    Collect draft samples for a specified duration.
    
    Args:
        duration: Collection time in seconds
        headless: Run browser in headless mode
    """
    print("📊 ESPN Draft Sample Data Collector")
    print("=" * 40)
    print(f"Collection time: {duration} seconds")
    print(f"Headless mode: {headless}")
    print()
    
    collector = PlayerIdDraftLogger(headless=headless)
    
    try:
        await collector.run_player_id_analysis(duration=duration)
    except Exception as e:
        print(f"Error during collection: {e}")
        

def create_mock_samples():
    """Create some mock sample data for testing when live drafts aren't available."""
    print("Creating mock sample data for testing...")
    
    # Sample ESPN-like messages based on research
    mock_messages = [
        {
            "type": "PICK_MADE",
            "playerId": 4241457,  # Najee Harris (from research)
            "teamId": 1,
            "pickNumber": 12,
            "round": 1,
            "timestamp": datetime.now().isoformat()
        },
        {
            "event": "draft_pick",
            "player": {
                "id": 3916387,  # Josh Allen
                "name": "Josh Allen",
                "pos": "QB",
                "team": "BUF",
                "fullName": "Josh Allen"
            },
            "draftInfo": {
                "pickNumber": 1,
                "round": 1,
                "teamId": 2
            }
        },
        {
            "data": {
                "selectedPlayer": {
                    "playerId": "4362628",  # Justin Jefferson
                    "fullName": "Justin Jefferson",
                    "position": "WR",
                    "nflTeam": "MIN",
                    "injuryStatus": "ACTIVE"
                },
                "pickInfo": {
                    "overall": 3,
                    "round": 1,
                    "teamIndex": 2
                }
            }
        },
        {
            "messageType": "ON_THE_CLOCK",
            "teamId": 4,
            "timeRemaining": 90,
            "pickNumber": 13,
            "round": 2
        },
        {
            "type": "ROSTER_UPDATE",
            "teamId": 1,
            "roster": {
                "QB": [{"playerId": 3916387, "name": "Josh Allen"}],
                "RB": [{"playerId": 4241457, "name": "Najee Harris"}],
                "WR": [{"playerId": 4362628, "name": "Justin Jefferson"}],
                "TE": [],
                "K": [],
                "DST": []
            }
        },
        {
            "event": "draft_pick",
            "player": {
                "id": 4567890,  # Mock rookie
                "name": "Rookie Player",
                "pos": "RB",
                "team": "NYG",
                "fullName": "Mock Rookie Player",
                "rookieYear": 2025
            }
        },
        {
            "type": "PICK_MADE",
            "playerId": 123456,  # Team Defense
            "teamId": 3,
            "pickNumber": 120,
            "round": 9,
            "playerType": "DST",
            "nflTeam": "SF"
        }
    ]
    
    # Create mock data directory
    mock_dir = Path("reports/mock_samples")
    mock_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mock_file = mock_dir / f"mock_draft_messages_{timestamp}.json"
    
    with open(mock_file, 'w') as f:
        json.dump(mock_messages, f, indent=2)
        
    print(f"Mock samples created: {mock_file}")
    
    # Test the extractor on mock data
    from utils.player_id_extractor import PlayerIdExtractor
    
    extractor = PlayerIdExtractor()
    total_extractions = 0
    
    print("\nTesting extractor on mock messages:")
    for i, message in enumerate(mock_messages, 1):
        payload = json.dumps(message)
        extractions = extractor.extract_from_message(payload, f"mock_ws_{i}", "mock_test")
        total_extractions += len(extractions)
        
        if extractions:
            print(f"  Message {i}: Found {len(extractions)} player ID(s)")
            for ext in extractions:
                print(f"    ID: {ext.player_id} (confidence: {ext.confidence:.2f})")
        else:
            print(f"  Message {i}: No player IDs found")
            
    print(f"\nMock Test Summary:")
    summary = extractor.get_extraction_summary()
    print(f"  Total extractions: {summary['total_extractions']}")
    print(f"  Unique players: {summary['unique_players']}")
    print(f"  High confidence: {summary['confidence_breakdown']['high_confidence']}")
    
    # Save mock extraction results
    mock_results_file = mock_dir / f"mock_extraction_results_{timestamp}.json"
    extractor.save_extractions(str(mock_results_file))
    
    print(f"  Results saved: {mock_results_file}")


def main():
    parser = argparse.ArgumentParser(description="Collect ESPN draft sample data")
    parser.add_argument("--duration", type=int, default=300,
                       help="Collection duration in seconds (default: 300)")
    parser.add_argument("--headless", action="store_true",
                       help="Run browser in headless mode")
    parser.add_argument("--mock", action="store_true",
                       help="Create mock sample data for testing")
    
    args = parser.parse_args()
    
    if args.mock:
        create_mock_samples()
    else:
        print("Starting live draft data collection...")
        print("Make sure to join an active ESPN mock draft!")
        print()
        
        try:
            asyncio.run(collect_draft_samples(args.duration, args.headless))
        except KeyboardInterrupt:
            print("\nCollection stopped by user")
        except Exception as e:
            print(f"Collection error: {e}")


if __name__ == "__main__":
    main()