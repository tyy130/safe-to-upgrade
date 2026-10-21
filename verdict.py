#!/usr/bin/env python3
"""Safe to Upgrade? — deterministic upgrade verdicts.

Reads a repo's package.json, takes breaking-change data (API identifiers
removed / renamed / changed between versions, each with a source URL), and
searches the codebase for actual usage of those identifiers.

Verdicts per package:
  REVIEW  — breaking-change data exists AND at least one removed/changed
            API is actually used in the code (evidence: file:line).
  SAFE    — breaking-change data exists AND none of its APIs are used.
  UNKNOWN — no breaking-change data for this package. We never guess.

The verdict logic is plain deterministic code: no model, no network.
Extraction of breaking changes from changelogs is a separate (model) step;
this file only disposes.

Usage:
  python verdict.py <repo_dir> <breaking_data.json> [--out report.md]
  python verdict.py --selftest

Standard library only.
"""

import argparse
import json
import os
import re
import sys
import tempfile

SOURCE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
EXCLUDED_DIRS = {"node_modules", ".git"}
MAX_LINE_CHARS = 120


# ---------------------------------------------------------------- data in

def load_dependencies(repo_dir):
    """Return {package_name: declared_version_spec} from package.json."""
    pkg_path = os.path.join(repo_dir, "package.json")
    with open(pkg_path, encoding="utf-8") as fh:
        pkg = json.load(fh)
    deps = {}
    for section in ("dependencies", "devDependencies"):
        entries = pkg.get(section) or {}
        for name, spec in entries.items():
            deps[name] = spec
    return deps


def load_breaking_data(path):
    """Load breaking-change data.

    Accepted shape:
      {"packages": {"<name>": {"from": "...", "to": "...", "source": url,
                               "changes": [{"api": "...", "change": "...",
                                            "replacement": "...",
                                            "note": "...", "source": url},
                                           ...]}}}
    A bare {"<name>": {...}} mapping is also accepted.
    Returns {name: package_entry}.
    """
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if isinstance(raw, dict) and "packages" in raw:
        return raw["packages"]
    return raw


# ---------------------------------------------------------------- search

def iter_source_files(repo_dir):
    """Yield source file paths under repo_dir, skipping excluded dirs."""
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for name in sorted(files):
            if os.path.splitext(name)[1] in SOURCE_EXTENSIONS:
                yield os.path.join(root, name)


def compile_api_pattern(api):
    """Build the search regex for one API identifier.

    Dotted forms (``app.del``, ``res.sendfile``) are searched literally as
    member accesses; plain identifiers (``Switch``, ``useHistory``) are
    searched on word boundaries. In both cases the match must not be
    immediately followed by a word character or ``$``, so ``app.del``
    does not match ``app.delete`` and ``req.param`` does not match
    ``req.params``.
    """
    return re.compile(re.escape(api) + r"(?![\w$])"
                      if "." in api else r"\b" + re.escape(api) + r"\b")


def search_api(lines, api):
    """Return [(lineno, trimmed_line)] for every use of `api` in `lines`."""
    pattern = compile_api_pattern(api)
    hits = []
    for lineno, line in enumerate(lines, start=1):
        if pattern.search(line):
            text = line.strip()
            if len(text) > MAX_LINE_CHARS:
                text = text[: MAX_LINE_CHARS - 3] + "..."
            hits.append((lineno, text))
    return hits


# ---------------------------------------------------------------- verdicts

