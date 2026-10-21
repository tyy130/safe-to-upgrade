# Safe to Upgrade?

Nobody upgrades their dependencies because nobody wants to read fifteen
changelogs. Safe to Upgrade? answers the only question that matters —
**"if I bump this package, does my code actually use anything that
broke?"** — with evidence, not vibes.

For each dependency in a repo's `package.json`, the tool takes
breaking-change data for the target upgrade (API identifiers that were
removed, renamed, or changed, each with a source URL), then
deterministically searches the codebase for real usage of those
identifiers and issues one verdict per package:

| Verdict | Meaning |
|---|---|
| **REVIEW** | Breaking APIs are used — evidence is listed as `file:line` with the matched line |
| **SAFE** | Breaking-change data exists, and none of its APIs are used anywhere in the code |
| **UNKNOWN** | No breaking-change data for that package — the tool says so instead of guessing |

## Architecture: model proposes, code disposes

- **Extraction is the model's job.** Reading a changelog or migration
  guide and listing the removed/renamed APIs is language work. The output
  of that step is `breaking_data.json`: plain data, every entry carrying
  the source URL it came from. `extract_breaking.py` implements this
  stage (see "Extraction" below): an Ollama model proposes entries when
  one is available, a deterministic heuristic proposes candidates
  otherwise, and a grounding check drops any proposed API that does not
  appear verbatim in the source guide — model proposes, code disposes.
- **Verdicts are deterministic code's job.** `verdict.py` (Python 3,
  standard library only) does the searching and decides. Dotted APIs
  (`res.sendfile`, `app.del`) are matched as literal member accesses with
  a trailing boundary, so `app.delete` does **not** match `app.del` and
  `req.params` does **not** match `req.param` (both cases are covered by
  the self-tests). Plain identifiers (`Switch`, `useHistory`) are matched
  on word boundaries. Files under `node_modules/` and `.git/` are
  excluded.
- **UNKNOWN is a first-class verdict.** If there is no breaking-change
  data for a package, the tool refuses to invent one.

Known limits of a text search, stated plainly: it cannot judge signature
changes that reuse the same identifier (e.g. Express 5's
`res.json(obj, status)` → `res.status(status).json(obj)`), and for
Express's `app.param` only the `app.param(fn)` signature was removed, so
any `app.param` use is flagged for a human to check. That is what REVIEW
means.

## Run it

```bash
cd safe-to-upgrade

# Self-tests (SAFE / REVIEW / UNKNOWN + the app.delete boundary cases)
python3 verdict.py --selftest

# Full pipeline on the bundled sample repo
python3 verdict.py sample_repo breaking_data.json --out report.md
# -> writes report.md and report.json

# Extraction stage: propose breaking-change entries from a guide.
# Merges into breaking_data.generated.json — the curated
# breaking_data.json is never overwritten.
python3 extract_breaking.py --selftest
python3 extract_breaking.py --package express --from 4.x --to 5.x \
    --source-url https://expressjs.com/en/guide/migrating-5.html \
    --fetch-url https://expressjs.com/en/guide/migrating-5.html
# ...or from a local copy of the guide text:
python3 extract_breaking.py --package express --from 4.x --to 5.x \
    --source-url https://expressjs.com/en/guide/migrating-5.html \
    --text-file guide.txt
```

## Demo results (actual run, verified 2026-10-21)

`sample_repo/` is a small shop app still declaring Express 4 /
React Router 5 era dependencies, plus lodash:

```
packages: 3  REVIEW: 1  SAFE: 1  UNKNOWN: 1
  express: REVIEW (1 use(s) found)
  lodash: UNKNOWN (0 use(s) found)
  react-router-dom: SAFE (0 use(s) found)
```

| Package | Upgrade checked | Verdict | Why |
|---|---|---|---|
| express `^4.19.2` | 4.x → 5.x | **REVIEW** | `res.sendfile(...)` used at `sample_repo/src/server.js:34` — removed in Express 5 in favour of `res.sendFile`. The same file also uses `app.delete(...)`, which was correctly **not** flagged. |
| react-router-dom `^5.3.4` | 5.x → 6.x | **SAFE** | The sample front end is written in v6 style (`Routes`, `Navigate`, `useNavigate`); none of the 4 known breaking APIs (`Switch`, `Redirect`, `useHistory`, `withRouter`) appear. |
| lodash `^4.17.21` | — | **UNKNOWN** | No breaking-change data for lodash in `breaking_data.json`, so no verdict is guessed — even though lodash *is* used in the sample code. |

