"""Writes one JSON file per question per run into ./logs (uploaded as a run artifact by CI).

Each question's file is written as soon as that question finishes (posted or failed), so a
crash or timeout later in the run can't lose it. write_run_log() at the end of the run is a
safety net that only writes what wasn't logged already.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from forecasting_tools import ForecastReport, NumericDistribution

from bot.postprocess import to_jsonable

logger = logging.getLogger(__name__)


def _log_dir() -> Path:
    out = Path("logs") / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _run_id() -> str:
    return os.getenv("GITHUB_RUN_ID", "local")


def submitted_forecast(report: ForecastReport):
    """The forecast exactly as it is sent to Metaculus. For numeric/date questions that is the
    standardized CDF (get_cdf), not the aggregate's declared percentiles, which read lower
    because Metaculus's minimum slope is only applied at submission."""
    pred = report.prediction
    if isinstance(pred, NumericDistribution):
        if pred.cdf_size is None:  # mirrors NumericReport.publish_report_to_metaculus
            pred = NumericDistribution.from_question(pred.declared_percentiles, report.question)
        return [{"p": x.percentile, "v": x.value} for x in pred.get_cdf()]
    return to_jsonable(pred)


def _question_record(bot, question, mode: str, report=None, error=None) -> dict:
    pid = question.id_of_post
    rec = {
        "mode": mode, "run_id": _run_id(), "logged_at": datetime.now(timezone.utc).isoformat(),
        "post_id": pid, "url": question.page_url,
        "type": type(question).__name__,
        "question": question.question_text,
        "close_time": str(question.close_time),
    }
    if report is not None:
        rec.update({
            "forecast": submitted_forecast(report),
            "minutes": report.minutes_taken,
            "cost_estimate_usd": report.price_estimate,  # unreliable for new models; see guide
            "minor_errors": report.errors,
        })
    if error is not None:
        rec["error"] = f"{type(error).__name__}: {error}"[:3000]
    # Members and dossiers are kept even when the question failed: they were paid for.
    rec["members"] = bot.members.get(pid, [])
    rec["dossiers"] = bot.dossiers.get(pid, {})
    return rec


def write_question_log(bot, question, mode: str, report=None, error=None) -> None:
    """Log one question now. Never raises: a logging problem must not cost a forecast."""
    try:
        rec = _question_record(bot, question, mode, report=report, error=error)
        name = f"{question.id_of_post}_{_run_id()}.json"
        (_log_dir() / name).write_text(json.dumps(rec, indent=1, default=str))
        bot.logged_urls.add(question.page_url)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Could not write the log for {getattr(question, 'page_url', '?')}: {e}")


def write_run_log(bot, reports, mode: str) -> None:
    """End-of-run safety net: write anything the per-question logging didn't."""
    logged = getattr(bot, "logged_urls", set())
    for r in reports:
        if isinstance(r, ForecastReport):
            if r.question.page_url not in logged:
                write_question_log(bot, r.question, mode, report=r)
        elif not any(url and url in str(r) for url in logged):
            rec = {"mode": mode, "run_id": _run_id(),
                   "logged_at": datetime.now(timezone.utc).isoformat(),
                   "error": f"{type(r).__name__}: {r}"[:3000]}
            (_log_dir() / f"error_{_run_id()}_{uuid.uuid4().hex[:6]}.json").write_text(
                json.dumps(rec, indent=1, default=str)
            )
