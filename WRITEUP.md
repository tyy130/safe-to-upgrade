# DEV submission — Safe to Upgrade?

> Submission text for the DEV post (posting package: `SUBMISSION.md`).
> Every number below is from a logged run in `EVALUATION.md`. Prize
> categories are claimed only for technology genuinely used.

## What I Built

Dependency upgrades are the chore everybody puts off. Versions drift,
upgrading feels risky, so it waits — until a CVE or a forced major
version turns it into an emergency. The fear isn't wrong. One migration
guide, read carefully, takes real time. Fifteen of them is a day.

**Safe to Upgrade?** answers one question: does my code use any of the
APIs this upgrade removes? It answers with evidence:

1. It reads your `package.json`.
2. For each dependency, it pulls the breaking changes between your
   version and the target version, from the project's own migration
   guide or release notes.
3. An open-weight model extracts the removed and renamed APIs from that
   guide text. (Live run: Gemma 3 4B via Ollama — Runs 4–6 in
   EVALUATION.md.)
4. Deterministic code — never the model — searches your codebase for
   those exact APIs and gives one verdict per package:
   - **REVIEW** — a removed API is used, with file:line evidence.
   - **SAFE** — breaking-change data exists and none of its APIs are used.
   - **UNKNOWN** — no breaking-change data. The tool says so instead of
     guessing. A dependency tool that bluffs is worse than no tool.

Dependabot and Renovate bump versions. A bump PR doesn't answer this
question. They'll open a PR that breaks you, or one that sits for a year
because checking it feels riskier than staying put. This is the step
before the bump: a verdict computed on your machine, from the guide
itself. Where the data doesn't exist, it says UNKNOWN and stops.

The model proposes. The code disposes. The model does the reading;
tested code owns the verdict.

## Demo

**Live demo: https://safe-to-upgrade-demo.onrender.com/** — the recorded
runs as a page, deployed on Render from this repo. The page says plainly
that its data is recorded, not a live backend.

What the demo shows, from a real run on the sample project:

| Package | Upgrade checked | Verdict | Evidence |
|---|---|---|---|
| express | 4.x → 5.x | **REVIEW** | `res.sendfile` used at `src/server.js:34` |
| react-router-dom | 5.x → 6.x | **SAFE** | 0 of 4 breaking APIs used |
| lodash | — | **UNKNOWN** | no data, not guessed |

## Code

