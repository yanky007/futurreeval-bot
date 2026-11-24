"""Builds the three research dossiers for one question, in parallel.
A = Sol with OpenAI native web search (via OpenRouter)
B = Gemini with Google Search grounding + URL context (direct, uses your Google credits)
C = AskNews articles + fetched resolution-source page, summarized by Gemini
"""
import asyncio
import os
import re
from datetime import datetime, timezone

import requests
from forecasting_tools import AskNewsSearcher, GeneralLlm, MetaculusQuestion, clean_indents
from google import genai
from google.genai import types

from bot import config as cfg

URL_RE = re.compile(r"https?://[^\s)\]>\"'<]+")


def research_prompt(q: MetaculusQuestion) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return clean_indents(
        f"""
        You are a research assistant for a professional forecaster. Today is {today} (UTC).
        Do NOT give a probability or a forecast. Gather and organize evidence only.

        Question: {q.question_text}
        Resolution criteria: {q.resolution_criteria}
        Fine print: {q.fine_print}
        Question closes: {q.close_time}. Scheduled to resolve: {q.scheduled_resolution_time}.

        Write a dossier with these sections:
        1. Current status, as of today, of exactly what the resolution criteria measure. Give dates.
        2. The latest value or state reported by the resolution source named in the criteria, if you can find it.
        3. Scheduled events between now and the resolution date that could move the outcome.
        4. Base rates or reference classes with numbers (how often similar things happened, historical ranges).
        5. Evidence pointing each way.
        6. Anything conflicting, stale, or uncertain.
        7. Sources: a list of URLs with publication dates.
        Keep it under 1,200 words. State units explicitly for every number.
        """
    )


# ---- A: Sol native search ---------------------------------------------------
async def dossier_sol(q: MetaculusQuestion) -> str:
    llm = GeneralLlm(
        model=cfg.SOL,
        temperature=None,
        timeout=cfg.RESEARCH_TIMEOUT_S,
        allowed_tries=1,
        plugins=[{"id": "web", "engine": "native", "max_results": 10}],
        web_search_options={"search_context_size": "medium"},
        reasoning={"effort": cfg.RESEARCH_EFFORT},
    )
    return await llm.invoke(research_prompt(q))


# ---- B: Gemini grounded -----------------------------------------------------
_client: genai.Client | None = None


def _gemini() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


async def dossier_gemini(q: MetaculusQuestion) -> str:
    resp = await _gemini().aio.models.generate_content(
        model=cfg.GEMINI_MODEL,
        contents=research_prompt(q),
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(google_search=types.GoogleSearch()),
                types.Tool(url_context=types.UrlContext()),
            ],
            thinking_config=types.ThinkingConfig(thinking_level=cfg.GEMINI_RESEARCH_THINKING),
        ),
    )
    text = resp.text or ""
    if not text.strip():
        raise RuntimeError("Gemini returned an empty dossier")
    sources: list[str] = []
    meta = resp.candidates[0].grounding_metadata if resp.candidates else None
    for chunk in (meta.grounding_chunks or []) if meta else []:
        if chunk.web and chunk.web.uri:
            sources.append(f"- {chunk.web.title or ''} {chunk.web.uri}")
    if sources:
        text += "\n\nGrounding sources:\n" + "\n".join(sources[:15])
    return text


# ---- C: AskNews + resolution page ------------------------------------------
def _fetch_page(url: str) -> str:
    # Jina Reader turns a page into plain text. Free without a key (rate-limited).
    r = requests.get(f"https://r.jina.ai/{url}", timeout=30)
    r.raise_for_status()
    return r.text[: cfg.PAGE_CHARS]


async def dossier_asknews(q: MetaculusQuestion) -> str:
    news = await AskNewsSearcher().get_formatted_news_async(q.question_text)
    urls = URL_RE.findall(f"{q.resolution_criteria or ''} {q.fine_print or ''}")[:2]
    pages = []
    for u in urls:
        try:
            pages.append(f"### {u}\n" + await asyncio.to_thread(_fetch_page, u))
        except Exception as e:  # a failed page fetch should not kill the dossier
            pages.append(f"### {u}\n(fetch failed: {type(e).__name__})")
    raw = (
        "## News articles (AskNews)\n" + news
        + "\n\n## Resolution-source pages\n" + ("\n\n".join(pages) or "(no URL in the criteria)")
    )
    summarizer = GeneralLlm(
        model=cfg.GEMINI_LITELLM, temperature=None, timeout=cfg.RESEARCH_TIMEOUT_S,
        reasoning_effort="low",
    )
    prompt = (
        research_prompt(q)
        + "\n\nBuild the dossier using ONLY the material below. Do not add outside facts.\n\n"
        + raw[: cfg.RAW_CHARS]
    )
    return await summarizer.invoke(prompt)


SOURCES = {
    "A": ("Sol web search", dossier_sol),
    "B": ("Gemini grounded search", dossier_gemini),
    "C": ("AskNews + resolution page", dossier_asknews),
}


async def build_dossiers(q: MetaculusQuestion) -> tuple[dict[str, str], dict[str, str]]:
    """Returns (dossiers that succeeded, errors for the ones that failed)."""
    keys = list(SOURCES)
    results = await asyncio.gather(
        *[asyncio.wait_for(SOURCES[k][1](q), timeout=cfg.RESEARCH_TIMEOUT_S + 30) for k in keys],
        return_exceptions=True,
    )
    dossiers, errors = {}, {}
    for k, res in zip(keys, results):
        if isinstance(res, BaseException) or not str(res).strip():
            errors[k] = f"{type(res).__name__}: {res}"[:300]
        else:
            dossiers[k] = str(res)[: cfg.DOSSIER_CHARS]
    return dossiers, errors


def combine_dossiers(dossiers: dict[str, str], errors: dict[str, str]) -> str:
    parts = [f"## Dossier {k}: {SOURCES[k][0]}\n{v}" for k, v in dossiers.items()]
    parts += [f"## Dossier {k}: FAILED ({e})" for k, e in errors.items()]
    return "\n\n".join(parts)
