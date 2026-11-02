/* MolPad D3 dashboard: min/mean/max ribbon plot per selected cluster. */
(function (MP) {
  "use strict";

  var container, legendDiv, svg;
  var STRIP_H = 16;
  var margin = { top: 6, right: 10, bottom: 46, left: 40 };
  var gapX = 14, gapY = 12;
  var SIDE_W = 14, SUB_GAP = 12;
  var MIN_PANEL_W = 180;

  function init(selector) {
    container = d3.select(selector);
    legendDiv = container.append("div").attr("class", "mp-swatches");
    svg = container.append("svg");
    MP.state.subscribe(["selectedClusters", "level1", "level2", "scope", "colourBy"], render);
  }

  var NONE = "all features", MISSING = "(none)";

  /* The colour grouping of the lines: key of a feature, ordered domain, colour, legend title. */
  function grouping() {
    var D = MP.D, by = MP.state.get().colourBy;
    if (by === "level2") {
      return { key: function (f) { return MP.data.levelOf(f, 2) || MISSING; },
               domain: D.taxa.concat([MISSING]), color: function (t) { return t === MISSING ? "#999" : D.taxaColor(t); },
               title: "taxonomic.scope" };
    }
    if (by === "type") {
      return { key: function (f) { return f.type; }, domain: D.types, color: D.typeColor, title: "type" };
    }
    if (by === "none") {
      return { key: function () { return NONE; }, domain: [NONE],
               color: function () { return MP.palettes.accent; }, title: "" };
    }
    return { key: function (f) { return MP.data.levelOf(f, 1) || MISSING; },
             domain: D.pathways.concat([MISSING]), color: function (t) { return t === MISSING ? "#999" : D.level1Color(t); },
             title: "Pathway" };
  }

  /* Per cluster, subject and colour group: min/mean/max at every time point. */
  function summarise(G) {
    var D = MP.D;
    var byCluster = new Map();
    MP.state.clusterFeatures().forEach(function (f) {
      if (!byCluster.has(f.cluster)) byCluster.set(f.cluster, new Map());
      var byType = byCluster.get(f.cluster);
      var k = G.key(f);
      if (!byType.has(k)) byType.set(k, []);
      byType.get(k).push(f);
    });

    return MP.state.sortedSelectedClusters().map(function (c) {
      var byType = byCluster.get(c) || new Map();
      var subjects = D.subjects.map(function (sub) {
        var series = [];
        G.domain.forEach(function (t) {
          var feats = byType.get(t);
          if (!feats || !feats.length) return;
          var points = sub.idx.map(function (i, j) {
            var vals = feats.map(function (f) { return f.values[i]; })
              .filter(function (v) { return v !== null && v !== undefined && Number.isFinite(v); });
            if (!vals.length) return null;
            return { i: i, day: sub.labels[j], min: d3.min(vals), mean: d3.mean(vals), max: d3.max(vals) };
          }).filter(Boolean);
          if (points.length) series.push({ type: t, points: points });
        });
        return { name: sub.name, series: series };
      });
      return { cluster: c, subjects: subjects, series: d3.merge(subjects.map(function (s) { return s.series; })) };
    });
  }

  function render() {
    var D = MP.D;
    var G = grouping();
    var panels = summarise(G);
    var width = Math.max(240, container.node().clientWidth || 400);
    var boxH = Math.max(200, container.node().clientHeight || 320);

    var typesPresent = G.domain.filter(function (t) {
      return panels.some(function (p) { return p.series.some(function (s) { return s.type === t; }); });
    });
    legendDiv.selectAll("*").remove();
    legendDiv.append("span").attr("class", "mp-swatch-title").text(G.title);
    typesPresent.forEach(function (t) {
      var s = legendDiv.append("span").attr("class", "mp-swatch");
      s.append("i").style("background", G.color(t));
      s.append("span").text(t);
    });

    svg.selectAll("*").remove();
    var k = panels.length;
    if (!k) {
      svg.attr("width", width).attr("height", 60);
      svg.append("text").attr("x", 8).attr("y", 30)
        .style("fill", "#666").style("font-style", "italic").text("No clusters selected");
      return;
    }

    var legendH = legendDiv.node().offsetHeight || 20;
    // As square as the panel count allows; more columns when the rows would not fit the box
    // height; never narrower than MIN_PANEL_W per panel.
    var nsub = D.subjects.length;
    var minPanelH = 150 + (nsub - 1) * 90;
    var available = boxH - legendH - 4;
    var maxCols = Math.max(1, Math.floor((width + gapX) / (MIN_PANEL_W + gapX)));
    var rowsFit = Math.max(1, Math.floor((available + gapY) / (minPanelH + gapY)));
    var ncol = Math.max(1, Math.min(k, maxCols, Math.max(Math.ceil(Math.sqrt(k)), Math.ceil(k / rowsFit))));
    var nrow = Math.ceil(k / ncol);
    var panelW = (width - gapX * (ncol - 1)) / ncol;
    var panelH = Math.max(minPanelH, (available - gapY * (nrow - 1)) / nrow);
    var height = nrow * panelH + gapY * (nrow - 1);
    svg.attr("width", width).attr("height", height);

    var innerW = panelW - margin.left - margin.right;
    var innerH = panelH - margin.top - margin.bottom - STRIP_H;
    var plotW = innerW - (nsub > 1 ? SIDE_W : 0);
    var subH = (innerH - SUB_GAP * (nsub - 1)) / nsub;
    var x = d3.scalePoint().domain(D.timeLabels).range([0, plotW]).padding(0.3);

    panels.forEach(function (p, idx) {
      var col = idx % ncol, row = Math.floor(idx / ncol);
      var g = svg.append("g").attr("transform",
        "translate(" + (col * (panelW + gapX) + margin.left) + "," +
        (row * (panelH + gapY) + margin.top) + ")");

      // facet strip
      g.append("rect").attr("class", "mp-strip").attr("x", 0).attr("y", 0)
        .attr("width", innerW).attr("height", STRIP_H);
      g.append("text").attr("class", "mp-strip-text")
        .attr("x", innerW / 2).attr("y", STRIP_H / 2 + 1).text(p.cluster);

      // one y scale per cluster, shared by its subject facets
      var lo = d3.min(p.series, function (s) { return d3.min(s.points, function (d) { return d.min; }); });
      var hi = d3.max(p.series, function (s) { return d3.max(s.points, function (d) { return d.max; }); });
      if (!Number.isFinite(lo) || !Number.isFinite(hi)) { lo = 0; hi = 1; }
      if (lo === hi) { lo -= 0.5; hi += 0.5; }
      var y = d3.scaleLinear().domain([lo, hi]).nice().range([subH, 0]);

      var area = d3.area()
        .x(function (d) { return x(d.day); })
        .y0(function (d) { return y(d.min); })
        .y1(function (d) { return y(d.max); });
      var line = d3.line()
        .x(function (d) { return x(d.day); })
        .y(function (d) { return y(d.mean); });

      // subject facets, stacked top to bottom on a shared time axis
      p.subjects.forEach(function (sub, si) {
        var last = si === nsub - 1;
        var plot = g.append("g").attr("transform",
          "translate(0," + (STRIP_H + si * (subH + SUB_GAP)) + ")");
        plot.append("rect").attr("class", "mp-panel-bg").attr("width", plotW).attr("height", subH);

        if (nsub > 1) {
          plot.append("rect").attr("class", "mp-strip").attr("x", plotW).attr("y", 0)
            .attr("width", SIDE_W).attr("height", subH);
          plot.append("text").attr("class", "mp-strip-text")
            .attr("transform", "translate(" + (plotW + SIDE_W / 2) + "," + (subH / 2) + ") rotate(90)")
            .text(sub.name);
        }

        plot.append("g").selectAll("line").data(y.ticks(nsub > 1 ? 3 : 4)).join("line").attr("class", "mp-gridline")
          .attr("x1", 0).attr("x2", plotW).attr("y1", y).attr("y2", y);

        sub.series.forEach(function (s) {
          plot.append("path").datum(s.points).attr("d", area)
            .attr("fill", G.color(s.type)).attr("fill-opacity", 0.2).attr("stroke", "none");
        });
        sub.series.forEach(function (s) {
          plot.append("path").datum(s.points).attr("d", line)
            .attr("fill", "none").attr("stroke", G.color(s.type))
            .attr("stroke-opacity", 0.8).attr("stroke-width", 1.5)
            .append("title").text(p.cluster + (sub.name ? " \u00b7 " + sub.name : "") +
              " \u00b7 " + s.type + " (mean, ribbon = min to max)");
        });

        plot.append("g").attr("class", "mp-axis").call(d3.axisLeft(y).ticks(nsub > 1 ? 3 : 4));
        if (last) {
          plot.append("g").attr("class", "mp-axis").attr("transform", "translate(0," + subH + ")")
            .call(d3.axisBottom(x))
            .selectAll("text")
            .attr("transform", "rotate(-90)")
            .attr("dx", "-0.6em").attr("dy", "-0.4em")
            .style("text-anchor", "end");
          plot.append("text").attr("class", "mp-axis-title")
            .attr("x", plotW / 2).attr("y", subH + margin.bottom - 4).text("Time");
        }
      });

      g.append("text").attr("class", "mp-axis-title")
        .attr("transform", "rotate(-90)")
        .attr("x", -(STRIP_H + (innerH) / 2)).attr("y", -margin.left + 11).text("Value");
    });
  }

  function resize() { render(); }

  MP.ribbon = { init: init, render: render, resize: resize };
})(window.MolPad = window.MolPad || {});
