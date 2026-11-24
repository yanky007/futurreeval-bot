"""Pure functions for cleaning model outputs. Unit-tested in tests/."""
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


def to_jsonable(value):
    """Compact, JSON-safe view of any prediction type, for the logs."""
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "declared_percentiles"):
        return [{"p": x.percentile, "v": x.value} for x in value.declared_percentiles]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return str(value)
