"""Harvest image filenames via category-page HTML scraping (avoids API rate limit)."""
import os
import sys
import re
import time
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
IMG_ROOT = os.path.join(BASE, "static", "images")
CATALOG_FILE = os.path.join(BASE, "_image_catalog.json")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}

CATALOGS = {
    "anatomy": [
        ("Anatomy_of_the_human_heart", 20),
        ("Heart_diagrams", 12),
        ("Lungs", 15),
        ("Human_lungs", 10),
        ("Brain", 18),
        ("Human_brain", 12),
        ("Liver", 12),
        ("Kidney", 12),
        ("Stomach", 10),
        ("Digestive_system", 15),
        ("Human_anatomy", 20),
        ("Diagrams_of_human_anatomy", 18),
        ("Endocrine_system", 10),
        ("Human_skeleton", 14),
        ("Eye", 10),
        ("Human_eye", 10),
        ("Ear", 8),
        ("Skin", 8),
        ("Pancreas", 8),
        ("Thyroid", 8),
        ("Gallbladder", 6),
        ("Spinal_cord", 8),
        ("Circulatory_system", 12),
        ("Respiratory_system", 12),
        ("Urinary_system", 8),
        ("Nervous_system", 12),
        ("Muscular_system", 8),
        ("Reproductive_system", 8),
        ("Diabetes_mellitus", 8),
        ("Joints", 8),
        ("Bones", 8),
    ],
    "departments": [
        ("Mayo_Clinic", 15),
        ("Mayo_Clinic_Hospital,_Rochester", 10),
        ("Saint_Marys_Hospital,_Rochester", 8),
        ("Plummer_Building", 8),
        ("Mayo_Building", 8),
        ("Operating_room", 12),
        ("Operating_theatres", 8),
        ("Hospital_buildings", 12),
        ("Hospitals", 15),
        ("Laboratory", 12),
        ("Magnetic_resonance_imaging", 10),
        ("Computed_tomography", 10),
        ("Ultrasound", 10),
        ("Radiology", 10),
        ("Stethoscopes", 6),
        ("Hospital_rooms", 10),
        ("Medical_equipment", 12),
        ("Intensive_care_unit", 8),
        ("Emergency_department", 8),
        ("Nurses", 10),
    ],
    "procedures": [
        ("Surgery", 15),
        ("Surgeries", 8),
        ("Endoscopy", 10),
        ("Colonoscopy", 8),
        ("Mammography", 6),
        ("Echocardiography", 6),
        ("Electrocardiography", 8),
        ("Surgical_instruments", 10),
        ("Laparoscopy", 8),
        ("Angiography", 6),
        ("Bronchoscopy", 6),
        ("Dialysis", 6),
        ("Vaccination", 8),
        ("Blood_test", 6),
        ("Robot-assisted_surgery", 6),
        ("Open_heart_surgery", 6),
        ("Stents", 4),
    ],
    "wellness": [
        ("Salad", 12),
        ("Mediterranean_cuisine", 10),
        ("Fruits", 12),
        ("Vegetables", 12),
        ("Whole_grain_bread", 6),
        ("Olive_oil", 6),
        ("Running", 10),
        ("Yoga", 10),
        ("Cycling", 10),
        ("Swimming", 10),
        ("Hiking", 10),
        ("Meditation", 8),
        ("Sleep", 6),
        ("Walking", 6),
        ("Pregnancy", 8),
        ("Cooking", 10),
        ("Smoothies", 6),
        ("Tea", 6),
        ("Breakfast", 8),
        ("Apples", 6),
        ("Berries", 6),
        ("Nuts_(food)", 4),
        ("Whole_grains", 4),
    ],
    "articles": [
        ("Healthy_food", 10),
        ("Family_meals", 8),
        ("Picnic", 6),
        ("Bicycles", 8),
        ("Sneakers", 6),
        ("Mindfulness", 6),
        ("Mother_and_child", 8),
        ("Senior_citizens", 8),
        ("Sunsets", 6),
        ("Mountains", 6),
        ("Beaches", 6),
        ("Sunrise", 6),
        ("Coffee", 6),
        ("Fish_as_food", 6),
        ("Bowls_of_food", 6),
        ("Trail_(path)", 4),
        ("Parks", 8),
        ("Lakes", 6),
    ],
    "doctors": [
        ("Female_physicians", 12),
        ("Male_physicians", 12),
        ("Physicians_of_the_United_States", 18),
        ("African-American_physicians", 12),
        ("Asian_American_physicians", 10),
        ("Physicians", 15),
        ("Surgeons", 15),
        ("Doctors", 15),
        ("Doctors_in_hospitals", 8),
        ("People_wearing_scrubs", 8),
        ("People_in_white_coats", 8),
        ("Hospital_staff", 8),
        ("Nurses", 10),
        ("Medical_education", 6),
    ],
    "stories": [
        ("Portraits_of_women", 10),
        ("Portraits_of_men", 10),
        ("Smiling_people", 10),
        ("Families", 8),
        ("Senior_citizens", 8),
        ("Children", 6),
        ("Couples", 4),
        ("Patients", 6),
    ],
    "cancer": [
        ("Cancer", 12),
        ("Oncology", 8),
        ("Mammograms", 6),
        ("Radiation_therapy", 8),
        ("Chemotherapy", 6),
        ("Pink_ribbon", 6),
        ("Lung_cancer", 6),
        ("Breast_cancer", 6),
        ("Skin_cancer", 4),
        ("Tumors", 6),
        ("Leukemia", 4),
        ("Lymphoma", 4),
    ],
    "brand": [
        ("Mayo_Clinic", 12),
        ("Plummer_Building", 8),
        ("Mayo_Building", 6),
        ("Saint_Marys_Hospital,_Rochester", 6),
        ("Gonda_Building", 4),
        ("William_James_Mayo", 4),
        ("Charles_Horace_Mayo", 4),
        ("William_Worrall_Mayo", 4),
    ],
    "locations": [
        ("Rochester,_Minnesota", 15),
        ("Phoenix,_Arizona", 12),
        ("Jacksonville,_Florida", 12),
        ("Mayo_Clinic_Hospital,_Phoenix", 8),
        ("Mayo_Clinic_Hospital,_Jacksonville", 8),
        ("Mayo_Clinic_Hospital,_Rochester", 8),
        ("Camelback_Mountain", 4),
        ("Mississippi_River", 6),
        ("St._Johns_River", 4),
        ("Scottsdale,_Arizona", 6),
        ("Minnesota", 8),
        ("Florida", 6),
        ("Arizona", 6),
    ],
    "symptoms": [
        ("Headache", 8),
        ("Cough", 4),
        ("Skin_diseases", 10),
        ("Rashes", 6),
        ("Back_pain", 6),
        ("Sore_throat", 4),
        ("Pain", 6),
        ("Dizziness", 4),
        ("Allergies", 6),
        ("Fatigue", 4),
    ],
    "trials": [
        ("Medical_research", 10),
        ("Pharmacology", 6),
        ("Laboratories", 10),
        ("Scientists", 12),
        ("Microscopes", 8),
        ("Pipettes", 6),
        ("Petri_dishes", 4),
        ("Test_tubes", 6),
        ("Research", 8),
    ],
}

