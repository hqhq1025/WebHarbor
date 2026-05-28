#!/usr/bin/env python3
"""Extend arxiv papers via the official export.arxiv.org Atom API.

Target: ~379k -> ~380k (saturated; this fills the last ~7 days across
        cs / math / physics / q-bio / stat).
Source: http://export.arxiv.org/api/query?search_query=cat:<grp>.*
        &start=0&max_results=200&sortBy=submittedDate&sortOrder=descending

Hard constraint: arxiv API ToS says 1 query per 3 sec — we sleep 3.5s
between requests. Burning this earns an IP ban.

INSERT OR IGNORE on arxiv_id (the bare id without version suffix).
"""
from __future__ import annotations
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import (  # noqa: E402
    fetch, open_db, insert_or_ignore, periodic_commit, upsert_count,
)

SITE = 'arxiv'
API = ('https://export.arxiv.org/api/query?search_query=cat:{cat}'
       '&start=0&max_results={n}&sortBy=submittedDate&sortOrder=descending')
GROUPS = ['cs.*', 'math.*', 'physics.*', 'q-bio.*', 'stat.*']
PER_GROUP = 200
ARXIV_SLEEP = 3.5  # seconds between API hits; ToS minimum is 3.

NS = {'atom': 'http://www.w3.org/2005/Atom',
      'arxiv': 'http://arxiv.org/schemas/atom'}

ID_RE = re.compile(r'arxiv\.org/abs/([^v]+)(v\d+)?')


def parse_entry(entry: ET.Element) -> dict | None:
    id_e = entry.find('atom:id', NS)
    if id_e is None or not id_e.text:
        return None
    m = ID_RE.search(id_e.text)
    if not m:
        return None
    arxiv_id = m.group(1)
    version = m.group(2) or 'v1'

    title = ((entry.find('atom:title', NS).text or '').strip()
             if entry.find('atom:title', NS) is not None else '')
    abstract = ((entry.find('atom:summary', NS).text or '').strip()
                if entry.find('atom:summary', NS) is not None else '')
    if not (arxiv_id and title):
        return None

    authors = [a.findtext('atom:name', default='', namespaces=NS).strip()
               for a in entry.findall('atom:author', NS)]
    authors = [a for a in authors if a]

    prim = entry.find('arxiv:primary_category', NS)
    prim_code = prim.get('term') if prim is not None else None  # e.g. cs.AI
    macro = (prim_code or '').split('.', 1)[0] or None         # e.g. cs

    cats = [c.get('term') for c in entry.findall('atom:category', NS) if c.get('term')]

    pub = entry.findtext('atom:published', default='', namespaces=NS).strip()
    upd = entry.findtext('atom:updated', default='', namespaces=NS).strip()
    sd = pub[:10] if len(pub) >= 10 else None
    yy = int(sd[:4]) if sd else None
    mm = int(sd[5:7]) if sd else None
    dd = int(sd[8:10]) if sd else None

    comment_e = entry.find('arxiv:comment', NS)
    doi_e = entry.find('arxiv:doi', NS)
    jref_e = entry.find('arxiv:journal_ref', NS)

    pdf_url = None
    for ln in entry.findall('atom:link', NS):
        if ln.get('title') == 'pdf':
            pdf_url = ln.get('href')
            break
    abs_url = f'https://arxiv.org/abs/{arxiv_id}'

    return {
        'arxiv_id': arxiv_id,
        'title': title,
        'abstract': abstract,
        'authors_json': json.dumps(authors),
        'subjects': ' '.join(cats) if cats else None,
        'primary_subject': prim_code,
        'primary_subject_code': prim_code,
        'primary_category_code': macro,
        'submitted_date': sd,
        'submitted_year': yy,
        'submitted_month': mm,
        'submitted_day': dd,
        'announce_date': upd[:10] if len(upd) >= 10 else None,
        'comments': comment_e.text.strip() if comment_e is not None and comment_e.text else None,
        'journal_ref': jref_e.text.strip()[:400] if jref_e is not None and jref_e.text else None,
        'doi': doi_e.text.strip()[:200] if doi_e is not None and doi_e.text else None,
        'pdf_url': pdf_url,
        'html_url': abs_url,
        'n_authors': len(authors) or None,
        'paper_version': version[:8],
    }


def fetch_group(cat: str, n: int) -> list[dict]:
    raw = fetch(API.format(cat=cat, n=n), timeout=40).decode('utf-8', 'ignore')
    root = ET.fromstring(raw)
    rows = []
    for entry in root.findall('atom:entry', NS):
        r = parse_entry(entry)
        if r:
            rows.append(r)
    return rows


def main():
    con = open_db(SITE)
    cur = con.cursor()
    existing = {r[0] for r in cur.execute('SELECT arxiv_id FROM papers')}
    before = upsert_count(con, 'papers')
    print(f'before: {before} papers')

    added = 0
    for cat in GROUPS:
        # Respect ToS sleep BEFORE every API call, including first (in case
        # someone else just hit it from this IP).
        time.sleep(ARXIV_SLEEP)
        try:
            rows = fetch_group(cat, PER_GROUP)
        except Exception as e:
            print(f'  {cat}: fetch fail {e}')
            continue
        new_for_cat = 0
        for r in rows:
            if r['arxiv_id'] in existing:
                continue
            if insert_or_ignore(con, 'papers', r) is not None:
                existing.add(r['arxiv_id'])
                added += 1
                new_for_cat += 1
                periodic_commit(con, added, every=50)
        print(f'  {cat}: harvested {len(rows)}, +{new_for_cat} new')

    con.commit()
    after = upsert_count(con, 'papers')
    print(f'after: {after} (+{added})')
    con.close()


if __name__ == '__main__':
    main()
