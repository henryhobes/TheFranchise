"""
AI Integration Module for DraftOps

This module contains the LangGraph supervisor framework integration
for AI-driven draft decision making.

Organized structure:
- core/: Core AI components (DraftSupervisor, LangGraph workflows)
- managers/: Enhanced state managers with AI integration
- tests/: Comprehensive test suites
- examples/: Demo scripts and usage examples
- docs/: Documentation and usage guides
"""

from .core import DraftSupervisor

# Import managers conditionally to handle import issues gracefully
try:
    from .managers import EnhancedDraftStateManager, create_enhanced_draft_state_manager
    __all__ = [
        'DraftSupervisor', 
        'EnhancedDraftStateManager', 
        'create_enhanced_draft_state_manager'
    ]
except ImportError:
    # Fallback if managers can't be imported due to dependency issues
    __all__ = ['DraftSupervisor']