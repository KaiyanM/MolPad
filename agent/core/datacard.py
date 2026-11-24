"""What a dataset is, in words: the `dataset` block of the page (inst/d3dashboard/SCHEMA.md).

The dashboard works on fixed column names (Pathway = level 1, taxonomic.scope = level 2,
type = ribbon colour). What they stand for differs per dataset, so it is written down once:

    block    R writes it into the page from the study (gStudy())
    context  an optional JSON file with the same entries, which overrules the page; the file
             written by write_study() in R is one
    build()  joins the two and fills what can be read from the data

    card = build(features, cfg, block, context, id_links)
    card["level1"]["name"]        "phylum"
    card["level2"]["relation"]    "nested" (a part of level 1) | "crossed" (another kind of tag)
    card["colour"]["same_as"]     "level1" when the colour column repeats level 1
    card["ids"]["KEGG_ID"]        {"type", "name", "example", "prefix", "pattern"}
    lines(card, ds)               the description for a prompt or a person
"""

import re

KEYS = ("background", "feature", "level1", "level2", "colour", "ids", "samples", "missing")
SAMPLE_KEYS = ("groups", "time", "columns")
# the fixed column names of the page; a study file names the user's own column instead
FIXED = ("Pathway", "taxonomic.scope", "type")
# older context files name the levels with these keys
OLD_KEYS = {"level1_name": "level1", "level2_name": "level2"}
# id types the dashboard links (R: d3_link_templates)
ID_TYPES = {"KEGG": {"name": "KEGG ortholog id", "pattern": r"K\d{5}"},
            "GO": {"name": "GO term id", "pattern": r"GO:\d{7}"}}
# written for a missing value by gAnnotation() and pre_process()
PLACEHOLDERS = ("Unknown", "Other", "-", "")
GENERIC = {"background": "Longitudinal data shown in a MolPad dashboard. Features are grouped into "
                         "clusters by the shape of their trajectory.",
           "level1": "functional annotation", "level2": "taxonomic scope", "feature": "feature"}


def normalise(raw, where="the description"):
    """Check the entries and write the short forms out: "phylum" -> {"name": "phylum"}."""
    raw = dict(raw or {})
    for old, key in OLD_KEYS.items():
        if old in raw:
            raw[key] = {**_entry(raw.get(key)), "name": raw.pop(old)}
    unknown = set(raw) - set(KEYS)
    if unknown:
        raise ValueError(f"unknown keys in {where}: {sorted(unknown)}; allowed: {list(KEYS)}")
    out = {}
    for key, value in raw.items():
        if value is None:
            continue
        if key in ("background", "missing"):
            out[key] = str(value)
        elif key == "ids":
            out[key] = {col: _entry(v, "type") for col, v in value.items()}
        elif key == "samples":
            samples = _entry(value, "groups")
            unknown = set(samples) - set(SAMPLE_KEYS)
            if unknown:
                raise ValueError(f"unknown keys in samples of {where}: {sorted(unknown)}; allowed: {list(SAMPLE_KEYS)}")
            samples.pop("columns", None)            # which columns: the page's "subjects" say it
            if "time" in samples:
                samples["time"] = _entry(samples["time"], "about")
            groups = samples.get("groups")           # one sentence, or a note per group
            if isinstance(groups, dict):
                samples["groups"] = {str(g): str(t) for g, t in groups.items()}
            elif groups:
                samples["groups"] = str(groups)
            else:
                samples.pop("groups", None)
            out[key] = samples
        else:
            entry = _entry(value, "name" if key == "feature" else "column")
            if key != "feature":
                # a study names the user's own column ("phylum"); in the page that is the source
                column = entry.pop("column", None)
                if column and column not in FIXED:
                    entry.setdefault("source", column)
            out[key] = entry
    return out


def _entry(x, short="name"):
    if x is None:
        return {}
    return dict(x) if isinstance(x, dict) else {short: str(x)}


