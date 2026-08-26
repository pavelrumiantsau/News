/* World Desk — renders docs/news.json. No dependencies, no network calls. */
(function () {
  "use strict";

  var TOP_N = 3;
  var REGION_ORDER = ["Europe", "Middle East", "Asia", "Africa", "Americas", "Oceania"];
  var state = { data: null, region: "All", q: "", onlyNews: false, open: {} };

  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  function hoursAgo(iso) {
    if (!iso) return Infinity;
    var h = (Date.now() - new Date(iso).getTime()) / 36e5;
    return isNaN(h) ? Infinity : h;
  }

  function isFresh(i) { return hoursAgo(i.pub) <= 24; }

  function ago(iso) {
    var h = hoursAgo(iso);
    if (h === Infinity) return "";
    if (h < 1) return "just now";
    if (h < 24) return Math.round(h) + "h ago";
    var d = Math.round(h / 24);
    if (d < 30) return d + "d ago";
    return Math.round(d / 30) + "mo ago";
  }

  function restore() {
    try {
      var s = JSON.parse(localStorage.getItem("worlddesk") || "{}");
      if (s.region) state.region = s.region;
      if (s.onlyNews) state.onlyNews = !!s.onlyNews;
      if (s.open) state.open = s.open;
    } catch (e) { /* private mode / blocked storage — defaults are fine */ }
  }
  function save() {
    try {
      localStorage.setItem("worlddesk", JSON.stringify({
        region: state.region, onlyNews: state.onlyNews, open: state.open
      }));
    } catch (e) { /* ignore */ }
  }

  function matches(c) {
    if (state.region !== "All" && c.region !== state.region) return false;
    if (state.onlyNews && !c.items.some(isFresh)) return false;
    var q = state.q.trim().toLowerCase();
    if (!q) return true;
    if (c.name.toLowerCase().indexOf(q) > -1) return true;
    if ((c.capital || "").toLowerCase().indexOf(q) > -1) return true;
    return c.items.some(function (i) {
      return i.title.toLowerCase().indexOf(q) > -1 ||
             (i.source || "").toLowerCase().indexOf(q) > -1;
    });
  }

  function storyHTML(i) {
    var tier = i.tier === 1 ? '<span class="tag t1">wire / public</span>'
                            : '<span class="tag t2">national</span>';
    var lang = (i.lang && i.lang !== "en")
      ? '<span class="tag lang">' + esc(i.lang.toUpperCase()) + "</span>" : "";
    return '<li><a href="' + esc(i.link) + '" target="_blank" rel="noopener noreferrer">' +
      esc(i.title) + "</a>" +
      '<div class="byline"><strong>' + esc(i.source || "") + "</strong>" +
      (i.pub ? "<span>" + ago(i.pub) + "</span>" : "") + tier + lang + "</div></li>";
  }

  function countryHTML(c) {
    var open = !!state.open[c.iso];
    var items = state.onlyNews ? c.items.filter(isFresh) : c.items;
    var n = items.length;
    var lead = n ? items[0].title : "no qualifying coverage found";
    var meta = [];
    if (c.stale) meta.push('<span class="tag stale">carried forward</span>');
    meta.push(n ? n + (n === 1 ? " story" : " stories") : "quiet");

    return '<article class="country' + (open ? " open" : "") + '" data-iso="' + c.iso + '">' +
      '<div class="chead" role="button" tabindex="0" aria-expanded="' + open + '">' +
        '<span class="arrow">▶</span>' +
        '<span class="cname">' + esc(c.name) + "</span>" +
        '<span class="clead">' + esc(lead) + "</span>" +
        '<span class="cmeta">' + meta.join(" ") + "</span>" +
      "</div>" +
      (n ? '<ul class="stories">' + items.map(storyHTML).join("") + "</ul>"
         : '<ul class="stories"><li class="none">No story from a trusted, free-to-read ' +
           "source mentioned this country in the period searched.</li></ul>") +
      "</article>";
  }

  function render() {
    var d = state.data;
    var list = d.countries.filter(matches);
    var host = $("#countries");

    var groups = {};
    list.forEach(function (c) { (groups[c.region] = groups[c.region] || []).push(c); });

    var html = "";
    REGION_ORDER.forEach(function (r) {
      if (!groups[r]) return;
      html += '<h2 class="regionhead">' + esc(r) + " · " + groups[r].length + "</h2>";
      html += groups[r].map(countryHTML).join("");
    });
    host.innerHTML = html;
    $("#empty").hidden = list.length > 0;
    $("#worldWrap").hidden = !!state.q || state.region !== "All";
  }

  function boot(d) {
    state.data = d;
    var s = d.stats;
    $("#sub").textContent = d.generated_human + " · " + s.countries + " countries · " +
      s.stories + " stories";
    $("#statline").textContent =
      s.covered + " countries with fresh coverage · " + s.stale +
      " carried forward · " + s.empty + " with nothing found · rebuilt " + d.generated_human + ".";

    $("#world").innerHTML = (d.world || []).map(function (i) {
      return '<li><span class="cty">' + esc(i.country) + "</span>" +
        '<a href="' + esc(i.link) + '" target="_blank" rel="noopener noreferrer">' +
        esc(i.title) + "</a></li>";
    }).join("");

    var regions = ["All"].concat(REGION_ORDER);
    $("#regions").innerHTML = regions.map(function (r) {
      return '<button class="chip" type="button" data-r="' + esc(r) + '" aria-pressed="' +
        (state.region === r) + '">' + esc(r) + "</button>";
    }).join("");
    $("#onlyNews").checked = state.onlyNews;

    $("#regions").addEventListener("click", function (e) {
      var b = e.target.closest(".chip");
      if (!b) return;
      state.region = b.dataset.r;
      [].forEach.call(this.children, function (x) {
        x.setAttribute("aria-pressed", x.dataset.r === state.region);
      });
      save(); render();
    });

    var timer;
    $("#q").addEventListener("input", function (e) {
      clearTimeout(timer);
      var v = e.target.value;
      timer = setTimeout(function () { state.q = v; render(); }, 110);
    });

    $("#onlyNews").addEventListener("change", function (e) {
      state.onlyNews = e.target.checked; save(); render();
    });

    $("#expandAll").addEventListener("click", function () {
      var anyClosed = state.data.countries.some(function (c) { return !state.open[c.iso]; });
      state.data.countries.forEach(function (c) { state.open[c.iso] = anyClosed; });
      this.textContent = anyClosed ? "Collapse all" : "Expand all";
      save(); render();
    });

    function toggle(el) {
      var art = el.closest(".country");
      if (!art) return;
      var iso = art.dataset.iso;
      state.open[iso] = !state.open[iso];
      art.classList.toggle("open", state.open[iso]);
      el.setAttribute("aria-expanded", String(!!state.open[iso]));
      save();
    }
    $("#countries").addEventListener("click", function (e) {
      var h = e.target.closest(".chead");
      if (h) toggle(h);
    });
    $("#countries").addEventListener("keydown", function (e) {
      if (e.key !== "Enter" && e.key !== " ") return;
      var h = e.target.closest(".chead");
      if (h) { e.preventDefault(); toggle(h); }
    });

    render();
  }

  restore();
  fetch("news.json?v=" + Date.now())
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(boot)
    .catch(function (err) {
      $("#sub").textContent = "Could not load news.json — " + err.message;
    });
})();
