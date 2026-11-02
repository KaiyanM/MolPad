/* MolPad D3 dashboard: single source of truth for the UI state.

   The level-1 and level-2 filters are shared by every view, with one rule:
   the network shows WHERE (node colour always follows the filters), the other
   views show WHAT is in the selected clusters. These follow the filters while
   scope is "filtered", and show every feature of the clusters when it is "all". */
(function (MP) {
  "use strict";

  var S = null;
  var subscribers = [];

  function init(D) {
    S = {
      level1: [],                     // [] means every level-1 value
      level2: [],                     // [] means every level-2 value
      scope: "filtered",              // "filtered" | "all": what the cluster views show
      colourBy: "level1",             // ribbon lines: "level1" | "level2" | "type" | "none"
      layout: "force",
      minWeight: D.weightSlider.value,
      selectedClusters: D.clusters.slice()
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

  /* Does a (level 1, level 2) pair pass the filters? A missing value ("") only
     passes while that level is unfiltered, so "All" really means every feature. */
  function passes(l1, l2, level1, level2) {
    level1 = level1 || S.level1;
    level2 = level2 || S.level2;
    return (!level1.length || level1.indexOf(l1) >= 0) &&
           (!level2.length || level2.indexOf(l2) >= 0);
  }

  function matches(f) {
    return passes(MP.data.levelOf(f, 1), MP.data.levelOf(f, 2));
  }

  function isFiltered() {
    return S.level1.length > 0 || S.level2.length > 0;
  }

  /* Features of the selected clusters as the cluster views show them. */
  function clusterFeatures() {
    var D = MP.D, all = S.scope === "all", out = [];
    S.selectedClusters.forEach(function (c) {
      (D.byCluster.get(c) || []).forEach(function (f) {
        if (all || matches(f)) out.push(f);
      });
    });
    return out;
  }

  /* cluster -> number of features passing the filters (the node colour). */
  function nodeCounts() {
    var out = new Map(MP.D.clusters.map(function (c) { return [c, 0]; }));
    MP.D.combos.forEach(function (c) {
      if (passes(c.l1, c.l2)) out.set(c.cluster, out.get(c.cluster) + c.n);
    });
    return out;
  }

  /* value -> features over all clusters for each option of one level, under the
     other level's filter only. An option with 0 cannot be combined with that filter. */
  function optionCounts(level) {
    var out = new Map();
    MP.D.combos.forEach(function (c) {
      var ok = level === 1 ? passes(c.l1, c.l2, [], S.level2) : passes(c.l1, c.l2, S.level1, []);
      if (!ok) return;
      var v = level === 1 ? c.l1 : c.l2;
      out.set(v, (out.get(v) || 0) + c.n);
    });
    return out;
  }

  /* "Pseudomonadota", "Pseudomonadota + Bacillota", "all" ... for titles. */
  function summary(level) {
    var v = level === 1 ? S.level1 : S.level2;
    if (!v.length) return "all";
    return v.length <= 2 ? v.join(" + ") : v.length + " selected";
  }

  function sortedSelectedClusters() {
    return S.selectedClusters.slice().sort(MP.utils.compareClusters);
  }

  MP.state = {
    init: init,
    get: get,
    set: set,
    subscribe: subscribe,
    passes: passes,
    matches: matches,
    isFiltered: isFiltered,
    clusterFeatures: clusterFeatures,
    selectedFeatures: clusterFeatures,   // older name
    nodeCounts: nodeCounts,
    optionCounts: optionCounts,
    summary: summary,
    sortedSelectedClusters: sortedSelectedClusters
  };
})(window.MolPad = window.MolPad || {});
