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
