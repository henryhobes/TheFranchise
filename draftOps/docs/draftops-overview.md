# DraftOps Overview

## Executive Summary

DraftOps is an intelligent draft assistant for ESPN Fantasy Football that provides real-time pick recommendations during live drafts. It combines deterministic value calculations with AI-enhanced decision-making to deliver optimal draft strategies within the time constraints of each pick.

## Core Concept

An agentic system that monitors your ESPN fantasy draft in real-time through network interception, analyzes available players using multiple data sources, and recommends the optimal pick based on value projections, roster construction, and opportunity cost modeling.

## Technical Architecture

### Data Capture Layer

**Primary Method: WebSocket Interception via Playwright**
- Attaches to ESPN draft room using Playwright browser automation
- Monitors WebSocket frames directly through `page.on('websocket')` events with `framereceived`/`framesent` handlers
- Captures picks, clock updates, and roster changes as they happen over the wire
- Near-zero latency - receives updates within Playwright's event scheduling overhead (~50-100ms)

**Why Not Alternatives:**
- REST API polling introduces 500ms+ lag and risks missing rapid-fire picks
- DOM scraping breaks whenever ESPN updates their UI (which happens mid-season)
- ESPN's undocumented API endpoints change without warning (April 2024: complete URL restructure)

### State Management

**DraftState Object**
- `drafted_players`: Set of ESPN player IDs already selected
- `available_pool`: Remaining players (canonical list minus drafted)
- `my_roster`: Current team composition with positional counts
- `picks_until_next`: Snake draft position calculator
- `time_left`: Countdown timer for current pick
- `pick_history`: Full draft sequence for pattern analysis

**Persistence Strategy**
- LangGraph checkpointer for automatic state recovery after disconnections
- Thread-scoped memory maintains context throughout entire draft
- SQLite cache layer for static data (projections, rankings, ADP)

### Decision Engine

**Three-Layer Architecture:**

1. **Deterministic Core (Always Runs)**
   - Value Over Baseline (VOB) calculations per position
   - Opportunity cost modeling based on pick gap to next turn
   - ADP-based availability projections
   - Positional scarcity analysis
   - Execution time: <200ms

2. **AI Enhancement Layer (Time-Permitting)**
   - GPT-5 with intelligent routing (nano/mini/standard based on complexity)
   - Roster construction analysis and bye week optimization
   - Contextual adjustments for league-specific strategies
   - Only engages when clock time > 3 seconds
   - Target latency: 230-800ms depending on routing

3. **Supervisor Orchestration**
   - LangGraph supervisor pattern coordinates specialized agents
   - Tools include: VOB calculator, opportunity modeler, roster analyzer
   - Handles tool failures gracefully with fallback to deterministic picks
   - Provides streaming feedback for user visibility

### Intelligence Model

**GPT-5 Integration**
- Leverages GPT-5's built-in routing system (released August 2025)
- Intelligent routing between gpt-5-nano/mini/standard based on complexity
- Performance: 95th percentile response times of 1.8s (standard) to 3.2s (complex multimodal)
- 156 tokens/second generation speed on standard infrastructure, up to 180 tokens/second optimized
- Sub-100ms routing latency with dedicated endpoints

**Why GPT-5 Over Local Models:**
- Native routing eliminates manual model selection complexity
- Superior context understanding for nuanced draft situations
- No local GPU requirements or model management overhead
- Model-adapter interface allows swapping/downshifting based on performance needs

## Key Design Decisions

### LangGraph Over Direct Implementation

**Advantages:**
- Built-in persistence and state recovery for network failures
- Supervisor pattern perfectly matches our agent coordination needs
- Thread-scoped memory for maintaining draft strategy coherence
- Native streaming for real-time user feedback
- Proven pattern from existing fantasy football implementations

**Trade-offs Accepted:**
- 100-200ms routing overhead (acceptable given 60-90 second pick windows)
- Framework complexity vs. raw Python simplicity
- Additional dependency and potential lock-in

### No Auto-Clicking

**Rationale:**
- Legal liability for automated drafting violations
- User maintains ultimate control and accountability
- Reduces complexity and potential failure modes
- Click-to-confirm provides safety valve for system errors

### Deterministic First, AI Second

