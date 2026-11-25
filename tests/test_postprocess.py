import pytest
from forecasting_tools import PredictedOption, PredictedOptionList

from bot import config as cfg
from bot.cells import assign_cell
from bot.postprocess import canonicalize_options, clip


def test_all_nine_cells_covered():
    cells = {assign_cell(k, list(cfg.DOSSIERS)).label for k in range(9)}
    assert len(cells) == 9


def test_failed_dossier_is_repointed_and_models_stay_balanced():
    cells = [assign_cell(k, ["A", "C"]) for k in range(9)]
    assert all(c.dossier in {"A", "C"} for c in cells)
    for m in cfg.MODELS:
        assert sum(c.model == m for c in cells) == 3


def test_clip():
    assert clip(0.999, cfg.MEMBER_CLIP) == 0.98
    assert clip(0.0, cfg.MEMBER_CLIP) == 0.02
    assert clip(0.5, cfg.MEMBER_CLIP) == 0.5


def _pol(pairs):
    return PredictedOptionList(
        predicted_options=[PredictedOption(option_name=n, probability=p) for n, p in pairs]
    )


def test_canonicalize_fixes_names_adds_missing_and_floors():
    options = ["In Phoenix not Las Vegas", "In both cities", "In neither city"]
    raw = _pol([("in phoenix  NOT las vegas", 0.5), ("In both cities.", 0.5)])
    out = canonicalize_options(raw, options, floor=0.005)
    names = [o.option_name for o in out.predicted_options]
    probs = [o.probability for o in out.predicted_options]
    assert names == options
    assert abs(sum(probs) - 1) < 1e-9
    assert min(probs) >= 0.004


def test_symbols_are_not_merged():
    out = canonicalize_options(_pol([("<5", 0.8), (">5", 0.2)]), ["<5", ">5"], 0.005)
    assert [round(o.probability, 2) for o in out.predicted_options] == [0.8, 0.2]
    with pytest.raises(ValueError):
        canonicalize_options(_pol([("5", 1.0)]), ["<5", ">5"], 0.005)


def test_canonicalize_rejects_unmatchable():
    with pytest.raises(ValueError):
        canonicalize_options(_pol([("Something else", 1.0)]), ["Yes option", "No option"], 0.005)


# ---- numeric/date pinning ----
from datetime import datetime, timezone

from forecasting_tools import NumericDistribution, Percentile

from bot.postprocess import parse_stated_probabilities, pin_percentiles

DAY = 86400.0


def _ts(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


def test_parse_stated_probabilities_last_wins():
    text = (
        "draft: Probability above the upper bound: 70%\n"
        "Percentile 99: 2031-01-01\n"
        "probability before today: 0%\n"
        "Probability above the upper bound: 88.5 %\n"
    )
    assert parse_stated_probabilities(text) == {"past": 0.0, "above": 0.885}
    assert parse_stated_probabilities("Percentile 10: 5") == {}


def test_pin_drops_points_beyond_open_bound_and_adds_anchors():
    lo, hi, today = _ts("2022-05-29"), _ts("2027-05-28"), _ts("2026-11-25")
    pts = [(0.01, _ts("2027-01-29")), (0.05, _ts("2027-04-29")), (0.10, _ts("2027-05-20")),
           (0.20, _ts("2027-06-30")), (0.60, _ts("2028-06-01")), (0.99, _ts("2031-01-01"))]
    kept, beyond, contradicting = pin_percentiles(pts, [(0.0, today), (1 - 0.88, hi)],
                                                  lower=lo, upper=hi, open_lower=False, open_upper=True)
    assert [v for _, v in beyond] == [v for _, v in pts[3:]]  # everything past the cutoff
    assert contradicting == []
    assert kept[0] == (0.001, today) and kept[-1] == (0.12, hi)  # anchors, 0% clamped up
    assert [p for p, _ in kept] == sorted(p for p, _ in kept)


def test_pin_drops_points_that_contradict_an_anchor():
    # model says 50% above the bound but puts its 80th percentile inside the range
    kept, beyond, contradicting = pin_percentiles([(0.2, 10.0), (0.8, 40.0)], [(0.5, 50.0)],
                                                  lower=0.0, upper=50.0, open_lower=False, open_upper=True)
    assert contradicting == [(0.8, 40.0)] and beyond == [] and kept == [(0.2, 10.0), (0.5, 50.0)]


def test_pinned_cdf_matches_stated_probabilities():
    """The martial-law case: the posted CDF should put ~nothing before today and
    match the stated 12% at the cutoff (it was 9.9% and 20.8% before the fix)."""
    lo, hi, today = _ts("2022-05-29"), _ts("2027-05-28"), _ts("2026-11-25")
    pts = [(0.01, _ts("2027-01-29")), (0.04, _ts("2027-01-30")), (0.05, _ts("2027-04-29")),
           (0.10, _ts("2027-05-01")), (0.20, _ts("2027-06-30"))]
    kept, _, _ = pin_percentiles(pts, [(0.0, today), (0.12, hi)],
                              lower=lo, upper=hi, open_lower=False, open_upper=True)
    dist = NumericDistribution(
        declared_percentiles=[Percentile(percentile=p, value=v) for p, v in kept],
        open_upper_bound=True, open_lower_bound=False, upper_bound=hi, lower_bound=lo,
        zero_point=None, is_date=True,
    )
    cdf = dist.cdf
    def cdf_at(t):
        i = round((t - lo) / (hi - lo) * (len(cdf) - 1))
        return cdf[i].percentile
    assert cdf_at(today) < 0.015  # only Metaculus's minimum slope is left in the past
    assert abs(cdf[-1].percentile - 0.12) < 0.015
