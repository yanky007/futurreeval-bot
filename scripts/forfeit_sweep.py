"""Daily: lists tournament questions that closed in the last 36 h without a forecast from this bot.
Exits 1 (so GitHub emails you) if any were missed."""
import asyncio
import sys
from datetime import datetime, timedelta, timezone

import dotenv

dotenv.load_dotenv()
from forecasting_tools import ApiFilter, MetaculusClient  # noqa: E402

client = MetaculusClient()
since = datetime.now(timezone.utc) - timedelta(hours=36)
missed = []
for tid in [client.CURRENT_AI_COMPETITION_ID, client.CURRENT_MINIBENCH_ID]:
    f = ApiFilter(
        allowed_tournaments=[tid],
        allowed_statuses=["closed", "resolved"],
        close_time_gt=since,
    )
    qs = asyncio.run(client.get_questions_matching_filter(f, error_if_question_target_missed=False))
    # The library only filters for 'forecasted = True', so filter for 'not forecasted' here.
    missed += [(tid, q.page_url, q.close_time) for q in qs if not q.already_forecasted]
for tid, url, ct in missed:
    print(f"MISSED  {tid}  {url}  closed {ct}")
print(f"{len(missed)} missed question(s) in the last 36 h")
sys.exit(1 if missed else 0)