def _merge(a, b):
    """b over a, entry by entry."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in a.items()}
    for key, value in b.items():
        if key == "ids":
            ids = out.setdefault("ids", {})
            for col, v in value.items():
                ids[col] = {**ids.get(col, {}), **v}
        elif isinstance(value, dict):
            out[key] = {**out.get(key, {}), **value}
        else:
            out[key] = value
    return out


def guess_links(columns):
    """Id columns of a CSV dataset: the type is read from the column name (KEGG_ID -> KEGG)."""
    out = {}
    for col in columns:
        kind = next((t for t in ID_TYPES if re.search(rf"(?i)\b{t}\b", col.replace("_", " "))), None)
        out[col] = {"type": kind, "pattern": ID_TYPES[kind]["pattern"]} if kind else {}
    return out


def _relation(features, cfg):
    """nested: every level-2 value sits under one level-1 value; crossed: another kind of tag."""
    df = features[[cfg.level1, cfg.level2]].dropna().astype(str)
    df = df[~df[cfg.level1].isin(PLACEHOLDERS) & ~df[cfg.level2].isin(PLACEHOLDERS)]
    parents = df.groupby(cfg.level2)[cfg.level1].nunique()
    return "nested" if len(parents) and (parents == 1).all() else "crossed"


def _same_as(features, cfg):
    if cfg.color not in features.columns:
        return None
    colour = features[cfg.color].astype(str)
    for key, col in (("level1", cfg.level1), ("level2", cfg.level2)):
        level = features[col].astype(str)
        keep = ~colour.isin(PLACEHOLDERS) & ~level.isin(PLACEHOLDERS) & features[col].notna()
        if keep.any() and (colour[keep] == level[keep]).all():
            return key
    return None


def _id(col, features, link, given, missing):
    """One id column: type and name, plus an example and the prefix the ids carry in the data."""
    kind = given.get("type") or link.get("type")
    known = ID_TYPES.get(kind, {})
    pattern = link.get("pattern") or known.get("pattern")
    out = {"type": kind, "name": known.get("name") or (f"{kind} id" if kind else "database id"),
           "pattern": pattern}
    cells = features[col].dropna().astype(str)
    if pattern:
        try:
            hit = cells.str.extract(rf"([^,;\s]*?)({pattern})").dropna()
        except re.error:           # a JavaScript-only expression: go without an example
            hit = None
        if hit is not None and len(hit):
            out["example"], out["prefix"] = hit.iloc[0, 1], hit.iloc[0, 0]
    else:
        cells = cells[(cells != (missing or "")) & (cells != "")]
        if len(cells):
            out["example"] = re.split(r"[,;\s]+", cells.iloc[0].strip())[0]
    out.update({k: v for k, v in given.items() if v not in (None, "")})
    return {k: v for k, v in out.items() if v not in (None, "")}


def build(features, cfg, block=None, context=None, id_links=None, context_name="the context file"):
    """The card of one dataset: the page's block, overruled by the context file, completed from the data."""
    card = _merge(normalise(block, "the page's dataset description"), normalise(context, context_name))
    for key, column in (("level1", cfg.level1), ("level2", cfg.level2)):
        level = {"column": column, **card.get(key, {})}
        level["name"] = level.get("name") or level.get("source") or GENERIC[key]
        card[key] = level
    card["level2"].setdefault("relation", _relation(features, cfg))
    if card["level2"]["relation"] not in ("nested", "crossed"):
        raise ValueError("level2.relation must be 'nested' or 'crossed'")

    colour = {"column": cfg.color, **card.get("colour", {})}
    if "same_as" not in colour:
        colour["same_as"] = _same_as(features, cfg)
    if not colour.get("name") and colour.get("same_as"):
        colour["name"] = card[colour["same_as"]]["name"]
    card["colour"] = {k: v for k, v in colour.items() if v}

    card["feature"] = {"name": GENERIC["feature"], **card.get("feature", {})}
    card.setdefault("background", GENERIC["background"])
    links = id_links or {}
    if "missing" not in card:
        cells = [features[c].astype(str) for c in links if c in features.columns]
        card["missing"] = "-" if any((c == "-").any() for c in cells) else cfg.missing
    given = card.get("ids", {})
    card["ids"] = {col: _id(col, features, link or {}, given.get(col, {}), card["missing"])
                   for col, link in links.items() if col in features.columns}
    return card


