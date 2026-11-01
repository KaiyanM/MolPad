/* MolPad D3 dashboard: text commands that drive the virtual mouse.
   A command is "function:param", for example "brush node:Group_2".
   "brush node", "select node", "search table" and "set filter2" take one value or several,
   comma-separated; "set filter1" takes one. "select all" and "clear table"
   take none. A JSON step list from the Python agent is played with play(). */
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

  /* Split a comma-separated list; the full-width comma is accepted too. */
  function listOf(param) {
    return String(param).split(/[,\uFF0C]/).map(function (v) { return v.trim(); })
      .filter(function (v) { return v; });
  }

  /* Level-1 filter: one value in the "Select a Functional Annotation" drop-down. */
  function setFilter1(param) {
    if (listOf(param).length > 1) {
      throw new Error("Filter 1 takes one value. Choose one of: " + MP.D.pathways.join(", "));
    }
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
      return "Filter 1 set to " + MP.state.get().pathway + ".";
    });
  }

  /* Level-2 filter: one or several values in the "Select a Taxonomic Scope"
     list. The first value is clicked (which drops the old choice), the others
     are added to it. "all" clears the list, which means every scope. */
  function setFilter2(param) {
    var parts = listOf(param);
    var clearAll = parts.length === 1 && parts[0].toLowerCase() === "all";
    var values = [];
    if (!clearAll) {
      parts.forEach(function (part) {
        var value = match(MP.D.taxa, part);
        if (value === null) {
          throw new Error('No taxonomic scope named "' + part + '". Choose from: ' +
            MP.D.taxa.join(", ") + ', or "all".');
        }
        if (values.indexOf(value) < 0) values.push(value);
      });
    }
    var select = document.getElementById("s_tax");
    var options = Array.prototype.slice.call(select.options);
    MP.app.showTab("main");

    function choose(target, change) {
      return MP.cursor.toElement(target, 400).then(function () {
        MP.cursor.press();
        change();
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return MP.cursor.wait(180);
      }).then(function () { MP.cursor.release(); });
    }

    var chain;
    if (clearAll) {
      chain = choose(select, function () {
        options.forEach(function (o) { o.selected = false; });
      });
    } else {
      chain = Promise.resolve();
      values.forEach(function (value, i) {
        var option = options.filter(function (o) { return o.value === value; })[0];
        chain = chain.then(function () {
          return choose(option, function () {
            if (i === 0) options.forEach(function (o) { o.selected = false; });
            option.selected = true;
          });
        });
      });
    }
    return chain.then(function () {
      var taxa = MP.state.get().taxa;
      return "Filter 2 set to " + (taxa.length ? taxa.join(", ") : "all") + ".";
    });
  }

  /* "Group_2, Group4" -> ["Group_2", "Group_4"]. Spaces, "_" and "-" inside
     a name are ignored, so "group 4" and "Group4" both find "Group_4". */
  function nodeList(param) {
    function loose(v) { return String(v).toLowerCase().replace(/[\s_-]+/g, ""); }
    var ids = [];
    listOf(param).forEach(function (part) {
      var id = match(MP.D.clusters, part);
      if (id === null) {
        var hit = MP.D.clusters.filter(function (c) { return loose(c) === loose(part); });
        id = hit.length === 1 ? hit[0] : null;
      }
      if (id === null) {
        throw new Error('No node named "' + part + '". Choose from: ' +
          MP.D.clusters.join(", "));
      }
      if (ids.indexOf(id) < 0) ids.push(id);
    });
    if (!ids.length) throw new Error("Missing value. Example: brush node:Group_2");
    return ids;
  }

  /* Show an error line in the dialogue panel while the command carries on. */
  function warn(text) {
    if (MP.chat && document.getElementById("chat_log")) MP.chat.say(text, "error");
    else if (window.console) window.console.warn(text);
  }

  function sameSet(a, b) {
    return a.length === b.length && a.every(function (v) { return b.indexOf(v) >= 0; });
  }

  /* One rectangle around the nodes, when a rectangle exists that holds them
     and no other node. Otherwise an error is shown and the command turns into
     "select node" for the same nodes. */
  function brushNode(param) {
    var ids = nodeList(param);
    MP.app.showTab("main");
    var svg = MP.network.nodeBox(ids).svg;
    svg.scrollIntoView({ block: "nearest", inline: "nearest" });
    var taken = MP.network.nodeBox(ids).others;
    if (taken.length) {
      warn("Cannot brush " + ids.join(", ") + ": the smallest rectangle around them also holds " +
        taken.join(", ") + ". Running select node:" + ids.join(", ") + " instead.");
      return selectNodes(ids);
    }

    function corner(which) {
      var b = MP.network.nodeBox(ids), r = svg.getBoundingClientRect();
      return which === 0 ? { x: r.left + b.x0, y: r.top + b.y0 }
                         : { x: r.left + b.x1, y: r.top + b.y1 };
    }

    return MP.cursor.moveTo(function () { return corner(0); }, 600).then(function () {
      MP.cursor.press();
      return MP.cursor.moveTo(function () { return corner(1); }, 450, function (p) {
        var b = MP.network.nodeBox(ids), r = svg.getBoundingClientRect();
        MP.network.brushTo([[b.x0, b.y0],
          [Math.max(b.x0 + 1, p.x - r.left), Math.max(b.y0 + 1, p.y - r.top)]], false);
      });
    }).then(function () {
      var b = MP.network.nodeBox(ids);
      MP.network.brushTo([[b.x0, b.y0], [b.x1, b.y1]], true);
      MP.cursor.release();
      var sel = MP.state.get().selectedClusters;
      if (sameSet(sel, ids)) return "Brushed " + ids.join(", ") + ".";
      return "Brushed around " + ids.join(", ") + ", but the selection is: " +
        (sel.length ? sel.join(", ") : "empty") + ".";
    });
  }

  /* Click "Clear all", then click the nodes in the order given. */
  function selectNodes(ids) {
    var clear = document.getElementById("btn_clear");
    MP.app.showTab("main");

    function click(run) {
      MP.cursor.press();
      run();
      return MP.cursor.wait(180).then(function () { MP.cursor.release(); });
    }

    var chain = MP.cursor.toElement(clear).then(function () {
      return click(function () { clear.click(); });
    });
    ids.forEach(function (id) {
      chain = chain.then(function () {
        var svg = MP.network.nodePoint(id).svg;
        svg.scrollIntoView({ block: "nearest", inline: "nearest" });
        return MP.cursor.moveTo(function () {
          var p = MP.network.nodePoint(id), r = svg.getBoundingClientRect();
          return { x: r.left + p.x, y: r.top + p.y };
        }, 450);
      }).then(function () {
        return click(function () {
          // A click toggles, so leave a node alone when it is already selected.
          if (MP.state.get().selectedClusters.indexOf(id) < 0) MP.network.toggleNode(id);
        });
      });
    });
    return chain.then(function () {
      var sel = MP.state.get().selectedClusters;
      if (sameSet(sel, ids)) return "Selected " + ids.join(", ") + ".";
      return "Clicked " + ids.join(", ") + ", but the selection is: " +
        (sel.length ? sel.join(", ") : "empty") + ".";
    });
  }

  function selectNode(param) {
    return selectNodes(nodeList(param));
  }

  /* Scroll to the feature table, click its search box and type the terms.
     Several comma-separated terms match rows that hold any of them. */
  function searchTable(param) {
    var text = listOf(param).join(", ");
    if (!text) throw new Error("Missing value. Example: search table:K00004, K00008");
    var input = document.getElementById("table_search");
    MP.app.showTab("main");
    input.scrollIntoView({ block: "center", inline: "nearest" });

    function type(i) {
      if (i > text.length) return Promise.resolve();
      input.value = text.slice(0, i);
      // The listener in table.js filters the rows, as for real typing.
      input.dispatchEvent(new Event("input", { bubbles: true }));
      return MP.cursor.wait(35).then(function () { return type(i + 1); });
    }

    return MP.cursor.toElement(input, 600).then(function () {
      MP.cursor.press();
      input.focus({ preventScroll: true });
      return MP.cursor.wait(180);
    }).then(function () {
      MP.cursor.release();
      return type(0);
    }).then(function () {
      return MP.cursor.wait(250);   // let the debounced search redraw the table
    }).then(function () {
      var info = document.getElementById("table_info");
      return "Searched the table for " + text + "." +
        (info && info.textContent ? " " + info.textContent.trim() : "");
    });
  }

  /* Pick one value in a drop-down with the pointer, as a user would. */
  function pick(select, value) {
    return MP.cursor.toElement(select).then(function () {
      MP.cursor.press();
      select.value = value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return MP.cursor.wait(180);
    }).then(function () { MP.cursor.release(); });
  }

  /* Click a button with the pointer. */
  function clickButton(button) {
    return MP.cursor.toElement(button).then(function () {
      MP.cursor.press();
      button.click();
      return MP.cursor.wait(180);
    }).then(function () { MP.cursor.release(); });
  }

  function setLayout(param) {
    var select = document.getElementById("s_layout");
    var layouts = Array.prototype.map.call(select.options, function (o) { return o.value; });
    var value = match(layouts, param);
    if (value === null) {
      throw new Error('No layout named "' + param + '". Choose one of: ' + layouts.join(", "));
    }
    MP.app.showTab("main");
    return pick(select, value).then(function () {
      return "Layout set to " + MP.state.get().layout + ".";
    });
  }

  /* Drag the Importance Score slider to a number, or to "min", "max" or
     "default" (the value at page load). The number is clamped to the slider
     range and rounded to its step. */
  function setImportance(param) {
    var slider = document.getElementById("obs");
    var ws = MP.D.weightSlider;
    var named = { min: ws.min, max: ws.max, "default": ws.value };
    var key = String(param).trim().toLowerCase();
    var want = named.hasOwnProperty(key) ? named[key] : Number(key);
    if (!isFinite(want) || key === "") {
      throw new Error('"' + param + '" is not a score. Give a number from ' + ws.min + " to " +
        ws.max + ', or "min", "max" or "default".');
    }
    var step = ws.step || 0.1;
    var value = MP.utils.clamp(Math.round(want / step) * step, ws.min, ws.max);
    value = Number(value.toFixed(6));
    MP.app.showTab("main");
    slider.scrollIntoView({ block: "nearest", inline: "nearest" });

    var EDGE = 8;   // half the thumb width: the thumb centre stays this far from the ends
    function thumb(v) {
      var r = slider.getBoundingClientRect();
      var k = ws.max > ws.min ? (v - ws.min) / (ws.max - ws.min) : 0;
      return { x: r.left + EDGE + k * (r.width - 2 * EDGE), y: r.top + r.height / 2 };
    }
    function put(v) {
      slider.value = v;
      // The listener in controls.js updates the label and the network.
      slider.dispatchEvent(new Event("input", { bubbles: true }));
    }

    return MP.cursor.moveTo(function () { return thumb(Number(slider.value)); }, 600).then(function () {
      MP.cursor.press();
      var target = thumb(value);
      return MP.cursor.moveTo(target, 500, function (p) {
        var r = slider.getBoundingClientRect();
        var k = MP.utils.clamp((p.x - r.left - EDGE) / (r.width - 2 * EDGE), 0, 1);
        put(ws.min + k * (ws.max - ws.min));
      });
    }).then(function () {
      put(value);
      return MP.cursor.wait(150);   // let the debounced listener apply the value
    }).then(function () {
      MP.cursor.release();
      var note = value === want ? "" : " (" + param + " is outside the slider range)";
      return "Importance score set to " + MP.state.get().minWeight + note + ".";
    });
  }

  /* Sort the table by clicking a column header: "GO_ID desc", "GO_ID asc"
     or just "GO_ID" (ascending). A header click sorts ascending first and
     flips on the next click, so a descending sort may take two clicks. */
  function sortTable(param) {
    var m = String(param).trim().match(/^(.*?)(?:\s+(asc|ascending|increase|desc|descending|decrease))?$/i);
    var name = m[1].trim();
    var desc = /^(desc|descending|decrease)$/i.test(m[2] || "");
    var table = document.getElementById("table_search");
    MP.app.showTab("main");

    function header() {
      var ths = Array.prototype.slice.call(document.querySelectorAll("table.mp-table th"));
      var cols = ths.map(function (th) { return th.getAttribute("data-col"); });
      var col = match(cols, name);
      if (col === null) {
        throw new Error('No table column named "' + name + '". Choose one of: ' + cols.join(", "));
      }
      return ths[cols.indexOf(col)];
    }
    function sortedAs(th) {
      var caret = th.querySelector(".mp-sort");
      if (!caret) return null;
      return caret.textContent === "\u25bc" ? "desc" : "asc";
    }
    function clickHeader(left) {
      var th = header();
      if (sortedAs(th) === (desc ? "desc" : "asc") || left === 0) return Promise.resolve();
      return MP.cursor.toElement(th, 500).then(function () {
        MP.cursor.press();
        th.click();   // the table is redrawn, so the header is looked up again
        return MP.cursor.wait(220);
      }).then(function () {
        MP.cursor.release();
        return clickHeader(left - 1);
      });
    }

    var first = header();   // fail before moving when the column does not exist
    table.scrollIntoView({ block: "center", inline: "nearest" });
    first.scrollIntoView({ block: "nearest", inline: "nearest" });
    return clickHeader(2).then(function () {
      var th = header();
      return "Table sorted by " + th.getAttribute("data-col") + ", " +
        (sortedAs(th) === "desc" ? "descending" : "ascending") + ".";
    });
  }

  /* "Select all": every cluster selected, brush removed. */
  function selectAll() {
    MP.app.showTab("main");
    return clickButton(document.getElementById("btn_reset")).then(function () {
      return "All " + MP.state.get().selectedClusters.length + " clusters selected.";
    });
  }

  /* The table's "Clear" button: empties the search box and the column filters. */
  function clearTable() {
    var button = document.getElementById("table_clear");
    MP.app.showTab("main");
    if (button.disabled) return Promise.resolve("The table has no search or filter to clear.");
    button.scrollIntoView({ block: "center", inline: "nearest" });
    return clickButton(button).then(function () {
      return "Table search and filters cleared.";
    });
  }

  /* The report is the message itself, so it shows up as a line of the dialogue. */
  function printMessage(param) {
    return Promise.resolve(String(param));
  }

  var commands = {
    "brush node": { usage: "brush node:Group_2, Group_3", run: brushNode },
    "select node": { usage: "select node:Group_2, Group_5", run: selectNode },
    "search table": { usage: "search table:K00004, K00008", run: searchTable },
    "set filter1": { usage: "set filter1:<annotation>", run: setFilter1 },
    "set filter2": { usage: "set filter2:<scope>, <scope>", run: setFilter2 },
    "set importance": { usage: "set importance:1.5", run: setImportance },
    "set layout": { usage: "set layout:circle", run: setLayout },
    "sort table": { usage: "sort table:GO_ID desc", run: sortTable },
    "select all": { usage: "select all", run: selectAll, noParam: true },
    "clear table": { usage: "clear table", run: clearTable, noParam: true },
    "print message": { usage: "print message:<text>", run: printMessage }
  };

  function usage() {
    return Object.keys(commands).map(function (k) { return commands[k].usage; }).join("\n");
  }

  function parse(text) {
    var str = String(text === null || text === undefined ? "" : text);
    var i = str.indexOf(":");
    var fn = (i < 0 ? str : str.slice(0, i)).trim().toLowerCase().replace(/\s+/g, " ");
    var param = i < 0 ? "" : str.slice(i + 1).trim();
    if (!commands[fn] || (i < 0 && !commands[fn].noParam)) {
      throw new Error('Type a command as "function:param". Known commands:\n' + usage());
    }
    if (!param && !commands[fn].noParam) throw new Error("Missing value. Example: " + commands[fn].usage);
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

  /* Play the step list written by the Python agent: an array of steps, or an
     object with a `steps` array (JSON text is parsed). Dashboard steps run as
     commands, message steps are printed, data steps are not played: they hold
     the evidence (findings and numbers) that a message lists by id. `say(text,
     kind, evidence)` receives each line; a failed step is reported and the rest
     go on. */
  function play(input, say) {
    var steps = typeof input === "string" ? JSON.parse(input) : input;
    if (steps && !Array.isArray(steps)) steps = steps.steps;
    if (!Array.isArray(steps)) throw new Error("Expected a list of steps, or an object with \"steps\".");
    say = say || function () {};
    var done = 0;
    var chain = Promise.resolve();
    var byId = {};
    steps.forEach(function (step) {
      if (step && step.kind === "data" && step.id) byId[step.id] = step;
    });
    steps.forEach(function (step) {
      if (!step || step.kind === "data") return;
      chain = chain.then(function () {
        if (step.kind === "message") {
          var evidence = (step.evidence || []).map(function (id) { return byId[id]; })
            .filter(function (d) { return d; });
          say(String(step.text), "bot", evidence);
          done += 1;
          return MP.cursor.wait(900);
        }
        say(String(step.command), "user");
        return run(step.command).then(function (report) {
          say(report, "bot");
          done += 1;
        }, function (err) {
          say(err && err.message ? err.message : String(err), "error");
        }).then(function () { return MP.cursor.wait(350); });
      });
    });
    return chain.then(function () { return "Played " + done + " steps."; });
  }

  MP.agent = { commands: commands, parse: parse, run: run, play: play, usage: usage };
})(window.MolPad = window.MolPad || {});
