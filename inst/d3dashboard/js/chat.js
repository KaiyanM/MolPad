/* MolPad D3 dashboard: dialogue panel that sends typed commands to the agent. */
(function (MP) {
  "use strict";

  var el = {};

  function say(text, kind) {
    var p = document.createElement("p");
    p.className = "mp-chat-msg " + kind;
    p.textContent = text;
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
    say(text, "user");
    busy(true);
    MP.agent.run(text).then(function (report) {
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
