"""The local agent server and the dashboard-JSON loader. No LLM: graph.answer is replaced."""

import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from agent import graph, payload, serve
from agent.data_tools import Dataset, Session, load_dataset


@pytest.fixture()
def server(monkeypatch):
    calls = []

    def fake_answer(question, state=None, debug=None):
        calls.append((question, state))
        if question == "slow":
            time.sleep(0.5)
        if question == "boom":
            raise RuntimeError("bad luck")
        return {"question": question, "trace": {"leaf": "L3"},
                "steps": [{"kind": "message", "text": "hi", "evidence": []}]}

    monkeypatch.setattr(graph, "answer", fake_answer)
    srv = serve.make_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", calls
    srv.shutdown()
    srv.server_close()


def call(url, path, body=None, origin="null", method=None):
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    req = urllib.request.Request(url + path, data=data, method=method)
    if origin:
        req.add_header("Origin", origin)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, dict(e.headers), json.loads(raw) if raw else {}


def test_health_lists_the_clusters(server):
    url, _ = server
    code, headers, body = call(url, "/health")
    assert code == 200 and body["ok"] and body["clusters"] == load_dataset().clusters
    assert headers["Access-Control-Allow-Origin"] == "null"


def test_ask_passes_a_cleaned_state(server):
    url, calls = server
    state = {"min_weight": 2.5, "selected_clusters": ["Group_3", "Group_99"], "pathway": "nope",
             "layout": "circle", "taxa": [], "extra": 1}
    code, _, body = call(url, "/ask", {"question": " Which cluster? ", "state": state})
    assert code == 200 and body["steps"][0]["text"] == "hi"
    question, sent = calls[0]
    assert question == "Which cluster?"
    assert sent["min_weight"] == 2.5 and sent["selected_clusters"] == ["Group_3"]
    assert sent["pathway"] == load_dataset().default_state()["pathway"] and "extra" not in sent


def test_preflight_from_a_file_page(server):
    url, _ = server
    code, headers, _ = call(url, "/ask", origin="null", method="OPTIONS")
    assert code == 204
    assert headers["Access-Control-Allow-Origin"] == "null"
    assert headers["Access-Control-Allow-Private-Network"] == "true"
    assert "POST" in headers["Access-Control-Allow-Methods"]


@pytest.mark.parametrize("origin, ok", [("null", True), ("http://localhost:3000", True),
                                        ("http://127.0.0.1:8000", True), ("https://example.com", False),
                                        ("http://localhost.evil.com", False)])
def test_only_local_pages_may_ask(server, origin, ok):
    url, calls = server
    code, _, _ = call(url, "/ask", {"question": "q"}, origin=origin)
    assert (code == 200) == ok and (len(calls) == 1) == ok


def test_bad_requests(server):
    url, calls = server
    assert call(url, "/ask", b"not json")[0] == 400
    assert call(url, "/ask", {"question": "   "})[0] == 400
    assert call(url, "/nowhere")[0] == 404
    code, _, body = call(url, "/ask", {"question": "boom"})
    assert code == 500 and "bad luck" in body["error"]


def test_one_question_at_a_time(server):
    url, _ = server
    first = threading.Thread(target=call, args=(url, "/ask", {"question": "slow"}))
    first.start()
    time.sleep(0.15)
    code, _, body = call(url, "/ask", {"question": "second"})
    first.join()
    assert code == 409 and "still answering" in body["error"]


