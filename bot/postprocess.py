"""Pure functions for cleaning model outputs. Unit-tested in tests/."""
import re

import numpy as np
from forecasting_tools import PredictedOption, PredictedOptionList


def clip(p: float, bounds: tuple[float, float]) -> float:
    lo, hi = bounds
    return float(min(hi, max(lo, p)))


def _norm(s: str) -> str:
    # Case and whitespace only. Symbols like -, <, >, %, $ change meaning and are kept.
    return " ".join(s.casefold().split()).rstrip(".")


def canonicalize_options(
    pred: PredictedOptionList, options: list[str], floor: float
) -> PredictedOptionList:
    """Map parsed option names onto the question's exact names (exact match, then
    case/whitespace-insensitive match), add missing options, smooth with a small
    floor, renormalize. Raises on anything ambiguous instead of guessing."""
    lookup: dict[str, str] = {}
    for o in options:
        if _norm(o) in lookup:
            raise ValueError(f"Options collide after normalization: {o!r}")
        lookup[_norm(o)] = o
    probs = {o: 0.0 for o in options}
    for po in pred.predicted_options:
        name = po.option_name if po.option_name in probs else lookup.get(_norm(po.option_name))
        if name is None:
            raise ValueError(f"Can't match option {po.option_name!r} to {options}")
        probs[name] += po.probability
    vals = np.maximum(np.array([probs[o] for o in options], dtype=float), floor)
    vals = vals / vals.sum()  # smoothing: entries end up near (not exactly at) the floor
    return PredictedOptionList(
        predicted_options=[
            PredictedOption(option_name=o, probability=float(p)) for o, p in zip(options, vals)
        ]
    )


# ---- numeric/date: pin the CDF to the probabilities the model states in words ----
# The library builds the CDF by straight-line interpolation between declared percentiles and
# the question's bounds. That misplaces mass in two ways: before the first percentile it draws
# a line back to the lower bound (for dates often years in the past), and a coarse percentile
# grid can't say "12% before the upper bound". So the prompt asks the model for the cumulative
# probability at those points directly, and we add them as exact CDF points ("anchors").

_STATED_RE = re.compile(
    r"Probability\s+(below the lower bound|above the upper bound|before today)\s*:\s*([0-9]*\.?[0-9]+)\s*%",
    re.IGNORECASE,
)
_STATED_KEYS = {
    "below the lower bound": "below",
    "above the upper bound": "above",
    "before today": "past",
}
ANCHOR_EPS = 1e-3  # keep anchors off exactly 0/1
MIN_GAP = 1e-4  # library requires adjacent percentiles >= 5e-05 apart


def parse_stated_probabilities(text: str) -> dict[str, float]:
    """Read 'Probability below the lower bound / above the upper bound / before today: X%'
    lines. The last occurrence wins (the final answer comes last). Values are fractions."""
    out: dict[str, float] = {}
    for m in _STATED_RE.finditer(text or ""):
        out[_STATED_KEYS[m.group(1).lower()]] = min(1.0, float(m.group(2)) / 100)
    return out


def pin_percentiles(
    points: list[tuple[float, float]],
    anchors: list[tuple[float, float]],
    *,
    lower: float,
    upper: float,
    open_lower: bool,
    open_upper: bool,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]]]:
    """Merge model percentiles `points` [(p, value)] with `anchors` [(cumulative p, value)].
    Anchors win. Model points beyond an open bound that has an anchor are dropped (expected:
    the anchor already says how much mass lies beyond it), as are model points that contradict
    an anchor (a real inconsistency in the model's answer).
    Returns (kept, beyond, contradicting), each as (p, value) sorted by value."""
    anchors = sorted(anchors, key=lambda a: a[1])
    fixed: list[tuple[float, float]] = []
    for p, v in anchors:  # clamp, and force the anchors themselves to increase
        p = min(1 - ANCHOR_EPS, max(ANCHOR_EPS, p))
        if fixed and p < fixed[-1][0] + MIN_GAP:
            p = fixed[-1][0] + MIN_GAP
        fixed.append((p, v))
    anchor_values = {v for _, v in fixed}
    has_upper_anchor = open_upper and upper in anchor_values
    has_lower_anchor = open_lower and lower in anchor_values

    kept, beyond, contradicting = list(fixed), [], []
    for p, v in points:
        if (has_upper_anchor and v >= upper) or (has_lower_anchor and v <= lower):
            beyond.append((p, v))
        elif any(
            (av <= v and p < ap + MIN_GAP) or (av >= v and p > ap - MIN_GAP) for ap, av in fixed
        ):
            contradicting.append((p, v))
        else:
            kept.append((p, v))
    by_value = lambda x: (x[1], x[0])  # noqa: E731
    return sorted(kept, key=by_value), sorted(beyond, key=by_value), sorted(contradicting, key=by_value)


def to_jsonable(value):
    """Compact, JSON-safe view of any prediction type, for the logs."""
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "declared_percentiles"):
        return [{"p": x.percentile, "v": x.value} for x in value.declared_percentiles]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return str(value)
