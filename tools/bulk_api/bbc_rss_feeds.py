#!/usr/bin/env python3
"""Extend BBC News articles via additional RSS feeds.

Target: 637 -> 1000+ articles
Source: feeds.bbci.co.uk/news/<section>/rss.xml (16+ extended feeds)
"""
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
import re
import datetime as dt
import time
from pathlib import Path

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/bbc_news/instance/bbc_news.db'

# Extended RSS feeds (battle-tested base 11 + 8 new sub-sections)
FEEDS = [
    ('http://feeds.bbci.co.uk/news/rss.xml', 'news', 2),
    ('http://feeds.bbci.co.uk/news/world/rss.xml', 'world', 3),
    ('http://feeds.bbci.co.uk/news/uk/rss.xml', 'uk', 4),
    ('http://feeds.bbci.co.uk/news/business/rss.xml', 'business', 6),
    ('http://feeds.bbci.co.uk/news/politics/rss.xml', 'politics', 5),
    ('http://feeds.bbci.co.uk/news/health/rss.xml', 'health', 9),
    ('http://feeds.bbci.co.uk/news/education/rss.xml', 'education', 2),
    ('http://feeds.bbci.co.uk/news/science_and_environment/rss.xml', 'science', 8),
    ('http://feeds.bbci.co.uk/news/technology/rss.xml', 'technology', 7),
    ('http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml', 'entertainment', 10),
    ('http://feeds.bbci.co.uk/sport/rss.xml', 'sport', 12),
    ('http://feeds.bbci.co.uk/sport/football/rss.xml', 'football', 12),
    ('http://feeds.bbci.co.uk/sport/cricket/rss.xml', 'cricket', 12),
    ('http://feeds.bbci.co.uk/sport/tennis/rss.xml', 'tennis', 12),
    ('http://feeds.bbci.co.uk/sport/rugby-union/rss.xml', 'rugby', 12),
    ('http://feeds.bbci.co.uk/news/world/europe/rss.xml', 'europe', 3),
    ('http://feeds.bbci.co.uk/news/world/asia/rss.xml', 'asia', 3),
    ('http://feeds.bbci.co.uk/news/world/africa/rss.xml', 'africa', 3),
    ('http://feeds.bbci.co.uk/news/world/middle_east/rss.xml', 'middle_east', 3),
    ('http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml', 'us_canada', 3),
    ('http://feeds.bbci.co.uk/news/world/latin_america/rss.xml', 'latam', 3),
]

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

NS = {
    'media': 'http://search.yahoo.com/mrss/',
    'atom': 'http://www.w3.org/2005/Atom',
}


def slugify(s, maxlen=70):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:maxlen]


def parse_pubdate(s):
    # BBC RSS uses RFC 822 e.g. "Tue, 28 May 2026 10:15:00 GMT"
    s = s.strip()
    # strip timezone tokens that strptime hates
    s = re.sub(r'\s+(GMT|UTC|EDT|EST|PDT|PST|BST|CET|CEST)$', '', s)
    try:
        return dt.datetime.strptime(s, '%a, %d %b %Y %H:%M:%S')
    except Exception:
        try:
            return dt.datetime.strptime(s, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=None)
        except Exception:
            return dt.datetime.utcnow()


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    existing_slugs = {r[0] for r in cur.execute('SELECT slug FROM articles').fetchall()}
    before = cur.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
    print(f'before: {before} articles')

    added = 0
    for url, section_slug, cat_id in FEEDS:
        try:
            data = fetch(url)
        except Exception as e:
            print(f'  skip {url}: {e}')
            continue
        try:
            root = ET.fromstring(data)
        except ET.ParseError as e:
            print(f'  parse fail {url}: {e}')
            continue
        items = root.findall('.//item')
        cnt = 0
        for it in items:
            title_e = it.find('title')
            link_e = it.find('link')
            desc_e = it.find('description')
            pub_e = it.find('pubDate')
            thumb_e = it.find('media:thumbnail', NS)
            if title_e is None or link_e is None:
                continue
            title = (title_e.text or '').strip()
            link = (link_e.text or '').strip()
            slug = slugify(title)
            if not slug or slug in existing_slugs:
                continue
            summary = (desc_e.text or '').strip() if desc_e is not None else ''
            hero = thumb_e.get('url', '') if thumb_e is not None else ''
            pub = parse_pubdate(pub_e.text) if pub_e is not None and pub_e.text else dt.datetime.utcnow()
            body = summary + '\n\nRead more on BBC: ' + link
            word_count = len(body.split())
            reading_time = max(1, word_count // 200)
            cur.execute('''INSERT INTO articles (slug, headline, subtitle, summary, body, author,
                                                 category_id, hero_image, gallery_json, topics_json,
                                                 published_at, reading_time, word_count, view_count,
                                                 is_featured, is_breaking, is_live, location, source_url,
                                                 section_slug, subsection, region, video_url, feature_tags,
                                                 content_type, gallery_full_json)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (slug, title, '', summary[:500], body, 'BBC News',
                         cat_id, hero, '[]', '[]', pub, reading_time, word_count, 0,
                         0, 0, 0, '', link, section_slug, '', '', '', '[]', 'article', '{}'))
            existing_slugs.add(slug)
            cnt += 1
            added += 1
        print(f'  {section_slug}: +{cnt}')
        time.sleep(0.5)

    con.commit()
    after = cur.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
    print(f'after: {after} (+{added})')
    con.close()


if __name__ == '__main__':
    main()
