/* MolPad D3 dashboard: text commands that drive the virtual mouse.
   A command is "function:param", for example "brush node:Group_2".
   "brush node", "select node", "search table", "set filter1" and "set filter2" take one
   value or several, comma-separated ("all" for every value of a filter). "select all" and "clear table"
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

  /* Level filters: the checkbox drop-downs of the filter bar. "set filter1:A, B"
     opens the level-1 list, clears it when it holds anything else, ticks A and B
     and closes it; "all" ticks All. A value that cannot be combined with the other
     filter (greyed out, 0 features) is refused with the reason. */
  function setLevel(level, param) {
    var D = MP.D;
    var values = level === 1 ? D.pathways : D.taxa;
    var noun = level === 1 ? D.labels.noun1 : D.labels.noun2;
    var widget = MP.filters["level" + level];
    var parts = listOf(param);
    var clearAll = parts.length === 1 && parts[0].toLowerCase() === "all";
    var want = [];
    if (!clearAll) {
      parts.forEach(function (part) {
        var value = match(values, part);
        if (value === null) {
          throw new Error("No " + noun + ' named "' + part + '". Choose from: ' + values.join(", ") + ', or "all".');
        }
        if (want.indexOf(value) < 0) want.push(value);
      });
      var counts = MP.state.optionCounts(level);
      var dead = want.filter(function (v) { return !counts.get(v); });
      if (dead.length) {
        var other = MP.state.summary(level === 1 ? 2 : 1);
        throw new Error(dead.join(", ") + " has no features under the other filter (" + other +
          "). Set that filter first, or to all.");
      }
    }
    var have = MP.state.get()["level" + level];
    MP.app.showTab("main");

    function click(node) {
      return MP.cursor.toElement(node, 350).then(function () {
        MP.cursor.press();
        node.click();
        return MP.cursor.wait(160);
      }).then(function () { MP.cursor.release(); });
    }

    var chain = click(widget.button).then(function () { if (!widget.isOpen()) widget.open(); });
    var same = MP.utils.setsEqual(have, want);
    if (!same && (clearAll || have.length)) {
      chain = chain.then(function () { return click(widget.option("")); });   // All: clears the list
    }
    if (!same) {
      want.forEach(function (v) {
        chain = chain.then(function () { return click(widget.option(v)); });
      });
    }
    return chain.then(function () {
      return click(widget.button);
    }).then(function () {
      widget.close();
      return "Filter " + level + " set to " + MP.state.summary(level) + ".";
    });
  }

  function setFilter1(param) { return setLevel(1, param); }
  function setFilter2(param) { return setLevel(2, param); }

  /* What the views of the selected clusters show: "filtered" or "all" features. */
  function setView(param) {
    var key = String(param).trim().toLowerCase();
    var scope = /^(all|whole|cluster|everything|all features)$/.test(key) ? "all"
      : /^(filtered|filter|filtered features)$/.test(key) ? "filtered" : null;
    if (!scope) throw new Error('Choose "filtered" or "all".');
    var button = document.querySelector('#s_scope [data-scope="' + scope + '"]');
    MP.app.showTab("main");
    return clickButton(button).then(function () {
      return "The selected clusters show " + (scope === "all" ? "all their features" : "the filtered features") + ".";
    });
  }

  /* Ribbon line colour: level1, level2, type (when offered) or none. */
  function setColour(param) {
    var select = document.getElementById("s_colour");
    var offered = Array.prototype.map.call(select.options, function (o) { return o.value; });
    var key = String(param).trim().toLowerCase();
    var alias = { "level 1": "level1", annotation: "level1", pathway: "level1",
                  "level 2": "level2", scope: "level2", "taxonomic scope": "level2", taxa: "level2",
                  off: "none", nothing: "none" };
    alias[MP.D.labels.noun1.toLowerCase()] = "level1";   // the names of the levels in this dataset
    alias[MP.D.labels.noun2.toLowerCase()] = "level2";
    var value = match(offered, alias[key] || key);
    if (value === null) throw new Error('No colour grouping "' + param + '". Choose one of: ' + offered.join(", "));
    MP.app.showTab("main");
    return pick(select, value).then(function () {
      return "Pattern lines coloured by " + select.options[select.selectedIndex].textContent + ".";
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
    "set filter1": { usage: "set filter1:<annotation>, <annotation> | all", run: setFilter1 },
    "set filter2": { usage: "set filter2:<scope>, <scope> | all", run: setFilter2 },
    "set view": { usage: "set view:filtered | all", run: setView },
    "set colour": { usage: "set colour:level1 | level2 | none", run: setColour },
    "set color": { usage: "set color:level1 | level2 | none", run: setColour },
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

  /* Playback pace, so the reader can follow the pointer and read each message.
     ?pace=0.5 in the page address plays twice as fast, ?pace=0 without pauses. */
  var PAUSE_BEFORE_CMD = 800;     // ms before the pointer moves to the next control
  var PAUSE_AFTER_CMD = 1200;     // ms to look at the dashboard after a command
  var WAIT_SIGN_MIN = 400;        // ms: shorter pauses do not show the waiting balls
  var READ_BASE = 1200, READ_PER_WORD = 250, READ_MIN = 2500, READ_MAX = 9000;

  function pace() {
    var m = /[?&]pace=([0-9.]+)/.exec(window.location.search || "");
    var k = m ? parseFloat(m[1]) : 1;
    return isFinite(k) && k >= 0 ? k : 1;
  }

  function pause(ms) {
    var t = Math.round(ms * pace());
    if (t <= 0) return Promise.resolve();
    if (t < WAIT_SIGN_MIN) return MP.cursor.wait(t);
    MP.cursor.waiting(true);   // the balls next to the pointer: paused on purpose, still running
    return MP.cursor.wait(t).then(function () { MP.cursor.waiting(false); });
  }

  /* Time to read a message: grows with its length, within READ_MIN..READ_MAX. */
  function readingTime(text) {
    var words = String(text).split(/\s+/).filter(function (w) { return w; }).length;
    return Math.min(READ_MAX, Math.max(READ_MIN, READ_BASE + READ_PER_WORD * words));
  }

  /* A player for the steps written by the Python agent. Steps can be handed over while it
     plays, and the text of a message can come after the message itself:

       var p = player(say, { writing: fn });
       p.push(steps);          // any number of times; plays in the order given
       p.text(slot, text);     // the text of the message step {kind: "message", slot: n}
       p.end();                // nothing more will come
       p.finished              // a promise: "Played n steps."

     Dashboard steps run as commands, message steps are printed, reasoning steps are printed
     before the actions they explain, data steps are not played: they hold the evidence
     (findings and numbers) that a message lists by id. `say(text, kind, evidence)` receives
     each line; a failed step is reported and the rest go on. A unit step opens one unit of
     the answer (a sub-question with its reason and an overview of its actions): `unit(step)`
     is called with it, and `unit(null)` when the lines that follow belong to no unit (the
     conclusion, kind "answer", and the end). `say` and `unit` may return the page elements
     they made; `record(entry)` is then called once per played step with
     {kind, nodes, command | text}, so the round can be replayed later (see replay). When the
     next step is a message
     whose text has not come yet, the player waits for that text only; `writing(true)` and
     `writing(false)` are called around the wait, so the page can say so. */
  function player(say, options) {
    say = say || function () {};
    var writing = (options && options.writing) || function () {};
    var unit = (options && options.unit) || function () {};
    var record = (options && options.record) || function () {};
    var queue = [], byId = {}, texts = {};
    var ended = false, running = false, done = 0, wake = null, finish;
    var last = null;   // kind of the step played before this one
    var finished = new Promise(function (resolve) { finish = resolve; });

    /* Pauses are for the time between two things to follow. None before the first command of
       a unit (the reader has just been told what will happen), none after a command unless
       another command follows (its message can come at once), none after the last line. */
    function isCommand(step) { return !!step && (step.kind === "dashboard" || (!!step.command && !step.kind)); }
    function nothingLeft() { return !queue.length && ended; }

    function textOf(step) {
      if (step.text !== null && step.text !== undefined) return Promise.resolve(String(step.text));
      return new Promise(function (resolve) {
        var waited = false;
        (function check() {
          var ready = Object.prototype.hasOwnProperty.call(texts, step.slot);
          if (!ready && !ended) {
            if (!waited) { waited = true; writing(true); MP.cursor.waiting(true); }
            wake = check;
            return;
          }
          if (waited) { writing(false); MP.cursor.waiting(false); }
          resolve(ready ? String(texts[step.slot]) : "");
        })();
      });
    }

    function one(step) {
      if (step.kind === "message") {
        return textOf(step).then(function (text) {
          if (!text.trim()) return null;   // never print an empty message
          var evidence = (step.evidence || []).map(function (id) { return byId[id]; })
            .filter(function (d) { return d; });
          var concluding = step.role === "conclusion";
          if (concluding) unit(null);
          record({ kind: "message", text: text, nodes: [say(text, concluding ? "answer" : "bot", evidence)] });
          done += 1;
          last = "message";
          return nothingLeft() ? null : pause(readingTime(text));
        });
      }
      if (step.kind === "reasoning") {
        record({ kind: "message", text: String(step.text), nodes: [say(String(step.text), "reason")] });
        last = "message";
        return nothingLeft() ? Promise.resolve() : pause(readingTime(step.text));
      }
      if (step.kind === "unit") {
        var heading = [step.of > 1 ? step.question : "", step.reason || "",
          (step.assumed || []).join(" "), step.overview || ""].join(" ");
        var shown = unit(step) || [];
        if (shown.length) record({ kind: "unit", text: heading, nodes: shown });
        last = "unit";
        return Promise.resolve();   // the first action starts at once
      }
      if (step.kind !== "dashboard" && !step.command) return Promise.resolve();   // a kind this page does not know
      var entry = { kind: "dashboard", command: String(step.command), nodes: [] };
      var first = last === null || last === "unit";
      last = "dashboard";
      return pause(first ? 0 : PAUSE_BEFORE_CMD).then(function () {
        entry.nodes.push(say(entry.command, "user"));
        return run(step.command);
      }).then(function (report) {
        entry.nodes.push(say(report, "bot"));
        done += 1;
      }, function (err) {
        entry.nodes.push(say(err && err.message ? err.message : String(err), "error"));
      }).then(function () {
        record(entry);   // a failed command is kept too: the replay runs the same list
        return isCommand(queue[0]) ? pause(PAUSE_AFTER_CMD) : null;
      });
    }

    function next() {
      if (!queue.length) {
        running = false;
        if (ended) { unit(null); finish("Played " + done + " steps."); }
        return;
      }
      one(queue.shift()).then(next, next);
    }

    function start() {
      if (running) return;
      running = true;
      next();
    }

    function nudge() {
      var w = wake;
      wake = null;
      if (w) w();
    }

    return {
      push: function (steps) {
        (steps || []).forEach(function (step) {
          if (!step) return;
          if (step.kind === "data") { if (step.id) byId[step.id] = step; return; }
          queue.push(step);
        });
        start();
      },
      text: function (slot, text) { texts[slot] = text; nudge(); },
      end: function () { ended = true; nudge(); start(); },
      finished: finished
    };
  }

  /* Play a finished step list: an array of steps, or an object with a `steps` array (JSON
     text is parsed). */
  function play(input, say, options) {
    var steps = typeof input === "string" ? JSON.parse(input) : input;
    if (steps && !Array.isArray(steps)) steps = steps.steps;
    if (!Array.isArray(steps)) throw new Error("Expected a list of steps, or an object with \"steps\".");
    var p = player(say, options);
    p.push(steps);
    p.end();
    return p.finished;
  }

  /* The dashboard as it is now: the shared state plus the table's own settings. */
  function snapshot() {
    var S = MP.state.get();
    return {
      state: { level1: S.level1.slice(), level2: S.level2.slice(), scope: S.scope, colourBy: S.colourBy,
               ribbonExpand: S.ribbonExpand, layout: S.layout, minWeight: S.minWeight,
               selectedClusters: S.selectedClusters.slice() },
      table: MP.table && MP.table.getState ? MP.table.getState() : null
    };
  }

  /* Put the dashboard back to a snapshot, at once and without the pointer. The layout list and
     the importance slider do not follow a state change by themselves, so they are set here. */
  function restore(snap) {
    MP.app.showTab("main");
    MP.network.clearBrush();
    MP.state.set(snap.state, "agent");
    var layout = document.getElementById("s_layout");
    if (layout) layout.value = snap.state.layout;
    var slider = document.getElementById("obs"), label = document.getElementById("obs_value");
    if (slider) slider.value = snap.state.minWeight;
    if (label) label.textContent = MP.utils.fmt(snap.state.minWeight, 1);
    if (snap.table && MP.table && MP.table.setState) MP.table.setState(snap.table);
  }

  /* Run the recorded entries of a round again, in order, without printing anything:

       var r = replay(entries, { on: fn, off: fn, error: fn });
       r.stop();        // stops after the step that is running
       r.finished       // a promise: "done" or "stopped"

     `on(nodes, entry)` and `off(nodes, entry)` are called around each step, so the page can
     mark the lines it belongs to; `error(err, entry)` when a command fails (the rest go on).
     The caller restores the dashboard to the start of the round first (see restore). */
  function replay(entries, hooks) {
    hooks = hooks || {};
    var stopped = false, i = 0;
    var finished = new Promise(function (resolve) {
      (function step() {
        if (stopped || i >= entries.length) { resolve(stopped ? "stopped" : "done"); return; }
        var before = entries[i - 1], e = entries[i++], after_ = entries[i];
        var nodes = (e.nodes || []).filter(function (n) { return n; });
        if (hooks.on) hooks.on(nodes, e);
        // the same pauses as the first play (see player)
        var first = !before || before.kind === "unit";
        var job = e.kind === "dashboard"
          ? pause(first ? 0 : PAUSE_BEFORE_CMD).then(function () { return run(e.command); })
              .then(null, function (err) { if (hooks.error) hooks.error(err, e); })
              .then(function () { return after_ && after_.kind === "dashboard" ? pause(PAUSE_AFTER_CMD) : null; })
          : (e.kind === "unit" || !after_) ? Promise.resolve() : pause(readingTime(e.text || ""));
        function after() { if (hooks.off) hooks.off(nodes, e); step(); }
        job.then(after, after);
      })();
    });
    return { finished: finished, stop: function () { stopped = true; } };
  }

  MP.agent = { commands: commands, parse: parse, run: run, play: play, player: player, usage: usage,
               snapshot: snapshot, restore: restore, replay: replay };
})(window.MolPad = window.MolPad || {});
