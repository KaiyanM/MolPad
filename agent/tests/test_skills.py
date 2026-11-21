"""Skill cards picked from the roles of a question. No LLM."""

from agent.skills import CARDS, card, pick_skills, plan_prompt


def test_every_card_exists():
    for name in ("core",) + CARDS:
        assert card(name)


def test_q04_similar_shape_reads_curves_not_the_network():
    # step 1 finds the cluster, step 2 starts from it and compares curves
    frames = [{"target": ["feature_number"], "measure": ["pattern"]},
              {"target": ["given", "pattern"], "measure": ["pattern"], "compare": "curves", "uses": 1}]
    assert pick_skills(frames) == ["pattern", "compare", "feature_number", "given"]


def test_breakdown_card_has_the_templates():
    text = card("breakdown")
    assert all(t in text for t in ("find, then relate", "find, then check", "hypothesis"))


def test_q05_curves_load_pattern_and_compare():
    assert pick_skills([{"target": ["pattern"], "compare": "curves"}]) == ["pattern", "compare"]


def test_q07_ribbon():
    assert pick_skills([{"target": ["ribbon"]}]) == ["ribbon"]


def test_q20_outside_concept_loads_lookup():
    assert "lookup" in pick_skills([{"target": ["feature_lookup"], "outside_concept": "Type IV secretion"}])


def test_q31_example():
    assert pick_skills([{"target": ["example"], "measure": ["pattern"]}]) == ["example"]


def test_q37_components_load_network():
    assert pick_skills([{"target": ["all"], "measure": ["weight"]}]) == ["network"]


def test_selection_loads_given():
    assert "given" in pick_skills([{"target": [], "measure": ["level3"]}], status="use_current_selection")


def test_nothing_read_loads_every_card():
    assert pick_skills([{}]) == list(CARDS)


def test_core_only_is_much_smaller_than_all_cards():
    assert len(plan_prompt([])) * 2 < len(plan_prompt(CARDS))
