#!/usr/bin/env python3
"""Safe to Upgrade? — breaking-change extraction.

Reads a changelog or migration guide and *proposes* breaking-change
entries ({api, kind, note}) for `breaking_data.json`-shaped output.
Extraction proposes; deterministic code disposes:

  1. MODEL path (preferred when available): a local Ollama server is
     asked, with a strict prompt, for ONLY a JSON array of
     {"api", "kind", "note"} objects extracted from the guide text.
     The response is parsed defensively — anything that is not a
     well-formed entry is dropped, and a parse failure yields an
     empty list plus an error note. Entries are never invented: if
     the model cannot be reached or its output cannot be parsed, we
     say so and fall back.
  2. HEURISTIC path (fallback, always available): deterministic
     regex/heading-based extraction. API-like tokens (dotted member
     forms like `res.sendfile`, and backticked identifiers like
     `useHistory`) that appear on or near a line carrying removal
     language ("removed", "no longer", "deprecated", "renamed to",
     "replaced by", ...) become candidate entries. Every candidate's
     note labels it as a heuristic candidate and quotes its source
     line. Candidates are candidates — a human still verifies them.
  3. GROUNDING check (both paths): every extracted `api` string must
     appear verbatim in the source guide text. Anything that does
     not is dropped and reported. Model proposes, code disposes.

Output is merged into a generated JSON file (default
`breaking_data.generated.json`) in the same schema as the curated
`breaking_data.json`, which this script never overwrites.

Usage:
  python extract_breaking.py --package express --from 4.x --to 5.x \
      --source-url https://expressjs.com/en/guide/migrating-5.html \
      --text-file guide.txt
  python extract_breaking.py --package express --from 4.x --to 5.x \
      --fetch-url https://expressjs.com/en/guide/migrating-5.html
  python extract_breaking.py --selftest

Standard library only.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_TIMEOUT = 2  # seconds — a local server answers fast or not at all
MODEL_TEXT_LIMIT = 12000  # chars of guide text sent to the model
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
DEFAULT_OUT = "breaking_data.generated.json"


# ---------------------------------------------------------------- Ollama

def check_ollama():
    """Return (available: bool, detail: str) for the local Ollama server.

    Evidence-based: a GET on /api/tags with a short timeout. Any
    connection error, timeout, or non-200 means "not available here".
    """
    url = OLLAMA_BASE + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=OLLAMA_TIMEOUT) as resp:
            if resp.status != 200:
                return False, f"GET {url} returned HTTP {resp.status}"
            data = json.load(resp)
    except Exception as exc:  # URLError, timeout, bad JSON — all "no"
        return False, f"GET {url} failed: {exc}"
    names = [m.get("name") for m in data.get("models", []) if m.get("name")]
    return True, f"GET {url} OK; models: {', '.join(names) or '(none listed)'}"


def build_model_prompt(package, from_version, to_version, guide_text):
    return (
        "You extract breaking changes from a migration guide.\n"
        f"Package: {package}, upgrade {from_version} -> {to_version}.\n"
        "From the guide text below, list every API that was removed, "
        "renamed, replaced, deprecated, or whose signature changed.\n"
        "Respond with ONLY a JSON array. Each element must be an object "
        'with exactly these string fields: "api" (the exact API '
        'identifier as written in the guide, e.g. "res.sendfile" or '
        '"useHistory"), "kind" (one of: removed, renamed, deprecated, '
        'changed), and "note" (one short sentence, grounded in the '
        "guide text).\n"
        "Rules: extract ONLY APIs that literally appear in the guide "
        "text. Do not invent APIs. Do not include the replacement API "
        "as its own entry. No prose, no markdown fences, only the JSON "
        "array.\n\n"
        "GUIDE TEXT:\n"
        + guide_text[:MODEL_TEXT_LIMIT]
    )


def parse_model_output(raw):
    """Defensively parse the model's reply.

    Returns (entries, error). On any failure: ([], "reason"). Extracts
    the JSON array substring (first '[' to last ']'), validates each
    item has non-empty string api/kind/note, drops invalid items.
    """
    if raw is None:
        return [], "model returned no output"
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        return [], "no JSON array found in model output"
    try:
        parsed = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        return [], f"model output was not valid JSON: {exc}"
    if not isinstance(parsed, list):
        return [], "model output JSON was not an array"
    entries = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        api = item.get("api")
        kind = item.get("kind")
        note = item.get("note")
        if not all(isinstance(v, str) and v.strip()
                   for v in (api, kind, note)):
            continue
        entries.append({"api": api.strip(), "kind": kind.strip(),
                        "note": note.strip()})
    return entries, None


def extract_with_model(package, from_version, to_version, guide_text,
                       model):
    """Run the Ollama model path. Returns (entries, error_or_None)."""
    prompt = build_model_prompt(package, from_version, to_version,
                                guide_text)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_BASE + "/api/generate", data=payload,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            data = json.load(resp)
    except Exception as exc:
        return [], f"POST /api/generate failed: {exc}"
    return parse_model_output(data.get("response"))


# ---------------------------------------------------------------- heuristic

REMOVAL_LANGUAGE = re.compile(
    r"removed|no longer|not supported|deprecated|renamed|replaced by"
    r"|pluralized|dropped|discontinued", re.IGNORECASE)

DOTTED_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z][A-Za-z0-9]*)+\b")
BACKTICK_RE = re.compile(r"`([^`\n]{1,120})`")
PLAIN_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")

# Last segments that make a dotted token a file name or a domain,
# not an API member access.
NON_API_SUFFIXES = {"js", "jsx", "ts", "tsx", "json", "html", "htm",
                    "css", "md", "txt", "xml", "yml", "yaml",
                    "com", "org", "net", "io", "dev", "app", "co"}

# Text after one of these markers on a line names the *replacement*,
# not the broken API — tokens there are skipped.
REPLACEMENT_MARKERS = ("renamed to", "replaced by", "now called",
                       "in favour of", "in favor of", "use the",
                       "use ", "instead")

NEARBY_LINES = 2  # removal language this many lines away still counts


def _is_api_token(token):
    parts = token.split(".")
    if any(len(p) < 2 for p in parts):
        return False  # version strings (v5.x), abbreviations (e.g.)
    if parts[-1].lower() in NON_API_SUFFIXES:
        return False  # file names, domains
    if parts[0].lower().startswith("v") and parts[0][1:].isdigit():
        return False  # version strings like v5.x
    return True


def _line_tokens(line):
    """Yield (token, start_index) API-like tokens found in a line."""
    found = []
    for match in DOTTED_RE.finditer(line):
        token = match.group(0)
        if _is_api_token(token):
            found.append((token, match.start()))
    for match in BACKTICK_RE.finditer(line):
        inner = match.group(1).strip().strip("<>/")
        dotted = DOTTED_RE.search(inner)
        if dotted and _is_api_token(dotted.group(0)):
            found.append((dotted.group(0), match.start()))
        else:
            plain = re.split(r"[(\s]", inner, 1)[0].strip()
            if PLAIN_IDENT_RE.match(plain) and len(plain) >= 2:
                found.append((plain, match.start()))
    return found


def infer_kind(line):
    """Infer the change kind from a line's removal language."""
    low = line.lower()
    if "renamed" in low or "pluralized" in low or "now called" in low:
        return "renamed"
    if "replaced by" in low:
        return "renamed"
    if "removed" in low or "no longer" in low or "not supported" in low:
        return "removed"
    if "deprecated" in low:
        return "deprecated"
    return "changed"


