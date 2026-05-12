#!/usr/bin/env python3
"""Scaffold a new site under sites/<name>/.

Creates the standard directory structure + minimal app.py and templates so
a contributor can start coding immediately.

Usage: ./scripts/new_site.py <site_name>
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_APP = '''"""{title} mirror — Flask app."""
import os
from flask import Flask, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SECRET_KEY"] = "{name}-dev-secret-please-change"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/_health")
def health():
    return {{"ok": True, "site": "{name}"}}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
'''

TEMPLATE_INDEX = '''<!doctype html>
<html><head><title>{title}</title></head>
<body>
  <h1>{title}</h1>
  <p>New mirror site scaffold. Edit <code>app.py</code> and templates to bring it to life.</p>
</body></html>
'''


def main():
    if len(sys.argv) != 2:
        print("usage: new_site.py <site_name>", file=sys.stderr)
        sys.exit(1)
    name = sys.argv[1]
    if not name.replace("_", "").isalnum() or name != name.lower():
        print("site_name must be lowercase letters / digits / underscores", file=sys.stderr)
        sys.exit(1)

    site = ROOT / "sites" / name
    if site.exists():
        print(f"sites/{name} already exists", file=sys.stderr)
        sys.exit(1)

    title = name.replace("_", " ").title()
    print(f"[new_site] scaffolding sites/{name} (title='{title}')")

    for sub in ["templates", "static/css", "static/js", "static/icons",
                "static/images", "static/external_cache",
                "instance_seed", "instance", "scraped_data"]:
        (site / sub).mkdir(parents=True, exist_ok=True)
        (site / sub / ".gitkeep").touch()

    (site / "app.py").write_text(TEMPLATE_APP.format(name=name, title=title))
    (site / "templates" / "index.html").write_text(TEMPLATE_INDEX.format(title=title))
    (site / "_health.py").write_text(
        f'"""Per-site health probe (optional, called by control_server)."""\n'
        f'def health():\n    return {{"ok": True, "site": "{name}"}}\n'
    )
    (site / "requirements.txt").write_text("Flask\n")

    print("[new_site] done. Next steps:")
    print(f"  1. edit sites/{name}/app.py + templates/")
    print(f"  2. drop seed data into sites/{name}/instance_seed/{name}.db")
    print(f"  3. drop images into sites/{name}/static/images/")
    print(f"  4. add to SITES list in ../websyn_start.sh and ../control_server.py")
    print(f"  5. ./scripts/build.sh && docker run ... && curl /reset/{name}")


if __name__ == "__main__":
    main()
