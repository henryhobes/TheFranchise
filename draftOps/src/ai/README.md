# DraftOps LangGraph AI Integration

This module implements the LangGraph Supervisor Framework Integration specified in Sprint 2, providing AI-driven draft decision making capabilities for the DraftOps fantasy football draft assistant.

## Overview

The AI integration uses LangGraph's StateGraph with GPT-5 to create a Supervisor Agent that orchestrates draft strategy, maintains context throughout the draft, and provides intelligent recommendations based on real-time draft state.

## Architecture

```
┌─────────────────────────────────────────┐
│           User Interface                 │
│      (Console/Web Application)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     EnhancedDraftStateManager          │
│  - WebSocket monitoring                 │
│  - Draft state management               │
│  - AI integration callbacks            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         DraftSupervisor                 │
│    (LangGraph StateGraph)              │
│  ┌─────────────────────────────────────┐│
│  │  Context      Supervisor    Rec.    ││
│  │  Processor → Agent Node → Generator ││
│  └─────────────────────────────────────┘│
│           GPT-5 Integration             │
└─────────────────────────────────────────┘
```

## Module Structure

```
draftOps/src/ai/
├── __init__.py                    # Main module exports
├── README.md                      # This documentation file
├── core/                          # Core AI components
│   ├── __init__.py
│   └── draft_supervisor.py        # LangGraph StateGraph implementation
├── managers/                      # State management integration
│   ├── __init__.py
│   └── enhanced_draft_state_manager.py  # AI-enhanced state management
├── tests/                         # Test suites
│   ├── __init__.py
│   ├── test_supervisor_integration.py    # Core LangGraph tests
│   └── test_enhanced_integration.py      # System integration tests
└── examples/                      # Demo scripts and examples
    ├── __init__.py
    └── demo.py                    # Interactive AI demonstration
```

### Directory Organization

#### `/core/` - Core AI Components
Contains the fundamental AI building blocks:
- **`draft_supervisor.py`**: LangGraph StateGraph implementation with GPT-5 integration

#### `/managers/` - State Management Integration
Contains AI-enhanced state managers:
- **`enhanced_draft_state_manager.py`**: Extended DraftStateManager with AI capabilities

#### `/tests/` - Test Suites
Comprehensive testing infrastructure:
- **`test_supervisor_integration.py`**: Core LangGraph functionality tests
- **`test_enhanced_integration.py`**: System-level integration tests

#### `/examples/` - Demonstration Scripts
Interactive examples and demos:
- **`demo.py`**: Comprehensive AI capabilities demonstration

### Import Structure

**Main Module Exports:**
```python
from draftOps.src.ai import DraftSupervisor, EnhancedDraftStateManager
```

**Direct Submodule Access:**
```python
from draftOps.src.ai.core import DraftSupervisor
from draftOps.src.ai.managers import EnhancedDraftStateManager
```

**Full Path Access:**
```python
from draftOps.src.ai.core.draft_supervisor import DraftSupervisor
from draftOps.src.ai.managers.enhanced_draft_state_manager import EnhancedDraftStateManager
```

## Key Components

### 1. DraftSupervisor (`draft_supervisor.py`)

The core LangGraph implementation that provides AI decision making:

- **StateGraph Workflow**: Uses LangGraph's StateGraph with 3 nodes
- **GPT-5 Integration**: Configured with `gpt-5` model
- **InMemorySaver**: Maintains conversation context and state
- **Context Injection**: Converts DraftState to AI-readable context

#### Workflow Nodes:
1. **Context Processor**: Prepares draft context for AI analysis
2. **Supervisor Agent**: Main AI decision-making node
3. **Recommendation Generator**: Creates specific draft recommendations

### 2. EnhancedDraftStateManager (`enhanced_draft_state_manager.py`)

Extends the base DraftStateManager with AI capabilities:

- **Non-blocking AI calls**: Async invocation that doesn't interfere with WebSocket monitoring
- **Automatic context updates**: Real-time injection of draft state into AI
- **Smart callbacks**: AI analysis triggered by significant draft events
- **Conversation persistence**: Thread-scoped memory across draft sessions

## Configuration

### Environment Setup

Ensure your `.env` file contains:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Dependencies

Required packages (already in `requirements.txt`):
```
langgraph>=0.6.6
langchain-openai>=0.3.32
python-dotenv>=1.0.0
```

### Model Configuration

Default configuration uses GPT-5:
- **Model**: `gpt-5`
- **Temperature**: `0.1` (for consistent draft decisions)
- **Max Tokens**: `2000`
- **Timeout**: `30 seconds`

## Usage

### Basic Usage

```python
from draftOps.src.ai.enhanced_draft_state_manager import EnhancedDraftStateManager

# Create enhanced manager with AI
manager = EnhancedDraftStateManager(
    league_id="your_league_id",
    team_id="your_team_id",
    team_count=12,
    ai_enabled=True
)

# Initialize (includes AI setup)
await manager.initialize()

# Connect to draft
await manager.connect_to_draft(draft_url)

# AI will automatically provide recommendations during draft
```

