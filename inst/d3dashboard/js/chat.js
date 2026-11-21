/* MolPad D3 dashboard: dialogue panel.

   What is typed goes to one of three places:
     a pasted step list ({...} or [...])  -> played (MP.agent.play)
     a known command ("brush node:...")    -> run with the pointer (MP.agent.run)
     anything else                          -> a question for the Python agent (MP.link) */
(function (MP) {
  "use strict";

  var el = {};

  function node(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  /* A closed "Evidence" dropdown under an agent message: per data step its
     action, its findings, and a second dropdown with the full numbers. */
  function evidenceBox(evidence) {
    var box = node("details", "mp-chat-evidence");
    box.appendChild(node("summary", null, "Evidence (" + evidence.length + ")"));
    evidence.forEach(function (step) {
      var item = node("div", "mp-ev-step");
      item.appendChild(node("div", "mp-ev-action", step.action));
      var list = node("ul", "mp-ev-findings");
      (step.findings || []).forEach(function (line) { list.appendChild(node("li", null, line)); });
      item.appendChild(list);
      var raw = node("details", "mp-ev-raw");
      raw.appendChild(node("summary", null, "Numbers"));
      raw.appendChild(node("pre", null, JSON.stringify(step.result, null, 1)));
      item.appendChild(raw);
      box.appendChild(item);
    });
    return box;
  }

  /* The body of the unit block that is open now: lines are printed there. null = the log itself. */
  var into = null;

  function say(text, kind, evidence) {
    var p = node("div", "mp-chat-msg " + kind);
    if (kind === "reason") p.appendChild(node("b", null, "Reasoning"));
    if (kind === "answer") p.appendChild(node("b", null, "Answer"));
    p.appendChild(node("span", null, text));
    if (evidence && evidence.length) p.appendChild(evidenceBox(evidence));
    (into || el.chat_log).appendChild(p);
    el.chat_log.scrollTop = el.chat_log.scrollHeight;
    return p;
  }

  /* One unit of the answer: a (sub-)question, why it is asked, what was assumed, and the
     actions in the order they will be played. The actions and messages of the unit are then
     printed inside the block. openUnit(null) closes the block: later lines go to the log.
     Returns the heading elements it made (none when there is nothing to head). */
  function openUnit(step) {
    into = null;
    if (!step) return [];
    var several = step.of > 1;
    var assumed = step.assumed || [];
    if (!several && !step.reason && !assumed.length && !step.overview) return [];   // nothing to head
    var box = node("section", "mp-chat-unit");
    var made = [];
    if (several) {
      var head = node("div", "mp-unit-head");
      head.appendChild(node("b", null, "Step " + (step.unit + 1) + " of " + step.of));
      head.appendChild(node("span", "mp-unit-q", step.question));
      box.appendChild(head);
      made.push(head);
    }
    function line(cls, label, text) {
      var d = node("div", "mp-unit-line " + cls);
      d.appendChild(node("b", null, label));
      d.appendChild(node("span", null, text));
      box.appendChild(d);
      made.push(d);
    }
    if (step.reason) line("why", "Why", step.reason);
    assumed.forEach(function (a) { line("assumed", "Assumed", a); });
    if (step.overview) line("overview", "Actions", step.overview);
    into = node("div", "mp-unit-body");
    box.appendChild(into);
    el.chat_log.appendChild(box);
    el.chat_log.scrollTop = el.chat_log.scrollHeight;
    return made;
  }

  /* While a round is played or replayed nothing else may start: the input and every Replay
     button are disabled, except `keep` (the button of the replay that runs, which stops it). */
  function busy(on, keep) {
    el.chat_input.disabled = on;
    Array.prototype.forEach.call(el.chat_log.querySelectorAll(".mp-chat-replay"), function (b) {
      b.disabled = on && b !== keep;
    });
    if (!on) el.chat_input.focus();
  }

  /* A round of agent actions that can be played again: the dashboard as it was before the
     round, and one entry per played step with the chat lines it printed. */
  function newRound() {
    return { start: MP.agent.snapshot(), entries: [] };
  }

  /* Put a Replay button on the closing line of a round. A click puts the dashboard back to
     the start of the round and runs its actions again; the lines already in the chat are
     marked one after another, and nothing new is printed. While it runs the button stops it. */
  function addReplay(line, round) {
    if (!round.entries.some(function (e) { return e.kind === "dashboard"; })) return;
    var button = node("button", "mp-chat-replay", "Replay");
    button.type = "button";
    button.title = "Reset the dashboard to the start of this answer and play its actions again";
    var note = node("span", "mp-chat-replay-note");
    var running = null;
    button.addEventListener("click", function () {
      if (running) { running.stop(); button.disabled = true; return; }
      busy(true, button);
      into = null;
      note.textContent = "";
      button.textContent = "Stop";
      MP.agent.restore(round.start);
      running = MP.agent.replay(round.entries, {
        on: function (nodes) {
          nodes.forEach(function (n) { n.classList.add("mp-replaying"); });
          if (nodes[0]) nodes[0].scrollIntoView({ block: "nearest" });
        },
        off: function (nodes) {
          nodes.forEach(function (n) { n.classList.remove("mp-replaying"); });
        },
        error: function (err) {
          note.textContent = "A step failed: " + (err && err.message ? err.message : String(err));
        }
      });
      running.finished.then(function () {
        running = null;
        button.textContent = "Replay";
        busy(false);
        line.scrollIntoView({ block: "nearest" });
      });
    });
    line.appendChild(button);
    line.appendChild(note);
  }

  function setStatus(text, kind) {
    if (!el.chat_status) return;
    el.chat_status.textContent = text;
    el.chat_status.className = "mp-chat-status " + kind;
  }

  /* Ask GET /health and show the result in the header; warn when the data differ. */
  function connect() {
    setStatus("Agent: checking...", "checking");
    return MP.link.check().then(function (info) {
      if (!info) {
        setStatus("Agent offline", "offline");
        el.chat_status.title = "Start it with: python -m agent.serve --dashboard <this page> " +
          "(click to check again)";
        return false;
      }
      setStatus("Agent connected", "online");
      el.chat_status.title = "Agent at " + MP.link.url() + " (" + info.model + "). Click to check again.";
      el.chat_input.placeholder = "Ask a question, or type a command";
      var diff = MP.link.mismatch();
      if (diff.length) {
        say("The agent reads other data than this page (clusters " + diff.slice(0, 5).join(", ") +
            (diff.length > 5 ? ", ..." : "") + " are on one side only). Start it with " +
            "--dashboard pointing at this page.", "error");
      }
      return true;
    });
  }

  function isCommand(text) {
    try {
      MP.agent.parse(text);
      return true;
    } catch (e) {
      return false;
    }
  }

  /* A line that counts the seconds while the agent works. `label(text)` says what it is doing
     now; `stop()` removes the line. It stays the last line of the log while it is shown. */
  function thinking(text) {
    var what = text || "Thinking";
    var p = node("div", "mp-chat-msg bot mp-chat-thinking", what + "...");
    var t0 = Date.now();
    function place() {
      el.chat_log.appendChild(p);   // moves it below what was printed meanwhile
      el.chat_log.scrollTop = el.chat_log.scrollHeight;
    }
    function draw() {
      var s = Math.round((Date.now() - t0) / 1000);
      p.textContent = what + "..." + (s ? " " + s + " s" : "");
    }
    place();
    var timer = setInterval(draw, 1000);
    return {
      label: function (next) { what = next; draw(); place(); },
      stop: function () {
        clearInterval(timer);
        if (p.parentNode) p.parentNode.removeChild(p);
      }
    };
  }

  /* Ask the agent and play its answer while it is still being written: the status line
     follows what the agent is doing, the dashboard actions start as soon as they are known,
     and each message is printed when both its turn and its text have come. */
  function askAgent(question, round) {
    var status = thinking();
    var writing = null;
    var player = MP.agent.player(say, {
      unit: openUnit,
      record: function (entry) { round.entries.push(entry); },
      writing: function (on) {
        if (writing) { writing.stop(); writing = null; }
        if (on) writing = thinking("Writing");
      }
    });
    return MP.link.ask(question, function (ev) {
      if (ev.event === "status") status.label(ev.text);
      else if (ev.event === "plan") { say(ev.text, "reason"); status.label("Planning what to look at"); }
      else if (ev.event === "steps") { status.stop(); player.push(ev.steps); }
      else if (ev.event === "text") player.text(ev.slot, ev.text);
    }).then(function (trace) {
      status.stop();
      if (window.console && console.debug) console.debug("MolPad agent trace", trace);
      player.end();
      return player.finished;
    }, function (err) {
      status.stop();
      player.end();
      if (!MP.link.connected()) connect();
      return player.finished.then(function () { throw err; });
    });
  }

  function submit(event) {
    event.preventDefault();
    var text = el.chat_input.value.trim();
    if (!text) return;
    el.chat_input.value = "";
    var list = text.charAt(0) === "{" || text.charAt(0) === "[";
    into = null;
    say(list ? "(step list)" : text, "user");
    busy(true);
    var job, round = null;
    if (list) {
      round = newRound();
      job = new Promise(function (resolve) {
        resolve(MP.agent.play(text, say, {
          unit: openUnit, record: function (entry) { round.entries.push(entry); }
        }));
      });
    } else if (isCommand(text) || !MP.link.connected()) {
      // Without the agent, an unknown text gets the command help, as before.
      job = MP.agent.run(text).catch(function (err) {
        if (!MP.link.connected()) {
          err.message += "\n\nTo ask questions, start the agent: python -m agent.serve --dashboard <this page>";
        }
        throw err;
      });
    } else {
      round = newRound();
      job = askAgent(text, round);
    }
    job.then(function (report) {
      into = null;
      var line = say(report, "bot");
      if (round) addReplay(line, round);
    }, function (err) {
      say(err && err.message ? err.message : String(err), "error");
    }).then(function () { busy(false); });
  }

  function init() {
    ["chat", "chat_log", "chat_form", "chat_input", "chat_toggle", "chat_status"].forEach(function (id) {
      el[id] = document.getElementById(id);
    });
    if (!el.chat) return;
    el.chat_form.addEventListener("submit", submit);
    el.chat_toggle.addEventListener("click", function () {
      var collapsed = el.chat.classList.toggle("collapsed");
      document.body.classList.toggle("mp-chat-collapsed", collapsed);
      el.chat_toggle.innerHTML = collapsed ? "&#187;" : "&#171;";
      el.chat_toggle.title = collapsed ? "Show the dialogue" : "Hide the dialogue";
    });
    if (el.chat_status) el.chat_status.addEventListener("click", connect);
    if (!MP.link) {
      say("Type a command and I will do it with the pointer:\n" + MP.agent.usage(), "bot");
      return;
    }
    // One greeting, chosen by whether the agent answers when the page opens.
    connect().then(function (online) {
      if (online) {
        say("Ask me a question about the data.", "bot");
      } else {
        say("The agent is offline: start it with python -m agent.serve --dashboard <this page>, " +
            "then click \"Agent offline\" above.\nUntil then, type a command and I will do it " +
            "with the pointer:\n" + MP.agent.usage(), "bot");
      }
    });
  }

  MP.chat = { init: init, say: say, connect: connect };
})(window.MolPad = window.MolPad || {});
