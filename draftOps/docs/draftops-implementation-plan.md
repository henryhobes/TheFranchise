# DraftOps Implementation Plan

## Overview

This implementation plan divides DraftOps development into focused sprints that minimize risk, enable early testing, and build confidence incrementally. Each sprint delivers a working system that can be tested with real ESPN drafts.

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
       picks_until_next: int
       time_remaining: float
       on_the_clock: str  # team/user ID
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
- Test with different league sizes (10, 12, 14 teams)
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

### Sprint 2: Deterministic Brain (4 days)
**Goal: Make useful recommendations without AI**

#### Objective
Build the mathematical foundation that provides valuable pick recommendations based purely on projections and opportunity cost.

#### Value Engine Components

1. **Projection Data Management**
   ```python
   class ProjectionEngine:
       def load_projections(self, sources: list[str])
       def calculate_consensus(self, player: Player) -> float
       def adjust_for_scoring(self, projection: float, scoring: ScoringSettings) -> float
   ```

2. **Value Over Baseline Calculator**
   ```python
   def calculate_vob(player: Player, position_baselines: dict) -> float:
       # Determine replacement level for position
       # Calculate value above replacement
       # Adjust for positional scarcity
   ```

3. **Opportunity Cost Model**
   ```python
   def model_opportunity_cost(
       candidates: list[Player], 
       picks_until_next: int,
       available_pool: list[Player]
   ) -> dict[Player, float]:
       # Model likelihood each candidate is available later
       # Calculate expected value drop-off by position
       # Factor in positional runs and draft tendencies
   ```

4. **Roster Need Analysis**
   ```python
   def analyze_roster_needs(
       current_roster: dict[str, list[Player]], 
       league_settings: LeagueSettings
   ) -> dict[str, float]:
       # Calculate positional requirements remaining
       # Factor in bye week coverage
       # Weight by scarcity and drop-off rates
   ```

#### Static Data Sources
- FantasyPros consensus projections
- Multiple expert rankings (Berry, Yates, etc.)
- ADP data from multiple platforms
- Historical positional value curves
- Bye week schedules

#### Decision Algorithm
```python
def generate_recommendations(state: DraftState) -> list[Recommendation]:
    candidates = get_top_available_players(state.available_pool, n=20)
    
    for player in candidates:
        vob_score = calculate_vob(player, position_baselines)
        opportunity_cost = model_opportunity_cost([player], state.picks_until_next, state.available_pool)
        roster_fit = calculate_roster_fit(player, state.my_roster)
        
        total_score = vob_score - opportunity_cost + roster_fit
        
    return sorted(recommendations, key=lambda x: x.score, reverse=True)[:3]
```

#### Deliverable
- Recommendation engine that suggests top 3 picks
- Clear numeric reasoning for each suggestion
- Console UI showing VOB scores and opportunity costs
- Recommendations update in real-time as picks are made

#### Success Criteria
- Recommendations align with expert consensus 80%+ of the time
- Opportunity cost model shows measurable predictive value
- System runs fast enough for real-time use (<200ms per update)
- Recommendations improve measurably over ADP-only strategy

---

### Sprint 3: Intelligence Layer (4 days)
**Goal: Add AI reasoning and decision streaming**

#### Objective
Integrate GPT-5 to enhance deterministic recommendations with contextual reasoning, while maintaining reliability through time-based scaling.

#### LangGraph Supervisor Setup

1. **Agent Architecture**
   ```python
   class DraftSupervisor:
       tools = {
           'vob_calculator': calculate_vob,
           'opportunity_modeler': model_opportunity_cost,
           'roster_analyzer': analyze_roster_needs,
           'news_checker': check_recent_news
       }
   ```

2. **Time-Based Decision Scaling**
   ```python
   async def generate_enhanced_recommendation(state: DraftState, time_limit: float):
       # Always run deterministic core
       base_recommendations = generate_deterministic_picks(state)
       
       if time_limit > 3.0:  # Safe to enhance
           enhanced = await supervisor.enhance_recommendations(
               base_recommendations, 
               state,
               timeout=time_limit - 1.0
           )
           return enhanced
       
       return base_recommendations
   ```

