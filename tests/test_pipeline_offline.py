"""Runs the full 3x3 pipeline on a fake binary question with fake models. No network."""
import asyncio

import main
from forecasting_tools import BinaryPrediction, BinaryQuestion


class FakeLlm:
    def __init__(self, p):
        self.p = p
        self.model = f"fake-{p}"

    async def invoke(self, prompt):
        assert "does NOT mean the event hasn" in prompt  # rules block made it into the prompt
        return f"reasoning...\nProbability: {self.p}%"


async def fake_structure_output(text, output_type, **kwargs):
    p = float(text.rsplit("Probability:", 1)[1].strip().rstrip("%")) / 100
    return BinaryPrediction(prediction_in_decimal=p)


async def fake_dossiers(q):
    return {"A": "dossier A", "B": "dossier B", "C": "dossier C"}, {}


def make_bot(monkeypatch, probs):
    monkeypatch.setattr(main, "structure_output", fake_structure_output)
    monkeypatch.setattr(main, "build_dossiers", fake_dossiers)
    bot = main.ThreeByThreeBot(
        research_reports_per_question=1, predictions_per_research_report=9,
        publish_reports_to_metaculus=False, required_successful_predictions=0.33,
        enable_summarize_research=False,
        llms={"default": "openrouter/openai/gpt-6-luna", "summarizer": "openrouter/openai/gpt-6-luna",
              "researcher": "x", "parser": "openrouter/openai/gpt-6-luna"},
    )
    bot.forecasters = {m: FakeLlm(p) for m, p in probs.items()}
    return bot


def question():
    return BinaryQuestion(question_text="Will X happen?", id_of_post=123, id_of_question=456,
                          page_url="https://www.metaculus.com/questions/123", resolution_criteria="X happens.")


def test_nine_cells_run_and_aggregate(monkeypatch):
    bot = make_bot(monkeypatch, {"sol": 30, "opus": 40, "gemini": 99.9})
    report = asyncio.run(bot.forecast_questions([question()]))[0]
    members = bot.members[123]
    assert len(members) == 9 and all(m["ok"] for m in members)
    assert {m["cell"] for m in members} == {f"{d}x{m}" for d in "ABC" for m in ("sol", "opus", "gemini")}
    assert max(m["value"] for m in members) == 0.98  # member clip applied to the 99.9%
    assert report.prediction == 0.4  # median of 3x0.30, 3x0.40, 3x0.98


def test_one_family_failing_still_submits(monkeypatch):
    class Broken:
        model = "broken"
        async def invoke(self, prompt):
            raise RuntimeError("provider down")
    bot = make_bot(monkeypatch, {"sol": 30, "opus": 40, "gemini": 50})
    bot.forecasters["opus"] = Broken()
    report = asyncio.run(bot.forecast_questions([question()]))[0]
    assert sum(m["ok"] for m in bot.members[123]) == 6
    assert report.prediction == 0.4  # median of 3x0.30, 3x0.50


def test_log_written(monkeypatch, tmp_path):
    import json
    from bot.log_store import write_run_log
    bot = make_bot(monkeypatch, {"sol": 30, "opus": 40, "gemini": 50})
    reports = asyncio.run(bot.forecast_questions([question()], return_exceptions=True))
    monkeypatch.chdir(tmp_path)
    write_run_log(bot, reports, "dry_run")
    files = list((tmp_path / "logs").rglob("*.json"))
    rec = json.loads(files[0].read_text())
    assert rec["forecast"] == 0.4 and len(rec["members"]) == 9 and set(rec["dossiers"]) == {"A", "B", "C"}


# ---- date question: prompt asks for the stated probabilities, and the CDF is pinned to them ----
import re
from datetime import datetime, timedelta, timezone

from forecasting_tools import DatePercentile, DateQuestion


class FakeDateLlm:
    model = "fake-date"

    def __init__(self, answer):
        self.answer = answer
        self.prompts = []

    async def invoke(self, prompt):
        self.prompts.append(prompt)
        return "reasoning...\n" + self.answer


async def fake_date_structure_output(text, output_type, **kwargs):
    return [
        DatePercentile(percentile=int(n) / 100, value=datetime.fromisoformat(d).replace(tzinfo=timezone.utc))
        for n, d in re.findall(r"Percentile (\d+): (\d{4}-\d{2}-\d{2})", text)
    ]


def test_date_question_pinned_to_stated_probabilities(monkeypatch):
    now = datetime.now(timezone.utc)
    lo, hi = now - timedelta(days=1640), now + timedelta(days=184)  # range mostly in the past
    d = lambda days: (now + timedelta(days=days)).date().isoformat()
    # The martial-law pattern: ~12% inside the range, the rest beyond the open upper bound.
    answer = "\n".join(
        [f"Percentile {n}: {d(k)}" for n, k in
         [(1, 65), (5, 155), (10, 160), (20, 220), (40, 400), (60, 700), (80, 1000), (90, 1300), (95, 1500), (99, 1800)]]
        + ["Probability before today: 0%", "Probability above the upper bound: 88%"]
    )
    monkeypatch.setattr(main, "structure_output", fake_date_structure_output)
    monkeypatch.setattr(main, "build_dossiers", fake_dossiers)
    bot = make_bot(monkeypatch, {"sol": 1, "opus": 1, "gemini": 1})
    monkeypatch.setattr(main, "structure_output", fake_date_structure_output)
    fakes = {m: FakeDateLlm(answer) for m in ("sol", "opus", "gemini")}
    bot.forecasters = fakes
    q = DateQuestion(question_text="When will X end?", id_of_post=321, id_of_question=654,
                     page_url="https://www.metaculus.com/questions/321", resolution_criteria="X ends.",
                     lower_bound=lo, upper_bound=hi, open_lower_bound=False, open_upper_bound=True)
    report = asyncio.run(bot.forecast_questions([q]))[0]

    prompt = fakes["opus"].prompts[0]
    assert "Percentile 1: YYYY-MM-DD" in prompt and "Percentile 99: YYYY-MM-DD" in prompt
    assert "Probability before today: XX%" in prompt and "Probability above the upper bound: XX%" in prompt
    assert "Probability below the lower bound" not in prompt  # lower bound is closed

    # Thresholds allow for the library's aggregator re-applying Metaculus's minimum slope to
    # already-standardized member CDFs (about +0.9 points here; a separate, pre-existing issue).
    cdf = report.prediction.cdf
    i_today = round((now.timestamp() - lo.timestamp()) / (hi.timestamp() - lo.timestamp()) * 200)
    assert cdf[i_today].percentile < 0.025  # was ~10% before the fix
    assert abs(cdf[-1].percentile - 0.12) < 0.025  # stated 12% inside the range
    assert all(m["ok"] for m in bot.members[321]) and len(bot.members[321]) == 9