{% github https://github.com/tyy130/safe-to-upgrade %}

## How I Built It

- `verdict.py` — the deterministic core (Python standard library only).
  Parses dependencies, then searches source files for each breaking API.
  Matching is careful about boundaries: dotted APIs match as literal
  member accesses with a trailing boundary, so `app.delete` does **not**
  match the removed `app.del`, and `req.params` does **not** match the
  removed `req.param`. Those two false positives are why this part is
  code and not a prompt.
- `breaking_data.json` — curated breaking changes, every entry carrying
  its source URL: Express 4→5 (7 APIs, from the official Express 5
  migration guide) and React Router 5→6 (4 APIs, from the official v6
  upgrade guide).
- `extract_breaking.py` — the extraction stage. Two paths, one rule:
  - A model path (Ollama, strict JSON-only prompt) for when a local model
    is available.
  - A deterministic heuristic fallback that finds API tokens near removal
    language in guide text.
  - Both paths pass through a **grounding check**: any extracted API that
    doesn't appear verbatim in the source guide is dropped. The model can
    propose; it cannot invent.
- `fetch_changelog.py` / `browserbase_fetch.py` — changelog fetching.
  Plain HTTP where it works; Browserbase for the guides that live outside
  GitHub Releases. The Browserbase path has a live run behind it: a real
  session was created through the API, and the Express guide was fetched
  through the Browserbase Fetch API (200, 211,507 characters — the same
  document the direct fetch produces).

## What the evaluation actually showed

I ran the engine on a real open-source project
(`gothinkster/node-express-realworld-example-app`, 39 dependencies) and
then hand-checked its verdict with an independent plain-text search:

- express: **SAFE** — and the hand-check agreed: zero true uses of the
  seven removed APIs.
- The hand-check nearly produced a false alarm: a plain search for
  `req.param` lights up on `req.params`, which appears all over that
  codebase. The engine's boundary matching excluded every one. One miss
  like that in a real upgrade is how a tool loses trust.
- The other 38 dependencies came back **UNKNOWN**. Coverage is the
  bottleneck, not the verdict logic: getting trustworthy breaking-change
  data for the long tail of packages. The number stays in because it's
  the honest state of the tool.

The extraction stage got the same treatment. On the real Express 5
guide, the heuristic recovered **7 of 7** curated APIs — from **24
candidates**. Some of the extra 17 are genuine signature changes the
curated set omits; several are junk (`res.status`, example-code tokens).
Fed into the verdict engine raw, the heuristic data flags 8 uses in the
sample project where the curated data flags 1. Recall is easy;
precision is the work.

The model pass closed that gap on this guide. Gemma 3 4B proposed 10
entries; the grounding check kept all 10 (each appears verbatim in the
guide); after normalizing signature forms (`res.send(obj, status)` →
`res.send`), the model data flags exactly **1 use** in the sample
project — the same `res.sendfile` call the curated data flags. Generated
data still isn't hand-verified the way the curated set is, so it stays
labelled as generated wherever it appears.

Then I ran the coverage pass the 38 UNKNOWNs were asking for:
extraction on the guides and release notes of every package in that
repo with a pending major — ESLint 9, Prisma 5, Prettier 3, Jest 30,
bcryptjs 3, body-parser 2, Nx 18. (Run 7 in EVALUATION.md.)

Two converted:

- **ESLint 8→9: SAFE, on the API axis.** 11 candidates from the
  official migration guide; the real ones are rule-API removals
  (`sourceCode.getComments`, `context.getSource`). Grep confirms the
  repo uses none of them. Its actual v9 risk is the `.eslintrc.json`
  file v9 no longer reads — and a config file is not an API call. The
  matcher can't see it, and the verdict doesn't claim to.
- **Prettier 2→3: SAFE.** The real v3 removals are the `.sync` APIs
  (`prettier.resolveConfig.sync` and friends) going async. The repo
  never calls the Prettier API at all. Grep confirms.

Two got rejected by inspection:

- **Jest 30.** The extracted data claimed `jest.spyOn` was removed. It
  wasn't — the Jest 30 post presents it as a feature (the new `using`
  syntax). Bad data, thrown out.
- **Prisma 5.** The candidates weren't Prisma Client APIs. And the repo
  does use `PrismaClient` (`src/prisma/prisma-client.ts`), so the
  engine's computed SAFE would have been a false all-clear on a package
  with a real upgrade surface. Inspection caught it. That check exists
  for exactly this.

Three produced nothing: bcryptjs (the break is ESM module shape,
described in prose), body-parser (behavior changes, prose), Nx
(release notes are feature lists). No API tokens, no data, still
UNKNOWN.

Final state of that repo: **3 verdicts out of 39, 36 UNKNOWN.** The
UNKNOWNs were never one problem. They split into no pending major
(roughly half), changes shaped like config or prose that an API
matcher can't judge, and extractable API removals — the only bucket
this tool converts, and only when the extracted data survives
inspection. Two of the four datasets produced in this pass wouldn't
have.

## What went wrong

- **GitHub Releases is not where changelogs live.** My first fetcher
  assumed releases would be there. For `facebook/react` it worked. For
  Express and React Router it returns 404 — they publish migration
  guides on their own sites. That failure is the reason the Browserbase
  fetch path exists: something has to go read the guide where it
  actually is.
- **Even the fetch redirects on you.** The first Browserbase fetch of the
  Express guide came back 301 — the Fetch API returned the redirect
  instead of following it to the trailing-slash URL. One more step the
  pipeline has to handle explicitly.