3. **GPT-5 Integration**
   - Configure GPT-5 API with model-adapter interface (gpt-5-nano/mini/standard)
   - Design prompts for draft-specific reasoning
   - Implement streaming for real-time feedback
   - Handle timeout and fallback scenarios with hard timeouts
   - Account for 95th percentile response times (1.8s standard, 3.2s complex)

4. **Reasoning Transparency**
   ```python
   class RecommendationWithReasoning:
       player: Player
       score: float
       deterministic_factors: dict  # VOB, opportunity cost, roster fit
       ai_adjustments: dict  # Context, news, strategy considerations
       confidence: float
       reasoning: str  # Human-readable explanation
   ```

#### AI Enhancement Areas
- **Roster Construction Strategy**: "Need RB depth before bye weeks cluster"
- **News Integration**: "CMC questionable, handcuff value increased"
- **Draft Flow Analysis**: "WR run likely starting, consider jumping ahead"
- **League-Specific Adjustments**: "Superflex league, QB scarcity premium"

#### Deliverable
- AI-enhanced recommendations with visible reasoning
- Streaming output showing agent thought process
- Time-based scaling that never compromises reliability
- A/B testing framework to compare AI vs deterministic picks

#### Success Criteria
- AI recommendations show measurable improvement over deterministic alone
- System gracefully degrades under time pressure
- User can follow the reasoning for each recommendation
- No picks missed due to AI processing delays

---

### Sprint 4: Production Hardening (5 days)
**Goal: Never miss a pick, ever**

#### Objective
Implement comprehensive reliability features and error handling to ensure the system works flawlessly during actual draft pressure.

#### Reliability Features

1. **Connection Failure Recovery**
   ```python
   class ConnectionManager:
       async def handle_websocket_close(self, code: int, reason: str)
       async def exponential_backoff_reconnect(self, max_attempts: int = 5)
       async def validate_connection_health(self)
       async def fallback_to_api_polling(self)
   ```

2. **State Persistence and Resume**
   ```python
   class StatePersistence:
       def checkpoint_state(self, state: DraftState)
       def restore_from_checkpoint(self) -> DraftState
       def validate_state_consistency(self, espn_state: dict) -> bool
       def reconcile_missed_picks(self, current_state: dict)
   ```

3. **Panic Mode Implementation**
   ```python
   def panic_mode_recommendation(state: DraftState, time_remaining: float) -> Recommendation:
       if time_remaining < 5.0:  # Panic threshold
           # Skip AI enhancement
           # Use cached VOB calculations
           # Return top available player immediately
           return get_best_available_by_vob(state.available_pool)
   ```

4. **Comprehensive Monitoring**
   ```python
   class SystemMonitor:
       def track_response_times(self)
       def monitor_connection_stability(self)
       def log_recommendation_accuracy(self)
       def alert_on_system_degradation(self)
   ```

#### Error Handling Scenarios
- **WebSocket Disconnection**: Auto-reconnect with state recovery
- **API Rate Limiting**: Exponential backoff with local cache fallback  
- **Invalid Player Data**: Fuzzy matching with manual override capability
- **Time Pressure**: Graceful degradation to deterministic mode
- **Memory Issues**: Automatic cleanup of completed draft data
- **Network Partitions**: Local mode with cached data

#### Testing Framework
```python
class DraftSimulator:
    def simulate_connection_failures(self)
    def test_rapid_fire_picks(self)
    def validate_state_consistency(self)
    def measure_performance_under_load(self)
```

#### Performance Optimization
- **Caching Strategy**: Pre-compute VOB scores for top 200 players
- **Memory Management**: Cleanup old draft threads automatically
- **Network Optimization**: Connection pooling and keep-alive
- **CPU Efficiency**: Async processing for all I/O operations

#### Deliverable
- Production-ready system that survives all failure modes
- Comprehensive error logging and monitoring
- Performance metrics dashboard
- Automated testing suite for reliability scenarios

#### Success Criteria
- System maintains 99.9% uptime during draft windows
- Recovery from any failure mode within 10 seconds
- Zero missed picks across 100+ test scenarios
- Performance remains stable under maximum load

---

## Critical Path Analysis