def _groups(card):
    """The notes per sample group; {} when the study describes the groups in one sentence."""
    groups = card.get("samples", {}).get("groups")
    return groups if isinstance(groups, dict) else {}


def groups_sentence(card):
    groups = card.get("samples", {}).get("groups")
    return groups if isinstance(groups, str) else ""


def group_words(card, subjects):
    """{sample group: other ways to name it}: what the study calls it ("cheese A"), without a
    note after a semicolon ("cheese C; no sample at time point 2" -> "cheese C")."""
    out = {}
    for s in subjects:
        text = _groups(card).get(s, "")
        out[s] = [w for w in dict.fromkeys([text.strip(), text.split(";")[0].strip()]) if w]
    return out


def group_note(card, s):
    """'C (cheese C; no sample at time point 2)': a sample group with what the study says of it."""
    text = _groups(card).get(s)
    return f"{s} ({text})" if text and text.lower() != str(s).lower() else str(s)


def time_note(card):
    """'sampling time point during ripening; unit: day', or '' when the study says nothing."""
    time = card.get("samples", {}).get("time") or {}
    return "; ".join(p for p in (time.get("about"), f"unit: {time['unit']}" if time.get("unit") else None) if p)


def prefixes(card):
    """Prefixes the ids carry in the data ("ko:"), to strip from a mention."""
    return sorted({i["prefix"] for i in card["ids"].values() if i.get("prefix")}, key=len, reverse=True)


def id_note(card, col):
    """'KEGG ortholog ids such as K00001', for the list of table columns."""
    i = card["ids"][col]
    return f"{i['name']}s" + (f" such as {i['example']}" if i.get("example") else "")


def level_note(card, key):
    """'phylum: the phylum a contig is assigned to'."""
    level = card[key]
    note = level["name"] + (f": {level['about']}" if level.get("about") else "")
    if key == "level2":
        one, two = card["level1"]["name"], level["name"]
        note += (f"; each {two} belongs to one {one}" if level["relation"] == "nested"
                 else f"; another kind of tag than the {one}, the same {two} occurs under several")
    return note


def lines(card, ds):
    """The dataset in words, for a person or a prompt (no value lists)."""
    out = [card["background"], f"One feature (a row of the table) is a {card['feature']['name']}."]
    for key, n in (("level1", 1), ("level2", 2)):
        level = card[key]
        was = f", column '{level['source']}' of the annotations" if level.get("source") else ""
        out.append(f"Level {n} is the {level_note(card, key)} ({len(getattr(ds, key + '_values'))} values{was}).")
    out.append(colour_note(card))
    for col in card["ids"]:
        out.append(f"{col} holds {id_note(card, col)}"
                   + (f", written with the prefix '{card['ids'][col]['prefix']}'" if card["ids"][col].get("prefix") else "")
                   + ".")
    if len(ds.subjects) > 1 or card.get("samples", {}).get("groups"):
        out.append("Sample groups: " + ", ".join(group_note(card, s) for s in ds.subjects) + "."
                   + (" " + groups_sentence(card) if groups_sentence(card) else ""))
    if time_note(card):
        out.append(f"Time points: {time_note(card).rstrip('.')}.")
    out.append(f"'{card['missing']}' stands for no annotation.")
    return out


def colour_note(card):
    colour = card["colour"]
    if colour.get("same_as"):
        n = colour["same_as"][-1]
        return (f"The colour column '{colour['column']}' repeats level {n} ({card[colour['same_as']]['name']}); "
                "the ribbon lines are grouped by what the page's 'Colour lines by' control shows.")
    return (f"The colour column '{colour['column']}'" + (f" holds the {colour['name']}" if colour.get("name") else "")
            + (f" ({colour['about']})" if colour.get("about") else "")
            + "; the ribbon lines can be grouped by it, by level 1, by level 2 or not at all.")
