/* MolPad D3 dashboard: boot sequence and page-level wiring. */
(function (MP) {
  "use strict";

  function showTab(name) {
    var main = document.getElementById("tab-main");
    var info = document.getElementById("tab-info");
    var bMain = document.getElementById("nav-main");
    var bInfo = document.getElementById("nav-info");
    var isMain = name === "main";
    main.hidden = !isMain;
    info.hidden = isMain;
    bMain.classList.toggle("active", isMain);
    bInfo.classList.toggle("active", !isMain);
    if (isMain) resizeAll();
  }

  var views = [];

  function resizeAll() {
    views.forEach(function (v) { if (v.resize) v.resize(); });
  }

  function fail(err) {
    var box = document.getElementById("box-network") || document.body;
    var p = document.createElement("p");
    p.className = "mp-empty";
    p.textContent = "MolPad could not start: " + (err && err.message ? err.message : err);
    box.insertBefore(p, box.firstChild);
    if (window.console) console.error(err);
  }

  function start() {
    var D;
    try {
      D = MP.data.load();
    } catch (err) {
      fail(err);
      return;
    }
    document.title = D.title;
    var titleEl = document.getElementById("mp-title");
    if (titleEl) titleEl.textContent = D.title;

    MP.state.init(D);
    MP.controls.init();

    views = [MP.network, MP.stackbar, MP.ribbon, MP.table];
    MP.network.init("#network");
    MP.stackbar.init("#stackbar");
    MP.ribbon.init("#ribbon");
    MP.table.init("#table");
    views.forEach(function (v) { v.render(); });
    MP.cursor.init();
    MP.chat.init();

    document.getElementById("nav-main").addEventListener("click", function () { showTab("main"); });
    document.getElementById("nav-info").addEventListener("click", function () { showTab("info"); });

    var onResize = MP.utils.debounce(resizeAll, 120);
    if (window.ResizeObserver) {
      new ResizeObserver(onResize).observe(document.getElementById("tab-main"));
    } else {
      window.addEventListener("resize", onResize);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

  MP.app = { start: start, showTab: showTab };
})(window.MolPad = window.MolPad || {});