### Manual AI Queries

```python
# Query AI with current draft context
result = await manager.query_ai("What position should I target next?")

if result['success']:
    print(f"AI Response: {result['messages'][-1]['content']}")
    
# Get immediate draft recommendation
recommendation = await manager.get_draft_recommendation()
print(f"Recommendation: {recommendation.get('recommendation')}")
```

### Callback Integration

```python
def handle_ai_recommendation(rec_data):
    print(f"AI Recommendation: {rec_data['recommendation']}")
    print(f"Reasoning: {rec_data['reasoning']}")

def handle_ai_response(response_data):
    print(f"AI Query Response: {response_data['response']['messages'][-1]['content']}")

# Set callbacks
manager.on_ai_recommendation = handle_ai_recommendation
manager.on_ai_response = handle_ai_response
```

## Features

### Context-Aware AI

The AI supervisor receives comprehensive draft context:
- Current pick number and timing
- Team rosters and positional needs
- Available players and recent picks
- Snake draft position calculations
- Time pressure indicators

### Memory Persistence

LangGraph's InMemorySaver provides:
- **Thread-scoped conversations**: Each draft session maintains context
- **Cross-pick memory**: AI remembers previous reasoning and decisions
- **Strategy coherence**: Consistent draft approach throughout rounds

### Performance Optimized

- **Async operation**: AI calls don't block WebSocket monitoring
- **Smart triggering**: AI analysis only for significant events
- **Context summarization**: Efficient draft state representation
- **Response caching**: Conversation history management

## Testing

### Run Basic Integration Tests

```bash
cd draftOps
python src/ai/test_supervisor_integration.py
```

### Run Enhanced Integration Tests

```bash
cd draftOps  
python src/ai/test_enhanced_integration.py
```

### Expected Output

```
SUCCESS: All tests passed! LangGraph integration is working correctly.

Deliverables completed:
[OK] LangGraph Dependency & Config
[OK] Supervisor Agent Node
[OK] Memory & State Management via LangGraph
[OK] Integration Test (LangGraph Round-Trip)
[OK] Draft Context Injection
[OK] Async Non-blocking AI Invocation
[OK] Integration with DraftStateManager
```

## API Reference

### DraftSupervisor

#### Methods

- `async invoke_async(user_input, draft_context, thread_id)` - Query AI with context
- `invoke_sync(user_input, draft_context, thread_id)` - Synchronous version
- `update_draft_context(draft_state_obj)` - Convert DraftState to AI context
- `get_conversation_history(thread_id)` - Get conversation messages
- `clear_conversation(thread_id)` - Clear conversation history
- `async test_connection()` - Test GPT-5 connectivity

### EnhancedDraftStateManager

#### Additional Methods

- `async query_ai(user_input, include_context)` - Manual AI query
- `async get_draft_recommendation()` - Get immediate recommendation
- `get_ai_conversation_history()` - Get AI conversation
- `clear_ai_conversation()` - Clear AI conversation
- `get_enhanced_state_summary()` - Get stats including AI metrics

#### Callbacks

- `on_ai_recommendation(rec_data)` - Triggered by automatic AI analysis
- `on_ai_response(response_data)` - Triggered by manual AI queries
- `on_ai_error(error_data)` - Triggered by AI errors

## Sprint 2 Deliverables Status

✅ **LangGraph Dependency & Config**: Installed and configured with GPT-5  
✅ **Supervisor Agent Node**: Implemented using StateGraph supervisor pattern  
✅ **Memory & State Management**: InMemorySaver with thread-scoped persistence  
✅ **Integration Test**: Complete round-trip testing with all features  
✅ **Documentation & Configurability**: Comprehensive setup and usage docs  

## Performance Characteristics

- **AI Response Time**: ~2-4 seconds typical (GPT-5 standard)
- **Context Processing**: <100ms for draft state injection
- **Memory Footprint**: Minimal (InMemorySaver for conversation history)
- **WebSocket Impact**: Zero blocking (async AI calls)

## Error Handling

The system includes comprehensive error handling:
- **Connection failures**: Graceful degradation without AI
- **API rate limits**: Built-in timeout and retry logic
- **Context errors**: Fallback to basic recommendations
- **Memory issues**: Automatic conversation cleanup

## Next Steps (Sprint 3)

The AI integration is ready for Sprint 3 testing and refinement:
1. **Mock draft testing** - Test with live ESPN mock drafts
2. **Prompt optimization** - Refine AI prompts based on performance
3. **Response handling** - Improve recommendation presentation
4. **Edge case management** - Handle unusual draft scenarios

## Support

For issues or questions about the AI integration:
1. Check test results: Run integration tests first
2. Verify configuration: Ensure `.env` file has valid OpenAI API key
3. Review logs: AI operations are logged with detailed context
4. Test connectivity: Use `DraftSupervisor.test_connection()` to verify GPT-5 access