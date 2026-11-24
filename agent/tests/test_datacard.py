"""The dataset card: what level 1, level 2, the colour column and the ids are (core/datacard.py)."""

import json

import pytest

from agent.core import keywords as kw
from agent.core import payload, prompts, skills
from agent.core import datacard
from agent.core.data_tools import Dataset, Session, load_dataset


def made_up(dataset=None):
    """Proteins tagged with a function (level 1) and an organ (level 2): two kinds of tag, so
    the same organ occurs under several functions. Ids are Pfam ids written 'pfam:PF00001'."""
    rows = [("transport", "liver", "a", "pfam:PF00001,pfam:PF00002", [0, 1, 2, 3]),
            ("transport", "kidney", "a", "pfam:PF00002", [0, 2, 3, 4]),
            ("signalling", "liver", "b", "-", [3, 2, 1, 0]),
            ("signalling", "kidney", "b", "pfam:PF00003", [4, 3, 1, 0]),
            ("signalling", "liver", "a", "-", [1, 1, 1, 1])]
    feats = [{"ID": f"P{i}", "cluster": "Group_1" if i < 2 else "Group_2", "type": t, "values": v,
              "PFAM": ids, "Pathway": l1, "taxonomic.scope": l2}
             for i, (l1, l2, t, ids, v) in enumerate(rows)]
    p = {"schema_version": 2, "title": "Made up", "timepoints": ["d1", "d2", "d3", "d4"], "subjects": [],
         "clusters": ["Group_1", "Group_2"], "features": feats,
         "id_links": {"PFAM": {"type": "Pfam", "pattern": "PF\\d{5}", "url": "x"}},
         "edges": [{"from": "Group_1", "to": "Group_2", "weight": 2.0}]}
    if dataset is not None:
        p["dataset"] = dataset
    return p


DESCRIBED = {"background": "Proteins of two organs over four days.", "feature": {"name": "protein"},
             "level1": {"column": "Pathway", "source": "fn", "name": "function"},
             "level2": {"column": "taxonomic.scope", "source": "organ", "name": "organ"},
             "samples": {"groups": "One series of four days.", "time": {"about": "day of sampling", "unit": "day"}}}


def test_cheese_card_is_read_from_the_data():
    card = load_dataset().card
    assert card["level1"]["name"] == "phylum" and card["level2"]["name"] == "class"
    assert card["level2"]["relation"] == "nested"            # every class sits under one phylum
    assert card["colour"]["same_as"] == "level1"             # `type` is the phylum again
    assert card["ids"]["KEGG_ID"]["prefix"] == "ko:" and card["ids"]["KEGG_ID"]["example"].startswith("K")
    assert card["ids"]["GO_ID"]["example"].startswith("GO:") and "prefix" not in card["ids"]["GO_ID"]
    ds = load_dataset()
    assert ds.cfg.level1_name == "phylum" and "KEGG ortholog ids such as K" in ds.cfg.level3_notes[1]


def test_page_with_a_description_gives_the_agent_its_words():
    ds = Dataset.from_payload(made_up(DESCRIBED))
    assert (ds.cfg.level1_name, ds.cfg.level2_name) == ("function", "organ")
    assert ds.cfg.background == "Proteins of two organs over four days."
    assert ds.card["level2"]["relation"] == "crossed"        # liver occurs under both functions
    assert "same_as" not in ds.card["colour"]
    assert ds.card["ids"]["PFAM"] == {"type": "Pfam", "name": "Pfam id", "pattern": "PF\\d{5}",
                                      "example": "PF00001", "prefix": "pfam:"}
    assert ds.cfg.level3 == ("ID", "PFAM") and ds.cfg.level3_notes == ("protein id", "Pfam ids such as PF00001")
    context = prompts.parse_context(ds)
    assert "One feature is a protein." in context
    assert "Level 1 (function): signalling, transport" in context
    assert "Level 2 (organ; another kind of tag than the function" in context
    assert "- Samples: One series of four days. day of sampling; unit: day" in context


def test_older_page_without_a_description_gets_generic_words():
    ds = Dataset.from_payload(made_up())
    assert (ds.cfg.level1_name, ds.cfg.level2_name) == ("functional annotation", "taxonomic scope")
    assert ds.card["feature"]["name"] == "feature"
    assert ds.card["level2"]["relation"] == "crossed" and ds.card["ids"]["PFAM"]["prefix"] == "pfam:"


