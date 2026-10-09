/* MolPad D3 dashboard: text commands that drive the virtual mouse.
   A command is "function:param", for example "brush node:Group_2". */
(function (MP) {
  "use strict";

  var queue = Promise.resolve();

  /* Case-insensitive exact match of `param` in `values`; null when absent. */
  function match(values, param) {
    var want = String(param).toLowerCase();
    for (var i = 0; i < values.length; i++) {
      if (String(values[i]).toLowerCase() === want) return values[i];
    }
    return null;
  }

  function setFilter(param) {
    var value = match(MP.D.pathways, param);
    if (value === null) {
      throw new Error('No annotation named "' + param + '". Choose one of: ' +
        MP.D.pathways.join(", "));
    }
    var select = document.getElementById("s_ptw");
    MP.app.showTab("main");
    return MP.cursor.toElement(select).then(function () {
      MP.cursor.press();
      select.value = value;
      // The listener in controls.js does the rest, as for a real choice.
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return MP.cursor.wait(180);
    }).then(function () {
      MP.cursor.release();
      return "Filter set to " + MP.state.get().pathway + ".";
    });
  }

  function brushNode(param) {
    var id = match(MP.D.clusters, param);
    if (id === null) {
      throw new Error('No node named "' + param + '". Choose one of: ' +
        MP.D.clusters.join(", "));
    }
    MP.app.showTab("main");
    var svg = MP.network.nodeBox(id).svg;
    svg.scrollIntoView({ block: "nearest", inline: "nearest" });

    function corner(which) {
      var b = MP.network.nodeBox(id), r = svg.getBoundingClientRect();
      return which === 0 ? { x: r.left + b.x0, y: r.top + b.y0 }
                         : { x: r.left + b.x1, y: r.top + b.y1 };
    }

    return MP.cursor.moveTo(function () { return corner(0); }, 600).then(function () {
      MP.cursor.press();
      return MP.cursor.moveTo(function () { return corner(1); }, 450, function (p) {
        var b = MP.network.nodeBox(id), r = svg.getBoundingClientRect();
        MP.network.brushTo([[b.x0, b.y0],
          [Math.max(b.x0 + 1, p.x - r.left), Math.max(b.y0 + 1, p.y - r.top)]], false);
      });
    }).then(function () {
      var b = MP.network.nodeBox(id);
      MP.network.brushTo([[b.x0, b.y0], [b.x1, b.y1]], true);
      MP.cursor.release();
      var sel = MP.state.get().selectedClusters;
      if (sel.length === 1 && sel[0] === id) return "Brushed " + id + ".";
      return "Brushed around " + id + ", but the selection is: " +
        (sel.length ? sel.join(", ") : "empty") + ".";
    });
  }

  var commands = {
    "brush node": { usage: "brush node:Group_2", run: brushNode },
    "set filter": { usage: "set filter:<annotation>", run: setFilter }
  };

  function usage() {
    return Object.keys(commands).map(function (k) { return commands[k].usage; }).join("\n");
  }

  function parse(text) {
    var str = String(text === null || text === undefined ? "" : text);
    var i = str.indexOf(":");
    var fn = (i < 0 ? str : str.slice(0, i)).trim().toLowerCase().replace(/\s+/g, " ");
    var param = i < 0 ? "" : str.slice(i + 1).trim();
    if (i < 0 || !commands[fn]) {
      throw new Error('Type a command as "function:param". Known commands:\n' + usage());
    }
    if (!param) throw new Error("Missing value. Example: " + commands[fn].usage);
    return { fn: fn, param: param };
  }

  /* Run one command after the ones already queued. Resolves with a short
     report, rejects with an Error whose message can be shown to the user. */
  function run(text) {
    var job = queue.then(function () {
      var cmd = parse(text);
      return commands[cmd.fn].run(cmd.param);
    });
    queue = job.catch(function () {});
    return job;
  }

  MP.agent = { commands: commands, parse: parse, run: run, usage: usage };
})(window.MolPad = window.MolPad || {});