def analyze(repo_dir, breaking_data):
    """Return the full result dict for a repo."""
    deps = load_dependencies(repo_dir)

    # Read every source file once.
    file_lines = {}
    for path in iter_source_files(repo_dir):
        rel = os.path.relpath(path, repo_dir).replace(os.sep, "/")
        with open(path, encoding="utf-8", errors="ignore") as fh:
            file_lines[rel] = fh.read().splitlines()

    packages = []
    for name in sorted(deps):
        entry = breaking_data.get(name)
        changes = (entry or {}).get("changes") or []
        base = {
            "name": name,
            "declared_version": deps[name],
            "upgrade": None if not entry else {
                "from": entry.get("from"),
                "to": entry.get("to"),
                "source": entry.get("source"),
            },
            "changes_checked": len(changes),
            "hits": [],
        }
        if not entry or not changes:
            base["verdict"] = "UNKNOWN"
            base["reason"] = ("No breaking-change data for this package; "
                              "verdict not guessed.")
            packages.append(base)
            continue

        hits = []
        for change in changes:
            api = change.get("api")
            if not api:
                continue
            for rel in sorted(file_lines):
                for lineno, text in search_api(file_lines[rel], api):
                    hits.append({
                        "api": api,
                        "change": change.get("change"),
                        "replacement": change.get("replacement"),
                        "source": change.get("source") or entry.get("source"),
                        "file": rel,
                        "line": lineno,
                        "text": text,
                    })
        base["hits"] = hits
        if hits:
            base["verdict"] = "REVIEW"
            base["reason"] = (f"{len(hits)} use(s) of removed/changed APIs "
                              "found in the codebase.")
        else:
            base["verdict"] = "SAFE"
            base["reason"] = (f"None of the {len(changes)} known breaking "
                              "APIs are used in the codebase.")
        packages.append(base)

    summary = {"total": len(packages), "REVIEW": 0, "SAFE": 0, "UNKNOWN": 0}
    for pkg in packages:
        summary[pkg["verdict"]] += 1
    return {"repo": os.path.abspath(repo_dir),
            "summary": summary, "packages": packages}


# ---------------------------------------------------------------- reports

def render_markdown(result):
    s = result["summary"]
    out = []
    out.append("# Safe to Upgrade? — verdict report")
    out.append("")
    out.append(f"Repo: `{result['repo']}`")
    out.append("")
    out.append("## Summary")
    out.append("")
    out.append("| Verdict | Count | Meaning |")
    out.append("|---|---|---|")
    out.append(f"| REVIEW | {s['REVIEW']} | Breaking APIs are used — "
               "manual review before upgrading |")
    out.append(f"| SAFE | {s['SAFE']} | Breaking-change data exists, "
               "none of its APIs are used |")
    out.append(f"| UNKNOWN | {s['UNKNOWN']} | No breaking-change data — "
               "not guessed |")
    out.append(f"| **Total packages** | **{s['total']}** | |")
    out.append("")
    out.append("## Per-package verdicts")
    out.append("")
    out.append("| Package | Declared | Upgrade checked | Verdict | "
               "Breaking APIs checked | Uses found |")
    out.append("|---|---|---|---|---|---|")
    for pkg in result["packages"]:
        up = pkg["upgrade"]
        up_text = f"{up['from']} → {up['to']}" if up else "—"
        out.append(f"| {pkg['name']} | {pkg['declared_version']} | "
                   f"{up_text} | **{pkg['verdict']}** | "
                   f"{pkg['changes_checked']} | {len(pkg['hits'])} |")
    out.append("")
    out.append("## Evidence")
    for pkg in result["packages"]:
        out.append("")
        out.append(f"### {pkg['name']} — {pkg['verdict']}")
        out.append("")
        out.append(pkg["reason"])
        if pkg["upgrade"] and pkg["upgrade"].get("source"):
            out.append("")
            out.append(f"Breaking-change source: {pkg['upgrade']['source']}")
        if pkg["hits"]:
            out.append("")
            for hit in pkg["hits"]:
                repl = (f" → use `{hit['replacement']}`"
                        if hit.get("replacement") else "")
                out.append(f"- `{hit['file']}:{hit['line']}` — "
                           f"`{hit['text']}`  \n"
                           f"  API `{hit['api']}` ({hit['change']}{repl}); "
                           f"source: {hit['source']}")
    out.append("")
    return "\n".join(out)


