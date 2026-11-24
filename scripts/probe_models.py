"""Calls every model and research source once. Run locally before going live:
    (run it from GitHub: Actions > Test Bot > probe)
Every line should say OK. Fix model IDs / parameters in bot/config.py until they do."""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dotenv  # noqa: E402

dotenv.load_dotenv()
from forecasting_tools import ApiFilter, GeneralLlm, MetaculusClient  # noqa: E402

from bot import config as cfg  # noqa: E402
from bot.dossiers import SOURCES  # noqa: E402


async def probe(name, coro):
    t = time.time()
    try:
        out = await coro
        print(f"OK    {name:28s} {time.time() - t:6.1f}s  {str(out)[:80]!r}")
        return True
    except Exception as e:
        print(f"FAIL  {name:28s} {time.time() - t:6.1f}s  {type(e).__name__}: {str(e)[:200]}")
        return False


async def main():
    ok = True
    for name, llm in cfg.build_forecasters().items():
        ok &= await probe(f"forecaster:{name}", llm.invoke("Reply with exactly the word OK."))
    ok &= await probe("cheap (parser/summarizer)", GeneralLlm(model=cfg.CHEAP).invoke("Reply OK."))
    # One real question from the bot-testing-area for the research sources:
    qs = await MetaculusClient().get_questions_matching_filter(
        ApiFilter(allowed_tournaments=["bot-testing-area"], allowed_statuses=["open"])
    )
    q = qs[0]
    print(f"Research probe question: {q.page_url}")
    for key, (label, fn) in SOURCES.items():
        ok &= await probe(f"dossier {key}: {label}", fn(q))
    sys.exit(0 if ok else 1)


asyncio.run(main())
