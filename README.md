<p align="center">
  <img src="assets/banner.svg" alt="deadlinks animated terminal demo" width="800">
</p>

<h1 align="center">deadlinks</h1>

<p align="center">
  Find broken links in your Markdown and HTML files.<br>
  <b>One file. Zero dependencies. Fast, parallel checks.</b>
</p>

---

## Quick start

No install needed. Download the single file and run it:

```bash
curl -O https://raw.githubusercontent.com/ERROR404DTIR/deadlinks/main/deadlinks.py
python deadlinks.py
```

Requires Python 3.8+ (standard library only).

## What it checks

- Web links (`http://`, `https://`) in Markdown `[text](url)` and HTML `href` / `src`
- Relative links to local files and images (`./img/logo.png`, `../docs/guide.md`)
- Links inside code blocks are ignored, so examples don't cause false alarms

## Usage

```bash
python deadlinks.py                    # scan the current folder
python deadlinks.py docs/ README.md    # scan folders and files
python deadlinks.py --local-only       # offline: only check local file links
python deadlinks.py -j 32 -t 5         # 32 parallel requests, 5s timeout
python deadlinks.py --ignore "localhost" --ignore "example\.com"
```

| Option | Meaning |
|---|---|
| `-t, --timeout` | Seconds to wait per request (default 10) |
| `-j, --workers` | Parallel requests (default 16) |
| `--local-only` | Skip all network checks |
| `--ignore REGEX` | Skip matching links (repeatable) |

## CI friendly

Exits with code `1` when broken links are found and `0` otherwise, so you can drop it straight into a pipeline:

```yaml
- run: python deadlinks.py --ignore "localhost"
```

## Notes

Each URL is tried with `HEAD` first, then `GET`. Responses like 401, 403 and 429 are treated as "site blocks bots" rather than dead links.