### Sequential Dependencies
1. **Sprint 0 → Sprint 1**: Protocol understanding enables connection management
2. **Sprint 1 → Sprint 2**: State tracking enables recommendation engine
3. **Sprint 2 → Sprint 3**: Deterministic foundation enables AI enhancement
4. **Sprint 3 → Sprint 4**: Working system enables reliability testing

### Parallel Work Opportunities

**Within Sprint 1:**
- Connection logic development
- DraftState class implementation  
- Player ID mapping research

**Within Sprint 2:**
- VOB calculation algorithms
- Data source integration
- Opportunity cost modeling

**Within Sprint 3:**
- LangGraph supervisor setup
- GPT-5 API integration
- Prompt engineering and testing

**Within Sprint 4:**
- Error handling implementation
- Performance optimization
- Comprehensive testing

## Risk Management Strategy

### Highest Risk Items (Address First)
1. **ESPN WebSocket Reliability** - Could invalidate entire approach
2. **Protocol Drift** - ESPN changes message formats without warning (April 2024 precedent)
3. **Player ID Consistency** - Wrong IDs = wrong recommendations  
4. **Time Management** - Slow decisions defeat the purpose
5. **Connection Recovery** - ESPN infrastructure will fail mid-draft
6. **Legal Compliance** - ToS risk exists but no documented enforcement for read-only monitoring

### Risk Mitigation Tactics
- **Legal Protection**: Read-only monitoring, single session, HAR file fallback mode
- **Multiple Fallback Options**: WebSocket → API (lm-api-reads.fantasy.espn.com) → DOM scraping
- **Protocol Versioning**: Schema mappers with golden-file replay testing
- **Comprehensive Testing**: Every mock draft is a test case
- **Performance Budgets**: Hard limits on processing time with model-adapter failover
- **State Validation**: Cross-check with ESPN UI continuously

### Go/No-Go Decision Points

**After Sprint 0:**
- Can we read ESPN WebSocket reliably? (90% success rate minimum)
- Do we understand their protocol well enough to build on?

**After Sprint 1:**  
- Can we track a full draft without state corruption?
- Does connection recovery work in realistic scenarios?

**After Sprint 2:**
- Do our recommendations align with expert consensus?
- Is performance acceptable for real-time use?

**After Sprint 3:**
- Does AI enhancement provide measurable value?
- Can we maintain reliability with added complexity?

## Testing Strategy

### Continuous Validation
- **Mock Draft Testing**: Join ESPN mocks during every development session
- **Recorded Traffic Replay**: Capture WebSocket streams for regression testing
- **Performance Profiling**: Time every operation with realistic network conditions
- **State Validation**: Compare our state to ESPN UI continuously

### Pre-Production Testing
- **Load Testing**: Simulate peak draft season traffic
- **Chaos Engineering**: Intentionally break connections and validate recovery
- **A/B Testing**: Compare recommendations against expert picks and outcomes
- **User Acceptance**: Test with real fantasy football players

## Success Metrics

### Technical Metrics
- **Latency**: WebSocket event → recommendation displayed (target: <1000ms)
- **Accuracy**: State consistency with ESPN UI (target: 100%)
- **Reliability**: Uptime during draft windows (target: 99.9%)
- **Recovery**: Time to restore from disconnection (target: <10 seconds)

### Product Metrics
- **Recommendation Quality**: Alignment with expert consensus (target: 80%+)
- **User Override Rate**: How often users reject recommendations (target: <30%)
- **Draft Performance**: Retrospective value vs. ADP expectations
- **User Satisfaction**: Perceived value and ease of use

## Execution Philosophy

**Build Vertically**: Each sprint delivers something testable end-to-end
**Test Early and Often**: Every mock draft is validation
**Fail Fast**: Identify blocking issues immediately  
**Reliability First**: Working deterministic > broken AI-enhanced
**Data-Driven**: Measure everything, assume nothing

## Conclusion

This implementation plan prioritizes de-risking the core technical assumptions first, then builds reliable value incrementally. By the end of Sprint 2, we have a useful tool that provides better recommendations than ADP alone. Sprints 3 and 4 enhance and harden the system without compromising the fundamental reliability.

The key insight: in a time-sensitive domain like fantasy drafts, "good enough and reliable" beats "perfect but fragile" every single time. This plan ensures we never sacrifice reliability for features.