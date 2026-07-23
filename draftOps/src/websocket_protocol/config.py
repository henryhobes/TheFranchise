"""Shared configuration constants for the draft monitor.

League IDs are not secrets -- they only identify a league to ESPN's API -- but
centralizing the value here keeps it out of scattered string literals.
"""

# ESPN league used for development and the 2025 draft-season run (from Sprint 0).
DEFAULT_LEAGUE_ID = "262233108"
DEFAULT_TEAM_ID = "1"
