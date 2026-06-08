"""Logic-clarity test suite.

Documents and validates the 47 fuzzy points identified in the discovery
report. See ``docs/logic-clarity/11-phase5b-handoff.md`` §6.2 for the
current status (9 residuals + their resolutions from the Phase 6
commit ``7f95e33``); the previous 01-discovery-report.md was retired
in the 2026-06-08 docs cleanup. Each test maps to exactly one fuzzy
point via its test docstring.

Categories:
    F01 - cross-layer state mutation
    F02 - dual-path code
    F03 - silent failures
    F04 - magic numbers / hardcoded values
    F05 - order dependencies
    F06 - interface contract gaps
    F07 - event-bus transparency
"""
