# ESPN Draft WebSocket Protocol Discovery

**Sprint 0 Implementation** - Reconnaissance phase for ESPN fantasy football draft WebSocket protocol mapping.

## Overview

This implementation validates our ability to intercept and understand ESPN's WebSocket draft communications. The goal is to prove we can reliably capture draft events in real-time and comprehend the message format.

## Project Structure

```
websocket_protocol/
├── monitor/
│   ├── __init__.py
│   └── espn_draft_monitor.py    # Core WebSocket monitoring class
├── protocol/
│   └── __init__.py              # (Future: message parsers)
├── utils/
│   ├── __init__.py
│   └── websocket_discovery.py  # WebSocket analysis utilities
├── discover_espn_protocol.py   # Main discovery script
├── poc_draft_logger.py         # Proof-of-concept logger
└── README.md                   # This file
```

## Quick Start

### 1. Prerequisites

Ensure you have the Python virtual environment set up with Playwright:

```bash
# From project root
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
playwright install
```

### 2. Run Tests

Verify everything is working:

```bash
python test_websocket_monitor.py
```

You should see "OK All tests passed! System ready for use."

### 3. Discovery Mode

Run the comprehensive protocol discovery script:

```bash
cd draftOps/src/websocket_protocol
python discover_espn_protocol.py
```

This will:
- Open ESPN mock draft lobby in browser
- Wait for you to join a draft room
- Monitor all WebSocket traffic
- Generate detailed analysis reports

### 4. Simple Logging Mode

For focused draft event monitoring:

```bash
cd draftOps/src/websocket_protocol  
python poc_draft_logger.py
```

This provides:
- Real-time draft event detection
- Clean console output
- Focused on pick announcements

## Usage Instructions

### Joining ESPN Mock Drafts

1. Script opens ESPN mock draft lobby
2. **Navigate to and JOIN an active mock draft**
3. Watch console for WebSocket connections
4. Monitor draft events in real-time
5. Results saved to `reports/` folder

### Key Features

**ESPNDraftMonitor Class:**
- Playwright-based WebSocket monitoring
- Automatic frame capture (sent/received)
- Connection resilience handling
- Message logging and analysis

**WebSocketDiscovery Utility:**
- Endpoint categorization  
- Message pattern analysis
- Draft-related content detection
- Protocol schema extraction

**Discovery Scripts:**
- Comprehensive traffic analysis
- Detailed reporting
- Multiple output formats
- Real-time monitoring feedback

## Output Files

All results are saved in the `reports/` directory:

- `espn_websocket_messages_TIMESTAMP.json` - Raw message log
- `espn_protocol_analysis_TIMESTAMP.json` - Comprehensive analysis
- `poc_draft_events_TIMESTAMP.json` - Draft-specific events only

## Configuration Options

### ESPNDraftMonitor

```python
monitor = ESPNDraftMonitor(
    headless=False,        # Set to True to hide browser
    log_level=logging.INFO # Adjust logging verbosity
)
```

### Discovery Script

```bash
python discover_espn_protocol.py --headless --duration 600
```

- `--headless`: Run browser in background
- `--duration SECONDS`: How long to monitor (default: 300)

## Development Notes

### Message Detection Heuristics

The system identifies draft-related messages using keywords:
- "pick", "draft", "player", "team", "roster"
- "clock", "turn", "selected", "available"
- "PICK_MADE", "ON_THE_CLOCK", "ROSTER_UPDATE"

### WebSocket Analysis

Endpoints are analyzed for:
- ESPN-specific URL patterns
- Draft-related path components  
- Message content analysis
- Protocol pattern detection

### Connection Handling

- Automatic WebSocket discovery via `page.on('websocket')`
- Frame-level monitoring with `framereceived`/`framesent`
- Connection state tracking
- Graceful error handling

## Troubleshooting

### No WebSocket Connections Found

**Issue**: Script reports no WebSocket connections  
**Solution**: 
1. Manually join a mock draft in the browser
2. Ensure draft has started (picks are happening)
3. Check browser console for errors
4. Try different draft rooms

### Import Errors

**Issue**: Module import failures  
**Solution**:
1. Verify virtual environment is activated
2. Check Python path includes websocket_protocol directory
3. Run test script to verify setup

### Browser Issues

**Issue**: Playwright browser fails to start  
**Solution**:
1. Run `playwright install` again
2. Check system permissions
3. Try headless mode: `--headless`

## Sprint 0 Success Criteria

- ✓ Can connect to ESPN draft rooms programmatically
- ✓ WebSocket monitoring system implemented  
- ✓ Message capture and analysis tools ready
- ⏳ Capture complete draft events (pending live testing)
- ⏳ Protocol documentation (pending analysis results)
- ⏳ Connection stability validation (pending extended testing)

## Next Steps (Sprint 1)

1. **Live Testing**: Run scripts against actual ESPN mock drafts
2. **Protocol Documentation**: Populate analysis document with findings
3. **Message Parsing**: Build specific handlers for identified message types
4. **Connection Manager**: Implement robust reconnection logic
5. **State Management**: Track draft state based on WebSocket events

## Legal Considerations

- **Read-only monitoring only** - No draft actions automated
- **Single session usage** - No concurrent connections
- **ESPN Terms of Service** - Use responsibly and sparingly
- **Testing focus** - Primarily on mock drafts, not real money leagues

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test script output for system validation
3. Examine generated log files in `reports/` directory
4. Verify ESPN mock draft availability and accessibility