FILE_RE = re.compile(r'href="/wiki/(File:[^"]+?\.(?:jpg|jpeg|JPG|JPEG|png|PNG|svg|SVG))"')


def harvest_category_html(category):
    """Scrape category HTML page for file names."""
    url = f"https://commons.wikimedia.org/wiki/Category:{category}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as r:
            html = r.read().decode("utf-8", errors="ignore")
        seen = []
        for m in FILE_RE.finditer(html):
            name = m.group(1)[len("File:"):]
            name = urllib.parse.unquote(name)
            if name not in seen:
                seen.append(name)
        return seen
    except Exception as e:
        print(f"  [html] {category}: {e}", file=sys.stderr, flush=True)
        return []


def harvest():
    catalog = {}
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE) as f:
            catalog = json.load(f)
    for subdir, cats in CATALOGS.items():
        sub = catalog.setdefault(subdir, [])
        existing = set(sub)
        for category, want_n in cats:
            marker = f"_html:{category}"
            if marker in existing:
                continue
            time.sleep(1.2)
            titles = harvest_category_html(category)
            picked = 0
            for t in titles:
                if t in existing:
                    continue
                sub.append(t)
                existing.add(t)
                picked += 1
                if picked >= want_n:
                    break
            sub.append(marker)
            existing.add(marker)
            print(f"[{subdir}] {category}: +{picked}", flush=True)
            with open(CATALOG_FILE, "w") as f:
                json.dump(catalog, f)
    return catalog


def safe_basename(title):
    base = title.replace(" ", "_").replace("/", "_").replace("%2C", ",")
    base = "".join(c for c in base if c.isalnum() or c in "._-")
    return base or "img.jpg"


def download(args):
    subdir, title = args
    fname = safe_basename(title)
    dest = os.path.join(IMG_ROOT, subdir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 2000:
        return True
    width = "" if title.lower().endswith(".svg") else "&width=800"
    url = (
        "https://commons.wikimedia.org/w/index.php?title=Special:FilePath/"
        + urllib.parse.quote(title.replace(" ", "_")) + width
    )
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=40) as r:
                content = r.read()
            if len(content) < 2000:
                return False
            with open(dest, "wb") as f:
                f.write(content)
            return True
        except Exception:
            time.sleep(1.5 + attempt * 2)
    return False


def download_phase():
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)
    jobs = []
    for subdir, titles in catalog.items():
        os.makedirs(os.path.join(IMG_ROOT, subdir), exist_ok=True)
        for t in titles:
            if t.startswith(("_from:", "_html:")):
                continue
            jobs.append((subdir, t))
    print(f"Phase 2: {len(jobs)} downloads.", flush=True)
    ok = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        for r in ex.map(download, jobs):
            if r:
                ok += 1
    print(f"Downloaded ok: {ok}/{len(jobs)}", flush=True)


def show_counts():
    grand = 0
    for subdir in CATALOGS.keys():
        d = os.path.join(IMG_ROOT, subdir)
        if not os.path.isdir(d):
            continue
        c = sum(1 for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)))
        grand += c
        print(f"  {subdir}: {c}", flush=True)
    print(f"GRAND TOTAL: {grand}", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("harvest", "all"):
        print("Phase 1...", flush=True)
        harvest()
    if mode in ("download", "all"):
        download_phase()
    show_counts()


if __name__ == "__main__":
    main()
