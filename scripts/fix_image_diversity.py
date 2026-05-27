"""Restore image diversity across sites whose placeholder images were heavily reused.

Background — see `.claude/skills/harden-env/gotchas.md` #42 for full root cause analysis.
At fix time (2026-05-27) the following 8 sites had image columns where the top
placeholder accounted for ≥25% of rows, sometimes 100% — visually obvious "Mock UI
Studio" reuse. This script restores per-entity diversity by either:

  - Strategy A (real fetch): not used here for time; pools come from existing assets.
  - Strategy B (md5 over real pool): stable per-entity mapping over the largest
    available real-image pool already on disk.
  - Strategy C (generated SVG): emit one distinct SVG per entity (gradient + initials)
    when no usable real pool exists.

This script is idempotent — running it twice yields the same DB content. Run it on
the SEED database (sites/<site>/instance_seed/<db>.db) before packing HF tarballs so
fresh container boots inherit the fix:

  python3 scripts/fix_image_diversity.py <site|all>

After running on instance_seed/, also `cp instance_seed/<db>.db instance/<db>.db`
so the running container reflects the fix without restart (or restart via
control_server POST /reset/<site>).
"""
import collections
import hashlib
import json
import pathlib
import sqlite3
import sys


REPO = pathlib.Path(__file__).resolve().parent.parent

PALETTES = [
    ("#0f172a", "#1e3a8a", "#3b82f6"), ("#7c2d12", "#9a3412", "#f59e0b"),
    ("#064e3b", "#047857", "#10b981"), ("#581c87", "#7e22ce", "#a855f7"),
    ("#831843", "#9d174d", "#ec4899"), ("#1e293b", "#334155", "#64748b"),
    ("#7f1d1d", "#991b1b", "#dc2626"), ("#365314", "#4d7c0f", "#84cc16"),
    ("#155e75", "#0e7490", "#06b6d4"), ("#713f12", "#854d0e", "#eab308"),
    ("#1e40af", "#2563eb", "#60a5fa"), ("#86198f", "#a21caf", "#d946ef"),
]


def _h(s, salt=""):
    return int(hashlib.md5((salt + s).encode()).hexdigest()[:8], 16)


def _initials(slug, n=3):
    parts = [p for p in slug.replace("_", "-").split("-") if p]
    if not parts: return "??"
    if len(parts) == 1: return parts[0][:n].upper()
    return "".join(p[0] for p in parts[:n]).upper()


def gen_label_svg(slug, kind="", w=600, h=360):
    """Single-entity SVG: gradient bg + accent shape + bold initials + small kind label."""
    pal = PALETTES[_h(slug, "p") % len(PALETTES)]
    bg1, bg2, accent = pal
    init = _initials(slug)
    shape_seed = _h(slug, "s") % 4
    if shape_seed == 0:
        shape = f'<circle cx="{w-80}" cy="80" r="110" fill="{accent}" opacity="0.18"/>'
    elif shape_seed == 1:
        shape = f'<polygon points="0,{h} {w},{h-120} {w},{h} 0,{h}" fill="{accent}" opacity="0.22"/>'
    elif shape_seed == 2:
        shape = f'<rect x="{w-160}" y="-50" width="220" height="220" transform="rotate(20 {w-50} 50)" fill="{accent}" opacity="0.20"/>'
    else:
        shape = f'<circle cx="60" cy="{h-50}" r="100" fill="{accent}" opacity="0.20"/>'
    fs = 130 if len(init) <= 2 else 100
    label_t = ""
    if kind:
        label_t = (f'<text x="{w//2}" y="{h-28}" font-family="ui-sans-serif,system-ui,sans-serif" '
                   f'font-size="18" fill="white" opacity="0.78" text-anchor="middle" '
                   f'letter-spacing="3">{kind.upper()[:24]}</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{bg1}"/><stop offset="100%" stop-color="{bg2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="{w}" height="{h}" fill="url(#g)"/>{shape}'
        f'<text x="{w//2}" y="{h//2 + fs//3}" font-family="ui-sans-serif,system-ui,sans-serif" '
        f'font-weight="700" font-size="{fs}" fill="white" text-anchor="middle" letter-spacing="-2">{init}</text>'
        f'{label_t}</svg>'
    )


