"""Layout constants for the welcome scene panels and inputs.

Centralizes pixel dimensions, gaps, and timings that the login panel,
difficulty panel, modals, and leaderboard overlay all share. WelcomeScene
re-exports these as class attributes so external callers can keep reading
``scene.PANEL_W`` / ``scene.LOGIN_ROW_GAP`` / etc.
"""

# -- Top-level panel geometry -------------------------------------------------
PANEL_W = 480
PANEL_H = 500
CHAMFER = 12

# -- Login panel internals ----------------------------------------------------
INPUT_W = 370
INPUT_H = 54
BTN_H = 48
LOGIN_PAD_X = 36
LOGIN_LABEL_W = 104
LOGIN_LABEL_GAP = 16
LOGIN_ROW_GAP = 24
LOGIN_PRIMARY_GAP = 16
LOGIN_PRIMARY_W = 172
LOGIN_SECONDARY_W = 172
LOGIN_SECONDARY_H = 42

# -- Username dropdown -------------------------------------------------------
USER_DROPDOWN_W = 46
USER_DROPDOWN_OPTION_H = 38
USER_DROPDOWN_MAX_ITEMS = 4

# -- Difficulty panel --------------------------------------------------------
DIFF_OPTION_H = 48
DIFF_GAP = 8

# -- Inter-panel spacing ------------------------------------------------------
PANEL_GAP = 30
STACKED_PANEL_GAP = 24

# -- Timings -----------------------------------------------------------------
MESSAGE_DISPLAY_FRAMES = 120
