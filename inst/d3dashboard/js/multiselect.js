/* MolPad D3 dashboard: checkbox drop-down for a multi-choice filter.

   A button reads "All", the one value, or "3 selected". It opens a checklist
   with "All" on top and a feature count after each option; an option whose
   count is 0 under the other filters is greyed out (but stays clickable while
   ticked, so it can always be removed). Ticking "All" clears the choice, and
   unticking the last value goes back to All. */
(function (MP) {
  "use strict";

  var open = null;   // the widget whose list is showing

  document.addEventListener("mousedown", function (event) {
    if (open && !open.root.contains(event.target)) open.close();
  });
  document.addEventListener("keydown", function (event) {
    if (open && event.key === "Escape") open.close();
  });

  /* opts: { mount (element), id, values, selected(): [], counts(): Map, onChange(list) } */
  function create(opts) {
    var root = document.createElement("div");
    root.className = "mp-ms";
    root.id = opts.id;

    var button = document.createElement("button");
    button.type = "button";
    button.className = "mp-ms-btn";
    button.id = opts.id + "_btn";
    button.setAttribute("aria-haspopup", "listbox");
    root.appendChild(button);

    var panel = document.createElement("div");
    panel.className = "mp-ms-panel";
    panel.hidden = true;
    root.appendChild(panel);
    opts.mount.appendChild(root);

    var rows = new Map();   // value ("" = All) -> { label, input, count }
    [""].concat(opts.values).forEach(function (v) {
      var label = document.createElement("label");
      label.className = "mp-ms-opt" + (v === "" ? " mp-ms-all" : "");
      label.setAttribute("data-value", v);
      var input = document.createElement("input");
      input.type = "checkbox";
      var name = document.createElement("span");
      name.className = "mp-ms-name";
      name.textContent = v === "" ? "All" : v;
      var count = document.createElement("span");
      count.className = "mp-ms-count";
      label.appendChild(input);
      label.appendChild(name);
      label.appendChild(count);
      panel.appendChild(label);
      rows.set(v, { label: label, input: input, count: count });
      input.addEventListener("change", function () { toggle(v, input.checked); });
    });

    function toggle(v, on) {
      var list = opts.selected().slice();
      if (v === "") {
        list = [];
      } else if (on) {
        if (list.indexOf(v) < 0) list.push(v);
        list = opts.values.filter(function (x) { return list.indexOf(x) >= 0; });   // keep data order
      } else {
        list = list.filter(function (x) { return x !== v; });
      }
      opts.onChange(list);
      refresh();
    }

    function refresh() {
      var sel = opts.selected();
      var counts = opts.counts();
      var total = 0;
      counts.forEach(function (n) { total += n; });
      rows.forEach(function (r, v) {
        var n = v === "" ? total : (counts.get(v) || 0);
        var on = v === "" ? !sel.length : sel.indexOf(v) >= 0;
        r.input.checked = on;
        r.count.textContent = "(" + MP.utils.fmtInt(n) + ")";
        var dead = v !== "" && n === 0 && !on;
        r.input.disabled = dead;
        r.label.classList.toggle("mp-ms-disabled", dead);
      });
      button.textContent = !sel.length ? "All" : sel.length === 1 ? sel[0] : sel.length + " selected";
      button.title = sel.length ? sel.join(", ") : "All";
    }

    var widget = {
      root: root,
      button: button,
      panel: panel,
      isOpen: function () { return !panel.hidden; },
      open: function () {
        if (open && open !== widget) open.close();
        refresh();
        panel.hidden = false;
        root.classList.add("mp-ms-open");
        open = widget;
      },
      close: function () {
        panel.hidden = true;
        root.classList.remove("mp-ms-open");
        if (open === widget) open = null;
      },
      /* The clickable row of one value ("" = All), for the virtual mouse. */
      option: function (v) { var r = rows.get(v); return r ? r.label : null; },
      refresh: refresh
    };

    button.addEventListener("click", function () {
      if (widget.isOpen()) widget.close(); else widget.open();
    });
    refresh();
    return widget;
  }

  MP.multiselect = { create: create };
})(window.MolPad = window.MolPad || {});
