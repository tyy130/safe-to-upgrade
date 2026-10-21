# Evaluation log — Safe to Upgrade?

Honest, reproducible checks of the verdict engine. Numbers here are the ones
quoted in the DEV write-up; if a run is not listed, it did not happen.

## Run 1 — sample_repo (designed fixture)

- Command: `python3 verdict.py sample_repo breaking_data.json`
- Result: 3 packages — REVIEW 1, SAFE 1, UNKNOWN 1
  - express 4→5: REVIEW, `res.sendfile` at `src/server.js:34`
  - react-router-dom 5→6: SAFE, 0 of 4 breaking APIs used
  - lodash: UNKNOWN (no breaking-change data; not guessed)
- Self-tests (`python3 verdict.py --selftest`): all pass, including the
  false-positive guards (`app.delete` is not `app.del`; `req.params` is not
  `req.param`).

## Run 2 — real public repo (2026-10-21)

- Repo: https://github.com/gothinkster/node-express-realworld-example-app
  at commit `30b68e1e881462b2f4164ea09ab4c4f5699c7b0b` (2024-01-04).
- Command: `python3 verdict.py <repo> breaking_data.json`
  (report saved as `realworld-report.md` / `realworld-report.json`)
- Result: 39 packages — SAFE 1, UNKNOWN 38, REVIEW 0.
  - express ~4.18.1, checked against the 7 Express 5 removed APIs: SAFE.
  - The other 38 deps have no breaking-change data yet → UNKNOWN.
    Coverage, not verdict logic, is the current bottleneck.
- Hand-check (independent of verdict.py, system grep over the repo's
  .ts/.js/.tsx/.jsx sources for all 11 curated APIs):
  - Zero true uses of any removed API — agrees with the engine's SAFE.
  - The only raw grep hits were `req.params` (5+ occurrences), which a naive
    search for `req.param` matches. The engine's trailing-boundary matching
    correctly excludes them; a plain text search would have produced a
    false REVIEW. This is the strongest single argument for the
    deterministic-matching design.

## Run 3 — Browserbase live run (2026-10-21)

- Credential path: Browserbase API key stored through the Secure Vault
  custom connector (`custom.browserbase`, `X-BB-API-Key` header). The key
  was never printed or written to a file.
- Session creation: `POST /v1/sessions` with the project ID returned a
  real session in `RUNNING` status (region us-west-2, five-minute expiry).
  The key works.
- Fetch API: `POST /v1/fetch` on
  `https://expressjs.com/en/guide/migrating-5.html` returned **301** —
  the Fetch API does not follow that redirect, and the `Location` header
  pointed at the trailing-slash URL. Fetching
  `https://expressjs.com/en/guide/migrating-5/` returned **200** with
  211,507 characters of HTML, the same document the direct fetch produced.
  Raw response saved in the project as `browserbase-express-fetch.json`.
- Pipeline proof: `extract_breaking.py` run on the Browserbase-fetched
  content recovered the same **7 of 7** curated Express APIs (24 heuristic
  candidates) as the direct-fetch run in Run 1's extraction test.
- New honest wrinkle for the write-up: even the fetch step has a failure
  mode (unfollowed redirects) that the pipeline has to handle explicitly.

## Run 4 — Gemma live run, first attempt (2026-10-21, Colab T4)

- Host: this VM has ~467 MB of memory available and the tailnet cloud
  server was unreachable, so the model run moved to a free Google Colab
  T4 GPU notebook: Ollama installed (after an `apt-get install zstd`
  fix), `gemma3:4b` pulled (3.3 GB, Q4_K_M) and confirmed serving via
  `GET /api/tags`. The script under test was the published repo version,
  downloaded from the public GitHub repo; the guide came from the
  script's own `--fetch-url` (26,787 chars).
