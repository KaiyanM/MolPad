"""Frame pipeline, code part: mentions with roles -> N3 filters, on the real CSVs. No LLM."""

import pytest

from agent.data_tools import load_dataset
from agent.frame import resolve


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


def frame(*mentions, compare="none", **kw):
    return {"mentions": [{"text": t, "role": r} for t, r in mentions], "compare": compare, **kw}


def filters(ds, fr):
    return resolve(fr, ds)[1]


def test_q15_level1_condition(ds):
    f = filters(ds, frame(("Pseudomonadota", "condition")))
    assert f["level1"] == ["Pseudomonadota"] and f["level2"] == [] and f["contrast"] == "none"


def test_q16_with_and_without_level2(ds):
    f = filters(ds, frame(("Pseudomonadota", "condition"), ("Gammaproteobacteria", "compare"),
                          compare="with_and_without_level2"))
    assert f["level1"] == ["Pseudomonadota"]
    assert f["level2"] == ["Gammaproteobacteria"]
    assert f["contrast"] == "with_and_without_level2"


def test_q17_level2_contrast(ds):
    f = filters(ds, frame(("Bacillota", "condition"), ("Bacilli", "compare"), ("Clostridia", "compare"),
                          compare="level2"))
    assert f["level2"] == ["Bacilli", "Clostridia"] and f["contrast"] == "level2"


def test_q18_ids_are_level3_filter(ds):
    f = filters(ds, frame(("Pseudomonadota", "condition"), ("Gammaproteobacteria", "condition"),
                          ("K11901", "condition")))
    assert f["level3_column"] == "KEGG_ID" and "K11901" in f["level3_values"]
    assert f["level3_has_annotation"] is False


def test_q19_annotation_column_named_in_words(ds):
    f = filters(ds, frame(("Actinomycetota", "condition"), ("GO annotation", "condition")))
    assert f["level3_column"] == "GO_ID" and f["level3_has_annotation"] is True


def test_q20_outside_concept_ids(ds):
    f = filters(ds, frame(outside_concept="Type IV secretion", outside_ids=["K03196", "K03197"]))
    assert f["external_concept"] == "Type IV secretion"
    assert f["level3_column"] == "KEGG_ID"
    assert f["level3_values"] == ["K03196", "K03197"]


def test_q33_measured_class_is_not_a_filter(ds):
    kmap, f, roles = resolve(frame(("Gammaproteobacteria", "measure")), ds)
    assert f["level2"] == []
    assert "level2=Gammaproteobacteria" in roles[0]


def test_q34_rank_by_phylum_filters(ds):
    assert filters(ds, frame(("Actinomycetota", "condition")))["level1"] == ["Actinomycetota"]


def test_sample_group_condition_sets_cols(ds):
    assert filters(ds, frame(("A", "condition")))["cols"] == "A"


def test_q03_compared_sample_groups_do_not_set_cols(ds):
    assert filters(ds, frame(("A", "compare"), ("C", "compare"), compare="curves"))["cols"] is None


def test_unknown_mention_is_reported(ds):
    kmap, f, roles = resolve(frame(("Archaea", "condition")), ds)
    assert f["level1"] == [] and "not in the data" in roles[0]
    assert kmap["notes"]


def test_exact_phylum_beats_close_class_spelling(ds):
    kmap, f, roles = resolve(frame(("Actinomycetota", "condition")), ds)
    assert f["level1"] == ["Actinomycetota"] and f["level2"] == []
    assert "Actinomycetes" not in roles[0]


def test_compared_taxa_without_level_contrast_are_not_filters(ds):
    f = filters(ds, frame(("Actinomycetota", "condition"), ("Bacillota", "compare")))
    assert f["level1"] == ["Actinomycetota"]
