"""Validated data-viz palette shared by every chart in the app.

Categorical order, diverging pair, sequential ramp, and status colors are
copied from the design skill's reference palette (references/palette.md) --
an ordering pre-validated for colorblind-safe adjacent contrast, not picked
by eye. Keep colors assigned by role (see MODEL_COLORS) rather than by
position in a loop, so the same entity keeps the same color everywhere.
"""

# Fixed-order categorical hues (validated adjacent-pair contrast; never reassign order)
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = CATEGORICAL

# Diverging pair (polarity) + neutral midpoint
DIVERGING_LOW, DIVERGING_MID, DIVERGING_HIGH = BLUE, "#f0efec", RED

# Sequential (magnitude) — single hue, light -> dark
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

# Status (fixed roles, never reused as a categorical slot)
STATUS_GOOD, STATUS_WARNING, STATUS_SERIOUS, STATUS_CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"

# Ink / chrome
TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED = "#0b0b0b", "#52514e", "#898781"
GRIDLINE = "#e1e0d9"

# One color per pipeline stage — the model-selection "journey" — assigned by
# identity so a chart never repaints a stage when others are filtered out.
STAGE_COLORS = {
    "1. Baseline (model_selection)": BLUE,
    "2. F1-optimized": ORANGE,
    "3. Recall-optimized": MAGENTA,
    "4. Precision/recall-balanced (deployed)": VIOLET,
    "5. Final (test set, one-time)": RED,
}

# Risk tiers map onto the fixed status palette, never a categorical hue
RISK_TIER_COLORS = {"Low": STATUS_GOOD, "Medium": STATUS_WARNING, "High": STATUS_CRITICAL}

PLOTLY_TEMPLATE = "plotly_white"


def plotly_layout_defaults() -> dict:
    """Common Plotly layout kwargs: recessive grid, consistent ink, legible font."""
    return dict(
        template=PLOTLY_TEMPLATE,
        font=dict(size=13, color=TEXT_PRIMARY),
        title_font=dict(size=16, color=TEXT_PRIMARY),
        legend=dict(font=dict(size=12)),
        margin=dict(t=60, l=10, r=10, b=10),
    )
