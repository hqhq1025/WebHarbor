"""Article generator helpers used by the per-wiki seed modules.

Each per-wiki module supplies a compact list of dicts describing characters /
items / locations and we expand each into a multi-section wiki article with
infobox, links, categories, and revision-friendly chunked content.
"""
import textwrap


def build_character_article(d: dict, wiki_slug: str) -> str:
    """Render a 4-6-section wikitext article from a compact character record."""
    title = d["title"]
    species = d.get("species", "Human")
    affiliation = d.get("affiliation", "")
    summary_line = d.get("blurb", "")
    bio = d.get("bio", "")
    powers = d.get("powers", [])
    appearances = d.get("appearances", [])
    relationships = d.get("relationships", [])
    quote = d.get("quote", "")
    legacy = d.get("legacy", "")
    trivia = d.get("trivia", [])

    parts = []
    parts.append(f"'''{title}''' {summary_line}".rstrip())
    parts.append("")

    parts.append("== Biography ==")
    parts.append("")
    parts.append(bio if bio else f"{title} is a {species.lower()} associated with {affiliation}.")
    parts.append("")

    if powers:
        parts.append("== Abilities ==")
        parts.append("")
        for p in powers:
            parts.append(f"* {p}")
        parts.append("")

    if relationships:
        parts.append("== Relationships ==")
        parts.append("")
        for name, rel in relationships:
            parts.append(f"* [[{name}]] &mdash; {rel}")
        parts.append("")

    if appearances:
        parts.append("== Appearances ==")
        parts.append("")
        for item in appearances:
            parts.append(f"* ''[[{item}]]''")
        parts.append("")

    if quote:
        parts.append("== Notable quote ==")
        parts.append("")
        parts.append(f"''\"{quote}\"''")
        parts.append("")

    if legacy:
        parts.append("== Legacy ==")
        parts.append("")
        parts.append(legacy)
        parts.append("")

    if trivia:
        parts.append("== Trivia ==")
        parts.append("")
        for t in trivia:
            parts.append(f"* {t}")
        parts.append("")

    return "\n".join(parts).strip() + "\n"


def build_location_article(d: dict, wiki_slug: str) -> str:
    title = d["title"]
    blurb = d.get("blurb", "")
    region = d.get("region", "")
    desc = d.get("desc", "")
    landmarks = d.get("landmarks", [])
    inhabitants = d.get("inhabitants", [])
    events = d.get("events", [])

    parts = [f"'''{title}''' {blurb}".rstrip(), ""]
    parts += ["== Geography ==", "", desc or f"{title} is located within {region}.", ""]
    if landmarks:
        parts += ["== Landmarks ==", ""]
        for l in landmarks:
            parts.append(f"* [[{l}]]")
        parts.append("")
    if inhabitants:
        parts += ["== Notable inhabitants ==", ""]
        for n in inhabitants:
            parts.append(f"* [[{n}]]")
        parts.append("")
    if events:
        parts += ["== Notable events ==", ""]
        for e in events:
            parts.append(f"* {e}")
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def build_item_article(d: dict, wiki_slug: str) -> str:
    title = d["title"]
    blurb = d.get("blurb", "")
    history = d.get("history", "")
    wielders = d.get("wielders", [])
    powers = d.get("powers", [])

    parts = [f"'''{title}''' {blurb}".rstrip(), ""]
    parts += ["== History ==", "", history or f"{title} has a long history of use.", ""]
    if powers:
        parts += ["== Properties ==", ""]
        for p in powers:
            parts.append(f"* {p}")
        parts.append("")
    if wielders:
        parts += ["== Known wielders ==", ""]
        for w in wielders:
            parts.append(f"* [[{w}]]")
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def expand_article(d: dict, wiki_slug: str) -> dict:
    """Return a complete article dict that the seeder consumes."""
    kind = d.get("kind", "character")
    if kind == "location":
        content = build_location_article(d, wiki_slug)
    elif kind == "item":
        content = build_item_article(d, wiki_slug)
    else:
        content = build_character_article(d, wiki_slug)
    summary = d.get("summary") or (d.get("blurb", "")[:280] or content[:280])
    # Dedupe categories while preserving order
    cats = []
    for c in d.get("categories", []):
        if c not in cats:
            cats.append(c)
    return dict(
        title=d["title"],
        content=content,
        summary=summary,
        infobox_kind=kind,
        infobox=d.get("infobox", {}),
        image=d.get("image", ""),
        categories=cats,
        views=d.get("views", 1000),
        featured=d.get("featured", False),
        age_days=d.get("age_days", 300),
        updated_days=d.get("updated_days", 7),
        namespace=d.get("namespace", "Main"),
    )
