"""Generate procedurally-drawn SVG placeholder images for the categories that
the Wikimedia fetcher couldn't fill (symptoms, doctor headshots, etc.).

Each SVG is a real image file checked in to static/images/. The output is
deterministic — same content for the same key.
"""
import os
import hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "static", "images")


PALETTES = [
    ("#0064a2", "#e6f1f8"),  # mayo blue
    ("#003b71", "#f0f4f8"),  # darker blue
    ("#f5b400", "#fff7e0"),  # yellow
    ("#5b6770", "#e8eaed"),  # gray
    ("#c8102e", "#fde0e3"),  # red
    ("#1c855c", "#dff2e6"),  # green
    ("#7e3a93", "#f4e8f7"),  # purple
    ("#cc6611", "#fdecd9"),  # orange
]


def doctor_svg(key):
    """Generate a stylized doctor avatar SVG."""
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    palette = PALETTES[h % len(PALETTES)]
    fg, bg = palette
    initial = key[0].upper() if key else "?"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240">
  <rect width="240" height="240" fill="{bg}"/>
  <circle cx="120" cy="100" r="48" fill="{fg}"/>
  <path d="M40 240 Q40 160 120 160 Q200 160 200 240 Z" fill="{fg}"/>
  <text x="120" y="232" text-anchor="middle" font-family="Georgia, serif" font-size="20" fill="{bg}" font-weight="700">Dr.</text>
  <text x="120" y="115" text-anchor="middle" font-family="Georgia, serif" font-size="56" fill="{bg}" font-weight="700">{initial}</text>
</svg>"""


def symptom_svg(name):
    """Generate a stylized symptom illustration."""
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    palette = PALETTES[h % len(PALETTES)]
    fg, bg = palette
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 280" width="400" height="280">
  <rect width="400" height="280" fill="{bg}"/>
  <g transform="translate(200, 140)">
    <circle cx="0" cy="-40" r="30" fill="{fg}" opacity="0.85"/>
    <rect x="-12" y="-15" width="24" height="80" rx="6" fill="{fg}" opacity="0.85"/>
    <rect x="-46" y="0" width="20" height="50" rx="4" fill="{fg}" opacity="0.65"/>
    <rect x="26" y="0" width="20" height="50" rx="4" fill="{fg}" opacity="0.65"/>
    <rect x="-15" y="55" width="12" height="40" rx="3" fill="{fg}" opacity="0.75"/>
    <rect x="3" y="55" width="12" height="40" rx="3" fill="{fg}" opacity="0.75"/>
  </g>
  <text x="200" y="265" text-anchor="middle" font-family="Source Serif 4, Georgia, serif" font-size="16" fill="{fg}" font-weight="700">{name[:40].title()}</text>
</svg>"""


