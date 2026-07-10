"""Layout constants for the welcome scene panels and inputs.

Centralizes pixel dimensions, gaps, and timings that the login panel,
difficulty panel, modals, and leaderboard overlay all share. WelcomeScene
re-exports these as class attributes for the scene and its panel renderers.
"""

# -- Top-level panel geometry -------------------------------------------------
# PANEL_W / PANEL_H are the *natural* dimensions of the welcome panels
# (used by the login-panel layout and as the upper bound for the responsive
# ``panel_h`` returned by ``WelcomeScene._get_layout``).
PANEL_W = 480
PANEL_H = 600
CHAMFER = 12

# Minimum panel height required to render the full right-panel content
# (title, tutorial, difficulty, leaderboard control, and the "Quick Controls"
# reference list). Below this, the controls list is skipped to keep the
# leaderboard control on screen at small window sizes.
MIN_PANEL_H_FOR_CONTROLS = 540

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
