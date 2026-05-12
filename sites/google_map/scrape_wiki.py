"""
Wikipedia scraper for place imagery. Downloads images for famous
places worldwide: landmarks, hotels, restaurants, parks, museums, etc.

Pattern: go to the Wikipedia article, extract img srcs, rewrite thumb
URLs to originals, download.
"""
import asyncio
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

# Lazy import: playwright is only needed when this module is run as a script
# (to actually scrape). Importing from seed_data at Flask startup should not
# require playwright to be installed.
if __name__ == "__main__":
    from playwright.async_api import async_playwright
    sys.stdout.reconfigure(line_buffering=True)

BASE_DIR = Path(__file__).parent
PLACE_DIR = BASE_DIR / "static/images/places"
CITY_DIR = BASE_DIR / "static/images/cities"
PLACE_DIR.mkdir(parents=True, exist_ok=True)
CITY_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# (slug, wikipedia_title, category, city_slug)
PLACES = [
    # === LANDMARKS / ATTRACTIONS ===
    ("eiffel-tower", "Eiffel_Tower", "attractions", "paris"),
    ("statue-of-liberty", "Statue_of_Liberty", "attractions", "new-york"),
    ("empire-state-building", "Empire_State_Building", "attractions", "new-york"),
    ("times-square", "Times_Square", "attractions", "new-york"),
    ("brooklyn-bridge", "Brooklyn_Bridge", "attractions", "new-york"),
    ("central-park", "Central_Park", "parks", "new-york"),
    ("one-world-trade-center", "One_World_Trade_Center", "attractions", "new-york"),
    ("colosseum", "Colosseum", "attractions", "rome"),
    ("roman-forum", "Roman_Forum", "attractions", "rome"),
    ("pantheon-rome", "Pantheon,_Rome", "attractions", "rome"),
    ("trevi-fountain", "Trevi_Fountain", "attractions", "rome"),
    ("vatican-city", "Vatican_City", "attractions", "rome"),
    ("sagrada-familia", "Sagrada_Fam%C3%ADlia", "attractions", "barcelona"),
    ("park-guell", "Park_G%C3%BCell", "parks", "barcelona"),
    ("casa-batllo", "Casa_Batll%C3%B3", "attractions", "barcelona"),
    ("big-ben", "Big_Ben", "attractions", "london"),
    ("tower-bridge", "Tower_Bridge", "attractions", "london"),
    ("london-eye", "London_Eye", "attractions", "london"),
    ("buckingham-palace", "Buckingham_Palace", "attractions", "london"),
    ("westminster-abbey", "Westminster_Abbey", "attractions", "london"),
    ("tower-of-london", "Tower_of_London", "attractions", "london"),
    ("british-museum", "British_Museum", "museums", "london"),
    ("natural-history-museum-london", "Natural_History_Museum,_London", "museums", "london"),
    ("tate-modern", "Tate_Modern", "museums", "london"),
    ("louvre", "Louvre", "museums", "paris"),
    ("notre-dame-de-paris", "Notre-Dame_de_Paris", "attractions", "paris"),
    ("arc-de-triomphe", "Arc_de_Triomphe", "attractions", "paris"),
    ("musee-d-orsay", "Mus%C3%A9e_d%27Orsay", "museums", "paris"),
    ("montmartre", "Montmartre", "attractions", "paris"),
    ("sacre-coeur", "Sacr%C3%A9-C%C5%93ur,_Paris", "attractions", "paris"),
    ("palace-of-versailles", "Palace_of_Versailles", "attractions", "paris"),
    ("great-wall-of-china", "Great_Wall_of_China", "attractions", "beijing"),
    ("forbidden-city", "Forbidden_City", "attractions", "beijing"),
    ("temple-of-heaven", "Temple_of_Heaven", "attractions", "beijing"),
    ("summer-palace", "Summer_Palace", "attractions", "beijing"),
    ("tiananmen-square", "Tiananmen_Square", "attractions", "beijing"),
    ("burj-khalifa", "Burj_Khalifa", "attractions", "dubai"),
    ("palm-jumeirah", "Palm_Jumeirah", "attractions", "dubai"),
    ("dubai-mall", "The_Dubai_Mall", "shopping", "dubai"),
    ("burj-al-arab", "Burj_Al_Arab", "hotels", "dubai"),
    ("sydney-opera-house", "Sydney_Opera_House", "attractions", "sydney"),
    ("sydney-harbour-bridge", "Sydney_Harbour_Bridge", "attractions", "sydney"),
    ("bondi-beach", "Bondi_Beach", "parks", "sydney"),
    ("taj-mahal", "Taj_Mahal", "attractions", "agra"),
    ("gateway-of-india", "Gateway_of_India", "attractions", "mumbai"),
    ("tokyo-tower", "Tokyo_Tower", "attractions", "tokyo"),
    ("tokyo-skytree", "Tokyo_Skytree", "attractions", "tokyo"),
    ("sensoji", "Sens%C5%8D-ji", "attractions", "tokyo"),
    ("shibuya-crossing", "Shibuya_Crossing", "attractions", "tokyo"),
    ("meiji-shrine", "Meiji_Shrine", "attractions", "tokyo"),
    ("fushimi-inari", "Fushimi_Inari-taisha", "attractions", "kyoto"),
    ("kinkakuji", "Kinkaku-ji", "attractions", "kyoto"),
    ("ginkakuji", "Ginkaku-ji", "attractions", "kyoto"),
    ("golden-gate-bridge", "Golden_Gate_Bridge", "attractions", "san-francisco"),
    ("alcatraz", "Alcatraz_Island", "attractions", "san-francisco"),
    ("fishermans-wharf", "Fisherman%27s_Wharf,_San_Francisco", "attractions", "san-francisco"),
    ("lombard-street", "Lombard_Street_(San_Francisco)", "attractions", "san-francisco"),
    ("golden-gate-park", "Golden_Gate_Park", "parks", "san-francisco"),
    ("hollywood-sign", "Hollywood_Sign", "attractions", "los-angeles"),
    ("griffith-observatory", "Griffith_Observatory", "attractions", "los-angeles"),
    ("santa-monica-pier", "Santa_Monica_Pier", "attractions", "los-angeles"),
    ("venice-beach", "Venice,_Los_Angeles", "attractions", "los-angeles"),
    ("getty-center", "Getty_Center", "museums", "los-angeles"),
    ("willis-tower", "Willis_Tower", "attractions", "chicago"),
    ("millennium-park", "Millennium_Park", "parks", "chicago"),
    ("navy-pier", "Navy_Pier", "attractions", "chicago"),
    ("art-institute-of-chicago", "Art_Institute_of_Chicago", "museums", "chicago"),
    ("space-needle", "Space_Needle", "attractions", "seattle"),
    ("pike-place-market", "Pike_Place_Market", "shopping", "seattle"),
    ("chihuly-garden", "Chihuly_Garden_and_Glass", "museums", "seattle"),
    ("fenway-park", "Fenway_Park", "attractions", "boston"),
    ("freedom-trail", "Freedom_Trail", "attractions", "boston"),
    ("harvard-yard", "Harvard_University", "attractions", "boston"),
    ("las-vegas-strip", "Las_Vegas_Strip", "attractions", "las-vegas"),
    ("bellagio", "Bellagio_(resort)", "hotels", "las-vegas"),
    ("caesars-palace", "Caesars_Palace", "hotels", "las-vegas"),
    ("venetian-resort", "The_Venetian_Resort_Las_Vegas", "hotels", "las-vegas"),
    ("golden-gate-park-2", "Yosemite_National_Park", "parks", "san-francisco"),
    ("grand-canyon", "Grand_Canyon", "parks", "las-vegas"),
    ("marina-bay-sands", "Marina_Bay_Sands", "hotels", "singapore"),
    ("gardens-by-the-bay", "Gardens_by_the_Bay", "parks", "singapore"),
    ("merlion", "Merlion", "attractions", "singapore"),
    ("raffles-hotel", "Raffles_Hotel", "hotels", "singapore"),
    ("brandenburg-gate", "Brandenburg_Gate", "attractions", "berlin"),
    ("reichstag", "Reichstag_building", "attractions", "berlin"),
    ("berlin-wall", "Berlin_Wall", "attractions", "berlin"),
    ("pergamon-museum", "Pergamon_Museum", "museums", "berlin"),
    ("museum-island", "Museum_Island", "museums", "berlin"),
    ("rijksmuseum", "Rijksmuseum", "museums", "amsterdam"),
    ("van-gogh-museum", "Van_Gogh_Museum", "museums", "amsterdam"),
    ("anne-frank-house", "Anne_Frank_House", "museums", "amsterdam"),
    ("vondelpark", "Vondelpark", "parks", "amsterdam"),
    ("canal-ring", "Canals_of_Amsterdam", "attractions", "amsterdam"),
    ("prado", "Museo_del_Prado", "museums", "madrid"),
    ("royal-palace-madrid", "Royal_Palace_of_Madrid", "attractions", "madrid"),
    ("retiro-park", "Buen_Retiro_Park", "parks", "madrid"),
    ("plaza-mayor-madrid", "Plaza_Mayor,_Madrid", "attractions", "madrid"),
    ("hagia-sophia", "Hagia_Sophia", "attractions", "istanbul"),
    ("blue-mosque", "Sultan_Ahmed_Mosque", "attractions", "istanbul"),
    ("topkapi-palace", "Topkap%C4%B1_Palace", "attractions", "istanbul"),
    ("grand-bazaar", "Grand_Bazaar,_Istanbul", "shopping", "istanbul"),
    ("acropolis", "Acropolis_of_Athens", "attractions", "athens"),
    ("parthenon", "Parthenon", "attractions", "athens"),
    ("charles-bridge", "Charles_Bridge", "attractions", "prague"),
    ("prague-castle", "Prague_Castle", "attractions", "prague"),
    ("old-town-square", "Old_Town_Square", "attractions", "prague"),
    ("st-stephens-cathedral", "St._Stephen%27s_Cathedral,_Vienna", "attractions", "vienna"),
    ("schonbrunn-palace", "Sch%C3%B6nbrunn_Palace", "attractions", "vienna"),
    ("belvedere-palace", "Belvedere,_Vienna", "museums", "vienna"),
    ("cn-tower", "CN_Tower", "attractions", "toronto"),
    ("niagara-falls", "Niagara_Falls", "parks", "toronto"),
    ("stanley-park", "Stanley_Park", "parks", "vancouver"),
    ("capilano-bridge", "Capilano_Suspension_Bridge", "attractions", "vancouver"),
    ("mexico-city-cathedral", "Mexico_City_Metropolitan_Cathedral", "attractions", "mexico-city"),
    ("teotihuacan", "Teotihuacan", "attractions", "mexico-city"),
    ("christ-the-redeemer", "Christ_the_Redeemer_(statue)", "attractions", "rio-de-janeiro"),
    ("sugarloaf", "Sugarloaf_Mountain", "attractions", "rio-de-janeiro"),
    ("copacabana", "Copacabana,_Rio_de_Janeiro", "parks", "rio-de-janeiro"),
    ("machu-picchu", "Machu_Picchu", "attractions", "lima"),
    ("doge-palace", "Doge%27s_Palace", "attractions", "venice"),
    ("rialto-bridge", "Rialto_Bridge", "attractions", "venice"),
    ("st-marks-square", "Piazza_San_Marco", "attractions", "venice"),
    ("santa-maria-del-fiore", "Florence_Cathedral", "attractions", "florence"),
    ("uffizi-gallery", "Uffizi", "museums", "florence"),
    ("ponte-vecchio", "Ponte_Vecchio", "attractions", "florence"),
    ("duomo-milano", "Milan_Cathedral", "attractions", "milan"),
    ("galleria-vittorio-emanuele", "Galleria_Vittorio_Emanuele_II", "shopping", "milan"),
    ("edinburgh-castle", "Edinburgh_Castle", "attractions", "edinburgh"),
    ("royal-mile", "Royal_Mile", "attractions", "edinburgh"),
    ("grand-place", "Grand_Place", "attractions", "brussels"),
    ("atomium", "Atomium", "attractions", "brussels"),
    ("parliament-building-budapest", "Hungarian_Parliament_Building", "attractions", "budapest"),
    ("buda-castle", "Buda_Castle", "attractions", "budapest"),
    ("chain-bridge", "Sz%C3%A9chenyi_Chain_Bridge", "attractions", "budapest"),
    ("warsaw-old-town", "Warsaw_Old_Town", "attractions", "warsaw"),
    ("market-square-krakow", "Main_Square,_Krak%C3%B3w", "attractions", "warsaw"),
]

