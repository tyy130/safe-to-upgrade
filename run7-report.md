# Safe to Upgrade? — verdict report

Repo: `/home/hatch/workspace/realworld-app`

## Summary

| Verdict | Count | Meaning |
|---|---|---|
| REVIEW | 0 | Breaking APIs are used — manual review before upgrading |
| SAFE | 3 | Breaking-change data exists, none of its APIs are used |
| UNKNOWN | 36 | No breaking-change data — not guessed |
| **Total packages** | **39** | |

## Per-package verdicts

| Package | Declared | Upgrade checked | Verdict | Breaking APIs checked | Uses found |
|---|---|---|---|---|---|
| @ngneat/falso | ^7.1.1 | — | **UNKNOWN** | 0 | 0 |
| @nx/esbuild | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| @nx/eslint | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| @nx/eslint-plugin | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| @nx/jest | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| @nx/js | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| @nx/node | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| @nx/workspace | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| @prisma/client | ^4.16.1 | — | **UNKNOWN** | 0 | 0 |
| @swc-node/register | ~1.6.7 | — | **UNKNOWN** | 0 | 0 |
| @swc/core | ~1.3.85 | — | **UNKNOWN** | 0 | 0 |
| @types/bcryptjs | ^2.4.6 | — | **UNKNOWN** | 0 | 0 |
| @types/cors | ^2.8.17 | — | **UNKNOWN** | 0 | 0 |
| @types/express | ~4.17.13 | — | **UNKNOWN** | 0 | 0 |
| @types/jest | ^29.4.0 | — | **UNKNOWN** | 0 | 0 |
| @types/node | 18.16.9 | — | **UNKNOWN** | 0 | 0 |
| @typescript-eslint/eslint-plugin | ^6.9.1 | — | **UNKNOWN** | 0 | 0 |
| @typescript-eslint/parser | ^6.9.1 | — | **UNKNOWN** | 0 | 0 |
| axios | ^1.0.0 | — | **UNKNOWN** | 0 | 0 |
| bcryptjs | ^2.4.3 | — | **UNKNOWN** | 0 | 0 |
| body-parser | ^1.20.2 | — | **UNKNOWN** | 0 | 0 |
| cors | ^2.8.5 | — | **UNKNOWN** | 0 | 0 |
| esbuild | ^0.19.2 | — | **UNKNOWN** | 0 | 0 |
| eslint | ~8.48.0 | 8 → 9 | **SAFE** | 11 | 0 |
| eslint-config-prettier | ^9.0.0 | — | **UNKNOWN** | 0 | 0 |
| express | ~4.18.1 | 4.x → 5.x | **SAFE** | 7 | 0 |
| express-jwt | ^8.4.1 | — | **UNKNOWN** | 0 | 0 |
| jest | ^29.4.1 | — | **UNKNOWN** | 0 | 0 |
| jest-environment-node | ^29.4.1 | — | **UNKNOWN** | 0 | 0 |
| jest-mock-extended | ^3.0.5 | — | **UNKNOWN** | 0 | 0 |
| jsonwebtoken | ^9.0.2 | — | **UNKNOWN** | 0 | 0 |
| nx | 17.2.6 | — | **UNKNOWN** | 0 | 0 |
| prettier | ^2.6.2 | 2 → 3 | **SAFE** | 20 | 0 |
| prisma | ^4.16.1 | — | **UNKNOWN** | 0 | 0 |
| slugify | ^1.6.0 | — | **UNKNOWN** | 0 | 0 |
| ts-jest | ^29.1.0 | — | **UNKNOWN** | 0 | 0 |
| ts-node | 10.9.1 | — | **UNKNOWN** | 0 | 0 |
| tslib | ^2.3.0 | — | **UNKNOWN** | 0 | 0 |
| typescript | ~5.2.2 | — | **UNKNOWN** | 0 | 0 |

## Evidence

### @ngneat/falso — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @nx/esbuild — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @nx/eslint — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @nx/eslint-plugin — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @nx/jest — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @nx/js — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @nx/node — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @nx/workspace — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @prisma/client — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @swc-node/register — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @swc/core — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @types/bcryptjs — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @types/cors — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @types/express — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @types/jest — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @types/node — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @typescript-eslint/eslint-plugin — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### @typescript-eslint/parser — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### axios — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### bcryptjs — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### body-parser — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### cors — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### esbuild — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### eslint — SAFE

None of the 11 known breaking APIs are used in the codebase.

Breaking-change source: https://eslint.org/docs/latest/use/migrate-to-9.0.0

### eslint-config-prettier — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### express — SAFE

None of the 7 known breaking APIs are used in the codebase.

Breaking-change source: https://expressjs.com/en/guide/migrating-5.html

### express-jwt — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### jest — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### jest-environment-node — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### jest-mock-extended — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### jsonwebtoken — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### nx — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### prettier — SAFE

None of the 20 known breaking APIs are used in the codebase.

Breaking-change source: https://prettier.io/blog/2023/07/05/3.0.0.html

### prisma — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### slugify — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### ts-jest — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### ts-node — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### tslib — UNKNOWN

No breaking-change data for this package; verdict not guessed.

### typescript — UNKNOWN

No breaking-change data for this package; verdict not guessed.
