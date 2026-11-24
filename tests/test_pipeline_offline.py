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
