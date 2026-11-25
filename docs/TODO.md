# Deferred fixes (not blocking)

Found during the step 9 smoke test (Nov 24, 2026). None of these blocks going live.

## 1. Research section garbled in the private Metaculus comment

- **Symptom:** the run log shows
  `ERROR - Error formatting research report: First section must be at the highest heading level ...`.
  forecasting-tools then falls back and replaces every `#` with `[Hashtag]` in the research part of the comment. The comment still posts, and the content is all there.
- **Cause:** `combine_dossiers()` in `bot/dossiers.py` wraps each dossier under a level-2 heading (`## Dossier A: ...`), but a dossier can itself start with a level-1 `#` heading (Sol's did). The library's `MarkdownTree.report_sections_to_markdown(sections, 3)` requires the first section to be at the highest level.
- **Fix:** demote every Markdown heading inside each dossier by two levels before wrapping (cap at `######`), so the inner headings are always below `## Dossier X`.
- **Test:** add an offline test that formatting succeeds on combined dossiers whose text starts with `#`.
- **Also watch:** the same fallback exists for forecaster rationales (`_format_forecaster_rationales`). It did not trigger in the test, but the same `ERROR` line would show up there.

## 2. Resolution-page fetch fails in dossier C

- **Symptom:** dossier C reported `HTTPError` fetching the Forbes and Wayback pages named in the resolution criteria. The fetch goes through Jina Reader (`r.jina.ai`, free tier, no key) in `_fetch_page()`.
- **Impact:** small. C then relies on the AskNews articles alone, and dossier A (Sol) reached Forbes directly.
- **Options:** add a Jina API key (higher limits), fall back to a direct `requests.get` of the URL, or leave it.

## 3. Shared concurrency queue (watch only, no change yet)

- The tournament, MiniBench and Test Bot workflows share `concurrency: forecast-paid`, so only one paid run uses Luna at a time.
- GitHub keeps only one *pending* run per group. If a run lasts more than 20 minutes, a queued run from the other workflow can be cancelled and replaced. Its questions are picked up by the next run.
- Revisit only if MiniBench or main-tournament questions get missed.
