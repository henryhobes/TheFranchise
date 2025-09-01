# DraftOps Implementation Plan

## Overview

This implementation plan focuses on building a pure AI-driven draft assistant that tests AI's capability to conduct fantasy football drafts. The system is designed specifically for snake draft formats in 8, 10, or 12-team leagues. The plan emphasizes simplicity and direct AI decision-making without complex mathematical models or hybrid approaches.

## Sprint Structure

### Sprint 0: Reconnaissance (2 days)
**Goal: Validate core technical assumption**

#### Objective
Prove we can reliably read ESPN's WebSocket draft stream and understand their protocol.

#### Critical Discovery Tasks
1. **ESPN Draft Room Protocol Mapping**
   - Join ESPN mock drafts with Chrome DevTools open
   - Identify WebSocket endpoints and connection patterns
   - Document message types (PICK_MADE, ON_THE_CLOCK, ROSTER_UPDATE, etc.)
   - Map message structure and field meanings

2. **Player ID System Reverse Engineering**
   - Determine how ESPN identifies players (numeric IDs vs names)
   - Test ID consistency across different draft rooms
   - Build preliminary ESPN ID → player name mapping
   - Identify edge cases (rookies, free agents, DST, etc.)

3. **Connection Stability Testing**
   - Monitor WebSocket behavior during full mock draft
   - Document disconnection/reconnection patterns
   - Test what happens during network interruptions
   - Identify session timeout behavior

4. **Message Flow Analysis**
   - Map the sequence of messages during pick process
   - Time delays between pick and broadcast
   - Identify pre-pick signals (ON_THE_CLOCK events)
   - Document draft room state synchronization

#### Deliverable
- Protocol documentation with message examples
- Proof-of-concept script that logs picks in real-time
- Connection stability assessment
- Risk assessment for WebSocket approach

#### Success Criteria
- Can connect to ESPN draft room programmatically
- Receives every pick without missed messages
- Understands message format well enough to extract player info
- Connection survives typical network hiccups