def _floorplan_svg(beds, variant):
    w, h = 480, 320
    palettes = [
        ("#e6f3fb","#fff3e0","#9aa6b3","#3b4955"),
        ("#dcfce7","#fef3c7","#86847a","#1f2937"),
        ("#ffe4e6","#dbeafe","#94a3b8","#0f172a"),
        ("#fae8ff","#fef9c3","#a8a29e","#374151"),
        ("#e0f2fe","#fee2e2","#9ca3af","#1f2937"),
        ("#ecfeff","#fce7f3","#a3a3a3","#111827"),
    ]
    bf, lf, st, tx = palettes[variant % 6]
    el = [f'<rect x="6" y="6" width="{w-12}" height="{h-12}" fill="#fff" stroke="{st}" stroke-width="2"/>']
    if beds == 0:
        el.append(f'<rect x="30" y="30" width="{w-60}" height="{h-60}" fill="{bf}" stroke="{st}"/>')
        el.append(f'<text x="{w//2}" y="{h//2}" text-anchor="middle" font-size="32" font-family="ui-sans-serif" fill="{tx}">Studio</text>')
        el.append(f'<rect x="{w-130}" y="{h-100}" width="80" height="60" fill="{lf}" stroke="{st}"/>')
        el.append(f'<text x="{w-90}" y="{h-65}" text-anchor="middle" font-size="11" fill="{tx}">Kitchen</text>')
    else:
        lv = variant % 4
        bw, bh, gap = 110, 95, 14
        if lv == 0 or beds == 1:
            for i in range(beds):
                x = 30 + i*(bw+gap)
                if x+bw > w-30: break
                el.append(f'<rect x="{x}" y="30" width="{bw}" height="{bh}" fill="{bf}" stroke="{st}"/>')
                el.append(f'<text x="{x+bw//2}" y="{30+bh//2+4}" text-anchor="middle" font-size="12" fill="{tx}">Bed {i+1}</text>')
            el.append(f'<rect x="30" y="{30+bh+16}" width="{w-60}" height="{h-30-bh-32-60}" fill="{lf}" stroke="{st}"/>')
            el.append(f'<text x="{w//2}" y="{h//2+30}" text-anchor="middle" font-size="14" fill="{tx}">Living / Dining</text>')
            el.append(f'<rect x="30" y="{h-70}" width="{w//2-30}" height="40" fill="{lf}" stroke="{st}"/>')
            el.append(f'<text x="{(30+w//2)//2}" y="{h-44}" text-anchor="middle" font-size="11" fill="{tx}">Kitchen</text>')
        elif lv == 1:
            cols = min(2, beds)
            for i in range(beds):
                c, r = i % cols, i // cols
                x = 30 + c*(bw+gap); y = 30 + r*(bh+gap)
                if y+bh > h-60: break
                el.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{bf}" stroke="{st}"/>')
                el.append(f'<text x="{x+bw//2}" y="{y+bh//2+4}" text-anchor="middle" font-size="12" fill="{tx}">Bed {i+1}</text>')
            el.append(f'<rect x="{30+cols*(bw+gap)}" y="30" width="{w-60-cols*(bw+gap)}" height="{h-90}" fill="{lf}" stroke="{st}"/>')
            el.append(f'<text x="{30+cols*(bw+gap)+(w-60-cols*(bw+gap))//2}" y="{h//2}" text-anchor="middle" font-size="13" fill="{tx}">Living</text>')
        elif lv == 2:
            for i in range(beds):
                x = 30 + i*(bw+gap)
                if x+bw > w-30: break
                el.append(f'<rect x="{x}" y="30" width="{bw}" height="{bh}" fill="{bf}" stroke="{st}"/>')
                el.append(f'<text x="{x+bw//2}" y="{30+bh//2+4}" text-anchor="middle" font-size="12" fill="{tx}">Bed {i+1}</text>')
            el.append(f'<rect x="30" y="{30+bh+16}" width="{w//2}" height="{h-30-bh-32}" fill="{lf}" stroke="{st}"/>')
            el.append(f'<text x="{30+w//4}" y="{h-60}" text-anchor="middle" font-size="13" fill="{tx}">Living</text>')
            el.append(f'<rect x="{30+w//2+10}" y="{30+bh+16}" width="{w//2-70}" height="{(h-30-bh-32)//2}" fill="{lf}" stroke="{st}"/>')
            el.append(f'<text x="{w-(w//2)//2-20}" y="{30+bh+16+(h-30-bh-32)//4+4}" text-anchor="middle" font-size="11" fill="{tx}">Kitchen</text>')
        else:
            for i in range(beds):
                y = 30 + i*(bh+gap)
                if y+bh > h-30: break
                el.append(f'<rect x="30" y="{y}" width="{bw+30}" height="{bh}" fill="{bf}" stroke="{st}"/>')
                el.append(f'<text x="{30+(bw+30)//2}" y="{y+bh//2+4}" text-anchor="middle" font-size="12" fill="{tx}">Bed {i+1}</text>')
            el.append(f'<rect x="{30+bw+50}" y="30" width="{w-60-bw-50}" height="{h-90}" fill="{lf}" stroke="{st}"/>')
            el.append(f'<text x="{30+bw+50+(w-60-bw-50)//2}" y="{h//2}" text-anchor="middle" font-size="13" fill="{tx}">Living / Kitchen</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{"".join(el)}</svg>'


# =============== per-site fixes ===============

def fix_github(target="instance_seed"):
    """github user.avatar: B md5 over 105-image avatars pool. Targets 6701 users."""
    site = REPO / "sites" / "github"
    pool = sorted([p.name for p in (site / "static/images/avatars").glob("*")])
    assert pool, "github avatars pool empty"
    db = site / target / "github_mirror.db"
    con = sqlite3.connect(str(db))
    rows = con.execute("SELECT username FROM user").fetchall()
    upd = [(f'/static/images/avatars/{pool[_h(u[0]) % len(pool)]}', u[0]) for u in rows]
    con.executemany("UPDATE user SET avatar=? WHERE username=?", upd)
    con.commit(); con.close()
    return len(rows)


def fix_carmax(target="instance_seed"):
    """carmax stores.image: C gen SVG per store (62 stores). Pool was empty (storefront_default.jpg)."""
    site = REPO / "sites" / "carmax"
    out = site / "static/images/stores"; out.mkdir(parents=True, exist_ok=True)
    db = site / target / "carmax.db"
    con = sqlite3.connect(str(db))
    rows = con.execute("SELECT id, slug, city, state FROM stores").fetchall()
    upd = []
    for sid, slug, city, state in rows:
        (out / f"{slug}.svg").write_text(gen_label_svg(slug, f"{city} {state}"))
        upd.append((f"/static/images/stores/{slug}.svg", sid))
    con.executemany("UPDATE stores SET image=? WHERE id=?", upd)
    con.commit(); con.close()
    return len(rows)


def fix_berkeley(target="instance_seed"):
    """berkeley libraries.photo: C gen SVG per library (23 libs)."""
    site = REPO / "sites" / "berkeley"
    out = site / "static/images"
    db = site / target / "berkeley.db"
    con = sqlite3.connect(str(db))
    rows = con.execute("SELECT id, slug FROM libraries").fetchall()
    upd = []
    for lid, slug in rows:
        fname = f"library-{slug}.svg"
        (out / fname).write_text(gen_label_svg(slug, "Library"))
        upd.append((fname, lid))
    con.executemany("UPDATE libraries SET photo=? WHERE id=?", upd)
    con.commit(); con.close()
    return len(rows)


def fix_compass(target="instance_seed"):
    """compass: cities/neighborhoods/blog_posts hero_image — B md5 over 524 listings hero.webp."""
    site = REPO / "sites" / "compass"
    pool = sorted([p.name for p in (site / "static/images/listings").iterdir() if p.is_dir()])
    assert pool, "compass listings pool empty"
    db = site / target / "compass.db"
    con = sqlite3.connect(str(db))

    def pick(seed, salt):
        return f"/static/images/listings/{pool[_h(seed, salt) % len(pool)]}/hero.webp"

    n = 0
    for tbl, key_cols, salt in [
        ("cities", ["slug"], "city:"),
        ("neighborhoods", ["city", "slug"], "nbh:"),
        ("blog_posts", ["slug"], "blog:"),
    ]:
        cols = ", ".join(["id"] + key_cols)
        rows = con.execute(f"SELECT {cols} FROM {tbl}").fetchall()
        upd = [(pick("/".join(r[1:]), salt), r[0]) for r in rows]
        con.executemany(f"UPDATE {tbl} SET hero_image=? WHERE id=?", upd)
        n += len(rows)
    con.commit(); con.close()
    return n


def fix_google_map(target="instance_seed"):
    """google_map city.hero_image: B md5 over per-city dirs + place hero pool (~206 images)."""
    site = REPO / "sites" / "google_map"
    cdir = site / "static/images/cities"
    pdir = site / "static/images/places"
    pool = []
    for d in sorted(cdir.iterdir()):
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in {".jpg",".png",".webp",".jpeg"}:
                    pool.append(f"/static/images/cities/{d.name}/{f.name}")
    for d in sorted(pdir.iterdir()):
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in {".jpg",".png",".webp",".jpeg"}:
                    pool.append(f"/static/images/places/{d.name}/{f.name}"); break
    assert pool, "google_map pool empty"
    db = site / target / "gmaps.db"
    con = sqlite3.connect(str(db))
    rows = con.execute("SELECT id, slug FROM city").fetchall()
    upd = []
    for cid, slug in rows:
        own = cdir / slug
        chosen = None
        if own.exists():
            files = sorted([f for f in own.iterdir() if f.suffix.lower() in {".jpg",".png",".webp"}])
            if files:
                chosen = f"/static/images/cities/{slug}/{files[0].name}"
        if chosen is None:
            chosen = pool[_h(slug) % len(pool)]
        upd.append((chosen, cid))
    con.executemany("UPDATE city SET hero_image=? WHERE id=?", upd)
    con.commit(); con.close()
    return len(rows)


def fix_google_search(target="instance_seed"):
    """google_search topic.images_json: populate empty `[]` arrays with 3-5 distinct images via md5."""
    site = REPO / "sites" / "google_search"
    pool = []
    real = site / "static/images/google_real"
    for f in sorted(real.iterdir()):
        if f.is_file() and f.suffix.lower() in {".jpg",".png",".svg",".webp",".jpeg"}:
            pool.append(f"/static/images/google_real/{f.name}")
    for d in sorted((site / "static/images/topics").iterdir()):
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in {".jpg",".png",".webp",".jpeg"}:
                    pool.append(f"/static/images/topics/{d.name}/{f.name}")
    db = site / target / "google_search.db"
    con = sqlite3.connect(str(db))
    rows = con.execute("SELECT id, slug, images_json FROM topic").fetchall()
    upd = []
    for tid, slug, ij in rows:
        try: existing = json.loads(ij) if ij else []
        except: existing = []
        if len(existing) >= 3:
            continue
        used = set(existing); chosen = []
        for i in range(5):
            h = _h(slug, f"|{i}")
            for off in range(len(pool)):
                c = pool[(h + off) % len(pool)]
                if c not in used:
                    chosen.append(c); used.add(c); break
        upd.append((json.dumps((existing + chosen)[:5]), tid))
    con.executemany("UPDATE topic SET images_json=? WHERE id=?", upd)
    con.commit(); con.close()
    return len(upd)


def fix_apartments_com(target="instance_seed"):
    """apartments_com floor_plans.plan_image: C generate 60 SVG variants per bedroom category, md5 distribute."""
    site = REPO / "sites" / "apartments_com"
    out = site / "static/images/floorplans"; out.mkdir(parents=True, exist_ok=True)
    VARIANTS = 60
    pool_by_beds = {}
    for beds in range(0, 5):
        files = []
        for v in range(VARIANTS):
            fname = f"plan-{beds}br-v{v:02d}.svg" if beds > 0 else f"plan-studio-v{v:02d}.svg"
            (out / fname).write_text(_floorplan_svg(beds, v))
            files.append(f"/static/images/floorplans/{fname}")
        pool_by_beds[beds] = files
    db = site / target / "apartments_com.db"
    con = sqlite3.connect(str(db))
    rows = con.execute("SELECT id, slug, beds FROM floor_plans").fetchall()
    upd = []
    for plan_id, slug, beds in rows:
        pool = pool_by_beds[min(max(beds, 0), 4)]
        upd.append((pool[_h(slug) % len(pool)], plan_id))
    con.executemany("UPDATE floor_plans SET plan_image=? WHERE id=?", upd)
    con.commit(); con.close()
    return len(rows)


def fix_wolfram_alpha(target=None):
    """wolfram_alpha topic_galleries.json: greedy least-used assignment over 154-image pool, themed when ≥4 candidates."""
    site = REPO / "sites" / "wolfram_alpha"
    pool = sorted([p.relative_to(site).as_posix() for p in (site / "static/images").rglob("*")
                   if p.is_file() and p.suffix.lower() in {".png",".jpg",".jpeg",".webp",".gif"}])
    jpath = site / "topic_galleries.json"
    data = json.load(open(jpath))
    used = collections.Counter()
    items = []
    for topic, sections in data.items():
        for i, s in enumerate(sections):
            items.append((topic, i, s))
    items.sort(key=lambda x: hashlib.md5(f"{x[0]}:{x[1]}".encode()).hexdigest())
    for topic, i, s in items:
        themed = [p for p in pool if topic.lower() in p.lower()]
        cands = themed if len(themed) >= 4 else pool
        seed = f"{topic}:{i}:{s.get('title','')}"
        cands_sorted = sorted(cands, key=lambda p: (used[p], hashlib.md5((seed+p).encode()).hexdigest()))
        chosen = cands_sorted[0]
        used[chosen] += 1
        s["images"] = [chosen]
    json.dump(data, open(jpath, "w"), indent=2)
    return sum(len(v) for v in data.values())


FIXERS = {
    "github": fix_github,
    "carmax": fix_carmax,
    "berkeley": fix_berkeley,
    "compass": fix_compass,
    "google_map": fix_google_map,
    "google_search": fix_google_search,
    "apartments_com": fix_apartments_com,
    "wolfram_alpha": fix_wolfram_alpha,
}


def _verify(site):
    """Print top-dup% per image column for the given site, post-fix."""
    targets = {
        "compass": [("instance/compass.db", "cities", "hero_image"),
                    ("instance/compass.db", "neighborhoods", "hero_image"),
                    ("instance/compass.db", "blog_posts", "hero_image")],
        "google_map": [("instance/gmaps.db", "city", "hero_image")],
        "github": [("instance/github_mirror.db", "user", "avatar")],
        "carmax": [("instance/carmax.db", "stores", "image")],
        "berkeley": [("instance/berkeley.db", "libraries", "photo")],
        "apartments_com": [("instance/apartments_com.db", "floor_plans", "plan_image")],
    }
    if site in targets:
        for dbp, tbl, col in targets[site]:
            db = REPO / "sites" / site / dbp
            if not db.exists(): continue
            con = sqlite3.connect(str(db))
            rows = con.execute(f'SELECT "{col}" FROM "{tbl}" WHERE "{col}" IS NOT NULL AND "{col}" != ""').fetchall()
            cnt = collections.Counter([r[0] for r in rows])
            top = cnt.most_common(1)[0]
            pct = top[1]*100.0/len(rows)
            status = "PASS" if pct < 5 else "FAIL"
            print(f"  [{status}] {site}.{tbl}.{col}: {len(rows)} rows, {len(cnt)} distinct, top {pct:.2f}%")
            con.close()
    elif site == "google_search":
        con = sqlite3.connect(str(REPO / "sites/google_search/instance/google_search.db"))
        imgs = []
        for (ij,) in con.execute("SELECT images_json FROM topic"):
            try: imgs.extend(json.loads(ij))
            except: pass
        cnt = collections.Counter(imgs)
        top = cnt.most_common(1)[0]
        pct = top[1]*100.0/len(imgs)
        status = "PASS" if pct < 5 else "FAIL"
        print(f"  [{status}] google_search.topic.images_json[refs]: {len(imgs)} refs, {len(cnt)} distinct, top {pct:.2f}%")
        con.close()
    elif site == "wolfram_alpha":
        data = json.load(open(REPO / "sites/wolfram_alpha/topic_galleries.json"))
        imgs = []
        for topic, sections in data.items():
            for s in sections:
                imgs.extend(s.get("images", []))
        cnt = collections.Counter(imgs)
        top = cnt.most_common(1)[0]
        pct = top[1]*100.0/len(imgs)
        status = "PASS" if pct < 5 else "FAIL"
        print(f"  [{status}] wolfram_alpha.topic_galleries.json: {len(imgs)} refs, {len(cnt)} distinct, top {pct:.2f}%")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <site|all> [--target instance|instance_seed]")
        print(f"Sites: {' '.join(FIXERS)}")
        return 1
    arg = sys.argv[1]
    target = "instance_seed"
    if "--target" in sys.argv:
        target = sys.argv[sys.argv.index("--target") + 1]
    sites = list(FIXERS) if arg == "all" else [arg]
    for s in sites:
        n = FIXERS[s](target) if s != "wolfram_alpha" else FIXERS[s]()
        print(f"[{s}] fixed {n} rows ({target})")
        _verify(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
