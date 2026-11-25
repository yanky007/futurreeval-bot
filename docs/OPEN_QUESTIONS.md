# Open questions

Questions about the bot's design and analysis that are still open. Add to this list as new ones come up; record the answer (and the date) when one is settled.

## 1. Research first or model first?

- **Now:** research first. Three dossiers are written blind to what the forecasters will need, then each model forecasts from each dossier.
- **Alternative (discussed Nov 24):** model first. Each forecaster decides what it wants to calculate and requests that research; researchers return a general dossier plus specific answers, giving 9 targeted research runs. Rough estimate: about 2× the cost per question.

## 2. Should I expect models to be able to assign confidence to their estimates?

- That is, are the models' stated probabilities and percentile widths calibrated, or does that need correcting after the fact (e.g. Platt scaling)?

## 3. How many predictions do I need to answer a question about model efficiency in a given direction?

- E.g. "is model X more accurate than model Y?", a one-sided test. Depends on the score difference to detect and its per-question variance. Earlier estimate: Fall alone gives too few resolved questions to detect differences smaller than about 4–7 peer points per question.

## 4. Once answers start coming in, should I weakly weight forecasters accordingly?

- E.g. weight cell (or model) $i$ as $w_i \propto e^{\beta S_i}$, where $S_i$ is its cumulative score on resolved questions, normalized so the weights sum to 1, with a small $\beta$.
- First resolutions: MiniBench rounds, and the Trump approval question on Dec 31.
- Only resolved questions may be used (tournament rule against tuning on open questions).

## 5. Should I do nested forecasts?

- **The issue:** to forecast event A, a forecaster often has to estimate the probabilities of dependent sub-events $x_1, \dots, x_n$. Right now it does that informally inside one rationale ("vibing" it).
- **Example:** the Trump net-worth question hinged on whether Trump Media (DJT) would spike or become very volatile (it needed roughly 3–5×). The forecasters hand-waved their way through that.
- **Idea:** when a forecast depends on a sub-quantity, run a separate forecast for that sub-quantity (its own research and forecast), then combine the results into the forecast for A.
- **Open sub-questions:** how to control errors as they propagate up through the levels, and how to avoid getting lost in endlessly nested forecasts (when to decompose, how deep, and at what cost).

## Also raised (Nov 25)

- **Sanity check fails twice:** if a cell's forecast fails a sanity check, the plan is to flag it and reforecast once. If the retry also fails, should that cell be dropped from the aggregate (keeping at least 3 cells) or kept with a flag?
- **Keep Sol?** Kept for robustness (Nov 25). On three test questions, removing it moved the combined forecast by 1.4 points or less, while it is about half the per-question cost. Revisit once questions resolve.
