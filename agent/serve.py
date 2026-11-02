"""Local server that links the D3 dashboard chat to the agent.

    R:       gDashboard_d3(...)                                    -> .../index.html
    Python:  python -m agent.serve --dashboard .../index.html [--context my_data.json]

Then type a question in the dashboard chat. The page sends it, with the current
dashboard state, to this server and plays back the steps it gets.

    GET  /health   {"ok", "model", "judge_tier", "title", "clusters", "timepoints"}
    POST /ask      {"question": str, "state": {...}} -> {"question", "trace", "steps"}

The agent reads the data from the same dashboard page (agent/payload.py), so both
sides see the same data. Without --dashboard it reads the CSVs of config.py.

The server spends API credits, so it listens on 127.0.0.1 only and answers pages
opened from a file (origin "null") or from localhost; other origins get 403.
"""

import argparse
import json
import re
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import graph
from .data_tools import load_dataset, use_dataset

DEFAULT_PORT = 8765
MAX_BODY = 1_000_000
_LOCAL = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$")
_lock = threading.Lock()


def allowed_origin(origin):
    """The page's origin when it may use the agent; None otherwise.

    No Origin header (curl, scripts on this machine) is allowed too; browsers always send one
    on a cross-origin request.
    """
    if origin is None:
        return "*"
    if origin == "null" or _LOCAL.match(origin):
        return origin
    return None


def clean_state(raw, ds):
    """The dashboard state as the agent reads it: known keys, valid values, defaults for the rest."""
    state = ds.default_state()
    raw = raw if isinstance(raw, dict) else {}
    if isinstance(raw.get("min_weight"), (int, float)) and not isinstance(raw["min_weight"], bool):
        state["min_weight"] = float(raw["min_weight"])
    if isinstance(raw.get("selected_clusters"), list):
        picked = [c for c in raw["selected_clusters"] if c in ds.clusters]
        state["selected_clusters"] = picked or state["selected_clusters"]
    for key, valid in (("level1", ds.level1_values), ("level2", ds.level2_values)):
        if isinstance(raw.get(key), list):
            state[key] = [v for v in raw[key] if v in valid]
    if not state["level1"] and raw.get("pathway") in ds.level1_values:   # an older page
        state["level1"] = [raw["pathway"]]
    state["pathway"] = state["level1"][0] if len(state["level1"]) == 1 else ""
    if raw.get("scope") in ("filtered", "all"):
        state["scope"] = raw["scope"]
    if raw.get("colour_by") in ("level1", "level2", "type", "none"):
        state["colour_by"] = raw["colour_by"]
    if isinstance(raw.get("layout"), str):
        state["layout"] = raw["layout"]
    return state


def health():
    from .llm import JUDGE_TIER, _MODELS, llm_source

    ds = load_dataset()
    return {"ok": True, "model": _MODELS.get(llm_source()), "judge_tier": JUDGE_TIER,
            "title": getattr(ds, "title", None), "clusters": ds.clusters, "timepoints": ds.timepoints}


class Handler(BaseHTTPRequestHandler):
    server_version = "MolPadAgent/1"

    def _origin(self):
        return allowed_origin(self.headers.get("Origin"))

    def _send(self, code, body, origin):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        origin = self._origin()
        if not origin:
            return self._send(403, {"error": "origin not allowed"}, None)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self):
        origin = self._origin()
        if not origin:
            return self._send(403, {"error": "origin not allowed"}, None)
        if self.path.rstrip("/") == "/health":
            return self._send(200, health(), origin)
        return self._send(404, {"error": "unknown path; use GET /health or POST /ask"}, origin)

    def do_POST(self):
        origin = self._origin()
        if not origin:
            return self._send(403, {"error": "origin not allowed"}, None)
        if self.path.rstrip("/") != "/ask":
            return self._send(404, {"error": "unknown path; use POST /ask"}, origin)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._send(413, {"error": "request too large"}, origin)
            body = json.loads(self.rfile.read(n) or b"{}")
            question = str(body.get("question") or "").strip()
        except (ValueError, AttributeError):
            return self._send(400, {"error": "send JSON: {\"question\": ..., \"state\": {...}}"}, origin)
        if not question:
            return self._send(400, {"error": "the question is empty"}, origin)
        if not _lock.acquire(blocking=False):
            return self._send(409, {"error": "the agent is still answering the previous question"}, origin)
        t0 = time.time()
        try:
            out = graph.answer(question, clean_state(body.get("state"), load_dataset()))
        except Exception as exc:   # report it in the chat; the traceback stays in the server log
            traceback.print_exc()
            return self._send(500, {"error": f"the agent failed: {type(exc).__name__}: {exc}"}, origin)
        finally:
            _lock.release()
        print(f"[serve] {time.time() - t0:5.1f}s  leaf {out['trace'].get('leaf')}  {question}",
              file=sys.stderr, flush=True)
        return self._send(200, out, origin)

    def log_message(self, fmt, *args):   # one line per question is printed above instead
        pass


def make_server(port=DEFAULT_PORT):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    p = argparse.ArgumentParser(description="Link the MolPad dashboard chat to the agent.")
    p.add_argument("--dashboard", help="index.html written by gDashboard_d3() (or its JSON payload); "
                   "default: the CSVs named in agent/config.py")
    p.add_argument("--context", help="JSON file with background, level1_name, level2_name, missing "
                   "(see agent/contexts/cheese.json)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--debug", action="store_true", help="print each LLM decision as a [debug] line")
    a = p.parse_args()

    from . import nodes

    nodes.DEBUG = a.debug or nodes.DEBUG
    if a.dashboard:
        from .payload import load

        use_dataset(load(a.dashboard, a.context))
    ds = load_dataset()
    print(f"[serve] data: {a.dashboard or 'CSV files of agent/config.py'}; {len(ds.features):,} features, "
          f"{len(ds.clusters)} clusters, sample groups {', '.join(ds.subjects)}", file=sys.stderr)
    server = make_server(a.port)
    print(f"[serve] agent listening on http://127.0.0.1:{a.port}  (Ctrl+C to stop)", file=sys.stderr,
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
