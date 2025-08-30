# The Franchise

ESPN Fantasy Football automation and analysis tools.

## Project Structure

```
thefranchise/
├── src/                    # Main source code
│   └── thefranchise/      # Core package
├── draftOps/              # Draft operation tools
│   └── src/
│       └── websocket_protocol/
│           ├── api/       # ESPN API clients
│           ├── monitor/   # WebSocket monitoring
│           ├── protocol/  # Protocol definitions
│           ├── scripts/   # Executable scripts
│           ├── utils/     # Utility functions
│           └── reports/   # Generated reports
├── .github/               # GitHub Actions workflows
│   └── workflows/
│       ├── claude-code-review.yml  # First principles PR review
│       ├── bug-bot.yml            # Automated bug detection
│       └── claude.yml             # Claude Code automation
└── requirements.txt       # Python dependencies
```

## Features

- ESPN Draft WebSocket protocol monitoring
- Player ID system reverse engineering
- Real-time draft event tracking
- Cross-reference validation between WebSocket and API data

## Setup

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## License

MIT License - see LICENSE file for details.