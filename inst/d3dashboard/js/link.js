/* MolPad D3 dashboard: connection to the local Python agent (python -m agent.serve).

   The address is ?agent=<url> in the page address, else http://127.0.0.1:8765.
   check() asks GET /health; ask() sends a question with the current dashboard
   state to POST /ask and resolves with the agent's step list. */
(function (MP) {
  "use strict";

  var DEFAULT_URL = "http://127.0.0.1:8765";
  var ASK_TIMEOUT_MS = 300000;
  var info = null;     // the /health reply while connected, else null

  function url() {
    var m = /[?&]agent=([^&#]*)/.exec(window.location.search || "");
    var u = m ? decodeURIComponent(m[1]) : DEFAULT_URL;
    return u.replace(/\/+$/, "");
  }

  /* fetch with a time limit; rejects with an Error whose message can be shown. */
  function request(path, options, ms) {
    var ctrl = window.AbortController ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, ms) : null;
    var opts = Object.assign({}, options || {});
    if (ctrl) opts.signal = ctrl.signal;
    return fetch(url() + path, opts).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        if (!res.ok) throw new Error(body.error || ("The agent answered " + res.status + "."));
        return body;
      });
    }, function (err) {
      if (err && err.name === "AbortError") throw new Error("The agent did not answer in time.");
      throw new Error("The agent is not reachable at " + url() + ".");
    }).then(function (body) {
      if (timer) clearTimeout(timer);
      return body;
    }, function (err) {
      if (timer) clearTimeout(timer);
      throw err;
    });
  }

  /* Resolves with the /health reply, or null when the agent is not running. */
  function check() {
    return request("/health", { method: "GET" }, 2000).then(function (body) {
      info = body;
      return body;
    }, function () {
      info = null;
      return null;
    });
  }

  /* Clusters on one side only: the agent and the page read different data. */
  function mismatch() {
    if (!info || !MP.D) return [];
    var page = MP.D.clusters || [], agent = info.clusters || [];
    return page.filter(function (c) { return agent.indexOf(c) < 0; })
      .concat(agent.filter(function (c) { return page.indexOf(c) < 0; }));
  }

  /* The dashboard state in the form the agent reads (agent/data_tools.py default_state). */
  function dashState() {
    var S = MP.state.get();
    return {
      level1: S.level1.slice(),          // [] = all
      level2: S.level2.slice(),          // [] = all
      scope: S.scope,                    // what the cluster views show: "filtered" | "all"
      colour_by: S.colourBy,
      pathway: S.level1.length === 1 ? S.level1[0] : "",   // older agents read this
      taxa: S.level2.slice(),
      min_weight: S.minWeight,
      selected_clusters: S.selectedClusters.slice(),
      layout: S.layout
    };
  }

  /* Send a question. The agent answers with one JSON event per line while it works; each is
     passed to onEvent as it arrives:
       {event: "status", text}   what the agent is doing now
       {event: "plan", text}     the steps of the argument
       {event: "steps", steps}   the playback; a message is {slot, text: null} until its text comes
       {event: "text", slot, text}
       {event: "done", trace}
     Resolves with the trace when the answer is complete. An agent that does not stream answers
     with the whole step list at once; it is passed on as one "steps" event. */
  function ask(question, onEvent) {
    onEvent = onEvent || function () {};
    var ctrl = window.AbortController ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, ASK_TIMEOUT_MS) : null;
    var trace = null;

    function handle(ev) {
      if (!ev || !ev.event) return;
      if (ev.event === "error") throw new Error(ev.error || "The agent failed.");
      if (ev.event === "done") trace = ev.trace || {};
      onEvent(ev);
    }

    function readLines(res) {
      var buffer = "";
      function feed(chunk, last) {
        buffer += chunk;
        var lines = buffer.split("\n");
        buffer = last ? "" : lines.pop();
        lines.forEach(function (line) { if (line.trim()) handle(JSON.parse(line)); });
      }
      if (!res.body || !res.body.getReader || !window.TextDecoder) {
        return res.text().then(function (all) { feed(all, true); });
      }
      var reader = res.body.getReader(), decoder = new TextDecoder("utf-8");
      function pump() {
        return reader.read().then(function (part) {
          if (part.done) { feed(decoder.decode(), true); return null; }
          feed(decoder.decode(part.value, { stream: true }), false);
          return pump();
        });
      }
      return pump();
    }

    var opts = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, state: dashState(), stream: true })
    };
    if (ctrl) opts.signal = ctrl.signal;
    return fetch(url() + "/ask", opts).then(function (res) {
      var type = res.headers.get("Content-Type") || "";
      if (!res.ok || type.indexOf("ndjson") < 0) {
        return res.json().catch(function () { return {}; }).then(function (body) {
          if (!res.ok) throw new Error(body.error || ("The agent answered " + res.status + "."));
          onEvent({ event: "steps", steps: body.steps || [] });   // an agent that does not stream
          trace = body.trace || {};
        });
      }
      return readLines(res).then(function () {
        if (trace === null) throw new Error("The agent stopped before the answer was complete.");
      });
    }, function (err) {
      if (err && err.name === "AbortError") throw new Error("The agent did not answer in time.");
      throw new Error("The agent is not reachable at " + url() + ".");
    }).then(function () {
      if (timer) clearTimeout(timer);
      return trace;
    }, function (err) {
      if (timer) clearTimeout(timer);
      if (err && err.name === "AbortError") throw new Error("The agent did not answer in time.");
      throw err;
    });
  }

  MP.link = {
    url: url,
    check: check,
    ask: ask,
    mismatch: mismatch,
    connected: function () { return !!info; },
    info: function () { return info; }
  };
})(window.MolPad = window.MolPad || {});
