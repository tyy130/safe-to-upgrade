# Demo script — Safe to Upgrade? (~2 minutes)

Screen-recording shot list. Every number spoken or shown comes from the
project's own files (`README.md`, `WRITEUP.md`, `EVALUATION.md`,
`report.md`, `realworld-report.md`) — nothing here is estimated on camera.

**Production note:** `WRITEUP.md`'s "~30–45 minutes per package" figure is
bracketed there as *an estimate to confirm*. Do not state it as a measured
fact in the recording; the close below uses only the logged numbers.

---

## 0:00–0:15 — The hook: the dreaded upgrade chore

- **On screen:** a `package.json` full of old version ranges; then the
  Express 5 migration guide scrolling.
- **Say:** "Nobody upgrades their dependencies, because nobody wants to
  read fifteen changelogs. So upgrades pile up — until a CVE or a forced
  major version turns it into an emergency. Safe to Upgrade? answers the
  one question that actually matters: if I bump this package, does my
  code use anything that broke?"

## 0:15–0:40 — Run it on the sample project (terminal)

- **On screen:** terminal in `safe-to-upgrade/`:

  ```bash
  python3 verdict.py sample_repo breaking_data.json --out report.md
  ```

- **Show the output** (as recorded in `README.md`):

  ```
  packages: 3  REVIEW: 1  SAFE: 1  UNKNOWN: 1
    express: REVIEW (1 use(s) found)
    lodash: UNKNOWN (0 use(s) found)
    react-router-dom: SAFE (0 use(s) found)
  ```

- **Say:** "Three dependencies, three different verdicts, in one run:
  REVIEW, SAFE, and UNKNOWN — the tool's word for 'no breaking-change
  data, and I'm not going to guess.'"

## 0:40–0:55 — The report, with evidence

- **On screen:** `report.md`. Zoom to the express evidence; optionally
  flip to the same table on the demo page (`demo/index.html`, Sample
  project toggle, click the express row).
- **Say:** "REVIEW comes with receipts: `res.sendfile` at
  `src/server.js:34` — removed in Express 5 in favour of `res.sendFile`,
  with the migration guide as the source. The same file also calls
  `app.delete(...)` — which was correctly *not* flagged, because the
  removed API is `app.del`. React Router gets a SAFE: none of its 4
  breaking APIs are used. Lodash is UNKNOWN — no data, no bluffing."

## 0:55–1:20 — A real open-source project

- **On screen:** terminal; run the engine on the cloned
  `gothinkster/node-express-realworld-example-app` (commit
  `30b68e1e881462b2f4164ea09ab4c4f5699c7b0b`, the run logged in
  `EVALUATION.md`), then open `realworld-report.md`.
- **Say:** "Same command on a real project with 39 dependencies:
  express — checked against the 7 Express 5 removed APIs — comes back
  SAFE. The other 38 come back UNKNOWN. That's the honest bottleneck:
  coverage of breaking-change data, not the verdict logic."

## 1:20–1:40 — The req.params moment (the hand-check)

- **On screen:** a plain grep of the real-world repo for `req.param`
  lighting up `req.params` hits, side by side with the engine's SAFE
  verdict.
- **Say:** "I hand-checked that SAFE with an independent text search —
  and the naive search almost cried wolf. Search for the removed
  `req.param` and you match `req.params`, which appears all over this
  codebase: five-plus raw hits, zero of them real. The engine's boundary
  matching excluded every one. That near-miss is the whole reason the
  verdicts are deterministic code, not a prompt."

## 1:40–2:00 — Close: the Lazy Payoff

- **On screen:** the verdict table from `realworld-report.md` (or the
  demo page's Real-world project toggle with its summary counts:
  39 total, 0 REVIEW, 1 SAFE, 38 UNKNOWN).
- **Say:** "The Express 5 migration guide alone is about 27,000
  characters of prose. Reading it, listing the removed APIs, and
  searching a codebase for each one — carefully — is the manual version
  of this chore. The engine produces the verdict table in under a
  second, with the evidence attached, and the same answer every run.
  On the real project: 39 dependencies triaged in one command — one
  verdict I can act on, and 38 honest UNKNOWNs showing exactly where
  the remaining manual work is. Don't read the changelog. Get the
  verdict."