- **The build VM couldn't run the model — and the first live run failed
  anyway.** This environment has a few hundred MB of free memory, so the
  model run moved to a free Colab T4 GPU: Ollama + Gemma 3 4B, the real
  script, the real guide. Run one produced no usable model output at all
  ("no JSON array found in model output") and fell back to the heuristic.
  Instead of accepting that, I captured the model's raw answers: it wraps
  JSON in markdown fences; under Ollama's JSON mode it returns an object,
  not the array my parser demanded; and Ollama's default 4096-token
  context truncates a guide-length prompt. Fixed all three — JSON mode,
  `num_ctx: 32768`, a parser that accepts the shapes a 4B model actually
  returns — and re-ran: **path used: model, 10 entries, 10 grounded, 0
  dropped.** The failure is Run 4 in EVALUATION.md. The fix is a commit.

## Why Does Open Innovation Matter?

Three concrete reasons, specific to this tool:

1. **Your codebase is the input.** What's being analysed is your source
   code and your dependency list. With open-weight models running on your
   own hardware, none of it has to leave your machine to get a verdict. A
   closed model makes "should I upgrade?" cost you a copy of that
   fingerprint, sent to someone else's API.
2. **The evaluation is reproducible.** Because the model is open, anyone
   can re-run my extraction on the same guide and check my numbers —
   including the bad precision ones. A closed endpoint can change under
   you between the run and the write-up.
3. **The guardrails are inspectable.** The grounding check and the
   boundary matcher are small, readable, and in the repo. For a tool
   whose output is a safety claim ("SAFE"), being able to read exactly
   how that claim is produced is the feature.

## The Lazy Payoff

- The Express 5 migration guide is ~27,000 characters of prose. The React
  Router v6 upgrade guide is comparable. Doing this by hand for one
  package means reading the guide, listing the removed APIs, and then
  searching your codebase for each one — carefully, because of traps like
  `req.param` vs `req.params`. My estimate is ~30–45 minutes per package,
  done carefully. That's an estimate, not a stopwatch number.
- The engine triaged all 39 dependencies of a real-world Express app in
  well under a second (0.08s on the fastest run I measured; ~0.2s on a
  loaded machine — and the verdicts reproduce exactly), with the evidence
  attached. It produces the same answer every time you run it.
- On the real-world run: 39 dependencies, one command. Three verdicts I
  could act on after the coverage pass; 36 UNKNOWNs that show exactly
  where the remaining manual work is, instead of a vague feeling that
  everything might be broken.

## My Agent Session

This project was built in one overnight session. An AI agent wrote the
implementation; I made the calls — direction, which failures were
acceptable, which numbers were honest enough to publish. The most
valuable moment wasn't generated code: it was the deterministic engine
passing a hand-check that a plain text search failed (the `req.params`
sweep above). The least valuable was the first Gemma run, which failed
quietly until the model's raw output was inspected and the failure
became three concrete fixes. The full record of what was run, what
broke, and where every number comes from is in the repo as
`EVALUATION.md`. It's a better record than a chat transcript.

## Prize Categories

Claim only what's genuinely used at submission time:

- [x] Browserbase — live run done 2026-10-21: real session created via
      the API and the Express guide fetched through the Fetch API.
- [x] Gemma — live run done 2026-10-21: Gemma 3 4B via Ollama (the live
      run executed on a free Colab T4, because the build VM couldn't host
      it; the same script runs on local hardware wherever Ollama does)
      extracted 10 grounded entries from the Express 5 guide; verdict
      with model data matches the curated-data verdict (Runs 4–6).
- [x] Render — demo deployed 2026-10-21:
      https://safe-to-upgrade-demo.onrender.com/ (static site from this
      repo, live and verified).
- [ ] GitHub Copilot — only if Copilot is genuinely part of the final
      build/demo workflow.
- [ ] .tech Domain — only if the demo is live on a claimed .tech domain.
