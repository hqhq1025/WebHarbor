"""Build google_search.db in a clean state for byte-id reset.

Run inside a python:3.12-slim-bookworm container with deps pinned.
Output: instance/google_search.db (then copied to instance_seed/).
"""
import os
import sys

# Ensure deterministic hashing across processes
os.environ.setdefault('PYTHONHASHSEED', '0')

import importlib
import app as appmod
import seed_data

# Clean instance dir first then recreate
import shutil
inst_dir = os.path.join(os.path.dirname(__file__), 'instance')
if os.path.exists(inst_dir):
    shutil.rmtree(inst_dir)
os.makedirs(inst_dir, exist_ok=True)

with appmod.app.app_context():
    appmod.db.create_all()
    seed_data.seed_database(
        appmod.db, appmod.User, appmod.Vertical, appmod.Topic,
        appmod.SearchResult, appmod.PaaQuestion, appmod.RelatedQuery,
        appmod.Doodle, appmod.GoogleApp, appmod.TrendingTerm,
        appmod.KnowledgeFact, appmod.bcrypt,
    )
    appmod.seed_benchmark_users()
    appmod.seed_result_feedback()

# Normalize indexes + VACUUM for byte-id rebuild
appmod.normalize_seed_db_layout()

print("[build_seed] done")
