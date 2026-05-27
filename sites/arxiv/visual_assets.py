"""
gen_visual_assets.py — emit deterministic SVG image pool for arxiv mirror.

Outputs:
  static/images/figures/<style>_<index>.svg     ~60 figures (scatter / bar /
                                                neural-net / heatmap /
                                                architecture / curve)
  static/images/headshots/avatar_<NN>.svg       24 avatars w/ initials + ramp
  static/images/conferences/<conf>.svg          10 conference banners
  static/images/categories/<code>.svg           10 category hero banners

Deterministic — re-running produces byte-identical files. Pool is small (~100
files) and shared across the whole site; per-row uniqueness comes from md5
mapping inside app.py + on-page overlay captions.

The figures aren't full reproductions of real papers; they are *visually
plausible* placeholders so the GUI matches a real paper-detail page. Real
arxiv figure thumbnails ship inside scraped_data/real_figures_meta.json for
a handful of well-known papers (see fetch_real_figures.py).
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent / "static" / "images"


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _h(seed: str, salt: int = 0) -> int:
    return int(hashlib.md5(f"{salt}|{seed}".encode()).hexdigest()[:8], 16)


def _palette(seed: str):
    """Return a 5-color palette derived from md5(seed)."""
    base = _h(seed, 17)
    hues = [(base + i * 67) % 360 for i in range(5)]
    return [f"hsl({h},65%,55%)" for h in hues]


# -----------------------------------------------------------------------
# Figure styles
# -----------------------------------------------------------------------

def figure_scatter(seed: str) -> str:
    pal = _palette(seed)
    pts = []
    for i in range(120):
        x = (_h(seed, i * 2 + 1) % 360) + 30
        y = (_h(seed, i * 2 + 2) % 200) + 20
        c = pal[(_h(seed, i) >> 4) % 5]
        r = 2 + (_h(seed, i) % 4)
        pts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}" fill-opacity="0.72"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#fafafa"/>
<g stroke="#dadada" stroke-width="0.6">
<line x1="30" y1="220" x2="410" y2="220"/>
<line x1="30" y1="20" x2="30" y2="220"/>
{"".join(f'<line x1="30" y1="{220-30*i}" x2="410" y2="{220-30*i}" stroke-dasharray="2 3"/>' for i in range(1,7))}
</g>
{"".join(pts)}
<text x="220" y="252" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#555">embedding dim 1</text>
<text x="14" y="120" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#555" transform="rotate(-90 14 120)">embedding dim 2</text>
</svg>'''


def figure_line(seed: str) -> str:
    pal = _palette(seed)
    lines = []
    for k in range(4):
        pts = []
        prev = 200 - (_h(seed, k * 7) % 60)
        for i in range(40):
            v = max(30, min(220, prev + (_h(seed, k * 31 + i) % 25) - 12))
            prev = v
            x = 30 + i * 9.5
            pts.append(f"{x:.1f},{v}")
        lines.append(f'<polyline fill="none" stroke="{pal[k]}" stroke-width="1.8" points="{" ".join(pts)}"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#fff"/>
<g stroke="#e3e3e3"><line x1="30" y1="20" x2="30" y2="220"/><line x1="30" y1="220" x2="410" y2="220"/></g>
{"".join(lines)}
<text x="220" y="252" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#555">training epoch</text>
<text x="14" y="120" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#555" transform="rotate(-90 14 120)">loss</text>
<g font-family="Helvetica" font-size="9" fill="#444">
<rect x="320" y="28" width="80" height="56" fill="#fff" stroke="#ccc"/>
<text x="360" y="42" text-anchor="middle">legend</text>
<g><rect x="328" y="48" width="10" height="3" fill="{pal[0]}"/><text x="343" y="52">baseline</text></g>
<g><rect x="328" y="58" width="10" height="3" fill="{pal[1]}"/><text x="343" y="62">ours-S</text></g>
<g><rect x="328" y="68" width="10" height="3" fill="{pal[2]}"/><text x="343" y="72">ours-L</text></g>
<g><rect x="328" y="78" width="10" height="3" fill="{pal[3]}"/><text x="343" y="82">+aug</text></g>
</g>
</svg>'''


def figure_bar(seed: str) -> str:
    pal = _palette(seed)
    bars = []
    labels = ["BLEU", "ROUGE", "F1", "Acc", "AUC", "mAP", "EM", "MRR"]
    for i, lab in enumerate(labels):
        h = 40 + (_h(seed, i * 11) % 150)
        x = 50 + i * 42
        bars.append(f'<rect x="{x}" y="{220 - h}" width="28" height="{h}" fill="{pal[i % 5]}"/>')
        bars.append(f'<text x="{x + 14}" y="234" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#444">{lab}</text>')
        bars.append(f'<text x="{x + 14}" y="{215 - h}" text-anchor="middle" font-family="Helvetica" font-size="9" fill="#222">{h / 2:.1f}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#fff"/>
<line x1="40" y1="220" x2="410" y2="220" stroke="#bbb"/>
{"".join(bars)}
<text x="220" y="20" text-anchor="middle" font-family="Helvetica" font-size="12" fill="#333">benchmark scores</text>
</svg>'''


def figure_heatmap(seed: str) -> str:
    rows, cols = 10, 16
    cells = []
    for r in range(rows):
        for c in range(cols):
            v = _h(seed, r * cols + c) % 100
            hue = 220 - int(v * 1.4)
            cells.append(f'<rect x="{40 + c * 22}" y="{30 + r * 18}" width="22" height="18" fill="hsl({hue},75%,{30 + v // 3}%)"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#fafafa"/>
{"".join(cells)}
<text x="220" y="20" text-anchor="middle" font-family="Helvetica" font-size="11" fill="#333">attention heatmap (layer / head)</text>
<text x="220" y="252" text-anchor="middle" font-family="Helvetica" font-size="9" fill="#555">heads →</text>
</svg>'''


def figure_arch(seed: str) -> str:
    pal = _palette(seed)
    boxes = ["Tokenizer", "Embed", "Encoder", "Self-Attn", "FFN", "Decoder", "Cross-Attn", "Output"]
    out = []
    for i, b in enumerate(boxes):
        x = 20 + i * 50
        c = pal[i % 5]
        out.append(f'<rect x="{x}" y="100" width="42" height="38" rx="4" fill="{c}" fill-opacity="0.18" stroke="{c}" stroke-width="1.4"/>')
        out.append(f'<text x="{x + 21}" y="123" text-anchor="middle" font-family="Helvetica" font-size="9" fill="#222">{b}</text>')
        if i < len(boxes) - 1:
            out.append(f'<line x1="{x + 42}" y1="119" x2="{x + 50}" y2="119" stroke="#666" stroke-width="1" marker-end="url(#arr)"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#666"/></marker></defs>
<rect width="100%" height="100%" fill="#fff"/>
<text x="210" y="56" text-anchor="middle" font-family="Helvetica" font-size="13" fill="#333">model architecture</text>
{"".join(out)}
<rect x="20" y="170" width="380" height="60" rx="4" fill="#f5f5f5" stroke="#ccc"/>
<text x="210" y="195" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#555">cross-attention pathway uses scaled dot-product over key-value cache</text>
<text x="210" y="215" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#888">parameter count derived from configuration table 1</text>
</svg>'''


def figure_curve(seed: str) -> str:
    # Loss / ROC style smooth curve
    pal = _palette(seed)
    pts1 = []
    pts2 = []
    for i in range(80):
        x = 30 + i * 4.7
        e1 = 200 - 160 * (1 - math.exp(-i / 24)) + ((_h(seed, i) % 6) - 3)
        e2 = 200 - 130 * (1 - math.exp(-i / 16)) + ((_h(seed, i + 99) % 6) - 3)
        pts1.append(f"{x:.1f},{e1:.1f}")
        pts2.append(f"{x:.1f},{e2:.1f}")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#fff"/>
<g stroke="#e3e3e3"><line x1="30" y1="20" x2="30" y2="220"/><line x1="30" y1="220" x2="410" y2="220"/></g>
<polyline fill="none" stroke="{pal[0]}" stroke-width="2" points="{" ".join(pts1)}"/>
<polyline fill="none" stroke="{pal[2]}" stroke-width="2" points="{" ".join(pts2)}"/>
<text x="220" y="252" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#555">false positive rate</text>
<text x="14" y="120" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#555" transform="rotate(-90 14 120)">true positive rate</text>
<text x="220" y="22" text-anchor="middle" font-family="Helvetica" font-size="11" fill="#333">ROC — ours vs baseline (AUC = 0.{(_h(seed) % 90 + 10)})</text>
</svg>'''


def figure_galaxy(seed: str) -> str:
    """Astro/physics-flavoured figure: spiral of points."""
    pal = _palette(seed)
    pts = []
    for i in range(420):
        t = i * 0.07
        r = 4 + 0.3 * i
        cx = 210 + r * math.cos(t + (_h(seed, i) % 30) * 0.01)
        cy = 130 + 0.55 * r * math.sin(t + (_h(seed, i) % 30) * 0.01)
        col = pal[(_h(seed, i) >> 4) % 5]
        pts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{1 + (i % 3)}" fill="{col}" fill-opacity="0.7"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#0a0a18"/>
{"".join(pts)}
<text x="210" y="248" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#bbb">simulated catalogue (N≈420)</text>
</svg>'''


def figure_lattice(seed: str) -> str:
    """Physics / chemistry lattice."""
    pal = _palette(seed)
    out = []
    for r in range(7):
        for c in range(13):
            x = 35 + c * 30 + (r % 2) * 15
            y = 35 + r * 30
            col = pal[(_h(seed, r * 13 + c) >> 4) % 5]
            out.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{col}" fill-opacity="0.7" stroke="#333" stroke-width="0.5"/>')
            if c < 12:
                out.append(f'<line x1="{x + 9}" y1="{y}" x2="{x + 21 + (r % 2) * 0}" y2="{y}" stroke="#888" stroke-width="0.6"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#fdfdf4"/>
{"".join(out)}
<text x="210" y="254" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#444">hexagonal lattice (a₀ = 2.46 Å)</text>
</svg>'''


def figure_brain(seed: str) -> str:
    """q-bio / neuro style — network graph."""
    pal = _palette(seed)
    nodes = []
    n = 22
    coords = []
    for i in range(n):
        t = 2 * math.pi * i / n + (_h(seed, i) % 30) * 0.005
        cx = 210 + 95 * math.cos(t)
        cy = 130 + 80 * math.sin(t)
        coords.append((cx, cy))
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if (_h(seed, i * 100 + j) % 100) < 12:
                edges.append(f'<line x1="{coords[i][0]:.1f}" y1="{coords[i][1]:.1f}" x2="{coords[j][0]:.1f}" y2="{coords[j][1]:.1f}" stroke="{pal[(i+j)%5]}" stroke-opacity="0.35"/>')
    for i, (cx, cy) in enumerate(coords):
        nodes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{pal[i%5]}" stroke="#222" stroke-width="0.6"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" width="420" height="260">
<rect width="100%" height="100%" fill="#fbfbff"/>
{"".join(edges)}
{"".join(nodes)}
<text x="210" y="248" text-anchor="middle" font-family="Helvetica" font-size="10" fill="#444">functional connectivity graph</text>
</svg>'''


FIGURE_STYLES = [
    ("scatter", figure_scatter),
    ("line", figure_line),
    ("bar", figure_bar),
    ("heatmap", figure_heatmap),
    ("arch", figure_arch),
    ("curve", figure_curve),
    ("galaxy", figure_galaxy),
    ("lattice", figure_lattice),
    ("brain", figure_brain),
]


# -----------------------------------------------------------------------
# Avatars (headshots)
# -----------------------------------------------------------------------

def avatar_svg(idx: int) -> str:
    seed = f"avatar_{idx:02d}"
    digest = hashlib.md5(seed.encode()).hexdigest()
    # background gradient
    h1 = int(digest[0:2], 16) % 360
    h2 = (h1 + 60) % 360
    # initials
    initials = chr(65 + (idx * 7) % 26) + chr(65 + (idx * 13 + 11) % 26)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
<defs><linearGradient id="g{idx}" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="hsl({h1},65%,55%)"/>
<stop offset="1" stop-color="hsl({h2},65%,40%)"/>
</linearGradient></defs>
<rect width="200" height="200" fill="url(#g{idx})"/>
<circle cx="100" cy="80" r="36" fill="#fff" fill-opacity="0.18"/>
<path d="M40 200 Q40 130 100 130 Q160 130 160 200 Z" fill="#fff" fill-opacity="0.18"/>
<text x="100" y="118" text-anchor="middle" font-family="Helvetica" font-size="56" font-weight="700" fill="#fff">{initials}</text>
</svg>'''


# -----------------------------------------------------------------------
# Conference banners
# -----------------------------------------------------------------------

CONFERENCES = [
    ("neurips", "NeurIPS", "Neural Information Processing Systems", "#5e3ec5"),
    ("icml", "ICML", "International Conference on Machine Learning", "#1b6ec2"),
    ("iclr", "ICLR", "International Conference on Learning Representations", "#0e8a6a"),
    ("acl", "ACL", "Association for Computational Linguistics", "#b13434"),
    ("emnlp", "EMNLP", "Empirical Methods in NLP", "#7a3da6"),
    ("cvpr", "CVPR", "Computer Vision and Pattern Recognition", "#1f6f4a"),
    ("iccv", "ICCV", "International Conference on Computer Vision", "#185680"),
    ("aaai", "AAAI", "AAAI Conference on Artificial Intelligence", "#a64a1a"),
    ("kdd", "KDD", "Knowledge Discovery and Data Mining", "#5a4f24"),
    ("siggraph", "SIGGRAPH", "Special Interest Group on Computer Graphics", "#3a4e8c"),
]


def conf_banner_svg(slug: str, abbr: str, full: str, color: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 180" width="600" height="180">
<defs><linearGradient id="bg_{slug}" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{color}"/>
<stop offset="1" stop-color="#1b1b2e"/>
</linearGradient></defs>
<rect width="600" height="180" fill="url(#bg_{slug})"/>
<g opacity="0.18" stroke="#fff">
<circle cx="510" cy="40" r="50" fill="none" stroke-width="1.2"/>
<circle cx="510" cy="40" r="70" fill="none" stroke-width="1.2"/>
<circle cx="510" cy="40" r="90" fill="none" stroke-width="1.2"/>
</g>
<text x="30" y="78" font-family="Helvetica" font-size="48" font-weight="800" fill="#fff">{abbr}</text>
<text x="30" y="110" font-family="Helvetica" font-size="15" fill="#fff" fill-opacity="0.85">{full}</text>
<text x="30" y="150" font-family="Helvetica" font-size="11" fill="#fff" fill-opacity="0.7">official conference banner — color palette: {color}</text>
</svg>'''


# -----------------------------------------------------------------------
# Category banners
# -----------------------------------------------------------------------

CATEGORY_BANNERS = [
    ("cs",        "Computer Science",          "algorithms / systems / AI",     "#b31b1b"),
    ("math",      "Mathematics",               "analysis / algebra / topology", "#1a4f7a"),
    ("physics",   "Physics",                   "classical / quantum / astro",    "#3a2f7a"),
    ("astro-ph",  "Astrophysics",              "cosmology / galaxies / stars",   "#0c1b3a"),
    ("cond-mat",  "Condensed Matter",          "materials / quantum gas",       "#1f4f3a"),
    ("quant-ph",  "Quantum Physics",           "qubits / entanglement",         "#5a1f7a"),
    ("q-bio",     "Quantitative Biology",      "genomics / neurons",            "#1a6f4a"),
    ("q-fin",     "Quantitative Finance",      "pricing / risk / portfolios",   "#7a5a1a"),
    ("stat",      "Statistics",                "Bayesian / methodology / ML",    "#1a5f6f"),
    ("eess",      "Electrical Engineering",    "signals / imaging / control",   "#7a3a1a"),
    ("econ",      "Economics",                 "econometrics / theory",         "#4a3a1a"),
]


def category_banner_svg(code: str, name: str, sub: str, color: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 160" width="720" height="160">
<defs><linearGradient id="cb_{code.replace('-','_').replace('.','_')}" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{color}"/>
<stop offset="1" stop-color="#0c0c14"/>
</linearGradient></defs>
<rect width="720" height="160" fill="url(#cb_{code.replace('-','_').replace('.','_')})"/>
<g opacity="0.2" stroke="#fff" fill="none" stroke-width="0.6">
{"".join(f'<line x1="0" y1="{i*12}" x2="720" y2="{i*12}"/>' for i in range(14))}
</g>
<text x="32" y="72" font-family="Helvetica" font-size="36" font-weight="700" fill="#fff">{name}</text>
<text x="32" y="100" font-family="Helvetica" font-size="14" fill="#fff" fill-opacity="0.8">{sub}</text>
<text x="32" y="130" font-family="Helvetica" font-size="11" fill="#fff" fill-opacity="0.55">arXiv category · {code}</text>
</svg>'''


# -----------------------------------------------------------------------
# Submission wizard step diagram
# -----------------------------------------------------------------------

def submit_step_diagram_svg() -> str:
    steps = ["metadata", "authors", "abstract", "files", "license", "preview", "submit"]
    out = []
    for i, s in enumerate(steps):
        x = 30 + i * 90
        out.append(f'<circle cx="{x}" cy="60" r="22" fill="#b31b1b"/>')
        out.append(f'<text x="{x}" y="65" text-anchor="middle" font-family="Helvetica" font-size="13" font-weight="700" fill="#fff">{i+1}</text>')
        out.append(f'<text x="{x}" y="105" text-anchor="middle" font-family="Helvetica" font-size="11" fill="#222">{s}</text>')
        if i < len(steps) - 1:
            out.append(f'<line x1="{x+22}" y1="60" x2="{x+68}" y2="60" stroke="#b31b1b" stroke-width="2"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 140" width="700" height="140">
<rect width="100%" height="100%" fill="#fff8f8"/>
{"".join(out)}
</svg>'''


def submit_dropzone_svg() -> str:
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 220" width="600" height="220">
<rect x="6" y="6" width="588" height="208" rx="14" fill="#fbfbff" stroke="#b31b1b" stroke-width="2" stroke-dasharray="8 5"/>
<g transform="translate(300 90)" font-family="Helvetica" text-anchor="middle">
<path d="M-22 -20 L0 -42 L22 -20 M0 -42 L0 16" stroke="#b31b1b" stroke-width="3" fill="none" stroke-linecap="round"/>
<rect x="-30" y="22" width="60" height="6" rx="2" fill="#b31b1b"/>
<text y="60" font-size="14" fill="#222">drop your LaTeX bundle here</text>
<text y="80" font-size="11" fill="#666">or click to browse · accepts .tex / .tar.gz / .zip ≤ 50MB</text>
</g>
</svg>'''


# -----------------------------------------------------------------------
# PDF cover thumbnail
# -----------------------------------------------------------------------

def pdf_cover_svg(seed: str) -> str:
    """Mock first page of a PDF (title + abstract layout)."""
    pal = _palette(seed)
    lines = []
    for i in range(14):
        w = 200 + (_h(seed, i) % 130)
        lines.append(f'<rect x="40" y="{105 + i * 16}" width="{w}" height="6" fill="#cfcfcf"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 380" width="300" height="380">
<rect width="100%" height="100%" fill="#fff" stroke="#aaa"/>
<rect x="0" y="0" width="300" height="8" fill="{pal[0]}"/>
<text x="150" y="45" text-anchor="middle" font-family="Helvetica" font-size="16" font-weight="700" fill="#222">preprint</text>
<text x="150" y="72" text-anchor="middle" font-family="Helvetica" font-size="11" fill="#666">authors et al., arXiv preprint</text>
<line x1="40" y1="92" x2="260" y2="92" stroke="#bbb"/>
{"".join(lines)}
<text x="150" y="360" text-anchor="middle" font-family="Helvetica" font-size="9" fill="#999">first page · click to open inline reader</text>
</svg>'''


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def bootstrap(force: bool = False) -> dict:
    """Generate the full visual-asset pool into static/images/.

    Idempotent: if the figure pool already exists and `force` is False,
    return early. Called from app.py at process start so the image bundle
    is always in place before the first request.
    """
    figs_dir = OUT / "figures"
    head_dir = OUT / "headshots"
    conf_dir = OUT / "conferences"
    cat_dir = OUT / "categories"
    cover_dir = OUT / "pdf_covers"

    # Sentinel — last asset emitted by the run. If present, treat as cached.
    sentinel = cover_dir / "cover_15.svg"
    if sentinel.exists() and not force:
        return {"cached": True, "out": str(OUT)}

    for d in (figs_dir, head_dir, conf_dir, cat_dir, cover_dir):
        d.mkdir(parents=True, exist_ok=True)

    figure_count = 0
    for style_name, fn in FIGURE_STYLES:
        for v in range(8):
            seed = f"{style_name}_v{v}"
            (figs_dir / f"{style_name}_{v:02d}.svg").write_text(fn(seed))
            figure_count += 1

    for i in range(24):
        (head_dir / f"avatar_{i:02d}.svg").write_text(avatar_svg(i))

    for slug, abbr, full, color in CONFERENCES:
        (conf_dir / f"{slug}.svg").write_text(conf_banner_svg(slug, abbr, full, color))

    for code, name, sub, color in CATEGORY_BANNERS:
        (cat_dir / f"{code}.svg").write_text(category_banner_svg(code, name, sub, color))

    (OUT / "submit_step_diagram.svg").write_text(submit_step_diagram_svg())
    (OUT / "submit_dropzone.svg").write_text(submit_dropzone_svg())

    for i in range(16):
        (cover_dir / f"cover_{i:02d}.svg").write_text(pdf_cover_svg(f"cover_{i}"))

    return {
        "cached": False,
        "out": str(OUT),
        "figures": figure_count,
        "headshots": 24,
        "conferences": len(CONFERENCES),
        "categories": len(CATEGORY_BANNERS),
        "covers": 16,
    }


def main():
    res = bootstrap(force=True)
    for k, v in res.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