def small_payload():
    """A dashboard JSON as gDashboard_d3() writes it, with two sample groups and a gap in C."""
    feats = []
    for i, (cl, vals) in enumerate([("G_1", [0, 1, 2, 3, 0, 1, 2]), ("G_1", [0, 2, 3, 4, 0, 2, 3]),
                                    ("G_2", [3, 2, 1, 0, 2, 1, 0]), ("G_2", [4, 3, 1, 0, 3, 2, 0]),
                                    ("G_2", [1, 1, 1, 1, 1, 1, 1])]):
        feats.append({"ID": str(i), "cluster": cl, "type": "x", "values": vals, "GO_ID": "-",
                      "KEGG_ID": "K00001" if i == 0 else "-", "Pathway": "P1" if i < 3 else "P2",
                      "taxonomic.scope": None if i == 4 else "T1"})
    return {"schema_version": 2, "title": "Tiny", "timepoints": ["A_1", "A_2", "A_3", "A_4", "C_1", "C_3", "C_4"],
            "subjects": [{"name": "A", "columns": ["A_1", "A_2", "A_3", "A_4"], "labels": ["1", "2", "3", "4"]},
                         {"name": "C", "columns": ["C_1", "C_3", "C_4"], "labels": ["1", "3", "4"]}],
            "clusters": ["G_1", "G_2", "G_3"], "features": feats,
            "id_links": {"KEGG_ID": {"type": "KEGG", "pattern": "K\\\\d{5}", "url": "x"}},
            "edges": [{"from": "G_1", "to": "G_2", "weight": 2.0}, {"from": "G_2", "to": "G_3", "weight": None}],
            "weight_slider": {"min": 0, "max": 2, "value": 1, "step": 0.1}}


def test_dataset_from_a_dashboard_page(tmp_path):
    p = small_payload()
    page = tmp_path / "index.html"
    page.write_text('<html><script id="molpad-data" type="application/json">'
                    + json.dumps(p).replace("</", "<\\/") + "</script></html>", encoding="utf-8")
    ctx = tmp_path / "ctx.json"
    ctx.write_text(json.dumps({"level1_name": "pathway", "background": "Tiny test data."}))
    ds = payload.load(page, ctx)
    assert len(ds.features) == 4                              # no taxonomic scope -> left out
    assert ds.subjects == {"A": ["A_1", "A_2", "A_3", "A_4"], "C": ["C_1", "C_3", "C_4"]}
    assert ds.times["C_3"] == 3.0 and ds.time_position("C_3") == pytest.approx(2 / 3)
    assert ds.cfg.level3 == ("ID", "KEGG_ID") and "KEGG" in ds.cfg.level3_notes[1]
    assert ds.cfg.level1_name == "pathway" and ds.cfg.level2_name == "taxonomic scope"
    assert ds.cluster_name("2") == "G_2" and ds.clusters == ["G_1", "G_2", "G_3"]
    assert len(ds.edges) == 1 and ds.default_threshold == 1 and ds.slider_max == 2
    s = Session(ds)
    r = s.run("select_by_pattern", criterion="increase_and_decrease")
    assert r["groups"][0]["clusters"] == ["G_1"] and r["groups"][1]["clusters"] == ["G_2"]
    assert Session(ds).run("select_by_network", criterion="strongest_edge")["groups"][0]["clusters"] == ["G_1", "G_2"]


def test_context_file_rejects_unknown_keys(tmp_path):
    ctx = tmp_path / "ctx.json"
    ctx.write_text(json.dumps({"backround": "typo"}))
    with pytest.raises(ValueError, match="backround"):
        payload.read_context(ctx)


def test_not_a_dashboard(tmp_path):
    page = tmp_path / "x.html"
    page.write_text("<html></html>")
    with pytest.raises(ValueError, match="molpad-data"):
        payload.read_payload(page)


def test_clean_state_reads_shared_filters():
    ds = load_dataset()
    s = serve.clean_state({"level1": ["Pseudomonadota", "Nope"], "level2": ["Bacilli"],
                           "scope": "all", "colour_by": "level2"}, ds)
    assert s["level1"] == ["Pseudomonadota"] and s["level2"] == ["Bacilli"]
    assert s["pathway"] == "Pseudomonadota" and s["scope"] == "all" and s["colour_by"] == "level2"
    old = serve.clean_state({"pathway": "Bacillota"}, ds)          # a page from before the filter bar
    assert old["level1"] == ["Bacillota"]
    default = serve.clean_state({}, ds)
    assert default["level1"] == [] and default["scope"] == "filtered" and default["pathway"] == ""
