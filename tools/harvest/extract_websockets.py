#!/usr/bin/env python3
"""extract_websockets.py — Feature T: WebSocket / EventSource streaming endpoints.

Catalogs real-time streaming endpoints buried in HTML / JS:
  - wss:// and ws:// URLs in inline JS or attributes (live game state, chat,
    stock tickers, sports scores)
  - new WebSocket("...") constructor calls
  - new EventSource("...") (SSE) constructor calls
  - Common pubsub hosts (pusher.com, ably.io, pubnub.com, ortc, signalr,
    socket.io, faye)

R06 chess.com bug B-06-CHESS-04 trigger: chess.com live game state goes via
`wss://stream.chess.com`, never appears in xhr_calls.jsonl (Playwright only
captures HTTP). Same pattern: trading apps, slack-like chat, multiplayer games.

Output: snapshots/<site>/_ws_streams.jsonl

Usage:
  python3 extract_websockets.py <site>
  python3 extract_websockets.py --all
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
import urllib.parse

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

WSS_URL_RE = re.compile(
    r'(?:wss?://[\w.-]+(?:[:/][\w./?=&%~+#-]*)?)',
    re.IGNORECASE,
)
NEW_WS_RE = re.compile(
    r'new\s+WebSocket\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
NEW_SSE_RE = re.compile(
    r'new\s+EventSource\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
PUBSUB_HOSTS_RE = re.compile(
    r'["\']https?://([\w.-]*(?:pusher\.com|pusherapp\.com|ably\.io|pubnub\.com|'
    r'realtime\.ortc|socket\.io|/sockjs/|signalr|faye|firebaseio\.com|'
    r'aws-iot-data|emqx)[^"\']*)["\']',
    re.IGNORECASE,
)


def process_page(page_dir: Path) -> list[dict]:
    html_path = page_dir / "full.html"
    if not html_path.exists():
        return []
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    out: list[dict] = []
    seen: set[str] = set()

    def add(url: str, source: str):
        url = url.strip()
        if url in seen or len(url) < 6:
            return
        seen.add(url)
        host = ""
        try:
            host = urllib.parse.urlparse(url if "://" in url else "ws://" + url).hostname or ""
        except Exception:
            pass
        out.append({
            "page": page_dir.name,
            "url": url[:500],
            "source": source,
            "host": host,
        })

    # 1. wss://... raw URLs anywhere
    for m in WSS_URL_RE.finditer(html):
        add(m.group(0), "wss-url")
    # 2. new WebSocket("...")
    for m in NEW_WS_RE.finditer(html):
        add(m.group(1), "new-WebSocket")
    # 3. new EventSource("...")
    for m in NEW_SSE_RE.finditer(html):
        add(m.group(1), "new-EventSource")
    # 4. pubsub vendor URLs (still useful even if not yet upgraded to WS)
    for m in PUBSUB_HOSTS_RE.finditer(html):
        add(m.group(1), "pubsub-vendor")
    return out


def process_site(site_dir: Path) -> dict:
    all_records: list[dict] = []
    pages_scanned = 0
    pages_with = 0
    source_counts: dict[str, int] = defaultdict(int)
    host_counts: dict[str, int] = defaultdict(int)
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir() or page_dir.name.startswith('_'):
            continue
        pages_scanned += 1
        records = process_page(page_dir)
        if records:
            pages_with += 1
        for r in records:
            source_counts[r["source"]] += 1
            if r["host"]:
                host_counts[r["host"]] += 1
        all_records.extend(records)
    out = site_dir / "_ws_streams.jsonl"
    with out.open("w") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    index = {
        "pages_scanned": pages_scanned,
        "pages_with_ws": pages_with,
        "total_records": len(all_records),
        "source_counts": dict(source_counts),
        "top_hosts": dict(sorted(host_counts.items(), key=lambda kv: -kv[1])[:10]),
    }
    (site_dir / "_ws_streams_index.json").write_text(json.dumps(index, indent=2))
    return index


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
    print(f"{'site':<30} {'pgs':>4} {'wWS':>4} {'recs':>5}  top sources")
    print("-" * 80)
    grand = 0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING"); continue
        idx = process_site(site_dir)
        n = idx['total_records']
        grand += n
        srcs = " ".join(f"{k.split('-',1)[-1]}={v}" for k, v in sorted(
            idx['source_counts'].items(), key=lambda kv: -kv[1])[:3])
        print(f"{site_dir.name:<30} {idx['pages_scanned']:>4} {idx['pages_with_ws']:>4} {n:>5}  {srcs}")
    print(f"\nGrand total WS/SSE records: {grand}")


if __name__ == "__main__":
    main()
