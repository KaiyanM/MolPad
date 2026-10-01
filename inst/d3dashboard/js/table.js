/* MolPad D3 dashboard: annotation table of the selected features. */
(function (MP) {
  "use strict";

  var container, el = {};
  var local = { page: 1, pageSize: 5, query: "", sortKey: null, sortDir: 1 };
  var cache = { rows: [], columns: [] };

  function init(selector) {
    container = d3.select(selector);
    ["table_search", "table_pagesize", "table_prev", "table_next", "table_info"].forEach(function (id) {
      el[id] = document.getElementById(id);
    });
    el.table_pagesize.value = String(local.pageSize);
    el.table_pagesize.addEventListener("change", function () {
      local.pageSize = Number(el.table_pagesize.value) || 5;
      local.page = 1;
      draw();
    });
    el.table_search.addEventListener("input", MP.utils.debounce(function () {
      local.query = el.table_search.value.trim().toLowerCase();
      local.page = 1;
      draw();
    }, 150));
    el.table_prev.addEventListener("click", function () { local.page -= 1; draw(); });
    el.table_next.addEventListener("click", function () { local.page += 1; draw(); });

    MP.state.subscribe(["selectedClusters", "taxa", "tablePathway"], function () {
      local.page = 1;
      render();
    });
  }

  function columns() {
    var S = MP.state.get();
    var ann = MP.D.annotationColumns.filter(function (c) {
      return !(c === "Pathway" && S.tablePathway !== "");
    });
    return ["ID", "cluster", "type"].concat(ann);
  }

  function rows() {
    var S = MP.state.get();
    var out = MP.state.selectedFeatures();
    if (S.tablePathway !== "") {
      out = out.filter(function (f) { return String(f.Pathway) === S.tablePathway; });
    }
    return out;
  }

  function cellText(f, c) {
    var v = f[c];
    return v === null || v === undefined ? "" : String(v);
  }

  function render() {
    cache.columns = columns();
    cache.rows = rows();
    draw();
  }

  function draw() {
    var D = MP.D;
    var cols = cache.columns;
    var data = cache.rows;

    if (local.query) {
      var q = local.query;
      data = data.filter(function (f) {
        return cols.some(function (c) { return cellText(f, c).toLowerCase().indexOf(q) >= 0; });
      });
    }

    if (local.sortKey && cols.indexOf(local.sortKey) >= 0) {
      var key = local.sortKey, dir = local.sortDir;
      data = data.slice().sort(function (a, b) {
        var va = cellText(a, key), vb = cellText(b, key);
        var na = Number(va), nb = Number(vb);
        var cmp;
        if (va !== "" && vb !== "" && Number.isFinite(na) && Number.isFinite(nb)) cmp = na - nb;
        else if (key === "cluster") cmp = MP.utils.compareClusters(va, vb);
        else cmp = va.localeCompare(vb);
        return cmp * dir;
      });
    }

    var total = data.length;
    var pages = Math.max(1, Math.ceil(total / local.pageSize));
    local.page = MP.utils.clamp(local.page, 1, pages);
    var start = (local.page - 1) * local.pageSize;
    var pageRows = data.slice(start, start + local.pageSize);

    el.table_info.textContent = total
      ? "Showing " + (start + 1) + "\u2013" + (start + pageRows.length) + " of " + total
      : "No matching features";
    el.table_prev.disabled = local.page <= 1;
    el.table_next.disabled = local.page >= pages;

    var html = ['<table class="mp-table"><thead><tr>'];
    cols.forEach(function (c) {
      var caret = "";
      if (local.sortKey === c) caret = '<span class="mp-sort">' + (local.sortDir > 0 ? "\u25b2" : "\u25bc") + "</span>";
      html.push('<th data-col="' + MP.utils.escapeHtml(c) + '">' + MP.utils.escapeHtml(c) + caret + "</th>");
    });
    html.push("</tr></thead><tbody>");
    pageRows.forEach(function (f) {
      html.push("<tr>");
      cols.forEach(function (c) {
        var link = D.idLinks[c];
        if (link) {
          html.push('<td class="mp-wrap"><div>' + MP.utils.renderLinks(f[c], link) + "</div></td>");
        } else {
          html.push("<td>" + MP.utils.escapeHtml(cellText(f, c)) + "</td>");
        }
      });
      html.push("</tr>");
    });
    html.push("</tbody></table>");
    container.html(html.join(""));

    container.selectAll("th").on("click", function () {
      var c = this.getAttribute("data-col");
      if (local.sortKey === c) {
        local.sortDir = -local.sortDir;
      } else {
        local.sortKey = c;
        local.sortDir = 1;
      }
      draw();
    });
  }

  MP.table = { init: init, render: render };
})(window.MolPad = window.MolPad || {});
