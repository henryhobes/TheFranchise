# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a newly initialized Python project (thefranchise) with MIT license. The repository is currently empty except for basic Git configuration files.

## Development Environment

### Hardware
- NVIDIA RTX 4070 GPU (use CUDA when applicable)
- Intel Core i7-12700K (8P+4E cores, up to 5.0 GHz)
- MSI PRO Z790-P WiFi DDR5 motherboard
- 32 GB RAM

### Development Preferences
- **Language**: Python exclusively
- **Code style**: Simple and clean over complexity - choose the most straightforward solution
- **Comments**: Only when absolutely necessary - write self-documenting code instead
- **Emojis**: Never use emojis in code, commit messages, or any technical content
- **Unicode**: Avoid Unicode characters (checkmarks, X marks, etc.) in print statements - use plain ASCII text like "[PASS]", "[FAIL]", "SUCCESS:", "ERROR:" instead
- **GPU optimization**: Leverage CUDA/GPU acceleration where beneficial (PyTorch, CuPy, RAPIDS, etc.)
- **Web search**: Perform web searches proactively when needed without asking permission

## Development Setup

Since this is a fresh Python project with no code yet, consider these standard Python development practices:

### Common Python Commands
- `python -m venv venv` - Create virtual environment
- `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix) - Activate virtual environment
- `pip install -r requirements.txt` - Install dependencies (once requirements.txt exists)
- `python -m pytest` - Run tests (once tests are added)
- `python -m black .` - Format code (if using Black formatter)
- `python -m flake8` - Lint code (if using flake8)
- `python -m mypy .` - Type check (if using mypy)

## Project Structure Recommendations

Since the project is empty, consider organizing it based on the project's purpose:

For a Python package:
```
thefranchise/
├── src/
│   └── thefranchise/
│       └── __init__.py
├── tests/
├── requirements.txt
├── setup.py or pyproject.toml
└── README.md
```

For a Python application:
```
thefranchise/
├── app/
│   └── main.py
├── tests/
├── requirements.txt
└── README.md
```

## Common Issues to Avoid

### Unicode Encoding Problems
- Windows command prompt uses CP1252 encoding which doesn't support many Unicode characters
- Always use plain ASCII characters in print statements and output
- Examples of what NOT to use: ✓, ✗, 🎉, ❌
- Examples of what TO use: "[PASS]", "[FAIL]", "SUCCESS:", "ERROR:", "*", "-", "+"

### Testing and Output
- Use descriptive ASCII text for test results instead of Unicode symbols
- Format test output with clear, readable ASCII text
- Avoid fancy Unicode box drawing characters - use simple dashes and equals signs

## Notes

- The .gitignore is configured for Python projects
- No existing code architecture to document yet
- No build or test commands configured yet