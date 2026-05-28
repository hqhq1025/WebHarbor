#!/usr/bin/env python3
"""extract_nav_graph.py — Pillar 4 (real-site navigation graph).

From all snapshots/<site>/<page>/full.html, parses internal <a href> + <button>
+ <a role=button> to build:
  - directed link graph (page → linked page, with anchor text)
  - per-button inventory (text, onclick, data-*, classes)

Outputs in snapshots/<site>/:
  _nav_graph.json    — {nodes, edges}
  _buttons.jsonl     — one button per line

Usage:
  python3 extract_nav_graph.py <site>
  python3 extract_nav_graph.py --all
"""
import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()


def normalize_url(url, base):
    absolute = urllib.parse.urljoin(base, url)
    absolute = absolute.split("#")[0]
    if absolute.endswith("/") and absolute.count("/") > 3:
        absolute = absolute[:-1]
    return absolute


def hostname(url):
    return urllib.parse.urlparse(url).netloc.lower()


def extract_links(html, base_url, base_host):
    links = []
    for m in re.finditer(
        r'<a\b([^>]*?)href=["\']([^"\']+)["\']([^>]*?)>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL):
        href = m.group(2).strip()
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute = normalize_url(href, base_url)
        if hostname(absolute) != base_host:
            continue
        text = re.sub(r"<[^>]+>", "", m.group(4)).strip()
        text = re.sub(r"\s+", " ", text)[:80]
        links.append((absolute, text))
    return links


# Feature K: isolate footer regions and extract their links separately.
FOOTER_BLOCK_RE = re.compile(
    r'<(footer|div|section)\b([^>]*\b(?:role\s*=\s*["\']contentinfo["\']|'
    r'class\s*=\s*"[^"]*(?:footer|site-footer|global-footer|page-footer)[^"]*"|'
    r'id\s*=\s*"[^"]*(?:footer|site-footer|global-footer)[^"]*")[^>]*)>',
    re.IGNORECASE)
FOOTER_TAG_RE = re.compile(r'<footer\b([^>]*)>(.*?)</footer>',
                            re.IGNORECASE | re.DOTALL)


def slice_balanced(html: str, start: int, tag: str, max_len: int = 200_000) -> str:
    """Return inner html up to balanced close tag."""
    open_pat = re.compile(rf'<{tag}\b', re.IGNORECASE)
    close_pat = re.compile(rf'</{tag}\s*>', re.IGNORECASE)
    depth = 1
    pos = start
    end_limit = min(start + max_len, len(html))
    while pos < end_limit and depth > 0:
        o = open_pat.search(html, pos, end_limit)
        c = close_pat.search(html, pos, end_limit)
        if not c:
            return html[start:end_limit]
        if o and o.start() < c.start():
            depth += 1
            pos = o.end()
        else:
            depth -= 1
            if depth == 0:
                return html[start:c.start()]
            pos = c.end()
    return html[start:pos]


def extract_footer_html(html: str) -> str:
    """Return concatenated footer-region html (footer tag + role=contentinfo + footer-class divs)."""
    chunks = []
    # <footer>...</footer>
    for m in FOOTER_TAG_RE.finditer(html):
        chunks.append(m.group(2))
    # role=contentinfo / class=footer divs (avoid double-counting <footer>)
    for m in FOOTER_BLOCK_RE.finditer(html):
        tag = m.group(1).lower()
        if tag == "footer":
            continue  # already covered above
        inner = slice_balanced(html, m.end(), tag, max_len=200_000)
        chunks.append(inner)
    return "\n".join(chunks)


def extract_buttons(html):
    buttons = []
    for m in re.finditer(r'<button\b([^>]*)>(.*?)</button>', html,
                          re.IGNORECASE | re.DOTALL):
        attrs, inner = m.group(1), m.group(2)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        text = re.sub(r"\s+", " ", text)[:60]
        if not text:
            continue
        onclick = re.search(r'\bonclick=["\']([^"\']+)["\']', attrs)
        classes = re.search(r'\bclass=["\']([^"\']+)["\']', attrs)
        data_attrs = dict(re.findall(r'\b(data-[a-zA-Z0-9_-]+)=["\']([^"\']+)["\']',
                                       attrs))
        buttons.append({
            "tag": "button", "text": text,
            "onclick": (onclick.group(1)[:120] if onclick else None),
            "classes": (classes.group(1)[:120] if classes else None),
            "data_attrs": {k: v[:80] for k, v in list(data_attrs.items())[:5]},
        })
    for m in re.finditer(
        r'<a\b([^>]*?(?:role=["\']button["\']|class=["\'][^"\']*btn[^"\']*["\'])[^>]*?)>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL):
        attrs, inner = m.group(1), m.group(2)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        text = re.sub(r"\s+", " ", text)[:60]
        if not text:
            continue
        href = re.search(r'\bhref=["\']([^"\']+)["\']', attrs)
        classes = re.search(r'\bclass=["\']([^"\']+)["\']', attrs)
        buttons.append({
            "tag": "a-btn", "text": text,
            "href": href.group(1)[:120] if href else None,
            "classes": classes.group(1)[:120] if classes else None,
        })
    return buttons


def process_site(site_dir: Path):
    nodes = set()
    edges = []
    all_buttons = []
    footer_edges = []  # Feature K
    pages = [p for p in site_dir.iterdir() if p.is_dir()]
    for page_dir in pages:
        full_path = page_dir / "full.html"
        md_path = page_dir / "metadata.json"
        if not (full_path.exists() and md_path.exists()):
            continue
        try:
            html = full_path.read_text(encoding="utf-8", errors="ignore")
            url = json.loads(md_path.read_text()).get("url", "")
        except Exception:
            continue
        if not url:
            continue
        base_host = hostname(url)
        nodes.add(url)
        for target, text in extract_links(html, url, base_host):
            nodes.add(target)
            edges.append({"from": url, "to": target, "text": text,
                           "from_page": page_dir.name})
        for btn in extract_buttons(html):
            btn["page"] = page_dir.name
            btn["page_url"] = url
            all_buttons.append(btn)

        # Feature K: footer-only links
        footer_html = extract_footer_html(html)
        if footer_html:
            footer_seen = set()
            for target, text in extract_links(footer_html, url, base_host):
                key = (target, text)
                if key in footer_seen:
                    continue
                footer_seen.add(key)
                footer_edges.append({
                    "from": url, "to": target, "text": text,
                    "from_page": page_dir.name,
                })

    graph = {
        "site": site_dir.name,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": sorted(nodes),
        "edges": edges,
    }
    (site_dir / "_nav_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2))
    with (site_dir / "_buttons.jsonl").open("w") as f:
        for b in all_buttons:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")
    # Feature K
    with (site_dir / "_footer_links.jsonl").open("w") as f:
        for e in footer_edges:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    return len(pages), len(nodes), len(edges), len(all_buttons), len(footer_edges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    sites = ([ROOT / args.site] if args.site else
             sorted(p for p in ROOT.iterdir() if p.is_dir()))
    print(f"{'site':<28} {'pgs':>5} {'nodes':>6} {'edges':>6} {'btns':>5} {'foot':>5}")
    print("-" * 70)
    for site_dir in sites:
        if not site_dir.is_dir():
            continue
        pgs, n, e, b, fl = process_site(site_dir)
        print(f"{site_dir.name:<28} {pgs:>5} {n:>6} {e:>6} {b:>5} {fl:>5}")


if __name__ == "__main__":
    main()