def extract_heuristic(guide_text):
    """Deterministic candidate extraction. Returns a list of entries."""
    lines = [ln.strip() for ln in guide_text.splitlines()]
    entries = {}
    for i, line in enumerate(lines):
        if not line:
            continue
        # Find the nearest line carrying removal language (same line
        # preferred), within NEARBY_LINES.
        lang_line = None
        for distance in range(0, NEARBY_LINES + 1):
            for j in ((i,) if distance == 0 else (i - distance, i + distance)):
                if 0 <= j < len(lines) and REMOVAL_LANGUAGE.search(lines[j]):
                    lang_line = lines[j]
                    break
            if lang_line is not None:
                break
        if lang_line is None:
            continue

        # On the token's own line, tokens after a replacement marker
        # name the new API, not the broken one — skip them.
        cutoff = None
        if lang_line is line:
            low = line.lower()
            positions = [low.find(m) for m in REPLACEMENT_MARKERS
                         if low.find(m) != -1]
            # Only treat markers that occur after the line's first
            # token as replacement markers.
            first_tokens = _line_tokens(line)
            if positions and first_tokens:
                first_pos = min(pos for _, pos in first_tokens)
                later = [p for p in positions if p > first_pos]
                if later:
                    cutoff = min(later)

        for token, pos in _line_tokens(line):
            if cutoff is not None and pos > cutoff:
                continue
            if token in entries:
                continue
            quote = line if len(line) <= 200 else line[:197] + "..."
            entries[token] = {
                "api": token,
                "kind": infer_kind(lang_line),
                "note": f"Heuristic candidate (unverified): extracted "
                        f"from source line: \"{quote}\"",
            }
    return list(entries.values())


