# Quickstart: from zero to live in 10 steps (detailed)

> **November 24 correction:** Paid smoke tests now run exactly **one** testing-area
> question, not the entire area. The parser and summarizer share a paced Luna
> instance (one request every four seconds, including retries). Paid workflows
> share a concurrency group so separate runs cannot exceed that allowance together.
> Test Bot requires an explicit **Allow paid API calls** checkbox; it defaults off.
> These are request/batch controls, **not a hard dollar cap**. Configure provider
> spending limits before enabling another paid test. Never rerun an older workflow
> attempt: it uses the old code. Start a new run after this correction is merged.

This guide pairs with `futureeval-bot.zip`, which is the complete repo. You won't fork anything or install Python locally. All testing runs on GitHub's servers.

**Time:** about 1.5–2 hours, much of it waiting for runs to finish.
**Order matters in only two places:** add the secrets *before* pushing (step 6 before step 7), and keep `LIVE` set to `false` until step 10.

**What you'll collect along the way.** Keep these in your password manager, never in a file in the repo:

| Name | From step | Becomes GitHub secret |
|---|---|---|
| Metaculus bot token | 1 | `METACULUS_TOKEN` |
| OpenRouter key | 2 | `OPENROUTER_API_KEY` |
| Gemini API key | 3 | `GEMINI_API_KEY` |
| AskNews credentials (arrive later) | 4 | `ASKNEWS_CLIENT_ID` + `ASKNEWS_SECRET`, or `ASKNEWS_API_KEY` |

---

## Part 1: Accounts (~45 min)

### Step 1. Metaculus bot account and participation form

1. Log in to Metaculus as yourself (`yankyl`).
2. Click your username (top right) → **Settings** → **My Forecasting Bots**. If you can't find it, start from https://www.metaculus.com/futureeval/participate/, which links there.
3. Create a bot. Choose its username carefully (e.g. `yankyl-bot`). This is your **main bot**, the only one eligible for prizes. Any experimental bot you add later must be labelled as secondary (e.g. `yankyl-bot-v2`).
4. Copy the bot's **API token** and save it as *Metaculus bot token*.
5. Note the email shown for the bot, if any. AskNews asks for it in step 4.
6. Open the participation form: https://forms.gle/aQdYMq9Pisrf1v7d8
   - Fill in the **first section** (3 required questions). Everyone has to do this before submitting forecasts.
   - **Skip the credit-request section.** You're self-funding. (GPT's review cited an Oct 13 Metaculus comment saying Fall credit applications are closed.)
   - Submit.

**Done when:** you have the token saved and the form submitted.

### Step 2. OpenRouter (runs Sol, Opus, and the cheap parser model)

1. Go to https://openrouter.ai and sign in (Google login is fine).
2. Click your avatar → **Credits** → **Add credits** → **$100**. OpenRouter adds a small fee (around 5%), shown at checkout. Prepaid credit also works as a hard stop: when it runs out, calls fail instead of billing you more.
3. Avatar → **Keys** → **Create key**:
   - Name: `futureeval-bot`
   - **Credit limit:** `150`. The key stops working after spending this much, even if you top up the account.
4. Copy the key immediately. OpenRouter shows it only once. Save it as *OpenRouter key*.

**Done when:** the key is saved and the account shows a $100 balance.

### Step 3. Google AI Studio (runs Gemini; your AI Pro credits pay first)

