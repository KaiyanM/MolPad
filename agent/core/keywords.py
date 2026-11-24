"""Keyword map: which level does each term of the question belong to?

Two parts, both without an LLM:

    vocabulary(ds)             the unique() values of level 1 and level 2
    map_keywords(words, ds)    look each keyword up in that vocabulary, the
                               level-3 columns, the sample groups, the
                               timepoints and the clusters

The keywords themselves are picked from the question by an LLM (node
`keywords` in nodes.py). The lookup here is plain matching, so a keyword can
only be mapped to a value that exists in the data.
"""

import difflib
import re

from . import datacard

FUZZY_CUTOFF = 0.8   # similarity needed to accept a misspelt or inflected name


def vocabulary(ds):
    """Unique values of level 1 and level 2, and which level-1 values each level-2 value sits under."""
    cfg = ds.cfg
    parents = {}
    for l1, l2s in ds.level2_by_level1.items():
        for l2 in l2s:
            parents.setdefault(l2, []).append(l1)
    return {
        "level1": {"column": cfg.level1, "name": cfg.level1_name, "values": list(ds.level1_values)},
        "level2": {"column": cfg.level2, "name": cfg.level2_name, "values": list(ds.level2_values),
                   "parents": parents},
    }


def _lookup(word, values):
    """Exact match ignoring case, else the closest spelling above FUZZY_CUTOFF."""
    low = {str(v).lower(): v for v in values}
    w = str(word).strip().lower()
    if w in low:
        return low[w], "exact"
    close = difflib.get_close_matches(w, list(low), n=1, cutoff=FUZZY_CUTOFF)
    return (low[close[0]], "close spelling") if close else (None, None)


def _level3_hits(word, ds):
    """Level-3 columns in which the keyword occurs as a whole id, with the row count."""
    token = str(word).strip()
    prefixes = datacard.prefixes(ds.card)     # the ids may carry a prefix in the data ("ko:K03196")
    for p in prefixes:
        if token.lower().startswith(p.lower()):
            token = token[len(p):]
            break
    if not re.search(r"\d", token):       # ids carry digits; plain words are not looked up
        return []
    hits = []
    lead = "(?:" + "|".join(re.escape(p) for p in prefixes) + ")?" if prefixes else ""
    pattern = rf"(?:^|,)\s*{lead}{re.escape(token)}\s*(?:,|$)"
    for column in ds.cfg.level3:
        n = int(ds.features[column].astype(str).str.contains(pattern, case=False).sum())
        if n:
            hits.append({"level": "level3", "column": column, "value": token, "n_features": n})
    return hits


def ids_in_data(ids, column, ds):
    """{id: number of features that carry it in `column`}, in the order given; 0 when absent."""
    out = {}
    for i in ids:
        hits = [h for h in _level3_hits(i, ds) if h["column"] == column]
        out[str(i)] = hits[0]["n_features"] if hits else 0
    return out


def memory_note(concept, ids, column, ds):
    """What to tell the reader when ids were written by the model from memory.

    Returns (kind, text). kind is "none" (no id given), "absent" (none of them is in the data:
    the agent stops and asks) or "assumed" (it goes on, and the text says what to check).
    """
    known = ds.card["ids"].get(column) or {}
    name = (known.get("name") or "id") + "s"
    if not ids and not known:      # no id column was named: show what an id of each column looks like
        examples = [i["example"] for i in ds.card["ids"].values() if i.get("example")]
        known = {"example": " or ".join(examples)} if examples else {}
    ask = "Give the ids you mean and I can show where they fall."
    if not ids:
        example = f' (such as {known["example"]})' if known.get("example") else ""
        return "none", (f'"{concept}" is not a value or an id in the data, and I cannot list its {name} '
                        f"reliably from memory. Give the ids you mean{example} and I can show where they fall.")
    found = ids_in_data(ids, column, ds)
    present = [i for i, n in found.items() if n]
    absent = [i for i, n in found.items() if not n]
    listed = ", ".join(found)
    if not present:
        return "absent", (f'I turned "{concept}" into these {name} from memory, not from a database: {listed}. '
                          "None of them is in the data, so either the list is wrong or the data has no such "
                          f"features. {ask}")
    text = (f'"{concept}" was turned into {name} from the model\'s memory, not looked up in a database: '
            f"{listed}. {len(present)} of {len(found)} are in the data"
            + (f" (not in the data: {', '.join(absent)})" if absent else "")
            + ". The list may be incomplete or wrong: check it, or ask again with the ids themselves.")
    return "assumed", text


