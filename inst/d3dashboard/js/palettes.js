/* MolPad D3 dashboard: colour palettes (mirrors R/color_palettes__.R). */
(function (MP) {
  "use strict";

  var graytone = ["#c3c5c7", "#30beba", "#998a73", "#807566", "#a5b1c9",
                  "#5d5232", "#9a2b41", "#d6b7a2", "#882db4", "#b47a53"];
  var darkwarm = ["#251305", "#C70A80", "#FBCB0A", "#ff1122", "#7D7463",
                  "#CECE5A", "#FF9B9B", "#A459D1", "#00235B", "#7E1717"];

  /* First n colours, extended with evenly spaced rainbow samples past the
     palette length (same intent as extend.color__ / match.color__). */
  function extend(n, colors) {
    var out = colors.slice(0, n);
    var extra = n - out.length;
    for (var i = 0; i < extra; i++) {
      out.push(d3.interpolateRainbow((i + 0.5) / extra));
    }
    return out;
  }

  function ordinal(domain, name) {
    var base = name === "darkwarm" ? darkwarm : graytone;
    return d3.scaleOrdinal().domain(domain).range(extend(domain.length, base));
  }

  MP.palettes = {
    graytone: graytone,
    darkwarm: darkwarm,
    nodeLow: "#BEBEBE",
    nodeHigh: "#00EEB1",
    edge: "#97a09e",
    brushFill: "#bd9fb7",
    brushStroke: "#85056d",
    accent: "#62AB89",
    extend: extend,
    ordinal: ordinal
  };
})(window.MolPad = window.MolPad || {});
