#!/usr/bin/env python3
"""extract_code_blocks.py — Feature N: code dimension.

Catalogs code references in snapshots/<site>/<page>/full.html:
  - <pre><code>...</code></pre>  (language from class attr)
  - GitHub-style ```fenced``` (in plain text fragments)
  - <script src="..."> external JS (not always app code, but worth indexing)
  - linked source files: .js .ts .py .go .rs .java .cpp etc as <a href>
  - Gist iframes (gist.github.com/<user>/<id>)

Goal: prove the dimension exists. Output code excerpts (first 300 chars) +
language hint + url where applicable.

Output: snapshots/<site>/_code_blocks.jsonl

Usage:
  python3 extract_code_blocks.py <site>
  python3 extract_code_blocks.py --all
"""
import argparse
import html as htmllib
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

CODE_EXTS = (".js", ".ts", ".tsx", ".jsx", ".py", ".go", ".rs", ".java",
             ".kt", ".swift", ".c", ".cpp", ".h", ".cs", ".rb", ".php",
             ".sh", ".bash", ".zsh", ".sql", ".yml", ".yaml", ".json",
             ".xml", ".toml", ".lua", ".scala", ".clj", ".ex", ".exs",
             ".jl", ".m", ".mm", ".pl", ".r", ".dart", ".f", ".f90", ".vue",
             ".svelte", ".css", ".scss", ".less", ".gradle", ".cmake", ".dockerfile")
