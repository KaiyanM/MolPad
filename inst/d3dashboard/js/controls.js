/* MolPad D3 dashboard: form controls bound to the shared state. */
(function (MP) {
  "use strict";

  var el = {};

  /* Restart the highlight animation on a control (see .mp-flash). */
  function flash(node) {
    if (!node) return;
    node.classList.remove("mp-flash");
    void node.offsetWidth;
    node.classList.add("mp-flash");
  }

  function fillSelect(select, items) {
    select.innerHTML = "";
    items.forEach(function (it) {
      var o = document.createElement("option");
      o.value = it.value;
      o.textContent = it.label;
      select.appendChild(o);
    });
  }

  /* Ribbon colour choices; `type` only when it is not just level 1 again. */
  function colourChoices() {
    var out = [{ value: "level1", label: "Functional Annotation" },
               { value: "level2", label: "Taxonomic Scope" }];
    if (MP.D.hasDistinctType) out.push({ value: "type", label: "type" });
    out.push({ value: "none", label: "None (one ribbon per cluster)" });
    return out;
  }

  function syncScope() {
    var scope = MP.state.get().scope;
    Array.prototype.forEach.call(el.s_scope.querySelectorAll("[data-scope]"), function (b) {
      var on = b.getAttribute("data-scope") === scope;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function init() {
    var D = MP.D, S = MP.state.get();
    ["f_level1", "f_level2", "btn_filters_reset", "s_layout", "obs", "obs_value", "s_scope",
     "s_colour", "btn_reset", "btn_clear"].forEach(function (id) {
      el[id] = document.getElementById(id);
    });

    // ---- shared level filters ------------------------------------------------
    MP.filters = {
      level1: MP.multiselect.create({
        mount: el.f_level1, id: "ms_level1", values: D.pathways,
        selected: function () { return MP.state.get().level1; },
        counts: function () { return MP.state.optionCounts(1); },
        onChange: function (list) { MP.state.set({ level1: list }, "controls"); }
      }),
      level2: MP.multiselect.create({
        mount: el.f_level2, id: "ms_level2", values: D.taxa,
        selected: function () { return MP.state.get().level2; },
        counts: function () { return MP.state.optionCounts(2); },
        onChange: function (list) { MP.state.set({ level2: list }, "controls"); }
      })
    };
    el.btn_filters_reset.addEventListener("click", function () {
      MP.state.set({ level1: [], level2: [] }, "controls");
    });

    // ---- network controls ------------------------------------------------------
    el.s_layout.value = S.layout;
    el.s_layout.addEventListener("change", function () {
      MP.state.set({ layout: el.s_layout.value }, "controls");
    });

    var ws = D.weightSlider;
    el.obs.min = ws.min;
    el.obs.max = ws.max;
    el.obs.step = ws.step;
    el.obs.value = S.minWeight;
    el.obs_value.textContent = MP.utils.fmt(S.minWeight, 1);
    var pushWeight = MP.utils.debounce(function () {
      MP.state.set({ minWeight: Number(el.obs.value) }, "controls");
    }, 60);
    el.obs.addEventListener("input", function () {
      el.obs_value.textContent = MP.utils.fmt(Number(el.obs.value), 1);
      pushWeight();
    });

    el.btn_reset.addEventListener("click", function () {
      MP.network.clearBrush();
      MP.state.set({ selectedClusters: D.clusters.slice() }, "controls");
    });
    el.btn_clear.addEventListener("click", function () {
      MP.network.clearBrush();
      MP.state.set({ selectedClusters: [] }, "controls");
    });

    // ---- views of the selected clusters ---------------------------------------
    el.s_scope.addEventListener("click", function (event) {
      var b = event.target.closest("[data-scope]");
      if (b) MP.state.set({ scope: b.getAttribute("data-scope") }, "controls");
    });
    syncScope();

    fillSelect(el.s_colour, colourChoices());
    el.s_colour.value = S.colourBy;
    el.s_colour.addEventListener("change", function () {
      MP.state.set({ colourBy: el.s_colour.value }, "controls");
    });

    // ---- keep the DOM in sync when state changes from elsewhere ----------------
    MP.state.subscribe(["level1", "level2"], function (S2, keys) {
      MP.filters.level1.refresh();
      MP.filters.level2.refresh();
      keys.forEach(function (k) { flash(MP.filters[k].button); });
    });
    MP.state.subscribe(["scope"], function () { syncScope(); flash(el.s_scope); });
    MP.state.subscribe(["colourBy"], function (S2) {
      if (el.s_colour.value !== S2.colourBy) { el.s_colour.value = S2.colourBy; flash(el.s_colour); }
    });

    // Every drop-down flashes when its value is chosen, by hand or by the virtual mouse.
    document.addEventListener("change", function (event) {
      var t = event.target;
      if (t && t.tagName === "SELECT") flash(t);
    });
    document.addEventListener("animationend", function (event) {
      if (event.animationName === "mp-flash") event.target.classList.remove("mp-flash");
    });
  }

  MP.controls = { init: init };
})(window.MolPad = window.MolPad || {});
