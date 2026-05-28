#!/usr/bin/env python3
"""extract_forms.py — Feature B: parse all <form> blocks from every snapshot.

Walks snapshots/<site>/<page>/full.html, finds every <form>, extracts:
  - action, method, name/id
  - fields: name, type, label, required, placeholder, pattern, default,
            min/max/maxlength/minlength, options (for select)
  - submit button text
  - fieldset/legend grouping

Outputs snapshots/<site>/_forms.jsonl — one form per line.

Usage:
  python3 extract_forms.py <site>
  python3 extract_forms.py --all
"""
import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

ATTR_RE = re.compile(r'([a-zA-Z_:][\w:.-]*)\s*=\s*"([^"]*)"|([a-zA-Z_:][\w:.-]*)\s*=\s*\'([^\']*)\'|([a-zA-Z_:][\w:.-]*)\s*=\s*([^\s>]+)|\b([a-zA-Z_:][\w:.-]*)\b')


def parse_attrs(attr_str: str) -> dict:
    out: dict = {}
    for m in ATTR_RE.finditer(attr_str):
        if m.group(1):
            out[m.group(1).lower()] = htmllib.unescape(m.group(2))
        elif m.group(3):
            out[m.group(3).lower()] = htmllib.unescape(m.group(4))
        elif m.group(5):
            out[m.group(5).lower()] = htmllib.unescape(m.group(6))
        elif m.group(7):
            out[m.group(7).lower()] = ""
    return out


def strip_tags(s: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", s)
    txt = htmllib.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


# Match <form ...>...</form> non-greedily; tolerate nested by smallest match.
FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.IGNORECASE | re.DOTALL)
INPUT_RE = re.compile(r'<input\b([^>]*?)/?>', re.IGNORECASE)
SELECT_RE = re.compile(r'<select\b([^>]*?)>(.*?)</select>', re.IGNORECASE | re.DOTALL)
TEXTAREA_RE = re.compile(r'<textarea\b([^>]*?)>(.*?)</textarea>', re.IGNORECASE | re.DOTALL)
OPTION_RE = re.compile(r'<option\b([^>]*?)>(.*?)</option>', re.IGNORECASE | re.DOTALL)
BUTTON_RE = re.compile(r'<button\b([^>]*?)>(.*?)</button>', re.IGNORECASE | re.DOTALL)
FIELDSET_RE = re.compile(r'<fieldset\b([^>]*?)>(.*?)</fieldset>', re.IGNORECASE | re.DOTALL)
LEGEND_RE = re.compile(r'<legend\b[^>]*>(.*?)</legend>', re.IGNORECASE | re.DOTALL)
LABEL_RE = re.compile(r'<label\b([^>]*?)>(.*?)</label>', re.IGNORECASE | re.DOTALL)


def build_label_map(form_inner: str) -> dict:
    """Return {id: label_text} for every <label for=ID>."""
    out = {}
    for m in LABEL_RE.finditer(form_inner):
        attrs = parse_attrs(m.group(1))
        for_id = attrs.get("for")
        text = strip_tags(m.group(2))
        if for_id and text:
            out[for_id] = text[:120]
    return out


def find_wrapping_label(field_match, form_inner: str) -> str | None:
    """For inputs not pointed at by for=ID, look for a <label>...<input>...</label>
    pattern by checking 200 chars before the input."""
    start = field_match.start()
    snippet = form_inner[max(0, start - 200):start]
    last_label = snippet.rfind("<label")
    if last_label < 0:
        return None
    # Make sure no </label> in between
    close = snippet[last_label:].find("</label>")
    if close >= 0:
        return None
    # Extract text inside the wrapping label up to the field
    label_inner = snippet[last_label:]
    label_inner = re.sub(r'^<label\b[^>]*>', "", label_inner)
    text = strip_tags(label_inner)
    return text[:120] if text else None


def _base_field(attrs: dict, label: str | None, typ: str) -> dict:
    """Spec-shaped field with canonical key order and explicit nulls."""
    return {
        "name": attrs.get("name") or attrs.get("id"),
        "type": typ,
        "label": label or attrs.get("aria-label") or attrs.get("title"),
        "required": "required" in attrs,
        "placeholder": attrs.get("placeholder"),
        "pattern": attrs.get("pattern"),
        "default": attrs.get("value"),
        "min": attrs.get("min"),
        "max": attrs.get("max"),
        "maxlength": attrs.get("maxlength"),
        "minlength": attrs.get("minlength"),
        "step": attrs.get("step"),
        "id": attrs.get("id"),
    }


def field_from_input(attrs: dict, label: str | None) -> dict:
    typ = (attrs.get("type") or "text").lower()
    field = _base_field(attrs, label, typ)
    field["tag"] = "input"
    if typ == "hidden":
        # keep but mark — hidden fields are still useful for form payload shape
        field["hidden"] = True
    return field