PRE_CODE_RE = re.compile(
    r'<pre\b([^>]*)>\s*<code\b([^>]*)>(.*?)</code>\s*</pre>',
    re.IGNORECASE | re.DOTALL,
)
# R02 github fix: bare <pre> blocks (GH README notranslate, MDN, Stack Overflow)
# and inline <code> are 90% of real code on dev sites. PRE_CODE_RE misses them.
PRE_BARE_RE = re.compile(
    r'<pre\b([^>]*)>(?!\s*<code\b)(.*?)</pre>',
    re.IGNORECASE | re.DOTALL,
)
INLINE_CODE_RE = re.compile(
    r'<code\b([^>]*)>([^<]{3,400})</code>',  # inline only — short, no nested tags
    re.IGNORECASE,
)
LANG_RE = re.compile(r'\b(?:language|lang|hljs|prism)-([a-zA-Z0-9+#-]+)', re.IGNORECASE)
SCRIPT_SRC_RE = re.compile(r'<script\b[^>]*?src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
HREF_RE = re.compile(r'<a\b[^>]*?href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
IFRAME_RE = re.compile(r'<iframe\b[^>]*?src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


def strip_tags(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s)


def normalize(url: str, base: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith(("http://", "https://", "data:")):
        return url
    return urllib.parse.urljoin(base, url)


def is_code_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower().split("?", 1)[0].split("#", 1)[0]
    return u.endswith(CODE_EXTS)


def detect_lang(class_attr: str) -> str:
    m = LANG_RE.search(class_attr)
    return m.group(1).lower() if m else ""


def extract_page(page_dir: Path, base_url: str = "") -> list[dict]:
    html_path = page_dir / "full.html"
    if not html_path.exists():
        return []
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    base = base_url
    m = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
    if m:
        base = m.group(1)

    out: list[dict] = []
    seen_excerpts: set[str] = set()
    seen_urls: set[str] = set()

    # pre/code blocks — inline code samples
    for m in PRE_CODE_RE.finditer(html):
        pre_attr, code_attr, body = m.group(1), m.group(2), m.group(3)
        lang = detect_lang(pre_attr) or detect_lang(code_attr)
        text = htmllib.unescape(strip_tags(body)).strip()
        if not text:
            continue
        key = text[:120]
        if key in seen_excerpts:
            continue
        seen_excerpts.add(key)
        out.append({
            "page": page_dir.name,
            "kind": "pre>code",
            "lang": lang,
            "lines": text.count("\n") + 1,
            "chars": len(text),
            "excerpt": text[:300],
        })

    # R02 github fix: bare <pre> blocks (GH README notranslate, MDN, SO)
    for m in PRE_BARE_RE.finditer(html):
        pre_attr, body = m.group(1), m.group(2)
        # Skip if body contains <code> (already matched by PRE_CODE_RE)
        if "<code" in body.lower():
            continue
        lang = detect_lang(pre_attr)
        text = htmllib.unescape(strip_tags(body)).strip()
        if not text or len(text) < 5:
            continue
        key = text[:120]
        if key in seen_excerpts:
            continue
        seen_excerpts.add(key)
        out.append({
            "page": page_dir.name,
            "kind": "pre-bare",
            "lang": lang,
            "lines": text.count("\n") + 1,
            "chars": len(text),
            "excerpt": text[:300],
        })

    # R02 github fix: inline <code> snippets (short, single-line)
    inline_count = 0
    for m in INLINE_CODE_RE.finditer(html):
        if inline_count >= 80:  # cap to avoid noise from per-word styling
            break
        code_attr, body = m.group(1), m.group(2)
        text = htmllib.unescape(body).strip()
        if not text or len(text) < 3:
            continue
        key = ("inline:" + text)[:120]
        if key in seen_excerpts:
            continue
        seen_excerpts.add(key)
        inline_count += 1
        out.append({
            "page": page_dir.name,
            "kind": "code-inline",
            "lang": detect_lang(code_attr),
            "chars": len(text),
            "excerpt": text[:200],
        })

    # external script srcs (likely libs/bundles, useful for clone target list)
    for m in SCRIPT_SRC_RE.finditer(html):
        url = normalize(m.group(1), base or base_url)
        if not url or url.startswith("data:") or url in seen_urls:
            continue
        seen_urls.add(url)
        out.append({
            "page": page_dir.name,
            "kind": "script[src]",
            "lang": "js",
            "url": url[:500],
        })

    # source-file links
    for m in HREF_RE.finditer(html):
        url = normalize(m.group(1), base or base_url)
        if not is_code_url(url) or url in seen_urls:
            continue
        seen_urls.add(url)
        ext = url.lower().split("?", 1)[0].split("#", 1)[0].rsplit(".", 1)[-1]
        out.append({
            "page": page_dir.name,
            "kind": "a[href]:code-file",
            "lang": ext,
            "url": url[:500],
        })

    # gist iframes
    for m in IFRAME_RE.finditer(html):
        url = m.group(1)
        if "gist.github.com" in url.lower() or "codepen.io" in url.lower() or "codesandbox.io" in url.lower() or "replit.com" in url.lower() or "jsfiddle.net" in url.lower():
            if url in seen_urls:
                continue
            seen_urls.add(url)
            host = urllib.parse.urlparse(url).hostname or "?"
            out.append({
                "page": page_dir.name,
                "kind": "iframe:code-embed",
                "lang": "",
                "url": url[:500],
                "host": host,
            })

    return out


def process_site(site_dir: Path) -> tuple[int, int, dict[str, int]]:
    all_records: list[dict] = []
    pages_scanned = 0
    pages_with = 0
    kind_counts: dict[str, int] = {}
    base_url = f"https://{site_dir.name.replace('_', '.')}/"
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        pages_scanned += 1
        records = extract_page(page_dir, base_url=base_url)
        if records:
            pages_with += 1
        for r in records:
            kind_counts[r["kind"]] = kind_counts.get(r["kind"], 0) + 1
        all_records.extend(records)
    out = site_dir / "_code_blocks.jsonl"
    with out.open("w") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return pages_scanned, pages_with, kind_counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all:
        targets = [d for d in sorted(ROOT.iterdir()) if d.is_dir()]
    elif args.site:
        targets = [ROOT / args.site]
    else:
        ap.error("provide <site> or --all")
        return
    print(f"{'site':<30} {'pgs':>5} {'wCd':>5} {'recs':>6}  top kinds")
    print("-" * 80)
    grand = 0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING")
            continue
        pgs, wc, kinds = process_site(site_dir)
        n = sum(kinds.values())
        grand += n
        kk = " ".join(f"{k}={v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:3])
        print(f"{site_dir.name:<30} {pgs:>5} {wc:>5} {n:>6}  {kk}")
    print(f"\nGrand total code refs: {grand}")


if __name__ == "__main__":
    main()
