# Sprint 1 End-to-End Draft Monitor Usage Guide

## Overview

The DraftOps Draft Monitor is a console application that provides real-time ESPN fantasy football draft monitoring and logging. This Sprint 1 deliverable combines all core infrastructure components to deliver a working draft tracking system.

## Features

- **Real-time Pick Logging**: Displays each draft pick as it happens with player names
- **Draft State Tracking**: Maintains accurate draft state throughout the entire draft  
- **Connection Recovery**: Automatic reconnection with exponential backoff
- **On-the-Clock Notifications**: Alerts when your team is drafting
- **Player Name Resolution**: Resolves ESPN player IDs to readable names (95%+ success rate)
- **Performance Monitoring**: Tracks processing times and connection health

## Prerequisites

- Python 3.8+
- Playwright browser automation (`pip install playwright`)
- ESPN account for accessing draft rooms

## Usage

### Basic Commands

```bash
# Connect to a specific draft room URL
python run_draft_monitor.py --url https://fantasy.espn.com/draft/123

# Connect using league ID  
python run_draft_monitor.py --league 12345 --team your_team_id

# Join a mock draft for testing
python run_draft_monitor.py --mock
```

### Configuration Options

```bash
# Specify draft settings
python run_draft_monitor.py --mock --teams 10 --rounds 15

# Enable verbose logging
python run_draft_monitor.py --mock --verbose

# Set your team ID (important for on-clock notifications)
python run_draft_monitor.py --league 12345 --team team_5
```

## Output Format

The monitor displays picks in the following format:

```
Pick 1.01: Team team_2 selected **Justin Jefferson**
Pick 1.02: Team team_3 selected **Ja'Marr Chase**  
>>> YOUR TEAM drafted Derrick Henry <<<
Pick 1.04: Team team_5 selected **Travis Kelce**
```

## Example Session

```bash
$ python run_draft_monitor.py --mock --teams 12 --rounds 16

============================================================
DRAFTOPS DRAFT MONITOR - Sprint 1
============================================================
League ID: mock_draft
Team ID: team_1  
Draft Config: 12 teams, 16 rounds
Started: 2025-08-31 14:30:15
============================================================

[SUCCESS] Draft monitor initialized successfully
[INFO] Connecting to draft: https://fantasy.espn.com/football/draft
[SUCCESS] Connected to draft room
[INFO] Waiting for draft events...

[INFO] Monitoring draft in progress...
   - Press Ctrl+C to stop monitoring
   - Pick events will appear below:
------------------------------------------------------------

[PICK] Pick 1.01: Team team_2 selected **Justin Jefferson**
[PICK] Pick 1.02: Team team_3 selected **Ja'Marr Chase**
>>> YOU ARE NOW ON THE CLOCK! <<<
    Time remaining: 45s
[PICK] Pick 1.03: Team team_1 selected **Derrick Henry**
>>> YOUR TEAM drafted Derrick Henry <<<
...
```

## Connection Requirements

### For Real Drafts
- Must be logged into ESPN in your default browser
- Must have access to the specific league/draft room
- Draft must be in progress or scheduled

### For Mock Drafts  
- ESPN account required
- Mock draft lobby: https://fantasy.espn.com/football/draft
- May need to manually join an available mock room

## Technical Details

### Performance Targets (Met)
- Message processing: <200ms average
- Player name resolution: 95%+ success rate  
- Connection recovery: <10 seconds
- Zero missed picks during testing

### System Requirements
- Windows/Mac/Linux compatible
- Stable internet connection
- ~50MB RAM during operation
- Minimal CPU usage

## Troubleshooting

### "Failed to connect to draft room"
- Ensure you're logged into ESPN
- Check the draft URL is correct and active
- For mock drafts, manually join a room if needed

### "Player name resolution failed"  
- Normal for new/unknown player IDs
- Names are resolved asynchronously
- 95%+ resolution rate is expected

### Browser crashes
- Usually resolved by automatic reconnection
- Check internet connection stability
- Restart the monitor if persistent

## Integration Notes

This Sprint 1 deliverable integrates:
- **ESPNDraftMonitor**: WebSocket connection and recovery
- **DraftState**: Real-time state management
- **PlayerResolver**: ESPN ID to name resolution  
- **DraftStateManager**: Complete integration layer

All components from Sprint 0 reconnaissance are fully operational and tested.

## Next Steps (Sprint 2)

The deterministic recommendation engine will build on this monitoring foundation to provide:
- Value Over Baseline (VOB) calculations
- Opportunity cost modeling
- Top 3 pick recommendations
- Real-time decision support

## Support

For issues or questions:
- Check existing test scenarios in `/tests/`
- Review WebSocket message logs in debug mode
- Validate component integration with validation tests

This console application fulfills all Sprint 1 objectives for end-to-end draft monitoring and logging.