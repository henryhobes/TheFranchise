# DraftOps Overview

## Executive Summary

DraftOps is an AI-powered draft assistant for ESPN Fantasy Football that provides real-time pick recommendations during live drafts. It tests the capability of modern AI to conduct fantasy football drafts using contextual reasoning and pre-loaded player data, without relying on complex mathematical models or deterministic algorithms.

## Core Concept

An AI-driven system that monitors your ESPN fantasy draft in real-time through network interception and makes pick recommendations based on AI reasoning using pre-loaded player rankings, ADP data, and contextual understanding of draft dynamics. The system is designed specifically for snake draft formats and supports 8, 10, or 12-team leagues.

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
- `picks_until_next`: Snake draft position calculator (8/10/12 team leagues)
- `time_left`: Countdown timer for current pick
- `pick_history`: Full draft sequence for pattern analysis

**Persistence Strategy**
- LangGraph checkpointer for automatic state recovery after disconnections
- Thread-scoped memory maintains context throughout entire draft
- SQLite cache layer for static data (projections, rankings, ADP)

### Decision Engine

**AI-Driven Architecture:**

1. **LangGraph Supervisor Framework**
   - Orchestrates the AI decision-making process
   - Maintains draft state and context throughout the draft
   - Handles the flow between data retrieval and recommendation generation
   - Provides streaming feedback for visibility into the decision process

2. **GPT-5 Decision Making**
   - Leverages GPT-5's intelligent routing (nano/mini/standard)
   - Makes draft decisions based on pre-loaded player data
   - Considers roster construction, positional needs, and draft flow
   - No reliance on mathematical models or algorithms

3. **Context and Data Management**
   - Pre-loaded player rankings and ADP data
   - Real-time draft state from WebSocket monitoring
   - Simple fallback to highest-ranked player in emergencies

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

### Snake Draft Focus

**Supported Format:**
- Snake draft only (no auction support)
- 8, 10, or 12-team leagues exclusively
- Standard roster sizes for each league format
- Pick order reverses each round as expected in snake drafts

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

### AI-First Philosophy

**Approach:**
- Pure AI reasoning for all draft decisions
- Test AI's genuine understanding of fantasy football
- No algorithmic safety nets or mathematical models
- Emergency fallback only for extreme time pressure

## Data Sources

### Pre-Draft Data (Loaded Before Draft)
- Fantasy football rankings (PPR, 6pt PaTD specific)
- ADP data from various platforms
- Position rankings
- Player and team information
- League scoring settings

### Real-Time Draft Data
- Live pick updates via WebSocket
- Current roster state
- Available player pool
- Time remaining on clock
- Draft position and order


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

## Project Goals

1. **Test AI Capability**: Evaluate how well AI can draft without algorithmic assistance
2. **Real-Time Performance**: Maintain reliable performance under draft time constraints
3. **Strategic Understanding**: Assess AI's grasp of draft strategy and team building
4. **Transparent Process**: Clear visibility into AI reasoning through LangGraph
5. **Simple Architecture**: Focus on AI performance rather than system complexity

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

DraftOps is an experiment in pure AI-driven fantasy football drafting for snake draft formats in 8, 10, or 12-team leagues. By removing deterministic models and complex calculations, we're testing whether modern AI can successfully navigate a fantasy draft using only contextual reasoning and pre-loaded data. The LangGraph supervisor framework provides the orchestration layer while keeping decision-making purely AI-driven.

This approach prioritizes understanding AI's true capabilities in a measurable, time-constrained environment over building a hybrid system that might mask AI's actual performance with algorithmic safety nets.