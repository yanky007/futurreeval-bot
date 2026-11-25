"""Every tunable lives here. Verify model IDs with scripts/probe_models.py before going live."""
from forecasting_tools import GeneralLlm
from bot.request_pacing import PacedLlm

# ---- Models -------------------------------------------------------------------
# Sol and Opus go through OpenRouter (one key, proven request format).
# Gemini goes direct to Google so your Google AI Pro credits pay for it.
SOL = "openrouter/openai/gpt-6.1-sol"
OPUS = "openrouter/anthropic/claude-opus-5.5"
GEMINI_MODEL = "gemini-4-hydrogen"               # name for the google-genai SDK
GEMINI_LITELLM = f"gemini/{GEMINI_MODEL}"         # name for litellm (reads GEMINI_API_KEY)
CHEAP = "openrouter/openai/gpt-6-luna"            # output parser + research summarizer

FORECAST_EFFORT = "high"           # report: high beat standard 8/8; xhigh ~ high
RESEARCH_EFFORT = "medium"         # Sol's effort while searching
GEMINI_RESEARCH_THINKING = "low"   # Gemini thinking level while searching

# ---- Grid ---------------------------------------------------------------------
DOSSIERS = ("A", "B", "C")         # A = Sol web search, B = Gemini grounded, C = AskNews + resolution page
MODELS = ("sol", "opus", "gemini")

# ---- Limits -------------------------------------------------------------------
RESEARCH_TIMEOUT_S = 240
FORECAST_TIMEOUT_S = 360
DOSSIER_CHARS = 12_000             # cap per dossier fed to forecasters
RAW_CHARS = 40_000                 # cap on raw AskNews + page text fed to the summarizer
PAGE_CHARS = 15_000                # cap per fetched resolution page

# ---- Calibration --------------------------------------------------------------
MEMBER_CLIP = (0.02, 0.98)         # each binary forecast
FINAL_CLIP = (0.02, 0.98)          # aggregate, when >= 2 model families succeeded
FINAL_CLIP_ONE_MODEL = (0.05, 0.95)  # aggregate, when only one family succeeded
MC_FLOOR = 0.005                   # minimum probability per multiple-choice option


def build_support_llm() -> GeneralLlm:
    # Use this SAME instance for parser and summarizer: 15 requests/minute total.
    # Pacing is applied to physical attempts, including library retries.
    return PacedLlm(model=CHEAP, interval_s=4.0, temperature=None, allowed_tries=1)


def build_forecasters() -> dict[str, GeneralLlm]:
    common = dict(temperature=None, timeout=FORECAST_TIMEOUT_S, allowed_tries=2)
    return {
        "sol": GeneralLlm(model=SOL, reasoning={"effort": FORECAST_EFFORT}, **common),
        "opus": GeneralLlm(model=OPUS, reasoning={"effort": FORECAST_EFFORT}, max_tokens=32_000, **common),
        "gemini": GeneralLlm(model=GEMINI_LITELLM, reasoning_effort=FORECAST_EFFORT, **common),
    }
