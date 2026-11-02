/* MolPad D3 dashboard: stacked bar of taxonomic scope per selected cluster.
   Bar length = number of features the cluster views show (state.clusterFeatures):
   the features passing the filters, or every feature with "All features". */
(function (MP) {
  "use strict";

  var container, legendDiv, svg;
  var margin = { top: 6, right: 12, bottom: 28, left: 70 };

  function init(selector) {
    container = d3.select(selector);
    legendDiv = container.append("div").attr("class", "mp-swatches");
    svg = container.append("svg");
    MP.state.subscribe(["selectedClusters", "level1", "level2", "scope"], render);
  }

  function counts() {
    var D = MP.D;
    var byCluster = new Map(MP.state.sortedSelectedClusters().map(function (c) {
      var row = { cluster: c, total: 0 };
      D.taxa.forEach(function (t) { row[t] = 0; });
      return [c, row];
    }));
    MP.state.clusterFeatures().forEach(function (f) {
      var t = MP.data.levelOf(f, 2);
      var row = byCluster.get(f.cluster);
      if (t === "" || !row) return;   // no taxonomic scope: no segment to draw
      row[t] = (row[t] || 0) + 1;
      row.total += 1;
    });
    return { rows: Array.from(byCluster.values()), keys: D.taxa };
  }

  function updateTitle() {
    var t = document.getElementById("stackbar_title");
    if (!t) return;
    var S = MP.state.get();
    t.textContent = "Taxonomic Scope of Selected Groups" +
      (S.scope === "all" || !MP.state.isFiltered() ? " (all features)" : " (filtered features)");
  }

  function render() {
    var D = MP.D;
    updateTitle();
    var data = counts();
    var present = data.keys.filter(function (t) {
      return data.rows.some(function (r) { return r[t] > 0; });
    });

    legendDiv.selectAll("*").remove();
    legendDiv.append("span").attr("class", "mp-swatch-title").text("taxonomic.scope");
    present.forEach(function (t) {
      var s = legendDiv.append("span").attr("class", "mp-swatch");
      s.append("i").style("background", D.taxaColor(t));
      s.append("span").text(t);
    });

    var width = Math.max(200, container.node().clientWidth || 300);
    var rowH = 22;
    var innerH = Math.max(rowH, rowH * data.rows.length);
    var height = innerH + margin.top + margin.bottom;
    svg.attr("width", width).attr("height", height);
    svg.selectAll("*").remove();

    if (!data.rows.length) {
      svg.append("text").attr("x", 8).attr("y", 20).attr("class", "mp-empty-svg")
        .style("fill", "#666").style("font-style", "italic").text("No clusters selected");
      return;
    }

    var g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    var innerW = width - margin.left - margin.right;
    var y = d3.scaleBand().domain(data.rows.map(function (r) { return r.cluster; }))
      .range([0, innerH]).padding(0.2);
    var maxTotal = d3.max(data.rows, function (r) { return r.total; }) || 1;
    var x = d3.scaleLinear().domain([0, maxTotal]).nice().range([0, innerW]);

    var stacked = d3.stack().keys(present)(data.rows);
    g.append("g").selectAll("g").data(stacked).join("g")
      .attr("fill", function (s) { return D.taxaColor(s.key); })
      .selectAll("rect").data(function (s) {
        return s.map(function (d) { d.key = s.key; return d; });
      }).join("rect")
      .attr("y", function (d) { return y(d.data.cluster); })
      .attr("x", function (d) { return x(d[0]); })
      .attr("width", function (d) { return Math.max(0, x(d[1]) - x(d[0])); })
      .attr("height", y.bandwidth())
      .append("title").text(function (d) {
        return d.data.cluster + " \u00b7 " + d.key + " \u00b7 " + (d[1] - d[0]) + " feature(s)";
      });

    g.append("g").attr("class", "mp-axis").call(d3.axisLeft(y));
    g.append("g").attr("class", "mp-axis").attr("transform", "translate(0," + innerH + ")")
      .call(d3.axisBottom(x).ticks(Math.min(6, maxTotal)).tickFormat(d3.format("d")));
    g.append("text").attr("class", "mp-axis-title")
      .attr("x", innerW / 2).attr("y", innerH + 24).text("number of features");
  }

  function resize() { render(); }

  MP.stackbar = { init: init, render: render, resize: resize };
})(window.MolPad = window.MolPad || {});