def write_reports(result, out_md_path):
    with open(out_md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(result))
    out_json_path = os.path.splitext(out_md_path)[0] + ".json"
    with open(out_json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")
    return out_md_path, out_json_path


# ---------------------------------------------------------------- self-test

def _write_file(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def run_selftest():
    """Build a throwaway repo and check SAFE / REVIEW / UNKNOWN verdicts."""
    data = {
        "packages": {
            "express": {
                "from": "4.x", "to": "5.x",
                "source": "https://expressjs.com/en/guide/migrating-5.html",
                "changes": [
                    {"api": "app.del", "change": "removed",
                     "replacement": "app.delete",
                     "source": "https://expressjs.com/en/guide/migrating-5.html"},
                    {"api": "req.param", "change": "removed",
                     "replacement": "req.params / req.query / req.body",
                     "source": "https://expressjs.com/en/guide/migrating-5.html"},
                ],
            },
            "react-router-dom": {
                "from": "5.x", "to": "6.x",
                "source": "https://reactrouter.com/6.30.1/upgrading/v5",
                "changes": [
                    {"api": "Switch", "change": "removed",
                     "replacement": "Routes",
                     "source": "https://reactrouter.com/6.30.1/upgrading/v5"},
                    {"api": "useHistory", "change": "removed",
                     "replacement": "useNavigate",
                     "source": "https://reactrouter.com/6.30.1/upgrading/v5"},
                ],
            },
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, "src"))
        _write_file(repo, "package.json", json.dumps({
            "name": "selftest-repo",
            "dependencies": {
                "express": "^4.19.2",
                "react-router-dom": "^5.3.4",
                "lodash": "^4.17.21",
            },
        }))
        # express: uses removed app.del (REVIEW). Also uses app.delete and
        # req.params, which must NOT match app.del / req.param.
        _write_file(repo, "src/server.js",
                    "app.del('/old', handler);\n"
                    "app.delete('/new', handler);\n"
                    "const id = req.params.id;\n")
        # react-router-dom: v6 APIs only (SAFE).
        _write_file(repo, "src/App.jsx",
                    "import { Routes, Route, useNavigate } "
                    "from 'react-router-dom';\n")
        # lodash has no breaking data (UNKNOWN) even though it is used.
        _write_file(repo, "src/util.js", "const _ = require('lodash');\n")

        result = analyze(repo, data["packages"])
        by_name = {p["name"]: p for p in result["packages"]}

        assert by_name["express"]["verdict"] == "REVIEW", by_name["express"]
        hits = by_name["express"]["hits"]
        assert len(hits) == 1 and hits[0]["api"] == "app.del", hits
        assert hits[0]["file"] == "src/server.js" and hits[0]["line"] == 1, hits

        assert by_name["react-router-dom"]["verdict"] == "SAFE", \
            by_name["react-router-dom"]
        assert by_name["lodash"]["verdict"] == "UNKNOWN", by_name["lodash"]
        assert result["summary"] == {"total": 3, "REVIEW": 1, "SAFE": 1,
                                     "UNKNOWN": 1}, result["summary"]

        # Markdown report renders and mentions every verdict.
        md = render_markdown(result)
        for token in ("REVIEW", "SAFE", "UNKNOWN", "src/server.js:1"):
            assert token in md, token

    print("selftest: REVIEW case passed (app.del found; app.delete and "
          "req.params correctly not matched)")
    print("selftest: SAFE case passed (react-router-dom, v6 APIs only)")
    print("selftest: UNKNOWN case passed (lodash, no breaking data)")
    print("selftest: all passed")
    return 0


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic dependency upgrade verdicts.")
    parser.add_argument("repo_dir", nargs="?",
                        help="repo containing package.json")
    parser.add_argument("breaking_data", nargs="?",
                        help="JSON file of breaking-change data")
    parser.add_argument("--out", default="report.md",
                        help="markdown report path (default: report.md); "
                             "the JSON report is written next to it")
    parser.add_argument("--selftest", action="store_true",
                        help="run the built-in self-tests and exit")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()
    if not args.repo_dir or not args.breaking_data:
        parser.error("repo_dir and breaking_data are required "
                     "(or pass --selftest)")

    breaking_data = load_breaking_data(args.breaking_data)
    result = analyze(args.repo_dir, breaking_data)
    md_path, json_path = write_reports(result, args.out)
    s = result["summary"]
    print(f"packages: {s['total']}  REVIEW: {s['REVIEW']}  "
          f"SAFE: {s['SAFE']}  UNKNOWN: {s['UNKNOWN']}")
    for pkg in result["packages"]:
        print(f"  {pkg['name']}: {pkg['verdict']} "
              f"({len(pkg['hits'])} use(s) found)")
    print(f"wrote {md_path} and {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
