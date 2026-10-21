<!--
POSTING PACKAGE — everything outside the post body is notes for posting.

Title: Safe to Upgrade? — know before you bump: per-dependency upgrade verdicts with file:line evidence
Tags (enter in the DEV editor): devchallenge, hf26challenge
(The challenge tags are added by the submission template; include them if the editor asks.)
Cover image: optional — a screenshot of the demo verdict table works.
-->

*This is a submission for the Hacktoberfest Open-Source AI Challenge: Week 3 — Slow and Steady.*

## What I Built

Every JavaScript project has the same dreaded chore: dependencies go out of
date, and upgrading feels risky, so nobody upgrades — until a CVE or a
forced major version makes it an emergency. The fear isn't irrational.
Reading one migration guide carefully takes real time; reading fifteen is
a day nobody has.

**Safe to Upgrade?** answers the only question you actually have about an
upgrade — *does my code use any of the APIs this version removes?* — and it
answers it with evidence, not vibes:

1. It reads your `package.json`.
2. For each dependency, it collects the breaking changes between the
   version you have and the version you'd move to (from the project's own
   migration guide or release notes).
3. An open-weight model extracts the removed/renamed APIs from that guide
   text. (Live run: Gemma 3 4B via Ollama — Runs 4–6 in EVALUATION.md.)
4. Deterministic code — never the model — searches your codebase for those
   exact APIs and issues one of three verdicts per package:
   - **REVIEW** — a removed API is used, with file:line evidence.
   - **SAFE** — breaking-change data exists and none of its APIs are used.
   - **UNKNOWN** — no breaking-change data. The tool says so instead of
     guessing. A dependency tool that bluffs is worse than no tool.

Dependabot and Renovate already automate the version bump — but a bump
PR doesn't answer this question. They will happily open a PR that
breaks you, or one you ignore for a year because checking it feels
riskier than staying put. Safe to Upgrade? is the step *before* the
bump: a triage verdict computed locally from the project's own
migration guide — not a hosted service your codebase gets uploaded to,
and not a model grading its own homework. Where the data doesn't
exist, it says UNKNOWN and stops.

The model proposes. The code disposes. If that split sounds familiar, it's
because it's the architecture that keeps showing up in projects judges
reward: the model does language work, tested code owns the facts.

## Demo

**Live demo: https://safe-to-upgrade-demo.onrender.com/** — the recorded
runs below as a page (deployed on Render from this repo; the page states
plainly that its data is recorded, not a live backend).

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
  Matching is careful about boundaries: dotted APIs are matched as literal
  member accesses with a trailing boundary, so `app.delete` does **not**
  match the removed `app.del`, and `req.params` does **not** match the
  removed `req.param`. Those two false positives are the whole reason this
  is code and not a prompt.
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
  GitHub Releases. The Browserbase path has had its live run: a real
  session was created through the API, and the Express guide was fetched
  through the Browserbase Fetch API (200, 211,507 characters — the same
  document the direct fetch produces).

## What the evaluation actually showed

I ran the engine on a real open-source project
(`gothinkster/node-express-realworld-example-app`, 39 dependencies) and
then hand-checked its verdict with an independent plain-text search:

- express: **SAFE** — and the hand-check agreed: zero true uses of the
  seven removed APIs.
- The hand-check almost produced a false alarm: a naive search for
  `req.param` lights up on `req.params`, which appears all over that
  codebase. The engine's boundary matching correctly excluded every one.
  One near-miss like that, in a real upgrade, is the difference between a
  team trusting the tool and never running it again.
- The other 38 dependencies came back **UNKNOWN**. Coverage — getting
  trustworthy breaking-change data for the long tail of packages — is the
  bottleneck, not the verdict logic. I'd rather show that number than
  hide it.

The extraction stage got the same honest treatment. On the real Express 5
guide, the heuristic recovered **7 of 7** curated APIs — from **24
candidates**. Some of the extra 17 are genuine signature changes the
curated set omits; several are junk (`res.status`, example-code tokens).
Fed into the verdict engine raw, the heuristic data flags 8 uses in the
sample project where the curated data flags 1. Recall is easy; precision
is the work.

