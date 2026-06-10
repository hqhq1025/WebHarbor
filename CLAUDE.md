@AGENTS.md

# Claude-specific notes

The full agent guide is loaded above via `@AGENTS.md`. The notes below apply only when Claude Code is the agent.

## Migration & fresh-machine bring-up (read first when setting up a new box)

See **`MIGRATION.md`** for the complete old-box → new-box runbook (asset resync, bootstrap,
bring-up, the structured-task / bulk_api data-gen pipeline, and every known risk). The two things
that bite hardest:

- **Heavy assets are NOT in git.** A fresh clone has *empty* `sites/*/instance_seed/` dirs — the
  seed DBs + `static/images/` + `static/external_cache/` live on the Hugging Face dataset
  `ChilleD/WebHarbor` and must be pulled with `./scripts/fetch_assets.sh` before `build.sh`/run.
  `check_assets.sh` hard-fails until they're present. `.assetpaths` and `.gitignore` list the same
  3 managed globs and must stay in sync.
- **⚠️ HF assets are stale (as of 2026-06-10).** The HF tarballs lag local content (11 sites have
  no tarball at all; ~23 have local edits newer than HF). Running `fetch_assets.sh` on a fresh box
  **right now would lose data**. Before migrating, on the OLD machine run
  `./scripts/extract_assets.sh ../wh-static-pr/ --push` to make HF authoritative, then pin a commit
  SHA in `.assets-revision`. This step is NOT yet done — see `MIGRATION.md §1c/§1d`.

This repo's heavy data-generation half (task construction → Azure CUA trajectory rollout → LLM
judge → Mage v2 SFT) lives in the sibling repo **`~/repos/mage_web_sft_factory`** (its own
`MIGRATION.md` + `CLAUDE.md`); WebHarbor only provides the mirror sites it drives.

## Source of truth for sites/ports

The `SITES` arrays in `control_server.py` and `websyn_start.sh` (kept index-aligned with the
Dockerfile `EXPOSE` line) are authoritative: **36 sites on `40000-40035`**. README/AGENTS prose
saying 15–20 sites / `40000-40014` is **stale** — using that port range silently drops sites 15–35.

## Tooling preferences

- Use `Edit` / `Write` for file changes, not `Bash sed` / `Bash echo >`.
- Use `Grep` / `Glob` for searching, not `Bash grep` / `Bash find`.
- Reserve `Bash` for things that are commands: `docker build`, `docker run`, `curl`, `python3 -c`, etc.
- Always call the venv binary directly (`.venv/bin/python3`, `.venv/bin/hf`); never `source activate`.
  Don't rsync the `.venv` to a new box — recreate it (`python3.12 -m venv .venv` + `pip install -r requirements.txt`).
  There is now a committed `requirements.txt` (host tooling env, 60 pkgs, `pip freeze` ground truth);
  the Dockerfile pip list is image-runtime-only (~12 pkgs) — do not "reconcile" the two.

## Long-running operations

`docker build` of this image runs ~30 s on a warm cache, ~3 minutes cold. `./scripts/fetch_assets.sh` (the first run after `git clone`) can take several minutes (~2.8 GB transfer from HF). Use `Bash` with `run_in_background: true` for these and check back, rather than blocking the conversation on a long sync call.

## Existing containers

If a container is already running on `:8101` / `:40000-40035`, treat it as the user's working environment — don't `docker stop` or `docker rm` it without explicit confirmation. Spin up your test container under a different name on alt ports (`:8201`, `:41000-41035`).
