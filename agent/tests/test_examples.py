"""Example finders (agent/examples.py) on the real CSVs. No LLM."""

import pytest

from agent.data_tools import Session, load_dataset
from agent.examples import examples_by_level2_composition
from agent.findings import conclude


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


def test_level2_composition_picks_highest_share(ds):
    s = Session(ds)
    r = examples_by_level2_composition(s, ["Flavobacteriia", "Bacilli"])
    assert [g["clusters"] for g in r["groups"]] == [["Group_3"], ["Group_4"]]
    assert r["groups"][0]["label"] == "example of Flavobacteriia"
    d = r["details"]["Flavobacteriia"]["Group_3"]
    assert d["share"] == pytest.approx(830 / 4033, abs=1e-3)
    assert "of its features are Flavobacteriia" in r["groups"][0]["why"]


def test_shares_ignore_level2_filter(ds):
    s = Session(ds)
    s.run("filter_level2", values=["Flavobacteriia", "Bacilli"])
    r = s.run("select_examples", by="level2_composition")
    assert r["values"] == ["Flavobacteriia", "Bacilli"]           # taken from the filter
    assert r["details"]["Bacilli"]["Group_4"]["share"] == pytest.approx(5482 / 17011, abs=1e-3)
    assert s.targets == ["Group_3", "Group_4"]


def test_small_clusters_are_skipped(ds):
    s = Session(ds)
    r = examples_by_level2_composition(s, ["Flavobacteriia"], top_n=10)
    picked = [g["clusters"][0] for g in r["groups"]]
    assert "Group_10" not in picked and "Group_7" not in picked   # 1 feature each


def test_needs_values_and_known_finder(ds):
    s = Session(ds)
    assert "error" in s.run("select_examples", by="level2_composition")
    assert "no example finder" in s.run("select_examples", by="ribbon", values=["Bacilli"])["error"]


def test_findings_line(ds):
    s = Session(ds)
    r = s.run("select_examples", values=["Bacilli"])
    line = conclude("select_examples", {}, r)[0]
    assert line.startswith("example of Bacilli: Group_4 (32% of its features are Bacilli")