def field_from_select(attrs: dict, inner: str, label: str | None) -> dict:
    options = []
    for m in OPTION_RE.finditer(inner):
        opt_attrs = parse_attrs(m.group(1))
        text = strip_tags(m.group(2))
        options.append({
            "value": opt_attrs.get("value", text),
            "label": text,
            "selected": "selected" in opt_attrs,
        })
    field = _base_field(attrs, label, "select")
    field["tag"] = "select"
    field["multiple"] = "multiple" in attrs
    field["options"] = options[:200]
    field["default"] = next((o["value"] for o in options if o["selected"]), None)
    return field


def field_from_textarea(attrs: dict, inner: str, label: str | None) -> dict:
    field = _base_field(attrs, label, "textarea")
    field["tag"] = "textarea"
    field["default"] = strip_tags(inner)[:200]
    return field


def extract_form(form_attrs_str: str, form_inner: str) -> dict:
    form_attrs = parse_attrs(form_attrs_str)
    label_map = build_label_map(form_inner)

    # Resolve fieldset boundaries: for each field, find enclosing fieldset legend
    fieldset_spans = []
    for m in FIELDSET_RE.finditer(form_inner):
        legend_m = LEGEND_RE.search(m.group(2))
        legend = strip_tags(legend_m.group(1)) if legend_m else None
        fieldset_spans.append((m.start(), m.end(), legend))

    def fieldset_for(pos: int) -> str | None:
        for start, end, leg in fieldset_spans:
            if start <= pos <= end:
                return leg
        return None

    fields = []

    for m in INPUT_RE.finditer(form_inner):
        attrs = parse_attrs(m.group(1))
        label = label_map.get(attrs.get("id", "")) or find_wrapping_label(m, form_inner)
        field = field_from_input(attrs, label)
        fs = fieldset_for(m.start())
        if fs:
            field["fieldset"] = fs
        fields.append(field)

    for m in SELECT_RE.finditer(form_inner):
        attrs = parse_attrs(m.group(1))
        label = label_map.get(attrs.get("id", "")) or find_wrapping_label(m, form_inner)
        field = field_from_select(attrs, m.group(2), label)
        fs = fieldset_for(m.start())
        if fs:
            field["fieldset"] = fs
        fields.append(field)

    for m in TEXTAREA_RE.finditer(form_inner):
        attrs = parse_attrs(m.group(1))
        label = label_map.get(attrs.get("id", "")) or find_wrapping_label(m, form_inner)
        field = field_from_textarea(attrs, m.group(2), label)
        fs = fieldset_for(m.start())
        if fs:
            field["fieldset"] = fs
        fields.append(field)

    # Submit button text
    submit_text = None
    for m in BUTTON_RE.finditer(form_inner):
        battrs = parse_attrs(m.group(1))
        if battrs.get("type", "submit").lower() in ("submit", "") or "submit" in (battrs.get("type") or ""):
            text = strip_tags(m.group(2))
            if text:
                submit_text = text[:60]
                break
    if not submit_text:
        for m in INPUT_RE.finditer(form_inner):
            attrs = parse_attrs(m.group(1))
            if (attrs.get("type", "").lower() in ("submit", "button")) and attrs.get("value"):
                submit_text = attrs.get("value")[:60]
                break

    return {
        "action": form_attrs.get("action"),
        "method": (form_attrs.get("method") or "GET").upper(),
        "name": form_attrs.get("name"),
        "id": form_attrs.get("id"),
        "enctype": form_attrs.get("enctype"),
        "fields": fields,
        "submit_text": submit_text,
        "field_count": len(fields),
    }


def process_page(page_dir: Path) -> list[dict]:
    full_path = page_dir / "full.html"
    md_path = page_dir / "metadata.json"
    if not full_path.exists():
        return []
    try:
        html = full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    url = ""
    if md_path.exists():
        try:
            url = json.loads(md_path.read_text()).get("url", "")
        except Exception:
            pass
    out = []
    for idx, m in enumerate(FORM_RE.finditer(html)):
        try:
            form = extract_form(m.group(1), m.group(2))
        except Exception:
            continue
        if form["field_count"] == 0 and not form.get("submit_text"):
            continue
        # spec-shaped record: page/url/form_idx first, then form body
        record = {
            "page": page_dir.name,
            "url": url,
            "form_idx": idx,
        }
        record.update(form)
        out.append(record)
    return out


def process_site(site_dir: Path):
    all_forms = []
    page_count = 0
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        page_count += 1
        all_forms.extend(process_page(page_dir))
    out_path = site_dir / "_forms.jsonl"
    with out_path.open("w") as f:
        for form in all_forms:
            f.write(json.dumps(form, ensure_ascii=False) + "\n")
    return page_count, len(all_forms), sum(f["field_count"] for f in all_forms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    sites = [ROOT / args.site] if args.site else sorted(p for p in ROOT.iterdir() if p.is_dir())
    print(f"{'site':<28} {'pgs':>5} {'forms':>5} {'fields':>6}")
    print("-" * 60)
    for site_dir in sites:
        if not site_dir.is_dir():
            continue
        pgs, fs, fl = process_site(site_dir)
        print(f"{site_dir.name:<28} {pgs:>5} {fs:>5} {fl:>6}")


if __name__ == "__main__":
    main()
