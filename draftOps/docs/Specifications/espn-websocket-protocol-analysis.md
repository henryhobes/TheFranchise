# ESPN Draft WebSocket Protocol Analysis

**Status**: Sprint 0 - Initial Discovery  
**Last Updated**: August 30, 2025  
**Next Review**: After Mock Draft Testing  

## Executive Summary

This document captures the discovered WebSocket protocol used by ESPN fantasy football draft rooms. This analysis is part of Sprint 0 reconnaissance to validate the feasibility of real-time draft monitoring.

## Discovery Methodology

### Tools Used
- **Playwright**: Browser automation with WebSocket monitoring via `page.on('websocket')` 
- **Chrome DevTools**: Manual inspection of network traffic
- **Custom Scripts**: `discover_espn_protocol.py` and `poc_draft_logger.py`

### Discovery Process
1. Connect to ESPN mock draft lobby
2. Join active mock draft rooms
3. Monitor WebSocket traffic during draft events
4. Categorize and analyze message patterns
5. Document connection requirements and message schemas

## WebSocket Connection Analysis

### Discovered Endpoints

*This section will be populated after running discovery scripts against live ESPN drafts.*

**Example Expected Patterns:**
- `wss://draft-socket.fantasy.espn.com/...`
- `wss://live-draft.fantasy.espn.com/...`
- `wss://socket.fantasy.espn.com/...`

### Connection Requirements

*To be documented after analysis:*
- Authentication headers
- Session cookies required
- Handshake parameters
- Connection persistence methods

## Message Type Analysis

### Identified Message Types

*This section will contain actual discovered message types. Expected types based on draft functionality:*

#### PICK_MADE
**Purpose**: Announces when a player has been drafted  
**Frequency**: Once per pick  
**Structure**: TBD after analysis  

**Expected Fields:**
- Player identifier (ESPN ID)
- Team/manager identifier  
- Pick number
- Timestamp
- Round information

#### ON_THE_CLOCK
**Purpose**: Indicates which team/manager is currently drafting  
**Frequency**: Once per turn change  
**Structure**: TBD after analysis  

**Expected Fields:**
- Team identifier
- Time remaining
- Pick number
- Round information

#### ROSTER_UPDATE
**Purpose**: Updates team rosters after picks  
**Frequency**: After each pick  
**Structure**: TBD after analysis  

**Expected Fields:**
- Team identifier
- Updated roster composition
- Positional counts

#### DRAFT_STATUS
**Purpose**: Overall draft state updates  
**Frequency**: Various triggers  
**Structure**: TBD after analysis  

**Expected Fields:**
- Draft phase (pre-draft, active, completed)
- Current round
- Available player pool updates

### Message Schemas

*JSON schemas will be documented here after protocol analysis.*

## Connection Stability Analysis

### Observed Behavior

*To be filled after testing:*
- Connection timeout behavior
- Reconnection patterns
- Message ordering guarantees
- Heartbeat/keepalive mechanisms

### Reliability Assessment

*Results from connection resilience testing:*
- Average connection duration
- Disconnection frequency
- Recovery success rate
- Message loss incidents

## Player Identification System

### ESPN Player IDs

*Analysis of how players are identified in messages:*
- ID format and structure
- Consistency across draft rooms
- Mapping to player names
- Handling of rookies/new players

### Data Correlation

*Methodology for matching ESPN IDs to external data sources:*
- Cross-reference with ESPN API
- Mapping to other fantasy platforms
- Name resolution strategies

## Protocol Versioning

### Version Detection

*Methods for identifying protocol versions:*
- Message format changes
- New field additions
- Deprecated message types

### Backwards Compatibility

*Assessment of protocol stability:*
- Breaking change frequency
- Migration strategies
- Fallback mechanisms

## Implementation Recommendations

### Connection Strategy

Based on discovery findings:

1. **Primary Method**: WebSocket monitoring via Playwright
2. **Fallback Options**: 
   - ESPN API polling (if WebSocket unavailable)
   - DOM scraping (last resort)
   - HAR file replay (for testing)

### Message Handling

Recommended approach for processing messages:

1. **Real-time Processing**: Handle critical messages immediately
2. **Buffering**: Queue non-critical updates for batch processing
3. **Error Recovery**: Graceful handling of malformed messages
4. **State Validation**: Cross-check message data with known state

### Performance Considerations

- **Latency Target**: <50ms from WebSocket frame to state update
- **Memory Usage**: Efficient message buffering and cleanup
- **CPU Usage**: Optimized JSON parsing and state management

## Risk Assessment

### Technical Risks

**Protocol Changes**: ESPN may modify message formats without notice
- *Mitigation*: Versioned protocol handlers, golden-file testing

**Connection Reliability**: WebSocket may disconnect during drafts
- *Mitigation*: Automatic reconnection with state recovery

**Rate Limiting**: ESPN may throttle connections
- *Mitigation*: Single connection, respectful usage patterns

### Legal Considerations

**Terms of Service**: ESPN prohibits automated access
- *Mitigation*: Read-only monitoring, single session, HAR mode option

**Account Risk**: Potential for account termination
- *Mitigation*: Test accounts, conservative usage, disclaimer

## Testing Results

### Mock Draft Analysis

*Results from testing with ESPN mock drafts:*
- Total drafts monitored: TBD
- Messages captured: TBD
- Connection success rate: TBD
- Protocol coverage: TBD

### Performance Metrics

- **Message Processing Latency**: TBD
- **Connection Stability**: TBD
- **Memory Usage**: TBD
- **CPU Impact**: TBD

## Next Steps

### Sprint 1 Requirements

Based on this analysis, Sprint 1 should focus on:

1. **Connection Manager**: Robust WebSocket connection handling
2. **Message Parser**: Efficient processing of identified message types  
3. **State Management**: Draft state tracking and validation
4. **Error Handling**: Graceful degradation and recovery

### Immediate Actions

1. Run discovery scripts against live ESPN mock drafts
2. Populate this document with actual findings
3. Create message schema definitions
4. Validate connection stability requirements

## Appendices

### A. Discovery Script Results

*Raw output from protocol discovery scripts will be linked here.*

### B. Sample Messages

*Example WebSocket messages captured during testing.*

### C. Connection Traces

*Network traces showing WebSocket handshake and message flow.*

---

**Document Status**: Template - Awaiting Live Draft Analysis  
**Confidence Level**: TBD after testing  
**Recommendation**: Proceed with WebSocket approach pending validation