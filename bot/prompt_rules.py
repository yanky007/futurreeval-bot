"""Rules pasted into every forecasting prompt (replaces the template's 'Today is ...' line)."""
from datetime import datetime, timezone


def forecast_rules() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""Today is {today} (UTC).
Rules you must follow:
- Keep three things separate: the forecasting deadline, whether the underlying event has already happened, and the official resolution. The question being open for forecasts does NOT mean the event hasn't happened. Judge the current evidence against the exact resolution criteria.
- Read the resolution criteria and fine print literally. Where they differ from the question title, the criteria win.
- For any deadline ("before X", "by X", "on or after X"), state exactly which dates count, using the fine print. Count the days left from today.
- Before giving any number, state its unit and scale (per day vs per month, millions vs raw count, percent vs fraction) and check it matches the question's unit.
- Start from a base rate or reference class, then adjust for the specific evidence."""