# ---------------------------------------------------------------- grounding

def ground_entries(entries, source_text):
    """The Paper Trail rule: keep only entries whose `api` string
    appears verbatim in the source text.

    Returns (kept, dropped) where dropped is a list of api strings.
    """
    kept, dropped = [], []
    seen = set()
    for entry in entries:
        api = entry.get("api", "")
        if api and api in source_text and api not in seen:
            kept.append(entry)
            seen.add(api)
        else:
            dropped.append(api)
    return kept, dropped


# ---------------------------------------------------------------- fetching

class _TextExtractor(HTMLParser):
    """Minimal HTML -> text: skip script/style, break lines on blocks."""

    BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
                  "pre", "tr", "section", "article", "header", "footer"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag in self.BLOCK_TAGS or tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html):
    parser = _TextExtractor()
    parser.feed(html)
    raw_lines = "".join(parser.parts).splitlines()
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw_lines]
    return "\n".join(ln for ln in lines if ln)


def fetch_url_text(url):
    """Download a URL with urllib; strip HTML if it looks like HTML."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "safe-to-upgrade-extract-breaking"})
    with urllib.request.urlopen(request, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
    if "<html" in body[:4000].lower() or "<div" in body[:4000].lower():
        return html_to_text(body)
    return body


def maybe_strip_html(text):
    if "<html" in text[:4000].lower() or "<div" in text[:4000].lower():
        return html_to_text(text)
    return text


# ---------------------------------------------------------------- output

def merge_into_generated(out_path, package, from_version, to_version,
                         source_url, kept_entries):
    """Merge kept entries into the generated JSON file.

    Same schema as breaking_data.json:
      {"packages": {name: {"from": ..., "to": ..., "source": ...,
                           "changes": [{"api", "change", "kind",
                                        "note", "source"}, ...]}}}
    Existing entries for the same package are kept; new APIs are
    appended; an API already present is not duplicated.
    Returns the number of entries actually added.
    """
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not (isinstance(data, dict) and "packages" in data):
            data = {"packages": data if isinstance(data, dict) else {}}
    else:
        data = {"packages": {}}

    entry = data["packages"].setdefault(package, {})
    entry["from"] = from_version
    entry["to"] = to_version
    entry["source"] = source_url
    changes = entry.setdefault("changes", [])
    known = {c.get("api") for c in changes}
    added = 0
    for item in kept_entries:
        if item["api"] in known:
            continue
        changes.append({
            "api": item["api"],
            "change": item["kind"],
            "kind": item["kind"],
            "note": item["note"],
            "source": source_url,
        })
        known.add(item["api"])
        added += 1

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    return added


# ---------------------------------------------------------------- self-test

SELFTEST_GUIDE = """\
# Migrating to v6

## Removed methods

The `res.sendfile()` function has been removed. Use `res.sendFile()` instead.

`useHistory` has been removed in v6; use `useNavigate` instead.

