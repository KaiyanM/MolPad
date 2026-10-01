/* MolPad D3 dashboard: single source of truth for the UI state. */
(function (MP) {
  "use strict";

  var S = null;
  var subscribers = [];

  function init(D) {
    S = {
      pathway: D.pathways[0] || "",
      layout: "force",
      minWeight: D.weightSlider.value,
      taxa: [],                       // [] means every taxon
      selectedClusters: D.clusters.slice(),
      tablePathway: D.pathways[0] || ""   // "" means every pathway
    };
    return S;
  }

  function get() {
    return S;
  }

  function changed(key, before, after) {
    if (Array.isArray(before) && Array.isArray(after)) {
      return before.length !== after.length ||
        before.some(function (v, i) { return v !== after[i]; });
    }
    return before !== after;
  }

  /* Apply a patch and notify subscribers whose keys intersect the change. */
  function set(patch, source) {
    var keys = [];
    Object.keys(patch).forEach(function (k) {
      if (!(k in S)) return;
      var v = patch[k];
      if (Array.isArray(v)) v = v.slice();
      if (changed(k, S[k], v)) {
        S[k] = v;
        keys.push(k);
      }
    });
    if (!keys.length) return keys;
    subscribers.forEach(function (sub) {
      if (sub.keys.some(function (k) { return keys.indexOf(k) >= 0; })) {
        sub.fn(S, keys, source);
      }
    });
    return keys;
  }

  function subscribe(keys, fn) {
    subscribers.push({ keys: keys, fn: fn });
    return function () {
      subscribers = subscribers.filter(function (s) { return s.fn !== fn; });
    };
  }

  function effectiveTaxa() {
    return S.taxa.length ? S.taxa : MP.D.taxa;
  }

  function taxaSet() {
    return new Set(effectiveTaxa());
  }

  /* Features of the selected clusters restricted to the effective taxa.
     Features with no taxonomic scope are left out, as in the Shiny filter. */
  function selectedFeatures() {
    var D = MP.D, taxa = taxaSet(), out = [];
    S.selectedClusters.forEach(function (c) {
      (D.byCluster.get(c) || []).forEach(function (f) {
        var t = f["taxonomic.scope"];
        if (t !== null && t !== undefined && taxa.has(String(t))) out.push(f);
      });
    });
    return out;
  }

  function sortedSelectedClusters() {
    return S.selectedClusters.slice().sort(MP.utils.compareClusters);
  }

  MP.state = {
    init: init,
    get: get,
    set: set,
    subscribe: subscribe,
    effectiveTaxa: effectiveTaxa,
    taxaSet: taxaSet,
    selectedFeatures: selectedFeatures,
    sortedSelectedClusters: sortedSelectedClusters
  };
})(window.MolPad = window.MolPad || {});