1. Go to https://aistudio.google.com, signed in with the Google account that has AI Pro.
2. **Billing and credits.** AI Studio now handles this inside the app (Google's Nov 13 post: "Claim your Google Cloud Credits in Google AI Studio"). Follow its prompts to set up billing, which needs a card, and **claim the monthly credits**. Your $10/month credit is spent before your card is charged.
3. **Get API key** (left sidebar) → **Create API key**. Pick the **same project** that has billing linked. A key in an unbilled project gets free-tier limits and won't use your credits.
4. Copy the key and save it as *Gemini API key*.
5. **Spend tab** (or Billing → Spend) → **Monthly spend cap** → enter what you're willing to pay per month in total, e.g. `25`. My estimate for Gemini's share is $40–50 over the season, so $25/month leaves room. Billing data lags about 10 minutes, so the cap can be overshot slightly.
6. Open the model picker in AI Studio's chat and confirm **`gemini-4-hydrogen`** is listed. If it isn't, note which Gemini models *are* listed; you'll swap the name in step 8.

**What happens if you hit the cap:** Gemini calls fail. That loses dossiers B and C plus the three Gemini forecasts, and the bot keeps submitting with Sol + Opus on dossier A. You'll get failure-free runs with a thinner ensemble, not missed questions.

**Done when:** the key is saved, the cap is set, and you know the exact Gemini model name.

### Step 4. AskNews (free news search; don't wait for it)

1. Sign up at https://my.asknews.app using the email from step 1.5. If the bot has no email of its own, use your Metaculus email.
2. Ask for the free FutureEval tier, either by messaging **@freqai** on the AskNews Discord (https://discord.gg/99qt5HGgUn) or by emailing **contact@asknews.app**. Include your bot username, the email you registered with, your name, LinkedIn, and affiliation.
3. **Carry on with the next steps.** When AskNews confirms (could be days), go to https://my.asknews.app/en/settings/api-credentials and create credentials. You'll get either a **client ID + secret** or a single **API key**. Add them as secrets as described in step 6. Nothing else changes.

**Until then:** dossier C fails on every question, and its three cells automatically use dossiers A and B instead. The bot works fine without it.

### Step 5. GitHub email alerts

1. On GitHub: avatar → **Settings** → **Notifications**.
2. Find the **Actions** section and turn on email for **failed workflows only**.

This email is your alarm. Every problem the bot can detect shows up as a failed run.

---

## Part 2: Repo (~15 min)

### Step 6. Create the empty repo and add the secrets

1. GitHub → **+** (top right) → **New repository**:
   - Name: `futureeval-bot`
   - Visibility: **Public**. Open source also earns the 2.5× multiplier on the MiniBench grant, if that ever applies to you.
   - **Leave every "Initialize" box unticked**: no README, no .gitignore, no license. The zip already has them, and an initialized repo would make the first push fail.
   - **Create repository.**
2. In the new repo: **Settings** (repo tab, not your account) → left sidebar **Secrets and variables** → **Actions**.
3. **Secrets** tab → **New repository secret**, once for each. The names must match exactly, including capitals:
   - `METACULUS_TOKEN` → Metaculus bot token
   - `OPENROUTER_API_KEY` → OpenRouter key
   - `GEMINI_API_KEY` → Gemini API key
   - (later, from AskNews) `ASKNEWS_CLIENT_ID` and `ASKNEWS_SECRET`, **or** `ASKNEWS_API_KEY`
4. **Variables** tab → **New repository variable**:
   - Name `LIVE`, value `false`.

**Why `LIVE`:** both tournament workflows and the daily check skip themselves unless `LIVE` is `true`. That's what lets you push and test without forecasting in the real tournaments.

**Done when:** the Secrets tab lists 3 secrets and the Variables tab lists `LIVE = false`.

### Step 7. Push the code

1. **Git for Windows** (skip this if `git --version` already works in PowerShell): install from https://git-scm.com/download/win with the default options, then reopen PowerShell.
2. Unzip `futureeval-bot.zip` somewhere convenient, e.g. `Documents`. You'll get a folder named `futureeval-bot`.
3. In PowerShell:
   ```powershell
   cd $HOME\Documents\futureeval-bot
   git init -b main
   git add -A
   git commit -m "FutureEval 3x3 bot"
   git remote add origin https://github.com/<your-username>/futureeval-bot.git
   git push -u origin main
   ```
   - If git asks for your name and email first, run `git config --global user.name "Yanky Landau"` and `git config --global user.email "<your GitHub email>"`, then repeat the `commit` line.
   - On the first push, a browser window opens to sign in to GitHub. Approve it.
4. Refresh the repo page on GitHub. You should see `bot/`, `scripts/`, `tests/`, `docs/`, `.github/`, `main.py`, and the rest.
5. Click the **Actions** tab:
   - **CI** runs the 10 offline tests and should turn green in about 2 minutes.
   - Over the next hour you'll also see **Forecast on new AI tournament questions** and **Forecast on MiniBench** runs appear every 20 minutes, marked **skipped**. That's `LIVE = false` working.

**If CI is red:** open the run → **tests** → read the last lines. A failure here means the repo was changed on the way. Re-unzip and push again.

**Done when:** CI is green.

---

## Part 3: Test and go live (~45 min)

### Step 8. Probe: call every model once

Before launching: configure provider spending limits, then explicitly check
**Allow paid API calls** in the Run workflow form. Leave it unchecked while
validating code with CI, which runs offline and has no paid model credentials.

1. **Actions** tab → left sidebar **Test Bot** → **Run workflow** (button on the right) → mode **`probe`** → **Run workflow**.
2. Wait about 2–5 minutes, then click the run → **test_job** → expand **Run bot**.
3. You want 7 lines starting with `OK`:
   ```
   OK    forecaster:sol        ...
   OK    forecaster:opus       ...
   OK    forecaster:gemini     ...
   OK    cheap (parser/summarizer) ...
   Research probe question: https://www.metaculus.com/questions/...
   OK    dossier A: Sol web search ...
   OK    dossier B: Gemini grounded search ...
   OK    dossier C: AskNews + resolution page ...   (FAIL is expected until AskNews arrives)
   ```

**If a line says FAIL**, the error text after it says why:

| Error mentions | Cause | Fix in `bot/config.py` |
|---|---|---|
| "not found", "No endpoints", 404, for sol / opus / cheap | Model ID differs on OpenRouter | Open the model's page on openrouter.ai, copy its ID (e.g. `openai/gpt-6.1-sol`), and set it with the `openrouter/` prefix: `SOL = "openrouter/openai/gpt-6.1-sol"` |
| "not found" for gemini, or dossier B | Gemini name differs | Set `GEMINI_MODEL = "<exact name from step 3.6>"` |
| "reasoning_effort" or "unexpected/unsupported parameter" for gemini | litellm doesn't map that parameter for this model | In `build_forecasters`, delete `reasoning_effort=FORECAST_EFFORT, ` from the `"gemini"` line. In `bot/dossiers.py`, also delete `reasoning_effort="low",` from the summarizer |
| "thinking_level" in dossier B | Model doesn't accept thinking levels | In `bot/dossiers.py`, delete the line `thinking_config=types.ThinkingConfig(...)` |
| 401 / "unauthorized" from Metaculus | Token wrong | Re-copy the bot token into the `METACULUS_TOKEN` secret |
| 401 / 402 from OpenRouter | Key wrong or no credit | Check the key and balance from step 2 |
| AskNews auth error in dossier C | No AskNews credentials yet | Expected. Ignore until AskNews replies |

**How to edit a file without Git:** in the repo on GitHub, click into the file (e.g. `bot` → `config.py`) → pencil icon (**Edit**) → make the change → **Commit changes…** → "Commit directly to the main branch" → **Commit changes**. Then run the probe again.

**Done when:** every line is `OK`, except dossier C if AskNews hasn't replied yet.

### Step 9. Live test on the bot-testing-area

**Revised scope:** Each run forecasts one question. With no question ID it selects
one binary question if available. To test another format, enter that testing-area
post ID in the Run workflow form. The script rejects IDs outside the open testing
area before making forecasts. Inspect the one result and real provider charges
before deciding whether to launch another test. The instructions below about
checking every format apply across these separate, deliberately selected runs.

The bot-testing-area is an unscored Metaculus tournament with one question of each type. Forecasting there is allowed and doesn't count.

1. **Actions → Test Bot → Run workflow → mode `test_questions` → Run workflow.**
2. It takes about 10–20 minutes. The run should finish **green**.
   - **If it's red:** open **Run bot** and scroll to the bottom. Lines starting with `ERROR` name the question and the failure. A single cell failing, for example an option name that couldn't be matched, is fine as long as each question still got at least 3 successful forecasts. A red run means some question got fewer.
3. **Check the forecasts on Metaculus, as the bot.** In **My Forecasting Bots**, use the option to view or switch to the bot account. Then open https://www.metaculus.com/tournament/bot-testing-area/ and, for **each question** (binary, numeric, multiple choice, date):
   - a forecast from the bot is on the graph
   - the **Private** comments tab has the bot's comment. **This is required for prizes**, so it's the most important check.
   - the comment looks complete: the three dossiers, nine rationales each tagged `[cell Axsol]`, `[cell Bxopus]` and so on, and the final forecast.
4. **Look at the nine forecasts (optional, 5 min).** Open the run's summary page, scroll to **Artifacts**, download `logs-<number>`, and unzip it. There's one JSON file per question. In each, check:
   - `members` lists 9 entries, mostly `"ok": true`, and any failure has a readable `"error"`
   - binary values are between 0.02 and 0.98, and multiple-choice options use the question's exact names and sum to 1
   - the three `dossiers` actually differ
5. **Measure the real cost.** On **OpenRouter → Activity**, add up today's spend. On **AI Studio → Spend**, check Gemini's share (it lags; look again an hour later). Divide by the number of testing-area questions. I estimated **$1.60–1.80 per question**. If you're far above that, tell me which provider is the expensive one and we'll trim it.

**Done when:** every testing-area question has a forecast and a private comment from the bot.

### Step 10. Go live

1. Repo → **Settings → Secrets and variables → Actions → Variables** → click `LIVE` → change the value to **`true`** → **Update variable**.
2. **Actions → Forecast on new AI tournament questions → Run workflow → Run workflow.** This starts the first run now instead of waiting up to 20 minutes.
3. **Actions → Forecast on MiniBench → Run workflow → Run workflow.**
4. When both runs finish green, check a couple of main-tournament questions on Metaculus as the bot: forecast plus private comment, same as step 9.
5. **Actions → Daily checks → Run workflow** once. On day one it may list questions that closed before you started. That's expected, not a problem.

**You're live.** Both tournaments now run every 20 minutes without you. The bot skips questions it has already forecast, so repeated runs are harmless.

---

## After launch

### What to watch
- **Your email, nothing else.** A failed run means something broke for at least one question. Open the run, find the `ERROR` lines, and fix the cause if it isn't a one-off provider outage.
- **The daily check** (8:17 am New Jersey time) fails and emails you if any question closed in the last 36 hours without your forecast.
- **Money, once a week:** check the OpenRouter balance (top up before it runs out) and the AI Studio Spend page.

### Making changes after you're live
1. Set `LIVE` to `false`.
2. Edit and commit.
3. Run **Test Bot → `test_questions`** and check the results as in step 9.
4. Set `LIVE` back to `true`.

This keeps you inside the tournament rule against testing on live questions. A change goes live the moment you push, so never push untested changes while `LIVE` is `true`.

### The tournament rules, in practice
- **While a question is open:** look only at operational status, meaning whether the forecast posted and what errored. Fixing a crash is fine.
- **Don't** read an open question's forecast and then change the bot to improve it. Read forecast content after questions close.
- **If you're unsure whether a fix is allowed,** ask on the Metaculus Discord before changing anything.

### If the daily check reports misses more than once: add a backup trigger
GitHub's scheduler sometimes drops runs. A second trigger from outside fixes that. **Only do this if you need it.**
1. GitHub → avatar → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**:
   - Name `cron-trigger`, expiration Mar 31, 2027
   - Repository access: **Only select repositories →** `futureeval-bot`
   - Permissions → Repository → **Actions: Read and write** (leave everything else at none)
   - Generate, then copy the token
2. Sign up at https://cron-job.org → **Create cronjob**:
   - URL: `https://api.github.com/repos/<your-username>/futureeval-bot/actions/workflows/run_bot_on_tournament.yaml/dispatches`
   - Schedule: every 30 minutes
   - Advanced → Request method **POST**
   - Headers: `Authorization: Bearer <the token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`
   - Request body: `{"ref":"main"}`
3. **Test run** should return **HTTP 204**, and a new run appears in the Actions tab. Overlapping runs queue rather than double up, so extra triggers are harmless.

### Logs
- Every run's detailed logs are saved as an artifact, `logs-<number>`, on its run page, and kept **90 days**. For your end-of-season analysis, download the ones you want **before mid-March**.
- Anyone signed in to GitHub can download them, so treat the bot's reasoning as public.

### Season end (Jan 6, 2027)
- Set `LIVE` to `false`.
- Before Spring: update `forecasting-tools` to the new season's version. The test `tests/test_season_ids.py` will fail in CI as a reminder. Rerun the probe and `test_questions`, then go live again.
