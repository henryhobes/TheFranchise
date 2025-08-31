#!/usr/bin/env python3
"""
Draft State Live Testing Script

End-to-end testing script for the complete draft state management system
using live ESPN mock drafts.
"""

import asyncio
import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from state.integration import create_draft_state_manager
from state.draft_state import DraftStatus


class DraftStateLiveTest:
    """Live testing framework for draft state management."""
    
    def __init__(self, league_id: str, team_id: str, 
                 team_count: int = 12, rounds: int = 16):
        """
        Initialize live test.
        
        Args:
            league_id: ESPN league ID
            team_id: User's team ID
            team_count: Number of teams
            rounds: Number of rounds
        """
        self.league_id = league_id
        self.team_id = team_id
        self.team_count = team_count
        self.rounds = rounds
        
        self.manager: Optional[object] = None
        
        # Test results tracking
        self.test_results = {
            'start_time': None,
            'end_time': None,
            'total_picks_processed': 0,
            'state_validation_errors': [],
            'performance_metrics': {},
            'final_state': {},
            'success': False
        }
        
        # Test callbacks
        self.pick_count = 0
        self.last_validation_time = None
        
        self.logger = logging.getLogger(__name__)
        
    async def run_live_test(self, draft_url: str, test_duration_minutes: int = 30) -> Dict[str, Any]:
        """
        Run complete live test of draft state system.
        
        Args:
            draft_url: ESPN draft room URL
            test_duration_minutes: Maximum test duration
            
        Returns:
            Test results dictionary
        """
        self.test_results['start_time'] = datetime.now().isoformat()
        
        try:
            # Initialize system
            self.logger.info("Initializing draft state management system...")
            self.manager = await create_draft_state_manager(
                self.league_id, self.team_id, self.team_count, self.rounds
            )
            
            # Set up test callbacks
            self._setup_test_callbacks()
            
            # Connect to draft
            self.logger.info(f"Connecting to draft: {draft_url}")
            success = await self.manager.connect_to_draft(draft_url)
            
            if not success:
                raise RuntimeError("Failed to connect to draft room")
                
            # Set up draft order (example for 12-team league)
            team_order = [str(i) for i in range(1, self.team_count + 1)]
            self.manager.set_draft_order(team_order)
            
            # Monitor draft
            self.logger.info(f"Starting draft monitoring (max {test_duration_minutes} minutes)")
            await self._monitor_draft_with_testing(test_duration_minutes * 60)
            
            # Final validation
            await self._perform_final_validation()
            
            self.test_results['success'] = True
            self.logger.info("Live test completed successfully")
            
        except Exception as e:
            self.logger.error(f"Live test failed: {e}")
            self.test_results['success'] = False
            self.test_results['error'] = str(e)
            
        finally:
            self.test_results['end_time'] = datetime.now().isoformat()
            if self.manager:
                await self.manager.close()
                
        return self.test_results
        
    def _setup_test_callbacks(self):
        """Set up callbacks for testing."""
        
        def on_pick_processed(pick_data: Dict[str, Any]):
            """Handle pick processed for testing."""
            self.pick_count += 1
            self.test_results['total_picks_processed'] = self.pick_count
            
            self.logger.info(
                f"Pick {self.pick_count}: {pick_data.get('player_name', 'Unknown')} "
                f"to team {pick_data['team_id']} (Pick #{pick_data['pick_number']})"
            )
            
            # Validate state after every 5th pick
            if self.pick_count % 5 == 0:
                asyncio.create_task(self._validate_state_async())
                
        def on_state_updated(state_summary: Dict[str, Any]):
            """Handle state updates for testing."""
            # Update performance metrics
            perf = state_summary.get('performance', {})
            self.test_results['performance_metrics'] = perf
            
            # Check processing speed
            avg_time = perf.get('avg_processing_time_ms', 0)
            if avg_time > 200:
                self.logger.warning(f"Processing time exceeds 200ms: {avg_time:.2f}ms")
                
        def on_error(error_msg: str):
            """Handle errors for testing."""
            self.logger.error(f"System error: {error_msg}")
            self.test_results['state_validation_errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': error_msg
            })
            
        self.manager.on_pick_processed = on_pick_processed
        self.manager.on_state_updated = on_state_updated
        self.manager.on_error = on_error
        
    async def _monitor_draft_with_testing(self, duration_seconds: int):
        """Monitor draft with periodic testing."""
        
        start_time = asyncio.get_event_loop().time()
        validation_interval = 30  # Validate every 30 seconds
        last_validation = start_time
        
        while True:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            
            # Check timeout
            if elapsed >= duration_seconds:
                self.logger.info("Test duration reached")
                break
                
            # Check if draft completed
            if self.manager.draft_state.draft_status == DraftStatus.COMPLETED:
                self.logger.info("Draft completed naturally")
                break
                
            # Periodic validation
            if current_time - last_validation >= validation_interval:
                await self._validate_state_async()
                last_validation = current_time
                
                # Resolve queued players
                resolved_count = await self.manager.resolve_queued_players()
                if resolved_count > 0:
                    self.logger.debug(f"Resolved {resolved_count} player names")
                    
            await asyncio.sleep(1)
            
    async def _validate_state_async(self):
        """Async state validation wrapper."""
        try:
            validation = self.manager.validate_current_state()
            self.last_validation_time = validation['timestamp']
            
            if not validation['is_valid']:
                self.logger.warning(f"State validation failed: {validation['errors']}")
                self.test_results['state_validation_errors'].append(validation)
            else:
                self.logger.debug("State validation passed")
                
        except Exception as e:
            self.logger.error(f"State validation error: {e}")
            
    async def _perform_final_validation(self):
        """Perform comprehensive final validation."""
        
        self.logger.info("Performing final state validation...")
        
        # Get final state summary
        final_summary = self.manager.get_state_summary()
        self.test_results['final_state'] = final_summary
        
        # Comprehensive validation
        validation = self.manager.validate_current_state()
        
        if not validation['is_valid']:
            self.test_results['state_validation_errors'].append({
                'type': 'final_validation',
                'timestamp': datetime.now().isoformat(),
                'errors': validation['errors'],
                'warnings': validation['warnings']
            })
            
        # Check success criteria from Sprint 1 spec
        success_criteria = self._evaluate_success_criteria(final_summary)
        self.test_results['success_criteria'] = success_criteria
        
        self.logger.info(f"Final validation complete. Success criteria: {success_criteria}")
        
    def _evaluate_success_criteria(self, state_summary: Dict[str, Any]) -> Dict[str, bool]:
        """
        Evaluate Sprint 1 success criteria.
        
        From spec:
        - Track complete mock draft end-to-end without state errors
        - State accuracy matches ESPN UI 100% of the time  
        - Update latency under 200ms per WebSocket message
        - Zero state corruption throughout draft session
        """
        
        criteria = {}
        
        # No state errors
        criteria['no_state_errors'] = len(self.test_results['state_validation_errors']) == 0
        
        # Processing speed under 200ms
        avg_time = state_summary.get('performance', {}).get('avg_processing_time_ms', 0)
        criteria['processing_under_200ms'] = avg_time < 200
        
        # State consistency
        draft_state = self.manager.draft_state
        expected_picks = len(draft_state.pick_history)
        actual_picks = len(draft_state.drafted_players)
        criteria['pick_consistency'] = expected_picks == actual_picks
        
        # No corruption (basic check)
        validation = self.manager.validate_current_state()
        criteria['no_state_corruption'] = validation['is_valid']
        
        # Message processing success
        perf = state_summary.get('performance', {})
        total_messages = perf.get('messages_processed', 0)
        errors = perf.get('errors', 0)
        criteria['high_message_success_rate'] = (errors / max(total_messages, 1)) < 0.05
        
        return criteria
        
    def save_test_results(self, output_file: Optional[str] = None):
        """Save test results to JSON file."""
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"draft_state_test_results_{timestamp}.json"
            
        try:
            with open(output_file, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            self.logger.info(f"Test results saved to: {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save test results: {e}")
            
    def print_test_summary(self):
        """Print human-readable test summary."""
        
        print("\n" + "="*60)
        print("DRAFT STATE LIVE TEST SUMMARY")
        print("="*60)
        
        success = self.test_results['success']
        print(f"Overall Success: {'✅ PASSED' if success else '❌ FAILED'}")
        
        print(f"\nTest Duration: {self.test_results.get('start_time', 'N/A')} to {self.test_results.get('end_time', 'N/A')}")
        print(f"Total Picks Processed: {self.test_results['total_picks_processed']}")
        print(f"State Validation Errors: {len(self.test_results['state_validation_errors'])}")
        
        # Performance metrics
        perf = self.test_results.get('performance_metrics', {})
        print(f"\nPerformance Metrics:")
        print(f"  Messages Processed: {perf.get('messages_processed', 0)}")
        print(f"  Average Processing Time: {perf.get('avg_processing_time_ms', 0):.2f}ms")
        print(f"  Player Resolutions: {perf.get('player_resolutions', 0)}")
        print(f"  Errors: {perf.get('errors', 0)}")
        
        # Success criteria
        if 'success_criteria' in self.test_results:
            print(f"\nSuccess Criteria:")
            for criterion, passed in self.test_results['success_criteria'].items():
                status = '✅' if passed else '❌'
                print(f"  {criterion}: {status}")
                
        # Errors
        if self.test_results['state_validation_errors']:
            print(f"\nValidation Errors:")
            for error in self.test_results['state_validation_errors'][-3:]:  # Last 3 errors
                print(f"  {error.get('timestamp', 'N/A')}: {error.get('error', error)}")
                
        print("="*60)


async def main():
    """Main test execution."""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"draft_state_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )
    
    # Test configuration
    LEAGUE_ID = "262233108"  # From Sprint 0
    TEAM_ID = "1"
    
    # Get draft URL from command line or use default
    if len(sys.argv) > 1:
        draft_url = sys.argv[1]
    else:
        draft_url = "https://fantasy.espn.com/football/mockdraftlobby"
        print(f"No draft URL provided. Using: {draft_url}")
        print("Usage: python draft_state_live_test.py <draft_room_url>")
        
    # Run test
    tester = DraftStateLiveTest(LEAGUE_ID, TEAM_ID)
    
    try:
        results = await tester.run_live_test(draft_url, test_duration_minutes=30)
        
        # Save and display results
        tester.save_test_results()
        tester.print_test_summary()
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        tester.print_test_summary()
        sys.exit(1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())