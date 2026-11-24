"""Writes one JSON file per question per run into ./logs (pushed to your PRIVATE logs repo by CI)."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from forecasting_tools import ForecastReport

from bot.postprocess import to_jsonable


def write_run_log(bot, reports, mode: str) -> None:
    now = datetime.now(timezone.utc)
    out = Path("logs") / now.strftime("%Y-%m-%d")
    out.mkdir(parents=True, exist_ok=True)
    run_id = os.getenv("GITHUB_RUN_ID", "local")
    for r in reports:
        if isinstance(r, ForecastReport):
            pid = r.question.id_of_post
            rec = {
                "mode": mode, "run_id": run_id, "logged_at": now.isoformat(),
                "post_id": pid, "url": r.question.page_url,
                "type": type(r.question).__name__,
                "question": r.question.question_text,
                "close_time": str(r.question.close_time),
                "forecast": to_jsonable(r.prediction),
                "members": bot.members.get(pid, []),
                "dossiers": bot.dossiers.get(pid, {}),
                "minutes": r.minutes_taken,
                "cost_estimate_usd": r.price_estimate,  # unreliable for new models; see guide
                "minor_errors": r.errors,
            }
            name = f"{pid}_{run_id}.json"
        else:
            rec = {"mode": mode, "run_id": run_id, "logged_at": now.isoformat(),
                   "error": f"{type(r).__name__}: {r}"[:3000]}
            name = f"error_{run_id}_{uuid.uuid4().hex[:6]}.json"
        (out / name).write_text(json.dumps(rec, indent=1, default=str))
