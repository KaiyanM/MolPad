/* MolPad D3 dashboard: dialogue panel that sends typed commands to the agent. */
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

  function submit(event) {
    event.preventDefault();
    var text = el.chat_input.value.trim();
    if (!text) return;
    el.chat_input.value = "";
    // Pasted JSON is a step list from the Python agent; anything else is one command.
    var list = text.charAt(0) === "{" || text.charAt(0) === "[";
    say(list ? "(step list)" : text, "user");
    busy(true);
    var job = list
      ? new Promise(function (resolve) { resolve(MP.agent.play(text, say)); })
      : MP.agent.run(text);
    job.then(function (report) {
      say(report, "bot");
    }, function (err) {
      say(err && err.message ? err.message : String(err), "error");
    }).then(function () { busy(false); });
  }

  function init() {
    ["chat", "chat_log", "chat_form", "chat_input", "chat_toggle"].forEach(function (id) {
      el[id] = document.getElementById(id);
    });
    if (!el.chat) return;
    el.chat_form.addEventListener("submit", submit);
    el.chat_toggle.addEventListener("click", function () {
      el.chat.classList.toggle("collapsed");
    });
    say("Type a command and I will do it with the pointer:\n" + MP.agent.usage(), "bot");
  }

  MP.chat = { init: init, say: say };
})(window.MolPad = window.MolPad || {});