Full output: [`report.md`](report.md) / [`report.json`](report.json)
(regenerate with the command above).

## Breaking-change data

`breaking_data.json` contains real changes, verified against the
official guides on 2026-10-21 — every entry carries its source URL:

- **Express 4 → 5** — `app.del`, `app.param(fn)`, `req.param`,
  `res.sendfile`, and the pluralized `req.acceptsCharset(s)` /
  `req.acceptsEncoding(s)` / `req.acceptsLanguage(s)` renames, from the
  official Express 5 migration guide:
  https://expressjs.com/en/guide/migrating-5.html
- **React Router (`react-router-dom`) 5 → 6** — `Switch` → `Routes`,
  `Redirect` → `Navigate`, `useHistory` → `useNavigate`, `withRouter`
  removed, from the official v6 upgrade guide:
  https://reactrouter.com/6.30.1/upgrading/v5

## Extraction (`extract_breaking.py`)

Two proposal paths, one grounding check:

- **Model path** — if a local Ollama server answers
  `GET http://localhost:11434/api/tags`, the script POSTs to
  `/api/generate` (model from `$OLLAMA_MODEL`, default `gemma3:4b`)
  with a strict prompt demanding ONLY a JSON array of
  `{api, kind, note}`. Parsing is defensive: the array substring is
  extracted, malformed items are dropped, and a parse failure returns
  an empty list with an error note — entries are never invented.
- **Heuristic path** (fallback, always available) — deterministic
  regex extraction: dotted member forms (`res.sendfile`) and
  backticked identifiers (`useHistory`) found on or near lines with
  removal language ("removed", "no longer", "renamed to",
  "replaced by", …), with tokens after a replacement marker
  ("replaced by", "use the", …) skipped. Every candidate's note
  labels it a heuristic candidate and quotes its source line.
- **Grounding (both paths)** — every proposed `api` must appear
  verbatim in the source guide text, or it is dropped and reported.

**Ollama in this environment (checked 2026-10-21): not available.**
There is no `ollama` binary on PATH, and
`curl http://localhost:11434/api/tags` fails with connection refused
(curl exit 7, HTTP 000); the script's own check reports
`available=False (… [Errno 111] Connection refused)`. The heuristic
live test below ran in this environment; the model path got its live
run on a free Colab T4 GPU instead (Gemma 3 4B via Ollama: first
attempt failed on output format, fixed, re-ran — 10 entries proposed,
10 grounded, 7 of 7 curated APIs recovered; EVALUATION.md Runs 4–6).

**Live test (2026-10-21): Express 5 migration guide.**
Fetched https://expressjs.com/en/guide/migrating-5.html directly
(211,507 chars of HTML, 26,787 chars after stripping) and ran the
heuristic path. It proposed 24 candidate entries; grounding dropped 0
(expected for the heuristic path: its tokens are substrings of the
text by construction — grounding is the guard that matters for
model output, and the self-test proves it drops a hallucinated API).

Recovery against the 7 hand-curated Express entries in
`breaking_data.json`: **7 of 7 recovered, none missed** —
`app.del`, `app.param`, `req.param`, `res.sendfile`,
`req.acceptsCharset`, `req.acceptsEncoding`, `req.acceptsLanguage`.

What went wrong / honest limits (write-up material):

- **Precision is the weak side.** 17 of the 24 candidates are not in
  the curated set. Some are real changes the curated set omits
  (signature changes `res.jsonp`, `res.redirect`, `res.send`,
  `router.param`), but several are plain false positives:
  `req.params` / `req.body` / `req.query` (the lookup targets named
  in the `req.param` removal paragraph, not broken APIs),
  `res.status` (the replacement pattern), `res.sendFile` (the
  replacement itself, picked up from its own options heading), and
  example-code tokens (`app.get`, `app.use`, `express.urlencoded`,
  `req.query.page`). This is why candidates stay labelled and a
  human verifies before anything reaches `breaking_data.json`.
