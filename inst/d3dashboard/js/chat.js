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

  function say(text, kind, evidence) {
    var p = node("div", "mp-chat-msg " + kind);
    p.appendChild(node("span", null, text));
    if (evidence && evidence.length) p.appendChild(evidenceBox(evidence));
    el.chat_log.appendChild(p);
    el.chat_log.scrollTop = el.chat_log.scrollHeight;
  }

  function busy(on) {
    el.chat_input.disabled = on;
    if (!on) el.chat_input.focus();
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

  /* A line that counts the seconds while the agent works; returns a function that removes it. */
  function thinking() {
    var p = node("div", "mp-chat-msg bot mp-chat-thinking", "Thinking...");
    el.chat_log.appendChild(p);
    el.chat_log.scrollTop = el.chat_log.scrollHeight;
    var t0 = Date.now();
    var timer = setInterval(function () {
      p.textContent = "Thinking... " + Math.round((Date.now() - t0) / 1000) + " s";
    }, 1000);
    return function () {
      clearInterval(timer);
      if (p.parentNode) p.parentNode.removeChild(p);
    };
  }

  function askAgent(question) {
    var done = thinking();
    return MP.link.ask(question).then(function (reply) {
      done();
      if (window.console && console.debug) console.debug("MolPad agent trace", reply.trace);
      return MP.agent.play(reply.steps || [], say);
    }, function (err) {
      done();
      if (!MP.link.connected()) connect();
      throw err;
    });
  }

  function submit(event) {
    event.preventDefault();
    var text = el.chat_input.value.trim();
    if (!text) return;
    el.chat_input.value = "";
    var list = text.charAt(0) === "{" || text.charAt(0) === "[";
    say(list ? "(step list)" : text, "user");
    busy(true);
    var job;
    if (list) {
      job = new Promise(function (resolve) { resolve(MP.agent.play(text, say)); });
    } else if (isCommand(text) || !MP.link.connected()) {
      // Without the agent, an unknown text gets the command help, as before.
      job = MP.agent.run(text).catch(function (err) {
        if (!MP.link.connected()) {
          err.message += "\n\nTo ask questions, start the agent: python -m agent.serve --dashboard <this page>";
        }
        throw err;
      });
    } else {
      job = askAgent(text);
    }
    job.then(function (report) {
      say(report, "bot");
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
      el.chat.classList.toggle("collapsed");
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
