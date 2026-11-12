#!/usr/bin/env python3
"""deadlinks - find broken links in Markdown and HTML files.

One file, zero dependencies. Checks web URLs (in parallel) and local file links.

  python deadlinks.py                 # scan the current folder
  python deadlinks.py docs/ README.md # scan a folder or a single file
  python deadlinks.py --local-only    # skip the network, check relative links only
"""
import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

__version__ = "1.0.0"

LINK = re.compile(r"""\]\(\s*<?([^)\s>]+)|(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
EXTS = {".md", ".markdown", ".html", ".htm"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}
IGNORED_SCHEMES = ("mailto:", "tel:", "data:", "javascript:", "#", "//")
SOFT_BLOCK = (401, 403, 429)  # site refuses bots; can't tell if the link is dead


def find_files(root):
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in EXTS and not SKIP_DIRS & set(p.parts):
            yield p


def extract(files):
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        in_code = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            for m in LINK.finditer(line):
                yield f, n, (m.group(1) or m.group(2))


def check_local(f, link, root_dir):
    path = urllib.parse.unquote(link.split("#")[0].split("?")[0])
    if not path:
        return None
    base = root_dir if path.startswith("/") else f.parent
    target = (base / path.lstrip("/")).resolve()
    return None if target.exists() else "file not found"


def check_url(url, timeout):
    last = "unreachable"
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(
            url, method=method, headers={"User-Agent": "Mozilla/5.0 deadlinks/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout):
                return None
        except urllib.error.HTTPError as e:
            if e.code in SOFT_BLOCK:
                return None
            last = f"HTTP {e.code}"
        except Exception as e:  # DNS failure, timeout, TLS error, bad URL...
            last = str(getattr(e, "reason", None) or type(e).__name__)
    return last


def main():
    p = argparse.ArgumentParser(prog="deadlinks", description="Find broken links in Markdown and HTML files.")
    p.add_argument("paths", nargs="*", default=["."], help="files or folders to scan (default: .)")
    p.add_argument("-t", "--timeout", type=float, default=10, help="seconds per request (default 10)")
    p.add_argument("-j", "--workers", type=int, default=16, help="parallel requests (default 16)")
    p.add_argument("--local-only", action="store_true", help="only check links to local files")
    p.add_argument("--ignore", action="append", default=[], metavar="REGEX", help="skip links matching this regex (repeatable)")
    p.add_argument("--version", action="version", version=__version__)
    a = p.parse_args()

    ignore = [re.compile(x) for x in a.ignore]
    items = []
    for raw in a.paths:
        root = Path(raw)
        if not root.exists():
            sys.exit(f"error: no such path: {raw}")
        root_dir = root if root.is_dir() else root.parent
        for f, n, link in extract(find_files(root)):
            if not any(r.search(link) for r in ignore):
                items.append((f, n, link, root_dir))

    is_web = lambda s: s.lower().startswith(("http://", "https://"))
    urls = sorted({l for _, _, l, _ in items if is_web(l)})
    results = {}
    if urls and not a.local_only:
        print(f"Checking {len(urls)} URLs in {len({f for f, *_ in items})} files...")
        with ThreadPoolExecutor(max(1, a.workers)) as ex:
            for url, err in zip(urls, ex.map(lambda u: check_url(u, a.timeout), urls)):
                results[url] = err

    broken = []
    for f, n, link, root_dir in items:
        if is_web(link):
            err = results.get(link)
        elif link.lower().startswith(IGNORED_SCHEMES) or "://" in link:
            continue
        else:
            err = check_local(f, link, root_dir)
        if err:
            broken.append((f, n, link, err))

    for f, n, link, err in broken:
        print(f"{f}:{n}  {link}  -> {err}")
    print(f"\n{len(items)} links checked, {len(broken)} broken.")
    return 1 if broken else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
