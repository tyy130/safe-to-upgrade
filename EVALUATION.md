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

## Write-up

`WRITEUP.md` (drafted 2026-10-21) is the DEV submission draft built on the
runs above. Its bracketed placeholders are the unfinished pieces: Gemma
live run, Browserbase live run, demo link/video, public GitHub repo,
agent-session link, and the per-package manual-time estimate.
