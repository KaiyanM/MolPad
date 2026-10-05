/* MolPad D3 dashboard: annotation table of the selected features. */
(function (MP) {
  "use strict";

  var MENU_MAX = 500;

  var container, el = {};
  /* filters: column -> Set of allowed value keys (absent = no filter). */
  /* terms: the global search, split on commas; a row matches any term. */
  var local = { page: 1, pageSize: 5, terms: [], sortKey: null, sortDir: 1, filters: {} };
  var cache = { rows: [], columns: [] };
  /* The sort & filter menu lives on <body> so table redraws and the
     horizontal scroll container do not destroy or clip it. */
  var menu = { el: null, col: null, query: "", values: [], shown: [] };
  var linkRe = {};

  function init(selector) {
    container = d3.select(selector);
    ["table_search", "table_pagesize", "table_prev", "table_next", "table_info", "table_clear"].forEach(function (id) {
      el[id] = document.getElementById(id);
    });
    el.table_pagesize.value = String(local.pageSize);
    el.table_pagesize.addEventListener("change", function () {
      local.pageSize = Number(el.table_pagesize.value) || 5;
      local.page = 1;
      draw();
    });
    el.table_search.addEventListener("input", MP.utils.debounce(function () {
      local.terms = el.table_search.value.toLowerCase().split(",")
        .map(function (t) { return t.trim(); })
        .filter(function (t) { return t !== ""; });
      local.page = 1;
      draw();
      if (menu.col !== null) renderMenuList();
    }, 150));
    el.table_prev.addEventListener("click", function () { local.page -= 1; draw(); });
    el.table_next.addEventListener("click", function () { local.page += 1; draw(); });
    el.table_clear.addEventListener("click", function () {
      local.filters = {};
      local.terms = [];
      el.table_search.value = "";
      local.page = 1;
      draw();
      if (menu.col !== null) renderMenuList();
    });

    initMenu();

    MP.state.subscribe(["selectedClusters", "taxa", "tablePathway"], function () {
      local.page = 1;
      closeMenu();
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

  /* Values a cell contributes to its column filter: every linked id for
     link columns (matching what the cell displays), else the cell text. */
  function cellKeys(f, c) {
    var text = cellText(f, c);
    var link = MP.D.idLinks[c];
    if (!link || !link.pattern) return [text];
    if (!(c in linkRe)) {
      try { linkRe[c] = new RegExp(link.pattern, "g"); } catch (e) { linkRe[c] = null; }
    }
    if (!linkRe[c]) return [text];
    var ids = text.match(linkRe[c]);
    return ids && ids.length ? ids : [""];
  }

  function compareValues(key, va, vb) {
    var na = Number(va), nb = Number(vb);
    if (va !== "" && vb !== "" && Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
    if (key === "cluster") return MP.utils.compareClusters(va, vb);
    return va.localeCompare(vb);
  }

  /* Rows passing the global search and every column filter except exceptCol. */
  function filtered(exceptCol) {
    var cols = cache.columns;
    var data = cache.rows;

    if (local.terms.length) {
      var terms = local.terms;
      data = data.filter(function (f) {
        return cols.some(function (c) {
          var text = cellText(f, c).toLowerCase();
          return terms.some(function (t) { return text.indexOf(t) >= 0; });
        });
      });
    }

    var active = cols.filter(function (c) { return local.filters[c] && c !== exceptCol; });
    if (active.length) {
      data = data.filter(function (f) {
        return active.every(function (c) {
          var allowed = local.filters[c];
          return cellKeys(f, c).some(function (k) { return allowed.has(k); });
        });
      });
    }
    return data;
  }

  function render() {
    cache.columns = columns();
    cache.rows = rows();
    draw();
  }

  function draw() {
    var D = MP.D;
    var cols = cache.columns;
    var data = filtered(null);

    if (local.sortKey && cols.indexOf(local.sortKey) >= 0) {
      var key = local.sortKey, dir = local.sortDir;
      data = data.slice().sort(function (a, b) {
        return compareValues(key, cellText(a, key), cellText(b, key)) * dir;
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
    el.table_clear.disabled = !local.terms.length && !Object.keys(local.filters).length;

    var html = ['<table class="mp-table"><thead><tr>'];
    cols.forEach(function (c) {
      var name = MP.utils.escapeHtml(c);
      var caret = "";
      if (local.sortKey === c) caret = '<span class="mp-sort">' + (local.sortDir > 0 ? "\u25b2" : "\u25bc") + "</span>";
      var btn = '<button type="button" class="mp-filter-btn' + (local.filters[c] ? " mp-active" : "") +
        '" aria-haspopup="true" aria-label="Sort and filter ' + name + '" title="Sort and filter">\u25be</button>';
      html.push('<th data-col="' + name + '">' + name + caret + btn + "</th>");
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
      local.page = 1;
      draw();
    });
    container.selectAll(".mp-filter-btn").on("click", function (event) {
      event.stopPropagation();
      var c = this.parentNode.getAttribute("data-col");
      if (menu.col === c) closeMenu();
      else openMenu(c);
    });
    placeMenu();
  }

  /* ---- sort & filter menu ------------------------------------------------ */

  function initMenu() {
    var m = document.createElement("div");
    m.className = "mp-menu";
    m.hidden = true;
    m.innerHTML =
      '<button type="button" class="mp-menu-item" data-act="asc">Sort ascending</button>' +
      '<button type="button" class="mp-menu-item" data-act="desc">Sort descending</button>' +
      '<button type="button" class="mp-menu-item" data-act="clear"></button>' +
      '<input type="search" class="mp-menu-search" placeholder="Search values..." aria-label="Search values">' +
      '<label class="mp-menu-check mp-menu-all"><input type="checkbox"><span></span></label>' +
      '<div class="mp-menu-list"></div>';
    document.body.appendChild(m);
    menu.el = m;
    menu.search = m.querySelector(".mp-menu-search");
    menu.all = m.querySelector(".mp-menu-all input");
    menu.allLabel = m.querySelector(".mp-menu-all span");
    menu.list = m.querySelector(".mp-menu-list");
    menu.clear = m.querySelector('[data-act="clear"]');

    m.addEventListener("click", function (event) {
      var act = event.target.getAttribute("data-act");
      if (!act) return;
      if (act === "clear") {
        setFilter(null);
      } else {
        local.sortKey = menu.col;
        local.sortDir = act === "asc" ? 1 : -1;
        local.page = 1;
        draw();
        renderMenuList();
      }
    });
    menu.search.addEventListener("input", MP.utils.debounce(function () {
      if (menu.col === null) return;
      menu.query = menu.search.value.trim().toLowerCase();
      renderMenuList();
      placeMenu();
    }, 150));
    menu.all.addEventListener("change", function () {
      var set;
      if (menu.all.checked) {
        /* With a search typed, keep exactly the matches (as Excel does). */
        set = menu.query ? new Set(menu.shown) : null;
      } else {
        set = menu.query ? currentSet() : new Set();
        menu.shown.forEach(function (k) { set.delete(k); });
      }
      setFilter(set);
    });
    menu.list.addEventListener("change", function (event) {
      var i = event.target.getAttribute("data-i");
      if (i === null) return;
      var set = currentSet();
      if (event.target.checked) set.add(menu.shown[Number(i)]);
      else set.delete(menu.shown[Number(i)]);
      setFilter(set);
    });

    document.addEventListener("mousedown", function (event) {
      if (menu.col === null || m.contains(event.target)) return;
      /* Header buttons toggle the menu themselves. */
      if (event.target.classList && event.target.classList.contains("mp-filter-btn")) return;
      closeMenu();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeMenu();
    });
    /* Filtering changes the page height, so follow the header button
       instead of closing when the page moves. */
    window.addEventListener("resize", placeMenu);
    window.addEventListener("scroll", function (event) {
      if (!m.contains(event.target)) placeMenu();
    }, true);
  }

  function valueLabel(k) {
    return k === "" ? "(Blanks)" : k;
  }

  /* Allowed values of the open column as an editable copy. */
  function currentSet() {
    var set = local.filters[menu.col];
    return new Set(set ? Array.from(set) : menu.values);
  }

  function setFilter(set) {
    var all = set && menu.values.every(function (k) { return set.has(k); });
    if (!set || all) delete local.filters[menu.col];
    else local.filters[menu.col] = set;
    local.page = 1;
    draw();
    renderMenuList();
  }

  function openMenu(col) {
    menu.col = col;
    menu.query = "";
    menu.search.value = "";
    menu.el.hidden = false;
    renderMenuList();
    placeMenu();
    menu.search.focus({ preventScroll: true });
  }

  /* Keep the menu under its column's header button, inside the viewport. */
  function placeMenu() {
    if (menu.col === null) return;
    var btn = container.selectAll(".mp-filter-btn").nodes().filter(function (b) {
      return b.parentNode.getAttribute("data-col") === menu.col;
    })[0];
    if (!btn) { closeMenu(); return; }
    var r = btn.getBoundingClientRect();
    var w = menu.el.offsetWidth, h = menu.el.offsetHeight;
    var left = MP.utils.clamp(r.left, 8, Math.max(8, window.innerWidth - w - 8));
    var top = MP.utils.clamp(r.bottom + 4, 8, Math.max(8, window.innerHeight - h - 8));
    menu.el.style.left = left + "px";
    menu.el.style.top = top + "px";
  }

  function closeMenu() {
    if (menu.col === null) return;
    menu.col = null;
    menu.el.hidden = true;
  }

  function renderMenuList() {
    var col = menu.col;
    var counts = new Map();
    filtered(col).forEach(function (f) {
      MP.utils.uniq(cellKeys(f, col)).forEach(function (k) {
        counts.set(k, (counts.get(k) || 0) + 1);
      });
    });
    menu.values = Array.from(counts.keys()).sort(function (a, b) {
      if (a === "" || b === "") return a === b ? 0 : (a === "" ? 1 : -1);
      return compareValues(col, a, b);
    });
    var q = menu.query;
    menu.shown = !q ? menu.values : menu.values.filter(function (k) {
      return valueLabel(k).toLowerCase().indexOf(q) >= 0;
    });

    var set = local.filters[col];
    function isChecked(k) { return !set || set.has(k); }

    var html = menu.shown.slice(0, MENU_MAX).map(function (k, i) {
      return '<label class="mp-menu-check"><input type="checkbox" data-i="' + i + '"' +
        (isChecked(k) ? " checked" : "") + "><span>" + MP.utils.escapeHtml(valueLabel(k)) +
        '</span><small>' + counts.get(k) + "</small></label>";
    });
    if (!menu.shown.length) {
      html.push('<div class="mp-menu-note">No matching values</div>');
    } else if (menu.shown.length > MENU_MAX) {
      html.push('<div class="mp-menu-note">' + (menu.shown.length - MENU_MAX) + " more, refine the search</div>");
    }
    menu.list.innerHTML = html.join("");

    var allOn = menu.shown.length > 0 && menu.shown.every(isChecked);
    menu.all.checked = allOn;
    menu.all.indeterminate = !allOn && menu.shown.some(isChecked);
    menu.all.disabled = !menu.shown.length;
    menu.allLabel.textContent = q ? "(Select all search results)" : "(Select all)";

    menu.clear.textContent = 'Clear filter from "' + col + '"';
    menu.clear.disabled = !set;
    ["asc", "desc"].forEach(function (act) {
      var on = local.sortKey === col && local.sortDir === (act === "asc" ? 1 : -1);
      menu.el.querySelector('[data-act="' + act + '"]').classList.toggle("mp-on", on);
    });
  }

  MP.table = { init: init, render: render };
})(window.MolPad = window.MolPad || {});