The grounded model pass closed that gap on this guide. Gemma 3 4B
proposed 10 entries; the grounding check kept all 10 (each appears
verbatim in the guide); after normalizing signature forms
(`res.send(obj, status)` → `res.send`), the model data flags exactly
**1 use** in the sample project — the same `res.sendfile` call the
curated data flags. Generated data still isn't hand-verified the way
the curated set is, so it stays labelled as generated wherever it
appears.

## What went wrong

- **GitHub Releases is not where changelogs live.** My first fetcher
  assumed releases would be there. For `facebook/react` it worked. For
  Express and React Router it returns 404 — they publish migration guides
  on their own sites. That failure is the reason the Browserbase fetch
  path exists: an agent has to go read the guide where it actually is.
- **Even the fetch redirects on you.** The first Browserbase fetch of the
  Express guide came back 301 — the Fetch API returned the redirect
  instead of following it to the trailing-slash URL. One more step the
  pipeline has to handle explicitly instead of discovering in production.
- **The build VM couldn't run the model — and the first live run failed
  anyway.** This environment has a few hundred MB of free memory, so the
  model run moved to a free Colab T4 GPU: Ollama + Gemma 3 4B, the real
  script, the real guide. Run one produced no usable model output at all
  ("no JSON array found in model output") and quietly fell back to the
  heuristic. Instead of accepting that, I captured the model's raw
  answers: it wraps JSON in markdown fences; under Ollama's JSON mode it
  returns an object, not the array my parser demanded; and Ollama's
  default 4096-token context truncates a guide-length prompt. Fixed all
  three — JSON mode, `num_ctx: 32768`, a parser that accepts the shapes
  a 4B model actually returns — and re-ran: **path used: model, 10
  entries, 10 grounded, 0 dropped.** The failure is Run 4 in
  EVALUATION.md; the fix is a commit, not a claim.

## Why Does Open Innovation Matter?

Three concrete reasons, specific to this tool:

1. **Your codebase is the input.** The thing being analysed is your
   source code and your dependency list. With open-weight models running
   locally, none of it has to leave your machine to get a verdict. A
   closed API makes "should I upgrade?" cost you a copy of your repo's
   fingerprint.
2. **The evaluation is reproducible.** Because the model is open, anyone
   can re-run my extraction on the same guide and check my numbers —
   including the embarrassing precision ones. A closed endpoint can
   change under you between the run and the write-up.
3. **The guardrails are inspectable.** The grounding check and the
   boundary matcher are small, readable, and in the repo. For a tool
   whose output is a safety claim ("SAFE"), being able to read exactly
   how that claim is produced is the feature.

## The Lazy Payoff

- The Express 5 migration guide is ~27,000 characters of prose. The React
  Router v6 upgrade guide is comparable. Doing this by hand for one
  package means reading the guide, listing the removed APIs, and then
  searching your codebase for each one — carefully, because of traps like
  `req.param` vs `req.params`. My estimate is ~30–45 minutes per
  package, done carefully — an estimate, not a stopwatch number.
- The engine triaged all 39 dependencies of a real-world Express app in
  0.08 seconds (measured, and the verdicts reproduce exactly), with the
  evidence attached, and — the part that matters at 11pm — it produces
  the same answer every time you run it.
- On the real-world run: 39 dependencies triaged in one command. One
  verdict I could act on, 38 honest UNKNOWNs telling me exactly where
  the remaining manual work actually is, instead of a vague feeling that
  everything might be broken.

## My Agent Session

This project was built in one overnight session with an AI agent
writing the implementation while I made the calls — direction, which
failures were acceptable, which numbers were honest enough to publish.
The session's most valuable moment wasn't generated code: it was the
deterministic engine surviving a hand-check that a naive text search
failed (the `req.params` sweep above). Its least valuable was the
first Gemma run, which failed silently until the model's raw output
was inspected and the failure became three concrete fixes. The full
record of what was run, what broke, and what every number is — is in
the repo as `EVALUATION.md`. I'd rather point judges at that than at a
chat transcript.

## Prize Categories

I'm entering the categories this project genuinely used:

- **Browserbase** — a real session was created through the API and the
  Express migration guide was fetched through the Browserbase Fetch API
  during the build (EVALUATION.md, Run 3).
- **Gemma** — Gemma 3 4B (open weights, run locally via Ollama) is the
  model in the extraction stage, with a full live run logged
  (EVALUATION.md, Runs 4–6).
- **Render** — the demo is deployed on Render:
  https://safe-to-upgrade-demo.onrender.com/
