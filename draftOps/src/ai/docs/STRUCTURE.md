# AI Module Structure

This document describes the organized structure of the `draftOps/src/ai/` module after cleanup and reorganization.

## Directory Structure

```
draftOps/src/ai/
├── __init__.py                    # Main module exports
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
├── examples/                      # Demo scripts and examples
│   ├── __init__.py
│   └── demo.py                    # Interactive AI demonstration
└── docs/                         # Documentation
    ├── README.md                 # Comprehensive usage documentation
    └── STRUCTURE.md             # This file
```

## Module Organization

### `/core/` - Core AI Components
Contains the fundamental AI building blocks:

- **`draft_supervisor.py`**: LangGraph StateGraph implementation with GPT-5 integration
  - `DraftSupervisor` class with 3-node workflow
  - Context processing, supervisor agent, and recommendation generation
  - InMemorySaver for conversation persistence
  - GPT-5 model configuration and connectivity

### `/managers/` - State Management Integration
Contains AI-enhanced state managers:

- **`enhanced_draft_state_manager.py`**: Extended DraftStateManager with AI capabilities
  - `EnhancedDraftStateManager` class
  - Non-blocking AI integration with WebSocket monitoring
  - Automatic context injection and callback system
  - Factory function for easy initialization

### `/tests/` - Test Suites
Comprehensive testing infrastructure:

- **`test_supervisor_integration.py`**: Core LangGraph functionality tests
  - Basic connectivity and GPT-5 integration
  - Context maintenance and conversation continuity
  - Draft state injection and workflow testing
  
- **`test_enhanced_integration.py`**: System-level integration tests
  - Enhanced manager initialization and AI integration
  - Callback system and conversation persistence
  - Complete system workflow validation

### `/examples/` - Demonstration Scripts
Interactive examples and demos:

- **`demo.py`**: Comprehensive AI capabilities demonstration
  - Basic AI functionality showcase
  - Draft context awareness examples
  - Conversation continuity demonstrations
  - Multiple scenario testing

### `/docs/` - Documentation
Module documentation and guides:

- **`README.md`**: Complete usage documentation with examples
- **`STRUCTURE.md`**: This organizational overview

## Import Structure

### Main Module Exports
```python
from draftOps.src.ai import DraftSupervisor, EnhancedDraftStateManager
```

### Direct Submodule Access
```python
from draftOps.src.ai.core import DraftSupervisor
from draftOps.src.ai.managers import EnhancedDraftStateManager
```

### Full Path Access
```python
from draftOps.src.ai.core.draft_supervisor import DraftSupervisor
from draftOps.src.ai.managers.enhanced_draft_state_manager import EnhancedDraftStateManager
```

## Benefits of This Structure

### 🎯 **Clear Separation of Concerns**
- Core AI logic separated from integration concerns
- Tests isolated from production code
- Documentation and examples clearly organized

### 📈 **Scalability**
- Easy to add new AI components in `/core/`
- Manager extensions go in `/managers/`
- New tests organized by category in `/tests/`

### 🔍 **Discoverability** 
- Clear naming conventions make functionality obvious
- Logical grouping helps developers find relevant code
- Documentation co-located with implementation

### 🛠 **Maintainability**
- Related functionality grouped together
- Clean import hierarchy
- Test coverage organized by component

### 🔌 **Extensibility**
- New AI agents can be added to `/core/`
- Additional state managers can extend existing patterns
- Example scripts provide templates for new functionality

## Testing

Run tests from the project root:

```bash
# Core LangGraph functionality
cd draftOps && python src/ai/tests/test_supervisor_integration.py

# System integration tests  
cd draftOps && python src/ai/tests/test_enhanced_integration.py

# Interactive demonstration
cd draftOps && python src/ai/examples/demo.py
```

## Development Guidelines

### Adding New Components

1. **Core AI Components** → `/core/`
   - New AI agents, workflows, or LangGraph implementations
   - Export from `/core/__init__.py`

2. **Integration Managers** → `/managers/` 
   - Extensions or alternatives to existing state managers
   - Export from `/managers/__init__.py`

3. **Test Coverage** → `/tests/`
   - Test files should match component names with `test_` prefix
   - Integration tests for system-level functionality

4. **Examples/Demos** → `/examples/`
   - Standalone scripts demonstrating functionality
   - Interactive examples for user education

5. **Documentation** → `/docs/`
   - Technical documentation and architectural overviews
   - Usage guides and API references

### Import Best Practices

- Use main module imports for public API: `from draftOps.src.ai import DraftSupervisor`
- Use submodule imports for internal development: `from .core import DraftSupervisor`
- Avoid deep path imports in external code: prefer module-level exports

This structure provides a solid foundation for continued development and maintains clear organization as the AI module grows in complexity.