# futureeval-bot

A forecasting bot for the [Metaculus FutureEval bot tournament](https://www.metaculus.com/futureeval/).

**Design: 3 × 3.** For each question the bot builds three independent research dossiers
(A: GPT-6.1 Sol with web search · B: Gemini with Google Search grounding · C: AskNews news + the
resolution-source page), then has three models (GPT-6.1 Sol, Claude Opus 5.5, Gemini) each forecast
from each dossier. The nine forecasts are aggregated by the `forecasting-tools` framework
(binary: median, multiple choice: mean, numeric: median CDF) and clipped.

Setup: see [docs/QUICKSTART.md](docs/QUICKSTART.md).

Built on Metaculus's [metac-bot-template](https://github.com/Metaculus/metac-bot-template);
the template code is theirs. Everything else is MIT-licensed (see LICENSE).
