#!/usr/bin/env python3
"""Fetch GitHub release notes for two tags of a repo (public API, stdlib).

Usage:
  python fetch_changelog.py <owner/repo> <tag_a> [tag_b]
  e.g. python fetch_changelog.py remix-run/react-router v6.30.0 v6.30.1

For each tag it calls GET /repos/{owner}/{repo}/releases/tags/{tag} on
api.github.com and prints the release name, publish date, URL, and body.
If a tag has no GitHub Release (many projects only tag), the API returns
404 and that is reported plainly — release notes are an input to the
breaking-change extraction step, and missing notes are never invented.
"""

import json
import sys
import urllib.error
import urllib.request

API_ROOT = "https://api.github.com"


def fetch_release(repo, tag):
    """Return the parsed GitHub Release for `tag`, or raise on failure."""
    url = f"{API_ROOT}/repos/{repo}/releases/tags/{tag}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "safe-to-upgrade-fetch-changelog",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main(argv):
    if len(argv) < 3 or len(argv) > 4:
        print(__doc__.strip())
        return 2
    repo = argv[1]
    if repo.count("/") != 1:
        print(f"error: expected owner/repo, got {repo!r}")
        return 2

    failures = 0
    for tag in argv[2:]:
        print(f"===== {repo} @ {tag} =====")
        try:
            release = fetch_release(repo, tag)
        except urllib.error.HTTPError as exc:
            failures += 1
            print(f"no GitHub Release found for tag {tag!r} "
                  f"(HTTP {exc.code})")
            continue
        except urllib.error.URLError as exc:
            failures += 1
            print(f"network error fetching tag {tag!r}: {exc.reason}")
            continue
        print(f"name: {release.get('name') or '(unnamed)'}")
        print(f"published_at: {release.get('published_at')}")
        print(f"url: {release.get('html_url')}")
        print()
        print((release.get("body") or "(no release notes body)").strip())
        print()
    return 1 if failures == len(argv[2:]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