# City hero images
CITIES = [
    ("new-york", "New_York_City", "New York", "United States"),
    ("los-angeles", "Los_Angeles", "Los Angeles", "United States"),
    ("chicago", "Chicago", "Chicago", "United States"),
    ("san-francisco", "San_Francisco", "San Francisco", "United States"),
    ("seattle", "Seattle", "Seattle", "United States"),
    ("boston", "Boston", "Boston", "United States"),
    ("las-vegas", "Las_Vegas", "Las Vegas", "United States"),
    ("london", "London", "London", "United Kingdom"),
    ("paris", "Paris", "Paris", "France"),
    ("rome", "Rome", "Rome", "Italy"),
    ("barcelona", "Barcelona", "Barcelona", "Spain"),
    ("madrid", "Madrid", "Madrid", "Spain"),
    ("amsterdam", "Amsterdam", "Amsterdam", "Netherlands"),
    ("berlin", "Berlin", "Berlin", "Germany"),
    ("vienna", "Vienna", "Vienna", "Austria"),
    ("prague", "Prague", "Prague", "Czech Republic"),
    ("istanbul", "Istanbul", "Istanbul", "Turkey"),
    ("athens", "Athens", "Athens", "Greece"),
    ("venice", "Venice", "Venice", "Italy"),
    ("florence", "Florence", "Florence", "Italy"),
    ("milan", "Milan", "Milan", "Italy"),
    ("tokyo", "Tokyo", "Tokyo", "Japan"),
    ("kyoto", "Kyoto", "Kyoto", "Japan"),
    ("beijing", "Beijing", "Beijing", "China"),
    ("singapore", "Singapore", "Singapore", "Singapore"),
    ("dubai", "Dubai", "Dubai", "United Arab Emirates"),
    ("mumbai", "Mumbai", "Mumbai", "India"),
    ("agra", "Agra", "Agra", "India"),
    ("sydney", "Sydney", "Sydney", "Australia"),
    ("toronto", "Toronto", "Toronto", "Canada"),
    ("vancouver", "Vancouver", "Vancouver", "Canada"),
    ("mexico-city", "Mexico_City", "Mexico City", "Mexico"),
    ("rio-de-janeiro", "Rio_de_Janeiro", "Rio de Janeiro", "Brazil"),
    ("lima", "Lima", "Lima", "Peru"),
    ("edinburgh", "Edinburgh", "Edinburgh", "United Kingdom"),
    ("brussels", "Brussels", "Brussels", "Belgium"),
    ("budapest", "Budapest", "Budapest", "Hungary"),
    ("warsaw", "Warsaw", "Warsaw", "Poland"),
]