- Result: **the model path produced nothing usable** — "no JSON array
  found in model output" — and the run fell back to the heuristic
  (24 candidates, same as Run 1's extraction test). Recorded as a
  failure, not dressed up as a model run.
- Diagnostics (same session): on a short prompt, Gemma returns its JSON
  wrapped in ```` ```json ```` fences; with Ollama's `format: "json"`
  it returns a wrapper **object** (`{"apis": [...]}`), not the bare
  array the parser demanded. Compounding factor: Ollama's default
  4096-token context truncates a guide-length prompt.

## Run 5 — Model-path fix and re-run (2026-10-21, same Colab runtime)

- Fix (commit `8dcb41c`): payload sends `format: "json"` and
  `options.num_ctx: 32768`; the prompt asks for the `{"changes": [...]}`
  object shape; `parse_model_output` accepts a bare array, a wrapper
  object, and fenced output, with both captured live outputs added as
  regression self-tests (all passing).
- Re-run result: **path used: model. 10 entries extracted, 10 kept by
  grounding, 0 dropped.** The 10: `app.del`, `req.acceptsCharset`,
  `req.acceptsEncoding`, `req.acceptsLanguage`, `app.param(fn)`,
  `req.param(name)`, `res.redirect(url, status)`, `res.send(obj,
  status)`, `res.send(status)`, `res.sendfile()` — **7 of 7 curated
  APIs recovered**, plus 3 genuine signature changes the curated set
  omits. Raw output preserved as `breaking_data.colab-raw.json`.

## Run 6 — Normalization and downstream effect (2026-10-21)

- The model returns APIs in signature form; `merge_into_generated` now
  normalizes them to bare member accesses (`res.send(obj, status)` →
  `res.send`) and dedupes: 10 model entries → **9 stored**
  (`model-generated-report.md`, data in `breaking_data.generated.json`).
- Verdict on the sample fixture with model-generated data: express
  **REVIEW, 1 use** — `res.sendfile` at `src/server.js:34`, exactly the
  curated-data verdict. The heuristic-generated data on the same
  fixture: 24 checked, **8 uses**, including false positives. On this
  guide, the grounded model pass matched curated precision; the
  heuristic did not.

## Run 7 — coverage pass on the real-world repo (2026-10-21)

Question (from the author): the curated run left 38 of 39 packages
UNKNOWN. Is the tool unreliable, or is the data just thin? Method: run
the extraction pipeline (heuristic path; no local model available in
this environment) on the migration guides / release notes of every
package in the repo with a pending major upgrade, inspect the
candidates by hand, re-run the verdict, hand-check the results.
Data file: `breaking_data.run7.json`; report: `run7-report.json`.

Starting point: 1 of 39 with a verdict (express SAFE). Ending point:
**3 of 39 with trustworthy verdicts** (SAFE 3 / UNKNOWN 36).

Converted:
- **eslint 8→9 — SAFE (API axis).** 11 grounded candidates from the
  official migration guide; the real ones are rule-API removals
  (`sourceCode.getComments`, `context.getSource`,
  `context.getAncestors`). Independent grep confirms zero uses — the
  repo consumes ESLint through config, it doesn't write rules.
  Caveat: this repo's actual ESLint 9 risk is its `.eslintrc.json`,
  which v9 no longer supports. That risk is config-shaped; an API
  matcher structurally cannot see it. SAFE here means "no removed
  APIs used," nothing more.
- **prettier 2→3 — SAFE (API axis).** 20 candidates; the real subset
  is the removed `.sync` APIs (`prettier.resolveConfig.sync`,
  `prettier.getFileInfo.sync`, `prettier.clearConfigCache`) — v3 made
  the API async. Junk candidates (`foo`, `parsers.parse`) matched
  nothing. Independent grep confirms the repo never calls the
  Prettier API.

Rejected on inspection (the human pass working as designed):
- **jest 29→30.** Candidates included `jest.spyOn` tagged "removed."
  It wasn't: the Jest 30 announcement presents spyOn as a feature
  (the new `using` syntax). Plus a junk token (`goo.gl`). Data
  rejected; jest stays UNKNOWN.
- **prisma 4→5.** Candidates (`prismaService.enableShutdownHooks`,
  `index.jsUsing`) are not Prisma Client APIs. The repo genuinely
  uses `PrismaClient` (`src/prisma/prisma-client.ts`), so the
  engine's computed SAFE would have been a false all-clear on a
  package with a real upgrade surface. Inspection caught it; prisma
  stays UNKNOWN.

No data produced (extraction returned 0 grounded candidates):
- **bcryptjs 2→3** — the breaking change is module shape (ESM by
  default), described in prose; no API tokens to extract.
- **body-parser 1→2** — breaking changes are behavior/defaults, in
  prose.
- **nx 17→18** — release notes are feature lists, no removal language
  near API tokens.

Finding: the 38 UNKNOWNs were never one problem. They split into
(a) no pending major (roughly half the repo), (b) pending majors whose
changes are config-shaped (ESLint's flat config) or prose-shaped
(bcryptjs, body-parser), which an API matcher cannot judge, and
(c) extractable API removals (ESLint rule APIs, Prettier `.sync`) —
the only bucket this tool can honestly convert, and only with the
inspection pass: two of the four datasets the pipeline produced this
run would have issued wrong or empty verdicts without it.

## Verification pass (2026-10-21, pre-submission)

Every number in the submission was reproduced from scratch before
posting, at the author's request:

- Both self-test suites pass.
- Sample fixture + curated data: REVIEW 1 / SAFE 1 / UNKNOWN 1;
  express 7 checked / 1 use (`res.sendfile`, `src/server.js:34`);
  `app.delete` in the same file correctly not flagged.
- Real-world repo at the recorded commit (`30b68e1`): 39 packages,
  express SAFE (7 checked / 0 hits), 38 UNKNOWN; runtime 0.08–0.21s
  across runs.
- Heuristic regeneration on the Express guide: 24 candidates, 7 of 7
  curated APIs recovered; sample verdict with that data: 24 checked /
  8 uses.
- Model data audit: raw Colab output 10 entries → 9 normalized;
  7 of 7 curated APIs present in the model set; extras are
  `res.redirect` and `res.send` (genuine signature changes).
- Source audit: both guide URLs in `breaking_data.json` return 200;
  the Browserbase fetch artifact is exactly 211,507 characters, as
  the write-up states; repo is public with an MIT license; the Render
  demo returns 200.
- Two wording hardenings from an adversarial read: the Gemma category
  line now states plainly that the live run executed on a Colab T4,
  and the engine-timing claim now gives the measured range instead of
  only the fastest number.

## Write-up

`SUBMISSION.md` is the canonical submission text (it began as a
separate `WRITEUP.md` draft; the duplicate was removed in the
2026-10-21 cleanup so the repo carries one copy of the post — the same
file that was verified byte-identical before publishing). The Gemma
live run, Browserbase live run, public GitHub repo, and Render demo
deploy (https://safe-to-upgrade-demo.onrender.com/, live 2026-10-21,
verified HTTP 200) are done. `demo/DEMO_SCRIPT.md` was also removed in
the cleanup: the video was never recorded; the live demo page replaced
it.
