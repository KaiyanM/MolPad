/* MolPad D3 dashboard: cluster network with brush/click selection. */
(function (MP) {
  "use strict";

  var NODE_W = 68, NODE_H = 24, PAD = 10;
  var container, svg, gBrush, gEdges, gNodes, brush, simulation;
  var nodes = [], nodeById = new Map(), links = [];
  var width = 600, height = 410;
  var brushActive = false;     // true while a brush rectangle is visible
  var programmatic = false;    // guard for brush.move() calls we make ourselves

  // ---- setup -----------------------------------------------------------------

  function init(selector) {
    container = d3.select(selector);
    measure();
    svg = container.append("svg").attr("width", width).attr("height", height);
    gBrush = svg.append("g").attr("class", "mp-brush");
    gEdges = svg.append("g").attr("class", "mp-edges");
    gNodes = svg.append("g").attr("class", "mp-nodes");

    brush = d3.brush()
      .extent([[0, 0], [width, height]])
      .on("end", onBrushEnd);
    gBrush.call(brush);

    buildNodes();
    simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink().id(function (d) { return d.id; }).distance(130))
      .force("charge", d3.forceManyBody().strength(-500))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(42))
      .on("tick", ticked)
      .stop();

    MP.state.subscribe(["pathway"], function () { colourNodes(); });
    MP.state.subscribe(["minWeight"], function () { drawEdges(); });
    MP.state.subscribe(["layout"], function () { clearBrush(); applyLayout(); });
    MP.state.subscribe(["selectedClusters"], function () { highlight(); });
    renderLegend();
  }

  function measure() {
    var node = container.node();
    width = Math.max(300, node.clientWidth || 600);
    height = Math.max(250, node.clientHeight || 410);
  }

  function buildNodes() {
    var D = MP.D;
    nodes = D.clusters.map(function (c, i) {
      return { id: c, index: i, x: width / 2 + (Math.random() - 0.5) * 50,
               y: height / 2 + (Math.random() - 0.5) * 50 };
    });
    nodeById = new Map(nodes.map(function (n) { return [n.id, n]; }));
  }

  // ---- rendering ---------------------------------------------------------------

  function render() {
    var sel = gNodes.selectAll("g.mp-node").data(nodes, function (d) { return d.id; });
    var enter = sel.enter().append("g").attr("class", "mp-node");
    enter.append("rect")
      .attr("width", NODE_W).attr("height", NODE_H)
      .attr("x", -NODE_W / 2).attr("y", -NODE_H / 2)
      .attr("rx", 4).attr("ry", 4);
    enter.append("text").text(function (d) { return d.id; });
    enter.append("title");
    enter.call(d3.drag()
      .on("start", dragStart).on("drag", dragged).on("end", dragEnd));
    enter.on("mousedown", function (event) { event.stopPropagation(); })
      .on("click", onNodeClick);
    sel.exit().remove();

    colourNodes();
    drawEdges();
    applyLayout();
    highlight();
  }

  function currentCounts() {
    var D = MP.D, S = MP.state.get();
    var m = D.pathwayCounts.get(S.pathway) || new Map();
    var maxN = 0;
    nodes.forEach(function (n) {
      n.n = m.get(n.id) || 0;
      if (n.n > maxN) maxN = n.n;
    });
    return maxN;
  }

  function colourNodes() {
    var maxN = currentCounts();
    var scale = d3.scaleLinear().domain([0, Math.max(1, maxN)])
      .range([MP.palettes.nodeLow, MP.palettes.nodeHigh]);
    var S = MP.state.get();
    gNodes.selectAll("g.mp-node").each(function (d) {
      var g = d3.select(this);
      g.select("rect").attr("fill", maxN === 0 ? MP.palettes.nodeLow : scale(d.n));
      g.select("title").text(d.id + "\n" + d.n + " feature(s) in " + S.pathway +
        "\n" + (MP.D.totalByCluster.get(d.id) || 0) + " feature(s) in total");
    });
    renderLegend(maxN);
  }

  function visibleLinks() {
    var S = MP.state.get();
    return MP.D.edges.filter(function (e) { return e.weight > S.minWeight; })
      .map(function (e) {
        return { source: nodeById.get(e.source), target: nodeById.get(e.target), weight: e.weight };
      })
      .filter(function (l) { return l.source && l.target; });
  }

  function drawEdges() {
    links = visibleLinks();
    var alpha = MP.utils.rescale(links.map(function (l) { return l.weight; }));
    links.forEach(function (l, i) { l.opacity = 0.1 + 0.9 * alpha[i]; });

    var update = gEdges.selectAll("line.mp-edge").data(links, function (l) {
      return l.source.id + "|" + l.target.id;
    });
    update.exit().remove();
    var enter = update.enter().append("line").attr("class", "mp-edge");
    enter.append("title");
    enter.merge(update)
      .attr("stroke-opacity", function (l) { return l.opacity; })
      .select("title").text(function (l) {
        return l.source.id + " - " + l.target.id + "\nweight " + MP.utils.fmt(l.weight, 3);
      });

    if (simulation) {
      simulation.force("link").links(links);
      if (MP.state.get().layout === "force") simulation.alpha(0.5).restart();
    }
    positionEdges();
    highlight();
  }

  function positionEdges() {
    gEdges.selectAll("line.mp-edge")
      .attr("x1", function (l) { return l.source.x; })
      .attr("y1", function (l) { return l.source.y; })
      .attr("x2", function (l) { return l.target.x; })
      .attr("y2", function (l) { return l.target.y; });
  }

  function positionNodes() {
    gNodes.selectAll("g.mp-node").attr("transform", function (d) {
      return "translate(" + d.x + "," + d.y + ")";
    });
  }

  function ticked() {
    nodes.forEach(function (d) {
      d.x = MP.utils.clamp(d.x, NODE_W / 2 + PAD, width - NODE_W / 2 - PAD);
      d.y = MP.utils.clamp(d.y, NODE_H / 2 + PAD, height - NODE_H / 2 - PAD);
    });
    positionNodes();
    positionEdges();
  }

  // ---- layouts -----------------------------------------------------------------

  function applyLayout() {
    var S = MP.state.get();
    if (S.layout === "force") {
      nodes.forEach(function (d) { d.fx = null; d.fy = null; });
      simulation.force("center", d3.forceCenter(width / 2, height / 2));
      simulation.alpha(1).restart();
      return;
    }
    simulation.stop();
    var n = nodes.length;
    if (S.layout === "circle") {
      var r = 0.4 * Math.min(width, height), cx = width / 2, cy = height / 2;
      nodes.forEach(function (d, i) {
        var a = -Math.PI / 2 + 2 * Math.PI * i / n;
        d.fx = d.x = cx + r * Math.cos(a);
        d.fy = d.y = cy + r * Math.sin(a);
      });
    } else { // grid
      var cols = Math.ceil(Math.sqrt(n)), rows = Math.ceil(n / cols);
      var dx = (width - 2 * PAD - NODE_W) / Math.max(1, cols - 1);
      var dy = (height - 2 * PAD - NODE_H) / Math.max(1, rows - 1);
      nodes.forEach(function (d, i) {
        var c = i % cols, rr = Math.floor(i / cols);
        d.fx = d.x = cols === 1 ? width / 2 : PAD + NODE_W / 2 + c * dx;
        d.fy = d.y = rows === 1 ? height / 2 : PAD + NODE_H / 2 + rr * dy;
      });
    }
    ticked();
  }

  // ---- drag ---------------------------------------------------------------------

  function dragStart(event, d) {
    if (MP.state.get().layout === "force" && !event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
    d._moved = false;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
    d._moved = true;
    if (MP.state.get().layout !== "force") {
      d.x = event.x;
      d.y = event.y;
      ticked();
    }
  }

  function dragEnd(event, d) {
    if (MP.state.get().layout === "force") {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
    if (d._moved && brushActive) selectFromBrush(d3.brushSelection(gBrush.node()));
  }

  // ---- selection ------------------------------------------------------------------

  function onNodeClick(event, d) {
    if (d._moved) { d._moved = false; return; }
    var S = MP.state.get();
    var sel = S.selectedClusters.slice();
    var i = sel.indexOf(d.id);
    if (i >= 0) sel.splice(i, 1); else sel.push(d.id);
    clearBrush();
    MP.state.set({ selectedClusters: sel }, "network");
  }

  function onBrushEnd(event) {
    if (programmatic) return;
    if (!event.selection) {
      // Click on empty canvas: no brush means every cluster, as in Shiny.
      brushActive = false;
      if (event.sourceEvent) MP.state.set({ selectedClusters: MP.D.clusters.slice() }, "network");
      return;
    }
    brushActive = true;
    selectFromBrush(event.selection);
  }

  function selectFromBrush(extent) {
    if (!extent) return;
    var x0 = extent[0][0], y0 = extent[0][1], x1 = extent[1][0], y1 = extent[1][1];
    var inside = nodes.filter(function (d) {
      return d.x >= x0 && d.x <= x1 && d.y >= y0 && d.y <= y1;
    }).map(function (d) { return d.id; });
    MP.state.set({ selectedClusters: inside }, "network");
  }

  function clearBrush() {
    if (!gBrush) return;
    programmatic = true;
    gBrush.call(brush.move, null);
    programmatic = false;
    brushActive = false;
  }

  /* Brush rectangle (SVG coordinates) that holds only the node `id`.
     Used by the virtual mouse; null when the node does not exist. */
  function nodeBox(id) {
    var d = nodeById.get(id);
    if (!d || !svg) return null;
    var hw = NODE_W / 2 + 6, hh = NODE_H / 2 + 6;
    var crowded = nodes.some(function (o) {
      return o !== d && Math.abs(o.x - d.x) <= hw && Math.abs(o.y - d.y) <= hh;
    });
    if (crowded) { hw = 6; hh = 6; }
    return {
      x0: MP.utils.clamp(d.x - hw, 0, width), y0: MP.utils.clamp(d.y - hh, 0, height),
      x1: MP.utils.clamp(d.x + hw, 0, width), y1: MP.utils.clamp(d.y + hh, 0, height),
      svg: svg.node()
    };
  }

  /* Move the brush rectangle. Only the final move selects, through onBrushEnd
     like a brush drawn by hand; earlier moves just draw the rectangle. */
  function brushTo(extent, final) {
    if (!gBrush) return;
    programmatic = !final;
    gBrush.call(brush.move, extent);
    programmatic = false;
  }

  function highlight() {
    var S = MP.state.get();
    var sel = new Set(S.selectedClusters);
    var subset = S.selectedClusters.length < MP.D.clusters.length;
    gNodes.selectAll("g.mp-node")
      .classed("selected", function (d) { return subset && sel.has(d.id); })
      .classed("faded", function (d) { return subset && !sel.has(d.id); });
    gEdges.selectAll("line.mp-edge")
      .classed("faded", function (l) {
        return subset && !(sel.has(l.source.id) && sel.has(l.target.id));
      });
  }

  // ---- legend and resize -------------------------------------------------------------

  function renderLegend(maxN) {
    if (maxN === undefined) maxN = currentCounts();
    var legend = d3.select("#network_legend");
    legend.selectAll("*").remove();
    legend.append("span").text("number of features");
    var w = 120, h = 12;
    var s = legend.append("svg").attr("width", w).attr("height", h);
    var id = "mp-node-grad";
    var grad = s.append("defs").append("linearGradient").attr("id", id);
    grad.append("stop").attr("offset", "0%").attr("stop-color", MP.palettes.nodeLow);
    grad.append("stop").attr("offset", "100%").attr("stop-color", MP.palettes.nodeHigh);
    s.append("rect").attr("width", w).attr("height", h).attr("fill", "url(#" + id + ")")
      .attr("stroke", "#999").attr("stroke-width", 0.5);
    legend.append("span").text("0 to " + maxN);
  }

  function resize() {
    if (!svg) return;
    var oldW = width, oldH = height;
    measure();
    if (oldW === width && oldH === height) return;
    svg.attr("width", width).attr("height", height);
    brush.extent([[0, 0], [width, height]]);
    gBrush.call(brush);
    clearBrush();
    nodes.forEach(function (d) { d.x *= width / oldW; d.y *= height / oldH; });
    applyLayout();
  }

  MP.network = {
    init: init, render: render, resize: resize, clearBrush: clearBrush,
    nodeBox: nodeBox, brushTo: brushTo
  };
})(window.MolPad = window.MolPad || {});
