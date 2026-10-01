/* MolPad D3 dashboard: load and index the embedded JSON (see SCHEMA.md). */
(function (MP) {
  "use strict";

  var REQUIRED = ["timepoints", "types", "taxa", "pathways", "clusters",
                  "annotation_columns", "features", "edges"];

  function load() {
    var el = document.getElementById("molpad-data");
    if (!el) throw new Error("MolPad: missing <script id=\"molpad-data\">.");
    var raw = JSON.parse(el.textContent);

    var missing = REQUIRED.filter(function (k) { return !(k in raw); });
    if (missing.length) {
      throw new Error("MolPad: data is missing keys: " + missing.join(", "));
    }

    var D = {
      title: raw.title || "MolPad Dashboard",
      timepoints: raw.timepoints.map(String),
      types: raw.types.map(String),
      taxa: raw.taxa.map(String),
      pathways: raw.pathways.map(String),
      annotationColumns: raw.annotation_columns.map(String),
      idLinks: raw.id_links || {},
      features: raw.features
    };

    // Clusters: declared list plus anything only seen in features/edges.
    var seen = new Set(raw.clusters.map(String));
    raw.features.forEach(function (f) { seen.add(String(f.cluster)); });
    raw.edges.forEach(function (e) { seen.add(String(e.from)); seen.add(String(e.to)); });
    D.clusters = Array.from(seen).sort(MP.utils.compareClusters);

    // Indexes.
    D.featuresById = new Map();
    D.byCluster = new Map(D.clusters.map(function (c) { return [c, []]; }));
    D.pathwayCounts = new Map();   // pathway -> Map(cluster -> n)
    D.totalByCluster = new Map(D.clusters.map(function (c) { return [c, 0]; }));

    raw.features.forEach(function (f) {
      f.ID = String(f.ID);
      f.cluster = String(f.cluster);
      f.type = f.type === null || f.type === undefined ? "" : String(f.type);
      D.featuresById.set(f.ID, f);
      D.byCluster.get(f.cluster).push(f);
      D.totalByCluster.set(f.cluster, D.totalByCluster.get(f.cluster) + 1);
      var p = f.Pathway;
      if (p !== null && p !== undefined) {
        p = String(p);
        if (!D.pathwayCounts.has(p)) D.pathwayCounts.set(p, new Map());
        var m = D.pathwayCounts.get(p);
        m.set(f.cluster, (m.get(f.cluster) || 0) + 1);
      }
    });

    // Undirected edges: drop null weights, keep the larger weight per pair.
    var pairs = new Map();
    raw.edges.forEach(function (e) {
      var w = e.weight;
      if (w === null || w === undefined || !Number.isFinite(w)) return;
      var a = String(e.from), b = String(e.to);
      if (a === b) return;
      var key = a < b ? a + "\u0000" + b : b + "\u0000" + a;
      var cur = pairs.get(key);
      if (!cur || w > cur.weight) {
        pairs.set(key, { source: a < b ? a : b, target: a < b ? b : a, weight: w });
      }
    });
    D.edges = Array.from(pairs.values());
    D.rawEdges = raw.edges;

    // Slider defaults: given, else the same quantiles as gDashboard().
    var ws = raw.weight_slider;
    if (!ws || !Number.isFinite(ws.max)) {
      var abs = raw.edges
        .map(function (e) { return Math.abs(e.weight); })
        .filter(function (w) { return Number.isFinite(w); })
        .sort(d3.ascending);
      var q75 = abs.length ? d3.quantileSorted(abs, 0.75) : 1;
      var q50 = abs.length ? d3.quantileSorted(abs, 0.5) : 0;
      ws = { min: 0, max: Math.round(q75 * 10) / 10, value: Math.round(q50 * 10) / 10, step: 0.1 };
    }
    ws.min = Number.isFinite(ws.min) ? ws.min : 0;
    ws.step = Number.isFinite(ws.step) && ws.step > 0 ? ws.step : 0.1;
    ws.max = Math.max(ws.max, ws.min + ws.step);
    ws.value = MP.utils.clamp(Number.isFinite(ws.value) ? ws.value : ws.min, ws.min, ws.max);
    D.weightSlider = ws;

    // Colour scales fixed for the whole session.
    D.typeColor = MP.palettes.ordinal(D.types, "darkwarm");
    D.taxaColor = MP.palettes.ordinal(D.taxa, "graytone");

    MP.D = D;
    return D;
  }

  MP.data = { load: load };
})(window.MolPad = window.MolPad || {});
