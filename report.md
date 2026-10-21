# Safe to Upgrade? — verdict report

Repo: `/home/hatch/workspace/safe-to-upgrade/sample_repo`

## Summary

| Verdict | Count | Meaning |
|---|---|---|
| REVIEW | 1 | Breaking APIs are used — manual review before upgrading |
| SAFE | 1 | Breaking-change data exists, none of its APIs are used |
| UNKNOWN | 1 | No breaking-change data — not guessed |
| **Total packages** | **3** | |

## Per-package verdicts

| Package | Declared | Upgrade checked | Verdict | Breaking APIs checked | Uses found |
|---|---|---|---|---|---|
| express | ^4.19.2 | 4.x → 5.x | **REVIEW** | 7 | 1 |
| lodash | ^4.17.21 | — | **UNKNOWN** | 0 | 0 |
| react-router-dom | ^5.3.4 | 5.x → 6.x | **SAFE** | 4 | 0 |

## Evidence

### express — REVIEW

1 use(s) of removed/changed APIs found in the codebase.

Breaking-change source: https://expressjs.com/en/guide/migrating-5.html

- `src/server.js:34` — `res.sendfile(path.join(__dirname, '..', 'public', 'manual.pdf'));`  
  API `res.sendfile` (removed → use `res.sendFile`); source: https://expressjs.com/en/guide/migrating-5.html

### lodash — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### react-router-dom — SAFE

None of the 4 known breaking APIs are used in the codebase.

Breaking-change source: https://reactrouter.com/6.30.1/upgrading/v5
