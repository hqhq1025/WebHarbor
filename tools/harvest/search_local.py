#!/usr/bin/env python3
"""search_local.py — local SearXNG meta-search replacement for Tavily/Exa.

SearXNG runs on http://localhost:8888 (docker, see ~/.../real_components/README.md
or just `docker ps | grep searxng`). It aggregates Google + Bing + DuckDuckGo +
Brave + Wikipedia + Wikimedia + ~70 other engines.

Free, unlimited (subject only to upstream engines' own rate limits, spread
across all of them).

Usage:
  from search_local import search, search_images

  # Text/web search (Tavily-equivalent)
  results = search("python pandas dataframe filter")
  # [{"title": ..., "url": ..., "content": "..."}, ...]

  # Image search (replaces Tavily include_images=True / Exa images)
  imgs = search_images("italian restaurant interior")
  # [{"img_src": ..., "thumbnail_src": ..., "title": ..., "source": ...}, ...]
"""
import json
import time
import urllib.parse
import urllib.request

BASE = "http://localhost:8888"
UA = "WebHarbor-Agent/1.0"
TIMEOUT = 15


def _get(path, params):
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}{path}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def search(query, n=10, engines=None, language="en"):
    """Text/web search — Tavily-equivalent. Returns up to `n` results.

    Each result: {title, url, content, engine, score}
    """
    params = {"q": query, "format": "json", "language": language}
    if engines:
        params["engines"] = ",".join(engines)
    data = _get("/search", params)
    return data.get("results", [])[:n]


def search_images(query, n=20, language="en"):
    """Image search — Tavily include_images=True equivalent.

    Each result: {img_src, thumbnail_src, title, source, resolution}
    """
    params = {"q": query, "format": "json", "categories": "images",
              "language": language}
    data = _get("/search", params)
    results = data.get("results", [])
    # Filter out broken / data: URLs
    valid = [r for r in results if r.get("img_src", "").startswith(("http://", "https://"))]
    return valid[:n]


def search_news(query, n=10, language="en"):
    """News search."""
    params = {"q": query, "format": "json", "categories": "news",
              "language": language}
    data = _get("/search", params)
    return data.get("results", [])[:n]


def is_alive():
    """Quick health check — call once before bulk operations."""
    try:
        results = search("test", n=1)
        return len(results) > 0
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: search_local.py <query>  [images|news]")
        sys.exit(1)
    query = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else "text"
    fn = {"text": search, "images": search_images, "news": search_news}[kind]
    for r in fn(query, n=5):
        print(json.dumps(r, ensure_ascii=False)[:200])