def map_keywords(words, ds):
    """Map each keyword to the level(s) it belongs to.

    Returns {"keywords": [...], "notes": [...]}. Each keyword entry has the
    keyword as written and a list of matches; a keyword with no match is
    marked unknown (an outside concept, or a name that is not in the data).
    """
    cfg = ds.cfg
    vocab = vocabulary(ds)
    out, notes = [], []
    for word in dict.fromkeys(str(w).strip() for w in words if str(w).strip()):
        matches = []
        for level in ("level1", "level2"):
            value, how = _lookup(word, vocab[level]["values"])
            if value is not None:
                m = {"level": level, "column": vocab[level]["column"], "value": value, "match": how}
                if level == "level2":
                    m["under_level1"] = vocab["level2"]["parents"].get(value, [])
                matches.append(m)
        if any(m["match"] == "exact" for m in matches):
            # an exact name at one level beats a close spelling at the other (Actinomycetota vs Actinomycetes)
            matches = [m for m in matches if m["match"] == "exact"]
        matches += _level3_hits(word, ds)

        low = word.lower()
        other = datacard.group_words(ds.card, ds.subjects)   # what the study calls the group ("cheese A")
        subject = next((s for s in ds.subjects if low == s.lower() or low.endswith(" " + s.lower())
                        or low in (w.lower() for w in other[s])), None)
        if subject and not matches:
            matches.append({"level": "sample_group", "value": subject, "columns": ds.subjects[subject]})
        timepoint = next((t for t in ds.timepoints if t.lower() == low), None)
        if timepoint:
            matches.append({"level": "timepoint", "value": timepoint})
        if re.search(r"(cluster|group)[\s_-]*\d+$", low) and ds.cluster_name(word):
            matches.append({"level": "cluster", "value": ds.cluster_name(word)})

        out.append({"keyword": word, "matches": matches} if matches
                   else {"keyword": word, "matches": [], "unknown": True})
        if not matches:
            notes.append(f"'{word}' is not a {cfg.level1_name}, a {cfg.level2_name}, an id or a "
                         "sample group in the data. If it names a gene family or function, it is an "
                         "outside concept whose ids come from model knowledge.")

    # a level-2 keyword that is not under any level-1 keyword of the same question
    l1 = [m["value"] for k in out for m in k["matches"] if m["level"] == "level1"]
    for k in out:
        for m in k["matches"]:
            if m["level"] == "level2" and l1 and not set(m["under_level1"]) & set(l1):
                notes.append(f"{m['value']} is a {cfg.level2_name} of {', '.join(m['under_level1'])}, "
                             f"not of {', '.join(l1)}: that combination has no features.")
    return {"keywords": out, "notes": notes}


def as_text(kmap):
    """The keyword map as lines for a prompt or the debug output."""
    lines = []
    for k in kmap["keywords"]:
        if not k["matches"]:
            lines.append(f"- {k['keyword']}: not found in the data")
            continue
        parts = []
        for m in k["matches"]:
            p = f"{m['level']}" + (f" ({m['column']})" if m.get("column") else "") + f" = {m['value']}"
            if m.get("under_level1"):
                p += f", under {', '.join(m['under_level1'])}"
            if m.get("n_features"):
                p += f", {m['n_features']} features"
            if m.get("match") == "close spelling":
                p += " [close spelling]"
            parts.append(p)
        lines.append(f"- {k['keyword']}: " + "; ".join(parts))
    lines += [f"- note: {n}" for n in kmap["notes"]]
    return "\n".join(lines) or "- (no keywords)"