- **Kind inference is approximate:** `res.sendfile` was inferred
  "renamed" (the guide says "replaced by a camel-cased version")
  where the curated entry says "removed".
- **Downstream effect, measured:** running `verdict.py` on the
  sample repo with the generated (unverified) data flags express as
  REVIEW with 8 uses, versus 1 use with the curated data — the
  extra candidates match real code that is not actually broken.

Generated output: [`breaking_data.generated.json`](breaking_data.generated.json).

## Fetch helpers

- `fetch_changelog.py` — pulls release notes from the public GitHub API
  for a repo and up to two tags:
  `python3 fetch_changelog.py facebook/react v19.1.0 v19.2.0`
  **Live test (2026-10-21): worked.** Both facebook/react tags returned
  full release notes (v19.1.0 published 2025-03-28, v19.2.0 published
  2025-10-01). Honest caveat: the GitHub *Releases* endpoint returns 404
  for `expressjs/express` and `remix-run/react-router` tags — those
  projects publish changelogs outside GitHub Releases, so for them the
  migration guides (above) are the source, not this script.
- `browserbase_fetch.py` — the Browserbase adapter (env-key path for
  anyone running this repo themselves). **Update 2026-10-21: Browserbase
  has now had a genuine live run**, through the project's registered
  Browserbase connector rather than this env adapter: a real session was
  created via `POST /v1/sessions` (RUNNING), and the Express 5 guide was
  fetched through the Browserbase Fetch API — first a 301 (the Fetch API
  does not follow that redirect), then 200 with 211,507 chars at the
  trailing-slash URL, and the extraction run on that content recovered
  the same 7 of 7 curated Express APIs. See `EVALUATION.md` Run 3 and
  `browserbase-express-fetch.json`. Stagehand-driven browsing is still
  not wired; the env adapter in this repo remains the fallback path and
  still says "not configured" when no key is set.

## Prize-category plan (Hacktoberfest Week 3)

Only categories genuinely used at submission time will be claimed:

- **Browserbase** (partner) — fetch path for changelog/guide pages.
  Live run done 2026-10-21 (session creation + Fetch API, see above);
  claimable.
- **GitHub Copilot** (partner) — only if Copilot is genuinely used in
  the remaining build/write-up workflow and documented in the post.
- **Render** (featured) — demo deployed 2026-10-21:
  https://safe-to-upgrade-demo.onrender.com/ (live, verified);
  claimable.
- **Gemma** (featured) — Gemma 3 4B via Ollama extracted the Express
  breaking-change entries live (Runs 4–6); claimable.

## Remaining

- [x] Breaking-change extraction wired (`extract_breaking.py`):
      model path (Ollama/Gemma, strict JSON prompt, defensive
      parsing), deterministic heuristic fallback, and a grounding
      check that drops any proposed API not verbatim in the source.
      Live heuristic run on the Express 5 guide recovered 7 of the 7
      curated Express APIs (see "Extraction" above). Data for
      2 packages is hand-verified today; generated candidates still
      need a human verification pass before use.
- [x] Model path live run (2026-10-21, Colab T4, Gemma 3 4B via
      Ollama): first attempt failed ("no JSON array found in model
      output"); diagnosed (fences, wrapper object, 4096-token default
      context), fixed, re-ran — model proposed 10 entries, grounding
      kept 10, 7 of 7 curated APIs recovered; verdict on the sample
      fixture with model data matches the curated-data verdict
      (EVALUATION.md Runs 4–6).
- [x] Browserbase live run (2026-10-21, through the registered
      connector): session created, Express guide fetched via the Fetch
      API, extraction re-run on the fetched content (7 of 7). Stagehand
      extraction remains unwired and is not claimed.
- [x] Hand-check verdicts on a real open-source repo (Run 2 in
      `EVALUATION.md`: 39 packages, express SAFE, independent grep
      hand-check agreed). More repos would strengthen the table.
- [x] Render deploy of the demo front end (2026-10-21):
      https://safe-to-upgrade-demo.onrender.com/ — static site from
      this repo, first deploy live in ~10s, verified HTTP 200.
- [ ] DEV submission write-up (the judged artifact): what was built,
      how, the lazy payoff with real numbers, honest limits, and the
      open-innovation argument. Due Sun Oct 25, 2026, 11:59 PM PDT.
