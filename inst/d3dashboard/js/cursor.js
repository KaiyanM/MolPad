/* MolPad D3 dashboard: virtual mouse. It only draws a pointer; the commands in
   agent.js apply the effect through the dashboard's own handlers. */
(function (MP) {
  "use strict";

  var el = null;
  var pos = { x: 0, y: 0 };

  function place(x, y) {
    pos.x = x;
    pos.y = y;
    el.style.left = (x - 3) + "px";   // the arrow tip sits at (3, 2) in the icon
    el.style.top = (y - 2) + "px";
  }

  function init() {
    if (el) return;
    el = document.createElement("div");
    el.className = "mp-cursor";
    el.innerHTML = '<svg viewBox="0 0 22 22" width="22" height="22">' +
      '<path d="M3 2 L3 18 L7.5 14 L10.5 20.5 L13 19.3 L10 13 L16 13 Z"/></svg>';
    document.body.appendChild(el);
    place(window.innerWidth - 60, window.innerHeight - 60);
  }

  function ease(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }

  /* Next animation frame, or 50 ms later when the browser is not painting
     (background tab), so a command never hangs half way. */
  function nextFrame(fn) {
    var done = false;
    function once() {
      if (done) return;
      done = true;
      fn();
    }
    window.requestAnimationFrame(once);
    setTimeout(once, 50);
  }

  /* Glide to `target`, a {x, y} point in viewport pixels or a function that
     returns one (re-read every frame, for nodes that are still moving).
     `onStep` receives the pointer position after each frame. */
  function moveTo(target, ms, onStep) {
    var from = { x: pos.x, y: pos.y };
    var t0 = null;
    ms = ms === undefined ? 500 : ms;
    return new Promise(function (resolve) {
      function frame() {
        var now = Date.now();
        if (t0 === null) t0 = now;
        var t = ms > 0 ? Math.min(1, (now - t0) / ms) : 1;
        var to = typeof target === "function" ? target() : target;
        var k = ease(t);
        place(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k);
        if (onStep) onStep(pos);
        if (t < 1) nextFrame(frame); else resolve(pos);
      }
      nextFrame(frame);
    });
  }

  function toElement(node, ms) {
    node.scrollIntoView({ block: "nearest", inline: "nearest" });
    return moveTo(function () {
      var r = node.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    }, ms);
  }

  function press() { el.classList.add("down"); }
  function release() { el.classList.remove("down"); }

  function wait(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  MP.cursor = {
    init: init, moveTo: moveTo, toElement: toElement,
    press: press, release: release, wait: wait
  };
})(window.MolPad = window.MolPad || {});