The app.del() helper is no longer supported; an error is thrown.
"""


def run_selftest():
    # Heuristic path extracts both required forms.
    entries = extract_heuristic(SELFTEST_GUIDE)
    apis = {e["api"] for e in entries}
    assert "res.sendfile" in apis, apis           # removed dotted API
    assert "useHistory" in apis, apis             # backticked identifier
    assert all(e["note"].startswith("Heuristic candidate")
               for e in entries), entries
    # The replacements named after "use" are not extracted as broken.
    assert "res.sendFile" not in apis, apis
    assert "useNavigate" not in apis, apis

    # Grounding drops a deliberately hallucinated API.
    poisoned = entries + [{"api": "res.frobnicate", "kind": "removed",
                           "note": "invented by the test"}]
    kept, dropped = ground_entries(poisoned, SELFTEST_GUIDE)
    kept_apis = {e["api"] for e in kept}
    assert "res.frobnicate" in dropped, dropped
    assert "res.frobnicate" not in kept_apis, kept_apis
    assert {"res.sendfile", "useHistory"} <= kept_apis, kept_apis

    # Model-output parsing is defensive: valid items survive, invalid
    # items are dropped, garbage yields ([], error).
    parsed, err = parse_model_output(
        'prose [{"api": "app.del", "kind": "removed", "note": "gone"},'
        ' {"api": "", "kind": "removed", "note": "bad"},'
        ' {"api": "x.y"}] trailing')
    assert err is None and len(parsed) == 1, (parsed, err)
    assert parsed[0]["api"] == "app.del", parsed
    parsed, err = parse_model_output("no json here")
    assert parsed == [] and err, (parsed, err)

    available, detail = check_ollama()
    print(f"selftest: heuristic extracted {sorted(apis)}")
    print("selftest: dotted removed API (res.sendfile) extracted — ok")
    print("selftest: backticked identifier (useHistory) extracted — ok")
    print("selftest: heuristic candidates labelled in notes — ok")
    print("selftest: grounding dropped hallucinated 'res.frobnicate' — ok")
    print("selftest: model-output defensive parsing — ok")
    print(f"selftest: ollama check -> available={available} ({detail})")
    print("selftest: all passed")
    return 0


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract breaking-change entries from a changelog "
                    "or migration guide (model proposes, code disposes).")
    parser.add_argument("--package", help="package name, e.g. express")
    parser.add_argument("--from", dest="from_version",
                        help="version upgrading from, e.g. 4.x")
    parser.add_argument("--to", dest="to_version",
                        help="version upgrading to, e.g. 5.x")
    parser.add_argument("--source-url",
                        help="source URL recorded on each entry "
                             "(defaults to --fetch-url when omitted)")
    parser.add_argument("--text-file",
                        help="path to a local file with the guide text")
    parser.add_argument("--fetch-url",
                        help="download the guide text from this URL")
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help=f"generated JSON output "
                             f"(default: {DEFAULT_OUT})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model (default: {DEFAULT_MODEL}, "
                             f"from $OLLAMA_MODEL)")
    parser.add_argument("--path", choices=("auto", "model", "heuristic"),
                        default="auto",
                        help="extraction path (default: auto — model "
                             "when Ollama is reachable, else heuristic)")
    parser.add_argument("--selftest", action="store_true",
                        help="run the built-in self-tests and exit")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()
    if not args.package or not args.from_version or not args.to_version:
        parser.error("--package, --from and --to are required "
                     "(or pass --selftest)")
    if not args.text_file and not args.fetch_url:
        parser.error("one of --text-file or --fetch-url is required")

    source_url = args.source_url or args.fetch_url

    if args.fetch_url:
        try:
            guide_text = fetch_url_text(args.fetch_url)
        except (urllib.error.URLError, OSError) as exc:
            print(f"error: could not fetch {args.fetch_url}: {exc}")
            return 1
    else:
        with open(args.text_file, encoding="utf-8", errors="ignore") as fh:
            guide_text = maybe_strip_html(fh.read())
    print(f"guide text: {len(guide_text)} chars from "
          f"{args.fetch_url or args.text_file}")

    # ---- extraction: model proposes (or heuristic proposes)
    path_used = None
    entries = []
    notes = []
    if args.path in ("auto", "model"):
        available, detail = check_ollama()
        print(f"ollama: available={available} ({detail})")
        if available:
            entries, err = extract_with_model(
                args.package, args.from_version, args.to_version,
                guide_text, args.model)
            if err is None and entries:
                path_used = "model"
            else:
                notes.append(f"model path produced nothing usable: "
                             f"{err or 'no valid entries returned'}")
                entries = []
                if args.path == "model":
                    print(f"error: {notes[-1]}")
                    return 1
        elif args.path == "model":
            print("error: --path model requested but Ollama is not "
                  f"available ({detail})")
            return 1
        else:
            notes.append("Ollama not available; fell back to heuristic")
    if path_used is None:
        entries = extract_heuristic(guide_text)
        path_used = "heuristic"

    # ---- grounding: code disposes
    kept, dropped = ground_entries(entries, guide_text)
    if path_used == "model" and not kept:
        notes.append("model entries all failed grounding; "
                     "fell back to heuristic")
        entries = extract_heuristic(guide_text)
        kept, dropped_h = ground_entries(entries, guide_text)
        dropped = dropped + dropped_h
        path_used = "heuristic"

    added = merge_into_generated(args.out, args.package,
                                 args.from_version, args.to_version,
                                 source_url, kept)

    for note in notes:
        print(f"note: {note}")
    print(f"path used: {path_used}")
    print(f"entries extracted: {len(entries)}")
    print(f"entries kept (grounded): {len(kept)}")
    print(f"entries dropped by grounding: {len(dropped)}"
          + (f" — {', '.join(dropped)}" if dropped else ""))
    print(f"entries added to {args.out}: {added} "
          f"(package '{args.package}' now merged there)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
