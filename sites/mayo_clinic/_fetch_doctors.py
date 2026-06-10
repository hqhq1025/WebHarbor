"""Download randomuser.me headshots, one stable JPG per doctor.slug.

Gender is picked from the doctor's first name with a simple heuristic so each
slug gets a believable headshot. Files are written into
static/images/doctors/<slug>.jpg.
"""
import hashlib
import os
import sqlite3
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "instance_seed", "mayo_clinic.db")
OUT = os.path.join(BASE, "static", "images", "doctors")
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Simple first-name gender heuristic. Anything not listed falls back to md5
# coin-flip so the assignment is still stable per slug.
FEMALE = {
    "anna","emily","sarah","jennifer","jessica","maria","linda","susan","karen","laura",
    "michelle","amanda","elizabeth","melissa","rebecca","stephanie","kimberly","amy",
    "angela","ashley","emma","olivia","sophia","isabella","mia","charlotte","amelia",
    "lily","grace","ella","rachel","megan","nicole","heather","tracy","tiffany","julie",
    "katherine","kathryn","catherine","margaret","barbara","patricia","mary","helen",
    "sandra","donna","carol","ruth","sharon","cynthia","kathleen","brenda","pamela",
    "deborah","martha","virginia","christine","beverly","denise","tammy","irene","jane",
    "lori","kelly","diane","frances","alice","julia","grace","judith","sara","theresa",
    "evelyn","cheryl","mildred","katherine","joan","ann","caroline","beth","wendy",
    "claire","priya","mei","yuki","fatima","aisha","leila","saroj","ananya","kavita",
    "natasha","sofia","sophie","camille","chloe","zara","jasmine","hannah","leah",
}
MALE = {
    "john","james","robert","michael","william","david","richard","joseph","thomas","charles",
    "christopher","daniel","matthew","anthony","mark","donald","steven","paul","andrew","joshua",
    "kenneth","kevin","brian","george","timothy","ronald","jason","edward","jeffrey","ryan",
    "jacob","gary","nicholas","eric","jonathan","stephen","larry","justin","scott","brandon",
    "benjamin","samuel","gregory","frank","alexander","raymond","patrick","jack","dennis","jerry",
    "tyler","aaron","jose","henry","adam","douglas","nathan","peter","zachary","kyle","walter",
    "ethan","jeremy","harold","keith","christian","roger","noah","gerald","carl","terry","sean",
    "austin","arthur","lawrence","jesse","dylan","bryan","joe","jordan","billy","bruce","albert",
    "willie","gabriel","logan","alan","juan","wayne","ralph","randy","russell","louis","philip",
    "vincent","bobby","johnny","luke","mason","caleb","colin","ahmed","mohammed","raj","arjun",
    "vikram","amir","carlos","luis","diego","santiago","mateo","liam","oliver","aiden","wei",
    "jian","hiroshi","takashi","kenji",
}


def gender_for(name: str, slug: str) -> str:
    first = name.split()[0].strip().lower() if name else ""
    if first in FEMALE:
        return "women"
    if first in MALE:
        return "men"
    # deterministic coin-flip when unknown
    h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    return "women" if h % 2 == 0 else "men"


def fetch(args):
    slug, name = args
    dest = os.path.join(OUT, f"{slug}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 2000:
        return True
    g = gender_for(name, slug)
    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16) % 100
    url = f"https://randomuser.me/api/portraits/{g}/{idx}.jpg"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                ct = r.headers.get("Content-Type", "")
                data = r.read()
            if not ct.startswith("image/") or len(data) < 2000:
                return False
            with open(dest, "wb") as f:
                f.write(data)
            return True
        except Exception:
            time.sleep(0.8 + attempt * 1.5)
    return False


def main():
    con = sqlite3.connect(DB)
    docs = con.execute("SELECT slug, name FROM doctor").fetchall()
    con.close()
    print(f"Doctors to fetch: {len(docs)}", flush=True)
    ok = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(fetch, docs):
            if r:
                ok += 1
    print(f"Doctor headshots ok: {ok}/{len(docs)}", flush=True)


if __name__ == "__main__":
    main()