def story_svg(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    palette = PALETTES[h % len(PALETTES)]
    fg, bg = palette
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320" width="320" height="320">
  <rect width="320" height="320" fill="{bg}"/>
  <circle cx="160" cy="120" r="56" fill="{fg}"/>
  <path d="M50 320 Q50 200 160 200 Q270 200 270 320 Z" fill="{fg}"/>
  <text x="160" y="140" text-anchor="middle" font-family="Georgia, serif" font-size="60" fill="{bg}" font-weight="700">{name[0].upper() if name else 'P'}</text>
</svg>"""


def brand_svg(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    palette = PALETTES[h % len(PALETTES)]
    fg, bg = palette
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 320" width="600" height="320">
  <defs>
    <linearGradient id="g{h%9}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{fg}"/>
      <stop offset="100%" stop-color="{bg}"/>
    </linearGradient>
  </defs>
  <rect width="600" height="320" fill="url(#g{h%9})"/>
  <g transform="translate(300, 140)">
    <circle r="56" fill="white" stroke="{fg}" stroke-width="6"/>
    <text x="0" y="20" text-anchor="middle" font-family="Georgia, serif" font-size="56" fill="{fg}" font-weight="700">M</text>
  </g>
  <text x="300" y="240" text-anchor="middle" font-family="Source Serif 4, Georgia, serif" font-size="22" fill="white" font-weight="700">Mayo Clinic</text>
  <text x="300" y="265" text-anchor="middle" font-family="sans-serif" font-size="13" fill="white" opacity="0.9" letter-spacing="2">{name[:48].upper()}</text>
</svg>"""


def location_svg(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    palette = PALETTES[h % len(PALETTES)]
    fg, bg = palette
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 320" width="600" height="320">
  <rect width="600" height="320" fill="{bg}"/>
  <rect x="100" y="100" width="120" height="180" fill="{fg}" opacity="0.85"/>
  <rect x="240" y="60" width="140" height="220" fill="{fg}"/>
  <rect x="400" y="120" width="100" height="160" fill="{fg}" opacity="0.85"/>
  <rect x="0" y="280" width="600" height="40" fill="{fg}" opacity="0.5"/>
  <text x="300" y="40" text-anchor="middle" font-family="Source Serif 4, Georgia, serif" font-size="22" fill="{fg}" font-weight="700">{name[:48]}</text>
  <text x="300" y="305" text-anchor="middle" font-family="sans-serif" font-size="13" fill="white" font-weight="600">MAYO CLINIC</text>
</svg>"""


def cancer_svg(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200">
  <rect width="400" height="200" fill="#f4e8f7"/>
  <g transform="translate(200, 100)">
    <path d="M -40 0 Q -40 -30 0 -30 Q 40 -30 40 0 Q 40 30 0 30 Q -40 30 -40 0 Z" fill="#7e3a93" opacity="0.85"/>
    <circle r="50" fill="none" stroke="#7e3a93" stroke-width="3" opacity="0.5"/>
    <circle r="70" fill="none" stroke="#7e3a93" stroke-width="2" opacity="0.3"/>
  </g>
  <text x="200" y="190" text-anchor="middle" font-family="serif" font-size="16" fill="#7e3a93" font-weight="700">{name}</text>
</svg>"""


def write(subdir, basename, content):
    p = os.path.join(IMG, subdir)
    os.makedirs(p, exist_ok=True)
    f = os.path.join(p, basename)
    if not os.path.exists(f):
        with open(f, "w") as fh:
            fh.write(content)


def main():
    # 1. Doctor avatars — generate placeholder for all 110 doctors using their slug
    import sqlite3
    conn = sqlite3.connect(os.path.join(BASE, "instance", "mayo_clinic.db"))
    cur = conn.execute("SELECT slug, name FROM doctor")
    doctors = cur.fetchall()
    conn.close()
    for slug, name in doctors:
        write("doctors", f"_gen_{slug}.svg", doctor_svg(name))

    # 2. Symptom illustrations — for each symptom slug
    conn = sqlite3.connect(os.path.join(BASE, "instance", "mayo_clinic.db"))
    cur = conn.execute("SELECT slug, name FROM symptom")
    symptoms = cur.fetchall()
    conn.close()
    for slug, name in symptoms:
        write("symptoms", f"_gen_{slug}.svg", symptom_svg(name))

    # 3. Story portrait placeholders
    stories = ["kevin", "maria", "james", "priya", "david", "emma", "samuel",
               "aiko", "luis", "hannah", "malcolm", "rebecca"]
    for s in stories:
        write("stories", f"_gen_{s}.svg", story_svg(s.capitalize()))

    # 4. Brand placeholders
    brand_names = ["Mayo Clinic", "Saint Marys Hospital", "Plummer Building",
                   "Gonda Building", "Mayo Building", "Charlton Building",
                   "Cancer Center", "Heart Center", "Neuro Center",
                   "Children's Center"]
    for n in brand_names:
        slug = n.lower().replace(" ", "_").replace("'", "")
        write("brand", f"_gen_{slug}.svg", brand_svg(n))

    # 5. Location placeholders
    locs = ["Rochester Minnesota", "Phoenix Arizona", "Jacksonville Florida",
            "Mayo Clinic Hospital Rochester", "Mayo Clinic Hospital Phoenix",
            "Mayo Clinic Hospital Jacksonville", "Saint Marys Hospital",
            "Methodist Hospital", "Davis Building"]
    for n in locs:
        slug = n.lower().replace(" ", "_")
        write("locations", f"_gen_{slug}.svg", location_svg(n))

    # 6. Cancer-type illustrations
    cancers = ["Breast Cancer", "Lung Cancer", "Colon Cancer", "Prostate Cancer",
               "Pancreatic Cancer", "Ovarian Cancer", "Liver Cancer", "Kidney Cancer",
               "Bladder Cancer", "Thyroid Cancer", "Melanoma", "Brain Tumor",
               "Head and Neck Cancer", "Leukemia", "Lymphoma", "Multiple Myeloma",
               "Sarcoma", "Esophageal Cancer", "Stomach Cancer", "Cervical Cancer",
               "Endometrial Cancer", "Testicular Cancer", "Bone Cancer", "Pediatric Cancer"]
    for n in cancers:
        slug = n.lower().replace(" ", "_")
        write("cancer", f"_gen_{slug}.svg", cancer_svg(n))

    # 7. Anatomy supplemental
    anatomy_topics = ["Heart", "Lung", "Brain", "Liver", "Kidney", "Stomach", "Pancreas",
                      "Thyroid", "Spleen", "Bladder", "Skeleton", "Muscle System",
                      "Nervous System", "Circulatory System", "Digestive System",
                      "Endocrine System", "Reproductive System", "Eye", "Ear", "Skin"]
    for n in anatomy_topics:
        slug = n.lower().replace(" ", "_")
        # use the symptom_svg shape but in blue palette by name hash
        write("anatomy", f"_gen_{slug}.svg", symptom_svg(n))

    print("Counts after placeholder generation:")
    for d in sorted(os.listdir(IMG)):
        full = os.path.join(IMG, d)
        if os.path.isdir(full):
            print(f"  {d}: {sum(1 for f in os.listdir(full) if os.path.isfile(os.path.join(full, f)))}")


if __name__ == "__main__":
    main()