def test_context_file_overrules_the_page_entry_by_entry(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('<script id="molpad-data" type="application/json">' + json.dumps(made_up(DESCRIBED))
                    + "</script>", encoding="utf-8")
    ctx = tmp_path / "ctx.json"
    ctx.write_text(json.dumps({"level2": {"about": "where the protein was measured"}, "level1_name": "role",
                               "feature": "peptide", "ids": {"PFAM": {"name": "domain id"}}}))
    ds = payload.load(page, ctx)
    assert ds.cfg.level1_name == "role"                                     # the older key still works
    assert ds.card["level1"]["source"] == "fn"                              # the rest of the entry stays
    assert ds.card["level2"]["name"] == "organ" and ds.card["level2"]["about"].startswith("where")
    assert ds.card["feature"]["name"] == "peptide" and ds.cfg.level3_notes[1] == "domain ids such as PF00001"
    assert ds.cfg.background == "Proteins of two organs over four days."   # not replaced by the title
    with pytest.raises(ValueError, match="nested"):
        Dataset.from_payload(made_up(), context={"level2": {"relation": "below"}})


def test_mentions_resolve_with_the_words_and_ids_of_another_dataset():
    ds = Dataset.from_payload(made_up(DESCRIBED))
    m = {k["keyword"]: k["matches"] for k in kw.map_keywords(["Liver", "pfam:PF00002", "PF00003", "heart"], ds)["keywords"]}
    assert m["Liver"][0]["level"] == "level2" and sorted(m["Liver"][0]["under_level1"]) == ["signalling", "transport"]
    assert m["pfam:PF00002"] == [{"level": "level3", "column": "PFAM", "value": "PF00002", "n_features": 2}]
    assert m["PF00003"][0]["n_features"] == 1 and m["heart"] == []
    note = kw.map_keywords(["heart"], ds)["notes"][0]
    assert "not a function, a organ" in note
    r = Session(ds).run("filter_level3", column="PFAM", values=["pfam:PF00002", "PF00009"])
    assert r["features_per_id"] == {"PF00002": 2, "PF00009": 0} and r["n_features"] == 2
    top = Session(ds).run("describe_level3", column="PFAM")
    assert "PF00002" in json.dumps(top) and "pfam:" not in json.dumps(top)


def test_ribbon_lines_follow_the_colour_control_of_the_page():
    ds = Dataset.from_payload(made_up(DESCRIBED))

    def run(by):
        return Session(ds, {**ds.default_state(), "colour_by": by}).run(
            "select_by_pattern", criterion="color_divergence")

    by_l1, by_l2, by_type = run("level1"), run("level2"), run("type")
    assert by_l1["lines_by"] == "level1" and by_type["lines_by"] == "type"
    # Group_2: one function, two organs, two types -> no gap by level 1, a gap by level 2 and by type
    assert by_l1["value_per_cluster"]["Group_2"] == 0 and by_l2["value_per_cluster"]["Group_2"] > 0
    assert by_type["value_per_cluster"]["Group_2"] > 0
    assert "not coloured" in run("none")["error"]
    assert "error" not in Session(ds, {**ds.default_state(), "colour_by": "none"}).run(
        "select_by_ribbon", criterion="tightest_ribbon")


def test_no_prompt_keeps_an_unfilled_place():
    for ds in (load_dataset(), Dataset.from_payload(made_up()), None):
        texts = [prompts.PARSE, prompts.COMPOSE, prompts.BREAKDOWN] + [skills.card(n) for n in skills.CARDS]
        for text in texts:
            assert "<<" not in prompts.for_data(text, ds)
    cheese = prompts.for_data(prompts.PARSE, load_dataset())
    assert "a phylum, a class" in cheese and "contig ids, KEGG ortholog ids such as K" in cheese
    other = prompts.for_data(prompts.PARSE, Dataset.from_payload(made_up(DESCRIBED)))
    assert "a function, a organ" in other and "protein ids, Pfam ids such as PF00001" in other


def test_description_lines_for_a_person():
    ds = Dataset.from_payload(made_up(DESCRIBED))
    text = "\n".join(datacard.lines(ds.card, ds))
    assert "Level 1 is the function (2 values, column 'fn' of the annotations)." in text
    assert "PFAM holds Pfam ids such as PF00001, written with the prefix 'pfam:'." in text
    assert "Time points: day of sampling; unit: day." in text


def test_sample_groups_are_found_by_the_words_of_the_description():
    p = made_up({**DESCRIBED, "samples": {"groups": {"X": "the control", "Y": "batch Y; day 2 repeated"}}})
    p["subjects"] = [{"name": "X", "columns": ["d1", "d2"], "labels": ["1", "2"]},
                     {"name": "Y", "columns": ["d3", "d4"], "labels": ["1", "2"]}]
    ds = Dataset.from_payload(p)
    found = {k["keyword"]: [m["value"] for m in k["matches"]]
             for k in kw.map_keywords(["batch X", "the control", "batch Y", "the treated one"], ds)["keywords"]}
    assert found == {"batch X": ["X"], "the control": ["X"], "batch Y": ["Y"], "the treated one": []}
    context = prompts.parse_context(ds)
    assert "X (the control): d1, d2; Y (batch Y; day 2 repeated): d3, d4" in context


def test_a_study_file_written_by_r_works_as_the_context(tmp_path):
    # write_study() names the user's own columns and may carry the column grouping
    study = {"feature": {"name": "protein"}, "level1": {"column": "fn", "name": "function"},
             "level2": {"column": "organ", "name": "organ"}, "colour": {"column": "batch", "name": "batch"},
             "samples": {"groups": "One series.", "columns": {"a": ["d1", "d2"], "b": ["d3", "d4"]}},
             "ids": {"PFAM": {"type": "Pfam"}}}
    ds = Dataset.from_payload(made_up(), context=datacard.normalise(study))
    assert ds.card["level1"] == {"column": "Pathway", "source": "fn", "name": "function"}
    assert ds.card["colour"]["column"] == "type" and ds.card["colour"]["source"] == "batch"
    assert ds.cfg.level1 == "Pathway" and ds.cfg.color == "type"
    assert "columns" not in ds.card["samples"] and ds.card["ids"]["PFAM"]["example"] == "PF00001"
    with pytest.raises(ValueError, match="desing"):
        datacard.normalise({"samples": {"desing": "typo"}})


def test_examples_are_written_with_values_of_the_loaded_data():
    cheese_values = prompts.example_values(load_dataset())
    assert cheese_values["L1A"] in load_dataset().level1_values and cheese_values["GB"] == "C"
    assert cheese_values["T"] == "C_5" and cheese_values["IDCOL"] == "KEGG_ID"
    ds = Dataset.from_payload(made_up(DESCRIBED))
    values = prompts.example_values(ds)
    assert values["L1A"] in ("signalling", "transport") and values["ID"] == "PF00001"
    assert "GA" not in values                                   # one series: no sample groups to name
    for text in [prompts.PARSE, prompts.COMPOSE, prompts.BREAKDOWN] + [skills.card(n) for n in skills.CARDS + ("core", "breakdown")]:
        own = prompts.for_data(text, ds)
        assert "<<" not in own
        for word in ("Pseudomonadota", "Actinomycetota", "cheese", "KEGG", "contig", "C_5", "K11901"):
            assert word not in own, (word, text[:40])
    parse = prompts.for_data(prompts.PARSE, ds)
    assert '"Within signalling and liver, which proteins carry PF00001?"' in parse
    assert "opposite shapes" not in parse                       # an example that needs two sample groups
    assert "opposite shapes" in prompts.for_data(prompts.PARSE, load_dataset())


def test_no_example_is_an_eval_question():
    import csv
    import difflib
    import re

    from agent.tests.eval_trace import QUESTIONS

    with open(QUESTIONS / "cheese_questions.csv", encoding="utf-8", errors="replace") as fh:
        asked = [r["question"].lower() for r in csv.DictReader(fh)]
    ds = load_dataset()
    texts = [prompts.PARSE, prompts.BREAKDOWN] + [skills.card(n) for n in skills.CARDS + ("core", "breakdown")]
    examples = [e.lower() for t in texts for e in re.findall(r'"([^"\n]{25,})"', prompts.for_data(t, ds))]
    assert len(examples) > 50
    for e in examples:
        assert all(difflib.SequenceMatcher(None, e, q).ratio() < 0.97 for q in asked), e
