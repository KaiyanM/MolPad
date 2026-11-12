/* MolPad D3 dashboard: min/mean/max ribbon plot per cluster.

   Overview (default): every cluster has a panel, the unselected ones are faded.
   Expanded ("Expand trajectories"): the selected clusters only, in larger panels. */
(function (MP) {
  "use strict";

  var container, legendDiv, svg;
  var STRIP_H = 16;
  var margin = { top: 6, right: 10, bottom: 46, left: 40 };
  var gapX = 14, gapY = 12;
  var SIDE_W = 14, SUB_GAP = 12;
  var MIN_PANEL_W = 56;    // narrower than this and the row scrolls sideways
  var NARROW_W = 110;      // below this a panel drops what does not fit
  var SCROLLBAR_H = 14;
  var FADED = 0.3;         // opacity of an unselected cluster in the overview
  var MAX_SHARE = 1 / 3;   // expanded: a panel is at most this share of the box width

  function init(selector) {
    container = d3.select(selector);
    legendDiv = container.append("div").attr("class", "mp-swatches");
    svg = container.append("svg");
    MP.state.subscribe(["selectedClusters", "level1", "level2", "scope", "colourBy", "ribbonExpand"], render);
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
    var D = MP.D, S = MP.state.get();
    var selected = new Set(S.selectedClusters);
    var shown = S.ribbonExpand ? MP.state.sortedSelectedClusters() : D.clusters;
    var all = S.scope === "all";

    return shown.map(function (c) {
      // the features of a cluster as the cluster views show them: filtered, or all of them
      var byType = new Map();
      (D.byCluster.get(c) || []).forEach(function (f) {
        if (!all && !MP.state.matches(f)) return;
        var k = G.key(f);
        if (!byType.has(k)) byType.set(k, []);
        byType.get(k).push(f);
      });
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
      return { cluster: c, selected: selected.has(c), subjects: subjects,
               series: d3.merge(subjects.map(function (s) { return s.series; })) };
    });
  }

  function render() {
    var D = MP.D;
    var G = grouping();
    var panels = summarise(G);
    var expanded = MP.state.get().ribbonExpand;
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
        .style("fill", "#666").style("font-style", "italic")
        .text("No clusters selected: select clusters in the network, or leave the expanded view");
      return;
    }

    var legendH = legendDiv.node().offsetHeight || 20;
    // Always one row: every shown cluster gets an equal share of the width and the full
    // height of the box. Expanded, a panel is at most MAX_SHARE of the width, so one or two
    // clusters are not stretched flat, and the row sits in the middle. A narrow panel keeps its own y axis (each cluster has its
    // own scale) but drops the inner x ticks, the repeated axis titles and the long name.
    // At MIN_PANEL_W the row gets wider than the box and scrolls sideways.
    var nsub = D.subjects.length;
    var fitW = (width - gapX * (k - 1)) / k;
    var narrow = fitW < NARROW_W;
    var gap = narrow ? 6 : gapX;
    var panelW = Math.max(MIN_PANEL_W, (width - gap * (k - 1)) / k);
    if (expanded) panelW = Math.min(panelW, Math.max(MIN_PANEL_W, width * MAX_SHARE));
    var total = k * panelW + gap * (k - 1);
    var scrolls = total > width + 0.5;
    var offset = scrolls ? 0 : (width - total) / 2;
    var panelH = Math.max(110, boxH - legendH - 4 - (scrolls ? SCROLLBAR_H : 0));
    svg.attr("width", scrolls ? total : width).attr("height", panelH);

    var mLeft = narrow ? 26 : margin.left, mRight = narrow ? 3 : margin.right;
    var subGap = narrow || panelH < 200 ? 6 : SUB_GAP;
    var sideW = narrow ? 10 : SIDE_W;
    var innerW = panelW - mLeft - mRight;
    var innerH = panelH - margin.top - margin.bottom - STRIP_H;
    var plotW = innerW - (nsub > 1 ? sideW : 0);
    var subH = (innerH - subGap * (nsub - 1)) / nsub;
    var x = d3.scalePoint().domain(D.timeLabels).range([0, plotW]).padding(0.3);
    // x ticks: all of them while they fit (about 12px each, the labels are upright), else the ends
    var xTicks = D.timeLabels.length * 12 <= plotW ? D.timeLabels
      : [D.timeLabels[0], D.timeLabels[D.timeLabels.length - 1]];
    var yTicks = subH < 60 ? 2 : (nsub > 1 ? 3 : 4);

    panels.forEach(function (p, idx) {
      var g = svg.append("g").attr("transform",
        "translate(" + (offset + idx * (panelW + gap) + mLeft) + "," + margin.top + ")");
      if (!expanded && !p.selected) g.attr("opacity", FADED).attr("class", "mp-ribbon-faded");

      // facet strip; a name that does not fit is cut to its number ("Group_5" -> "5")
      var name = p.cluster;
      if (name.length * 6.5 > innerW) name = name.replace(/^.*[^0-9](?=[0-9]+$)/, "") || name;
      g.append("rect").attr("class", "mp-strip").attr("x", 0).attr("y", 0)
        .attr("width", innerW).attr("height", STRIP_H)
        .append("title").text(p.cluster);
      g.append("text").attr("class", "mp-strip-text")
        .attr("x", innerW / 2).attr("y", STRIP_H / 2 + 1).text(name)
        .append("title").text(p.cluster);

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
          "translate(0," + (STRIP_H + si * (subH + subGap)) + ")");
        plot.append("rect").attr("class", "mp-panel-bg").attr("width", plotW).attr("height", subH);

        if (nsub > 1) {
          plot.append("rect").attr("class", "mp-strip").attr("x", plotW).attr("y", 0)
            .attr("width", sideW).attr("height", subH);
          plot.append("text").attr("class", "mp-strip-text")
            .attr("transform", "translate(" + (plotW + sideW / 2) + "," + (subH / 2) + ") rotate(90)")
            .text(sub.name);
        }

        plot.append("g").selectAll("line").data(y.ticks(yTicks)).join("line").attr("class", "mp-gridline")
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

        plot.append("g").attr("class", "mp-axis").call(d3.axisLeft(y).ticks(yTicks));
        if (last) {
          plot.append("g").attr("class", "mp-axis").attr("transform", "translate(0," + subH + ")")
            .call(d3.axisBottom(x).tickValues(xTicks))
            .selectAll("text")
            .attr("transform", "rotate(-90)")
            .attr("dx", "-0.6em").attr("dy", "-0.4em")
            .style("text-anchor", "end");
          if (!narrow || idx === 0) {
            plot.append("text").attr("class", "mp-axis-title")
              .attr("x", plotW / 2).attr("y", subH + margin.bottom - 4).text("Time");
          }
        }
      });

      if (!narrow) {
        g.append("text").attr("class", "mp-axis-title")
          .attr("transform", "rotate(-90)")
          .attr("x", -(STRIP_H + (innerH) / 2)).attr("y", -margin.left + 11).text("Value");
      }
    });
  }

  function resize() { render(); }

  MP.ribbon = { init: init, render: render, resize: resize };
})(window.MolPad = window.MolPad || {});
