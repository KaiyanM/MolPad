/* MolPad D3 dashboard: form controls bound to the shared state. */
(function (MP) {
  "use strict";

  var el = {};

  function fillSelect(select, values, labelFn) {
    select.innerHTML = "";
    values.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v;
      o.textContent = labelFn ? labelFn(v) : v;
      select.appendChild(o);
    });
  }

  function selectedValues(select) {
    return Array.from(select.selectedOptions).map(function (o) { return o.value; });
  }

  /* Per-pathway counts among the currently selected clusters and taxa. */
  function pathwayCounts() {
    var counts = new Map();
    MP.state.selectedFeatures().forEach(function (f) {
      var p = f.Pathway;
      if (p === null || p === undefined) return;
      counts.set(String(p), (counts.get(String(p)) || 0) + 1);
    });
    return counts;
  }

  function refreshTablePathway() {
    var D = MP.D, S = MP.state.get();
    var counts = pathwayCounts();
    var total = 0;
    counts.forEach(function (n) { total += n; });
    var values = [""].concat(D.pathways);
    fillSelect(el.s_p, values, function (v) {
      if (v === "") return "All annotations (" + total + ")";
      return v + " (" + (counts.get(v) || 0) + ")";
    });
    el.s_p.value = D.pathways.indexOf(S.tablePathway) >= 0 ? S.tablePathway : "";
  }

  function init() {
    var D = MP.D, S = MP.state.get();
    ["s_ptw", "s_layout", "obs", "obs_value", "s_tax", "s_p", "btn_reset"].forEach(function (id) {
      el[id] = document.getElementById(id);
    });

    fillSelect(el.s_ptw, D.pathways);
    el.s_ptw.value = S.pathway;
    el.s_ptw.addEventListener("change", function () {
      MP.state.set({ pathway: el.s_ptw.value, tablePathway: el.s_ptw.value }, "controls");
    });

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

    fillSelect(el.s_tax, D.taxa);
    el.s_tax.size = Math.min(6, Math.max(3, D.taxa.length));
    el.s_tax.addEventListener("change", function () {
      MP.state.set({ taxa: selectedValues(el.s_tax) }, "controls");
    });

    refreshTablePathway();
    el.s_p.addEventListener("change", function () {
      MP.state.set({ tablePathway: el.s_p.value }, "controls");
    });

    el.btn_reset.addEventListener("click", function () {
      MP.network.clearBrush();
      MP.state.set({ selectedClusters: D.clusters.slice() }, "controls");
    });

    // Keep the DOM in sync when state changes from elsewhere (brush, clicks).
    MP.state.subscribe(["selectedClusters", "taxa", "tablePathway", "pathway"], function (S2, keys) {
      if (keys.indexOf("pathway") >= 0 && el.s_ptw.value !== S2.pathway) el.s_ptw.value = S2.pathway;
      refreshTablePathway();
    });
  }

  MP.controls = { init: init };
})(window.MolPad = window.MolPad || {});