def thumb_to_orig(url):
    """Convert wikimedia thumb URL to original."""
    url = url.replace('/thumb/', '/')
    url = re.sub(r'/\d+px-[^/]+$', '', url)
    return url


def download(url, dest):
    if dest.exists() and dest.stat().st_size > 10000:
        return True
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
            "Referer": "https://en.wikipedia.org/",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 10000:
            return False
        if len(data) > 3_500_000:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception:
        return False


BLACKLIST_KW = [
    'flag_of', 'coat_of_arms', 'on_the_globe', 'location_',
    'orthographic', 'ambox', 'disambig', 'edit-ic', 'question_book',
    'semi-protection', 'audio_a', 'play_button', 'crystal_clear',
    'nuvola', 'folder_', 'chevron', 'padlock', 'cc-by', 'cc-sa',
    'wikisource', 'wikiquote', 'commons-logo', 'wiki-logo',
    'wikipedia_', 'p_literature', 'symbol_', 'sound-icon',
    'osmooth', 'gnome-', 'blank_map', 'redaguoti', 'searchtool',
    'red_pog', 'blue_pog', 'green_pog', 'location_dot',
]


async def scrape_wiki_page(context, slug, wiki_title, out_dir, max_images=8):
    page = await context.new_page()
    try:
        url = f"https://en.wikipedia.org/wiki/{wiki_title}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(1.0)

        imgs = await page.evaluate('''() => {
            const out = [];
            document.querySelectorAll('img').forEach(img => {
                if (img.src && img.src.startsWith('http')) {
                    out.push({src: img.src, w: img.naturalWidth || 0, h: img.naturalHeight || 0});
                }
            });
            return out;
        }''')

        good = []
        seen = set()
        for img in imgs:
            if img['w'] < 200 or img['h'] < 150:
                continue
            src = img['src']
            if '.svg' in src.lower():
                continue
            if not re.search(r'\.(jpe?g|png|webp)', src, re.I):
                continue
            orig = thumb_to_orig(src)
            fname = orig.split('/')[-1].split('?')[0].lower()
            if fname in seen:
                continue
            if any(k in fname for k in BLACKLIST_KW):
                continue
            seen.add(fname)
            good.append(orig)

        item_dir = out_dir / slug
        item_dir.mkdir(parents=True, exist_ok=True)
        for old in item_dir.glob('img_*'):
            old.unlink()

        saved = 0
        for src in good:
            if saved >= max_images:
                break
            ext = 'jpg' if '.jp' in src.lower() else 'png' if '.png' in src.lower() else 'jpg'
            fname = item_dir / f"img_{saved:02d}.{ext}"
            if download(src, fname):
                saved += 1
        print(f"  {slug}: {saved} images", flush=True)
        return saved
    except Exception as e:
        print(f"  {slug}: ERROR {e}", flush=True)
        return 0
    finally:
        await page.close()


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=UA,
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )

        print(f"=== Scraping {len(PLACES)} places ===", flush=True)
        total_p = 0
        for i, (slug, title, _, _) in enumerate(PLACES):
            print(f"[P {i+1}/{len(PLACES)}]", flush=True)
            n = await scrape_wiki_page(context, slug, title, PLACE_DIR, max_images=6)
            total_p += n
            await asyncio.sleep(0.3)

        print(f"\n=== Scraping {len(CITIES)} cities ===", flush=True)
        total_c = 0
        for i, (slug, title, _, _) in enumerate(CITIES):
            print(f"[C {i+1}/{len(CITIES)}]", flush=True)
            n = await scrape_wiki_page(context, slug, title, CITY_DIR, max_images=4)
            total_c += n
            await asyncio.sleep(0.3)

        await browser.close()
        print(f"\nTOTAL: {total_p} place images + {total_c} city images = {total_p + total_c}", flush=True)

        # Write manifest
        (BASE_DIR / "scraped_data/scrape_manifest.json").write_text(
            json.dumps({
                "places_scraped": len(PLACES),
                "cities_scraped": len(CITIES),
                "place_images": total_p,
                "city_images": total_c,
            }, indent=2)
        )


if __name__ == "__main__":
    asyncio.run(main())
