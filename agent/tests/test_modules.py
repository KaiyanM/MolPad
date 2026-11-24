"""The module manifests: they load, they agree with the page, and they describe the links."""

import re
from pathlib import Path

import pytest

from agent import describe
from agent.core import config
from agent.core import links, module

JS = Path(__file__).resolve().parents[2] / "inst" / "d3dashboard" / "js"
MODS = module.manifests()


def _subscribed(script):
    """State fields a page script subscribes to."""
    text = (JS / script).read_text(encoding="utf-8")
    return {k for keys in re.findall(r"subscribe\(\[([^\]]*)\]", text) for k in re.findall(r'"(\w+)"', keys)}


def test_state_fields_are_those_of_the_page():
    text = (JS / "state.js").read_text(encoding="utf-8")
    block = text[text.index("    S = {"):]
    fields = set(re.findall(r"^\s+(\w+):", block[:block.index("};")], re.M))
    assert fields == set(module.STATE)


@pytest.mark.parametrize("m", [m for m in MODS if m.kind == "view"], ids=lambda m: m.name)
def test_a_view_reads_what_its_script_subscribes_to(m):
    assert set(m.reads) == _subscribed(m.js)


def test_every_control_the_page_listens_to_has_an_owner():
    written = {f for m in MODS for f in m.writes}
    assert _subscribed("controls.js") <= written
    assert set(module.by_name("filters", code=False).reads) <= _subscribed("controls.js")
    assert written == set(module.STATE)


def test_commands_are_those_of_the_page():
    text = (JS / "agent.js").read_text(encoding="utf-8")
    block = text[text.index("var commands = {"):]
    on_page = set(re.findall(r'^\s+"([a-z0-9 ]+)": \{ usage', block[:block.index("};")], re.M))
    ours = set(module.commands())
    # "print message" belongs to the chat, and "set color" is a second spelling of "set colour"
    assert on_page - {"print message", "set color"} == ours
    assert config.SUPPORTED_COMMANDS == ours | {"print message"}


def test_links_follow_from_reads_and_writes():
    got = set(links.links())
    assert ("network", "selectedClusters", "stackbar") in got
    assert ("filters", "level1", "network") in got
    assert ("filters", "scope", "table") in got
    assert not any(to == "network" and f == "scope" for _, f, to in got)   # node colours ignore the scope
    assert links.follows("stackbar")["level2"]["set_by"] == ["filters"]


def test_each_name_has_one_owner():
    assert module.owner("selectors", "network", code=False).name == "network"
    assert module.owner("measures", "level2", code=False).name == "stackbar"
    assert module.owner("cards", "nothing", code=False) is None


def test_describe_names_every_part_and_field():
    text = describe.text()
    for m in MODS:
        assert f"## {m.title}" in text
    for f in module.STATE:
        assert f"\n{f}: " in text
    assert describe.as_json(["ribbon"])["modules"][0]["name"] == "ribbon"


def test_a_manifest_that_names_a_missing_operation_fails(tmp_path, monkeypatch):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "module.json").write_text(
        '{"name": "x", "title": "X", "selectors": {"k": "select_x"}}', encoding="utf-8")
    monkeypatch.setattr(module, "MODULES_DIR", tmp_path)
    with pytest.raises(module.ModuleError, match="select_x"):
        module.load("x", code=False)


def test_words_of_the_plan_cover_the_modules():
    from agent.core import schemas, skills
    kinds = {k for m in MODS for k in m.selectors}
    assert set(schemas.SELECTOR_KINDS) == kinds
    assert set(schemas.MEASURES) == {k for m in MODS for k in m.measures}
    assert set(skills.CARDS) == {Path(f).stem for m in MODS for f in m.cards.values()}
    assert set(skills._BY_TARGET) == kinds - {"all"}
    assert schemas.COMPARE_TOOLS and schemas.RIBBON_MEASURES[-1] == "all"


def test_the_session_has_every_operation_of_every_module():
    from agent.core.data_tools import Session
    assert set(Session.OPS) == {o for m in module.modules() for o in m.ops}
    assert all(callable(getattr(Session, o)) for o in Session.OPS)


def test_a_reference_named_in_the_manifest_must_be_there(tmp_path, monkeypatch):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "module.json").write_text(
        '{"name": "x", "title": "X", "knowledge": {"file": "method.md", "writer": "How to word it"}}', encoding="utf-8")
    monkeypatch.setattr(module, "MODULES_DIR", tmp_path)
    with pytest.raises(module.ModuleError, match="method.md"):
        module.load("x", code=False)
    (tmp_path / "x" / "method.md").write_text("# X\n\n## Limits\n- none\n", encoding="utf-8")
    with pytest.raises(module.ModuleError, match="How to word it"):
        module.load("x", code=False)
    (tmp_path / "x" / "method.md").write_text("# X\n\n## How to word it\n- say linked\n\n## Sources\n- a\n", encoding="utf-8")
    m = module.load("x", code=False)
    assert m.writer_notes() == "- say linked" and m.reference().startswith("# X")


def test_parts_that_can_explain_themselves():
    assert set(module.explainable()) >= {"network", "clusters"}
    net = module.by_name("network")
    assert net.avoid().findall("it causes, because it is significantly linked") == ["causes", "significantly"]
    assert "ranking, not a test" in net.writer_notes() and "Sources" not in net.writer_notes()
