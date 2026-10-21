# Safe to Upgrade? — verdict report

Repo: `/home/hatch/workspace/safe-to-upgrade/sample_repo`

## Summary

| Verdict | Count | Meaning |
|---|---|---|
| REVIEW | 1 | Breaking APIs are used — manual review before upgrading |
| SAFE | 0 | Breaking-change data exists, none of its APIs are used |
| UNKNOWN | 2 | No breaking-change data — not guessed |
| **Total packages** | **3** | |

## Per-package verdicts

| Package | Declared | Upgrade checked | Verdict | Breaking APIs checked | Uses found |
|---|---|---|---|---|---|
| express | ^4.19.2 | 4 → 5 | **REVIEW** | 9 | 1 |
| lodash | ^4.17.21 | — | **UNKNOWN** | 0 | 0 |
| react-router-dom | ^5.3.4 | — | **UNKNOWN** | 0 | 0 |

## Evidence

### express — REVIEW

1 use(s) of removed/changed APIs found in the codebase.

Breaking-change source: https://expressjs.com/en/guide/migrating-5/

- `src/server.js:34` — `res.sendfile(path.join(__dirname, '..', 'public', 'manual.pdf'));`  
  API `res.sendfile` (replaced); source: https://expressjs.com/en/guide/migrating-5/

### lodash — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### react-router-dom — UNKNOWN

No breaking-change data for this package; verdict not guessed.
