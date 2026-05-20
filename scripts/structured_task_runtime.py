#!/usr/bin/env python3
"""Shared helpers for structured WebHarbor task generation and validation.

These helpers intentionally live under scripts/ instead of importing across site
packages: each mirror is self-contained and its Flask app owns its SQLAlchemy
models. The helper loads one app at a time from the real site directory, using a
fresh local instance DB so generator/validator checks are DB-oracle based.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE_ORDER = [
    "allrecipes",
    "amazon",
    "apple",
    "arxiv",
    "bbc_news",
    "booking",
    "github",
    "google_flights",
    "google_map",
    "google_search",
    "huggingface",
    "wolfram_alpha",
    "cambridge_dictionary",
    "coursera",
    "espn",
]
SITE_DIRS = {site: ROOT / "sites" / site for site in SITE_ORDER}
WEB_URLS = {site: f"http://localhost:{40000 + idx}/" for idx, site in enumerate(SITE_ORDER)}
UPSTREAM_URLS = {
    "allrecipes": "https://www.allrecipes.com/",
    "amazon": "https://www.amazon.com/",
    "apple": "https://www.apple.com/",
    "arxiv": "https://arxiv.org/",
    "bbc_news": "https://www.bbc.com/news",
    "booking": "https://www.booking.com/",
    "github": "https://github.com/",
    "google_flights": "https://www.google.com/travel/flights/",
    "google_map": "https://www.google.com/maps/",
    "google_search": "https://www.google.com/",
    "huggingface": "https://huggingface.co/",
    "wolfram_alpha": "https://www.wolframalpha.com/",
    "cambridge_dictionary": "https://dictionary.cambridge.org/",
    "coursera": "https://www.coursera.org/",
    "espn": "https://www.espn.com/",
}

UPSTREAM_LOGIN_URLS = {
    "allrecipes": "https://www.allrecipes.com/account/signin/",
    "amazon": "https://www.amazon.com/ap/signin",
    "apple": "https://account.apple.com/sign-in",
    "arxiv": "https://arxiv.org/login",
    "bbc_news": "https://account.bbc.com/signin",
    "booking": "https://www.booking.com/signin.html",
    "cambridge_dictionary": "https://login.sso.cambridge.org/",
    "coursera": "https://www.coursera.org/login",
    "espn": "https://www.espn.com/login",
    "github": "https://github.com/login",
    "google_flights": "https://accounts.google.com/",
    "google_map": "https://accounts.google.com/",
    "google_search": "https://accounts.google.com/",
    "huggingface": "https://huggingface.co/login",
    "wolfram_alpha": "https://user.wolfram.com/",
}



@dataclass(frozen=True)
class LoadedSite:
    site: str
    module: Any
    tempdir: tempfile.TemporaryDirectory | None = None


@contextmanager
def pushd(path: Path):
    old_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def _copy_site_for_fresh_db(site: str, site_dir: Path) -> tuple[Path, tempfile.TemporaryDirectory]:
    """Copy one site into a temporary directory for a disposable instance DB.

    Several mirror apps hard-code `BASE_DIR / "instance"` at import time. To get
    a fresh DB oracle without deleting or mutating a developer's working
    `sites/<site>/instance/`, import the app from a lightweight temporary copy of
    the site directory. Heavy runtime artifacts are intentionally skipped.
    """
    tmp = tempfile.TemporaryDirectory(prefix=f"webharbor-{site}-oracle-")
    tmp_site_dir = Path(tmp.name) / site
    ignore = shutil.ignore_patterns(
        "instance",
        "instance_seed",
        "__pycache__",
        "*.pyc",
        "static/images",
        "static/external_cache",
    )
    shutil.copytree(site_dir, tmp_site_dir, ignore=ignore)
    (tmp_site_dir / "instance").mkdir(exist_ok=True)
    return tmp_site_dir, tmp


def load_site_app(site: str, *, fresh_instance: bool = True) -> LoadedSite:
    """Load a site app module and ensure its DB is seeded.

    With `fresh_instance=True`, the app is imported from a temporary copy of the
    site directory so the generated SQLite DB is disposable. This keeps
    generator/validator checks deterministic without deleting untracked local
    `sites/<site>/instance/` files.
    """
    if site not in SITE_DIRS:
        raise ValueError(f"unsupported site: {site}")
    original_site_dir = SITE_DIRS[site]
    tempdir = None
    site_dir = original_site_dir
    if fresh_instance:
        site_dir, tempdir = _copy_site_for_fresh_db(site, original_site_dir)

    old_path = list(sys.path)
    module_name = f"webharbor_structured_{site}_app"
    sys.modules.pop(module_name, None)
    previous_app_module = sys.modules.pop("app", None)
    # Site apps use same short helper module names (especially seed_data.py).
    # Drop them before each import so one site's seed module cannot leak into
    # the next site app loaded in the same Python process.
    for helper_name in ("seed_data", "content_data"):
        sys.modules.pop(helper_name, None)
    sys.path.insert(0, str(site_dir))
    try:
        with pushd(site_dir):
            spec = importlib.util.spec_from_file_location(module_name, site_dir / "app.py")
            if spec is None or spec.loader is None:
                raise RuntimeError(f"cannot load app.py for {site}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            # A few seed_data.py files do `from app import ...`; expose the
            # currently loaded site app under that conventional module name
            # while seeding, then restore the caller's previous module below.
            sys.modules["app"] = module
            spec.loader.exec_module(module)
            # Some site apps seed on import, others only inside __main__. For
            # structured task checks we need a fresh DB oracle either way.
            flask_app = getattr(module, "app", None)
            db = getattr(module, "db", None)
            seed_database = getattr(module, "seed_database", None)
            seed_benchmark_users = getattr(module, "seed_benchmark_users", None)
            if flask_app is not None and db is not None:
                with flask_app.app_context():
                    db.create_all()
                    if callable(seed_database):
                        # The seed functions are expected to be idempotent.
                        seed_database()
                    if callable(seed_benchmark_users):
                        seed_benchmark_users()
    finally:
        if previous_app_module is not None:
            sys.modules["app"] = previous_app_module
        else:
            sys.modules.pop("app", None)
        sys.path[:] = old_path
    return LoadedSite(site=site, module=module, tempdir=tempdir)


def json_dump_line(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=False) + "\n"


def stable_task_id(site: str, family: str, target: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in target).strip("_")
    while "__" in safe:
        safe = safe.replace("__", "_")
    return f"{site}.{family}.{safe}"


def iso(d: date | None) -> str | None:
    return d.isoformat() if d is not None else None
