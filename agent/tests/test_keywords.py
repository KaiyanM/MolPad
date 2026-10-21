"""Keyword map on the real CSVs. No LLM."""

import pytest

from agent import keywords as kw
from agent.data_tools import load_dataset


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


def levels(kmap, word):
    entry = next(k for k in kmap["keywords"] if k["keyword"] == word)
    return [(m["level"], m["value"]) for m in entry["matches"]]


def test_vocabulary_lists_unique_values(ds):
    v = kw.vocabulary(ds)
    assert v["level1"]["values"] == ["Actinomycetota", "Bacillota", "Bacteroidota", "Pseudomonadota"]
    assert "Clostridia" in v["level2"]["values"]
    assert v["level2"]["parents"]["Clostridia"] == ["Bacillota"]
    assert len(v["level2"]["parents"]["Unknown"]) > 1


def test_keywords_are_found_in_their_level(ds):
    m = kw.map_keywords(["Pseudomonadota", "gammaproteobacteria", "K11901", "cheese A", "C_5", "cluster 3"], ds)
    assert levels(m, "Pseudomonadota") == [("level1", "Pseudomonadota")]
    assert levels(m, "gammaproteobacteria") == [("level2", "Gammaproteobacteria")]
    assert levels(m, "K11901") == [("level3", "K11901")]
    assert levels(m, "cheese A") == [("sample_group", "A")]
    assert levels(m, "C_5") == [("timepoint", "C_5")]
    assert levels(m, "cluster 3") == [("cluster", "Group_3")]
    assert m["notes"] == []


def test_close_spelling_and_unknown_category(ds):
    m = kw.map_keywords(["Pseudomonadotta", "unknown"], ds)
    entry = m["keywords"][0]["matches"][0]
    assert (entry["value"], entry["match"]) == ("Pseudomonadota", "close spelling")
    assert levels(m, "unknown") == [("level2", "Unknown")]


def test_outside_concept_is_marked_unknown(ds):
    m = kw.map_keywords(["Type IV secretion"], ds)
    assert m["keywords"][0].get("unknown") and len(m["notes"]) == 1


def test_level2_outside_the_named_level1_is_noted(ds):
    m = kw.map_keywords(["Pseudomonadota", "Clostridia"], ds)
    assert any("Clostridia is a class of Bacillota" in n for n in m["notes"])
    assert kw.map_keywords(["Bacillota", "Clostridia"], ds)["notes"] == []
    assert "under Bacillota" in kw.as_text(m)