**Philosophy:**
- Mathematical foundation ensures baseline competence
- AI adds nuance only when time permits
- Hard timeout guarantees no missed picks
- Panic fallback to best VOB if all systems fail

## Data Sources

### Static Inputs (Cached Locally)
- Player projections from multiple sources
- Consensus rankings and tier breaks
- ADP distributions by platform and scoring
- Positional baseline calculations
- League settings and scoring rules

### Dynamic Signals
- Real-time pick announcements via WebSocket
- Current roster composition and needs
- Remaining time on pick clock
- Pick distance to next selection
- Draft position tendencies (reaches, runs)

### Optional Enhancements
- Targeted injury/news checks for final candidates
- Recent transaction data from ESPN
- Weather data for outdoor games (when relevant)

## Performance Requirements

### Latency Targets
- Network event to state update: <50ms
- Deterministic calculation: <200ms
- AI enhancement (when safe): <800ms
- Total decision time: <1000ms optimal, <2000ms acceptable
- Panic mode activation: >85% of clock expired

### Reliability Metrics
- Zero missed picks across all drafts
- Successful reconnection within 5 seconds
- State recovery from any point in draft
- Graceful degradation under time pressure

## Risk Mitigation

### Legal Risks
- **Terms of Service Violation**: ESPN/Disney ToS prohibit automated access, though no documented cases of draft monitoring bans exist
- **Account Risk**: Policy allows termination but enforcement appears focused on disruptive behavior rather than read-only monitoring
- **Mitigation Strategy**: Keep monitoring read-only, single session, test in mock drafts; HAR file fallback available

### Technical Risks
- **WebSocket Protocol Changes**: Monitor frames continuously, maintain versioned protocol mappers with golden-file replays
- **ESPN Infrastructure Failures**: Automatic reconnection with exponential backoff
- **Player Name Mismatches**: Use ESPN player IDs exclusively, names for display only
- **State Corruption**: Immutable state updates, checkpoint before modifications
- **Undocumented Protocol Drift**: ESPN changes base URLs and message formats without warning (April 2024: URL restructure)

### Operational Risks
- **Time Pressure**: Hard timeouts with deterministic fallback
- **Network Latency**: All calculations assume 500ms network buffer plus Playwright event scheduling delays
- **Concurrent Drafts**: Single-instance lock to prevent state collision
- **Memory Leaks**: Automatic cleanup of completed draft threads

## Success Metrics

### Primary KPIs
- Pick latency (WebSocket frame → recommendation displayed)
- Decision accuracy (recommended pick vs. retrospective optimal)
- Positional coverage (scarce positions filled appropriately)
- System stability (uptime during draft windows)

### Secondary Metrics
- User override rate (how often users reject recommendations)
- Regret minimization (performance vs. ADP expectations)
- Clock utilization (time used vs. time available)
- Recovery speed (disconnection to operational)

## Competitive Advantages

1. **True Real-Time**: WebSocket interception provides instant updates vs. polling delays
2. **Intelligent Time Management**: Scales decision complexity to available clock
3. **Resilient Architecture**: Survives disconnections and ESPN infrastructure issues
4. **GPT-5 Enhancement**: Latest AI capabilities when time permits
5. **Transparent Reasoning**: Streaming feedback shows decision process

## Future Considerations

### Potential Enhancements
- Multi-platform support (Yahoo, Sleeper)
- Keeper league value optimization
- Dynasty rookie draft specialization
- Auction draft budget optimization
- Trade analyzer using same value engine

### Scaling Challenges
- Multiple concurrent drafts for same user
- Cross-league pattern learning
- Historical performance analysis
- Community aggregate strategies

## Conclusion

DraftOps represents a pragmatic approach to fantasy draft assistance - sophisticated enough to provide genuine value, simple enough to work reliably under pressure. By combining deterministic calculations with optional AI enhancement, monitoring the actual data stream instead of the UI, and accepting reasonable trade-offs around automation and complexity, we create a tool that materially improves draft outcomes without the brittleness of over-engineered solutions.

The system acknowledges that perfect information is impossible in a draft environment, but good-enough information delivered instantly is invaluable. Every architectural decision flows from this principle: be fast, be reliable, and when you can't be both, choose reliable.