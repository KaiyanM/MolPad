/* MolPad D3 dashboard: small shared helpers. */
(function (MP) {
  "use strict";

  function uniq(arr) {
    return Array.from(new Set(arr));
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function debounce(fn, ms) {
    var t = null;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms);
    };
  }

  /* Min-max scaling like R's convert_range(); all 1 when the range is empty. */
  function rescale(values) {
    var finite = values.filter(function (v) { return Number.isFinite(v); });
    if (!finite.length) return values.map(function () { return 1; });
    var lo = Math.min.apply(null, finite), hi = Math.max.apply(null, finite);
    if (hi === lo) return values.map(function () { return 1; });
    return values.map(function (v) {
      return Number.isFinite(v) ? (v - lo) / (hi - lo) : 1;
    });
  }

  /* Sort key so "Group_10" sorts after "Group_2". */
  function clusterKey(name) {
    var m = /(\d+)\s*$/.exec(String(name));
    return m ? Number(m[1]) : Number.POSITIVE_INFINITY;
  }

  function compareClusters(a, b) {
    var ka = clusterKey(a), kb = clusterKey(b);
    if (ka !== kb) return ka - kb;
    return String(a).localeCompare(String(b));
  }

  /* Render every id matched by link.pattern as an anchor, joined by <br/>. */
  function renderLinks(text, link) {
    if (text === null || text === undefined) return "";
    var str = String(text);
    if (!link || !link.pattern) return escapeHtml(str);
    var re;
    try {
      re = new RegExp(link.pattern, "g");
    } catch (e) {
      return escapeHtml(str);
    }
    var ids = str.match(re);
    if (!ids || !ids.length) return "";
    return ids.map(function (id) {
      var href = String(link.url || "").split("{id}").join(encodeURIComponent(id));
      return '<a href="' + escapeHtml(href) + '" target="_blank" rel="noopener">' +
        escapeHtml(id) + "</a>";
    }).join("<br/>");
  }

  function fmt(x, digits) {
    if (x === null || x === undefined || !Number.isFinite(x)) return "";
    return Number(x).toFixed(digits === undefined ? 2 : digits);
  }

  function clamp(x, lo, hi) {
    return Math.max(lo, Math.min(hi, x));
  }

  function setsEqual(a, b) {
    if (a.length !== b.length) return false;
    var s = new Set(a);
    return b.every(function (v) { return s.has(v); });
  }

  MP.utils = {
    uniq: uniq,
    escapeHtml: escapeHtml,
    debounce: debounce,
    rescale: rescale,
    clusterKey: clusterKey,
    compareClusters: compareClusters,
    renderLinks: renderLinks,
    fmt: fmt,
    clamp: clamp,
    setsEqual: setsEqual
  };
})(window.MolPad = window.MolPad || {});