#### Risk Mitigation
If WebSocket approach proves unreliable, have backup plan ready:
- API polling implementation (current base URL: https://lm-api-reads.fantasy.espn.com/apis/v3/games)
- DOM scraping fallback
- HAR file import for manual traffic analysis mode
- Hybrid approach (WebSocket primary, polling backup)

#### Legal Considerations
- ESPN/Disney ToS prohibit automated access but no documented enforcement for read-only draft monitoring
- Include disclaimer about Terms of Service policy
- Keep implementation read-only, single session, low-rate
- HAR file mode available for maximum caution

---

### Sprint 1: Minimal Viable Monitor (3 days)
**Goal: Track a complete mock draft end-to-end**

#### Objective
Build the foundation infrastructure that can maintain connection through an entire draft and track state accurately.

#### Core Infrastructure Components

1. **Playwright Connection Manager**
   ```python
   class ESPNDraftMonitor:
       async def connect_to_draft(self, draft_url)
       async def setup_websocket_listeners(self)  # page.on('websocket') with framereceived/framesent
       async def handle_disconnection(self)
       async def reconnect_with_backoff(self)
       async def setup_protocol_mapper(self)  # Versioned message schema handling
   ```

2. **Draft State Management**
   ```python
   class DraftState:
       drafted_players: set[str]
       available_players: list[Player]
       my_roster: dict[str, list[Player]]
       current_pick: int
       picks_until_next: int  # Snake draft calculation for 8/10/12 teams
       time_remaining: float
       on_the_clock: str  # team/user ID
       league_size: int  # 8, 10, or 12 only
   ```

3. **Player Resolution System**
   ```python
   class PlayerResolver:
       def resolve_espn_id(self, espn_id: str) -> Player
       def fuzzy_match_name(self, name: str) -> Player
       def handle_unknown_player(self, espn_data: dict) -> Player
   ```

4. **Event Processing Pipeline**
   ```python
   def process_websocket_frame(payload: str):
       # Parse message
       # Update state
       # Trigger callbacks
       # Log for debugging
   ```

#### Testing Strategy
- Run against multiple ESPN mock drafts
- Test with supported league sizes (8, 10, 12 teams)
- Verify state accuracy at every pick
- Test connection recovery scenarios

#### Deliverable
- Console application that connects to ESPN draft
- Real-time logging of every pick as it happens
- Accurate draft state maintained throughout
- Connection survives typical interruptions

#### Success Criteria
- Tracks complete 15-round mock draft without errors
- State matches ESPN UI at all times
- Recovers from 1-2 connection drops per draft
- Player names resolve correctly 95%+ of the time

---

### Sprint 2: Data Preparation & AI Integration
**Goal: Set up player data and AI decision-making**

#### Focus Areas

**Data Management**
- Load pre-draft player data (rankings, ADP, positions)
- Prepare data in format suitable for AI context
- Handle league-specific scoring settings

**LangGraph Integration**
- Set up supervisor framework for orchestration
- Implement state management throughout draft
- Enable streaming for real-time feedback

**AI Decision Making**
- Integrate GPT-5 for draft recommendations
- Design initial prompt strategies
- Handle AI responses and reasoning

#### Flexible Implementation
The specific implementation details will emerge during development based on:
- Data availability and format
- AI response quality with different prompt approaches
- Performance characteristics observed during testing
- Integration challenges discovered along the way

---

### Sprint 3: Testing and Refinement
**Goal: Evaluate and improve AI performance**

#### Testing Approach

**Mock Draft Testing**
- Run system through multiple ESPN mock drafts
- Test various draft positions in 8, 10, and 12-team leagues
- Document AI decision patterns and quality
- Identify strengths and weaknesses

**Areas for Refinement**
- Prompt optimization based on results
- Context presentation adjustments
- Response handling improvements
- Edge case management

#### Iterative Improvement
Refine the system based on observations:
- What types of decisions does AI handle well?
- Where does it struggle?
- How can prompts be improved?
- What additional context helps?

---

### Sprint 4: Production Hardening
**Goal: Ensure reliability for real drafts**

#### Core Requirements

**Connection Reliability**
- Handle WebSocket disconnections gracefully
- Implement reconnection logic
- Maintain state consistency through interruptions

**Error Handling**
- Manage time pressure scenarios
- Handle unexpected data or responses
- Implement appropriate fallback strategies
- Ensure no missed picks

**System Stability**
- Test under various failure conditions
- Implement logging and monitoring
- Optimize performance where needed

#### Production Readiness
The system should:
- Complete drafts without critical failures
- Recover from common error scenarios
- Provide clear feedback when issues occur
- Maintain reasonable performance throughout

---

## Critical Path Analysis

### Sequential Dependencies
1. **Sprint 0 → Sprint 1**: Protocol understanding enables connection management
2. **Sprint 1 → Sprint 2**: State tracking enables AI integration
3. **Sprint 2 → Sprint 3**: Working AI system enables testing and refinement
4. **Sprint 3 → Sprint 4**: Tested system ready for production hardening

### Development Flexibility

Each sprint can adapt based on discoveries and challenges:

**Sprint Evolution**
- Sprints may overlap or extend based on findings
- Features can be moved between sprints as priorities emerge
- Implementation details will be determined during development
- Testing and refinement happen continuously, not just in Sprint 3

## Risk Management Strategy

### Key Risk Areas
1. **ESPN WebSocket Reliability** - Foundation of the entire system
2. **Protocol Changes** - ESPN may modify message formats
3. **Player Identification** - Accurate player matching is critical
4. **AI Response Time** - Must work within draft time constraints
5. **Connection Stability** - Network issues during drafts
6. **Legal Considerations** - ToS compliance for monitoring

### Risk Mitigation Tactics
- **Legal Protection**: Read-only monitoring, single session, HAR file fallback mode
- **Multiple Fallback Options**: WebSocket → API (lm-api-reads.fantasy.espn.com) → DOM scraping
- **Protocol Versioning**: Schema mappers with golden-file replay testing
- **Comprehensive Testing**: Every mock draft is a test case
- **Simple Fallbacks**: Highest-ranked available player in emergencies
- **State Validation**: Cross-check with ESPN UI continuously

### Go/No-Go Decision Points

**After Sprint 0:**
- Can we read ESPN WebSocket reliably? (90% success rate minimum)
- Do we understand their protocol well enough to build on?
- Can we handle snake draft logic for 8/10/12 team leagues?

**After Sprint 1:**  
- Can we track a full draft without state corruption?
- Does connection recovery work in realistic scenarios?

**After Sprint 2:**
- Does AI make reasonable draft recommendations?
- Is performance acceptable for real-time use?

**After Sprint 3:**
- Is AI performance consistent and reliable?
- Have we identified clear patterns in AI decision-making?

## Testing Philosophy

### Iterative Testing
- Use ESPN mock drafts throughout development
- Capture and replay WebSocket traffic for debugging
- Continuously validate state accuracy
- Refine based on observed behavior

### Flexible Validation
- Test what matters most as it emerges
- Adapt testing approach based on findings
- Focus on real-world scenarios
- Learn from each mock draft session

## Success Indicators

### System Performance
- Maintains accurate draft state throughout
- Provides recommendations in reasonable time
- Handles disconnections and recovers
- Completes drafts without missing picks

### AI Performance
- Makes logical draft decisions
- Provides clear reasoning for picks
- Adapts to draft flow and context
- Builds balanced, competitive teams

## Execution Philosophy

**Build Vertically**: Each sprint delivers something testable end-to-end
**Test Early and Often**: Every mock draft is validation
**Fail Fast**: Identify blocking issues immediately  
**Simplicity First**: Focus on AI capability rather than system complexity
**Data-Driven**: Measure everything, assume nothing

## Conclusion

This implementation plan focuses on testing AI's ability to conduct snake draft fantasy football drafts in 8, 10, or 12-team leagues without algorithmic assistance. By removing mathematical models and deterministic approaches, we create a pure test of AI capability in a measurable, time-constrained environment.

The goal is not to build the most sophisticated draft tool, but to understand how well modern AI can handle strategic decision-making in the specific context of snake drafts when given appropriate context and data. Success is measured not by perfection, but by demonstrating that AI can make reasonable, explainable draft decisions consistently.