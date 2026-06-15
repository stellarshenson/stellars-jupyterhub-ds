/* Stellars portal mock - shell renderer + theme + command palette
 * No build step, no framework. Each page sets <body data-page="..."> and
 * supplies <main> content; this script injects the shared chrome so the
 * shell stays DRY across the static tree.
 */
(function () {
  "use strict";

  // ---------- icons (Remix-style line paths, 24x24) ----------
  var I = {
    grid:    'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
    server:  'M4 5h16v6H4zM4 13h16v6H4z M8 8h.01M8 16h.01',
    users:   'M16 19v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 19v-2a4 4 0 0 0-3-3.87M16 3.13A4 4 0 0 1 16 11',
    group:   'M17 20v-2a4 4 0 0 0-3-3.87M5 20v-2a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v2M10 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6M17 11a3 3 0 1 0-2-5.2',
    shield:  'M12 2l8 3v6c0 5-3.5 8-8 11-4.5-3-8-6-8-11V5z M9 12l2 2 4-4',
    activity:'M22 12h-4l-3 9L9 3l-3 9H2',
    settings:'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-2.7-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 4.6 15H4.5a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.1-2.7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 11 4.6V4.5a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8 1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z',
    search:  'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16M21 21l-4.3-4.3',
    sun:     'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
    moon:    'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
    plus:    'M12 5v14M5 12h14',
    bell:    'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
    play:    'M5 3l14 9-14 9z',
    restart: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5',
    stop:    'M6 6h12v12H6z',
    dots:    'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2M19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2M5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2',
    key:     'M21 2l-2 2m-3.5 3.5a5 5 0 1 0-2 2l1.5-1.5 2 2 2-2-2-2 2.5-2.5',
    user:    'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8',
    cpu:     'M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3M5 5h14v14H5zM9 9h6v6H9z',
    check:   'M20 6L9 17l-5-5',
    arrowup: 'M12 19V5M5 12l7-7 7 7'
  };
  function svg(name) {
    return '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="' + (I[name] || '') + '"/></svg>';
  }
  // expand {ic:name} tokens placed in page markup, using the shared icon set
  function expandIcons(html) {
    return html.replace(/\{ic:(\w+)\}/g, function (m, n) { return svg(n); });
  }

  // ---------- navigation model ----------
  var NAV = [
    { group: "Overview", items: [
      { id: "home",     label: "Home",     icon: "grid",     href: "home.html" },
      { id: "servers",  label: "Servers",  icon: "server",   href: "servers.html", badge: "3" },
      { id: "activity", label: "Activity", icon: "activity", href: "activity.html" }
    ]},
    { group: "Access", items: [
      { id: "users",    label: "Users",    icon: "users",    href: "users.html", badge: "2" },
      { id: "groups",   label: "Groups",   icon: "group",    href: "groups.html" },
      { id: "policies", label: "Policies", icon: "shield",   href: "policies.html" }
    ]},
    { group: "System", items: [
      { id: "settings", label: "Settings", icon: "settings", href: "settings.html" }
    ]}
  ];

  // command palette actions
  var ACTIONS = [
    { group: "Create", icon: "plus", label: "Add user",        hint: "U", run: function(){ toast("Add-user drawer (mock)"); } },
    { group: "Create", icon: "plus", label: "Create group",    hint: "G", run: function(){ toast("Create-group drawer (mock)"); } },
    { group: "Create", icon: "plus", label: "New policy",      hint: "P", run: function(){ toast("New-policy editor (mock)"); } },
    { group: "Actions", icon: "bell", label: "Broadcast notification", run: function(){ toast("Broadcast composer (mock)"); } },
    { group: "Actions", icon: "stop", label: "Stop server: jupyterlab-alice", run: function(){ toast("Stopping jupyterlab-alice (mock)"); } }
  ];

  function navItems() {
    return NAV.reduce(function (a, g) { return a.concat(g.items); }, []);
  }

  // ---------- theme ----------
  var THEMES = { dark: "optimum-hub-dark", light: "optimum-hub-light" };
  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || THEMES.dark;
  }
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("optimum-hub-theme", t); } catch (e) {}
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.innerHTML = (t === THEMES.light) ? svg("moon") : svg("sun");
  }
  function toggleTheme() {
    applyTheme(currentTheme() === THEMES.light ? THEMES.dark : THEMES.light);
  }

  // ---------- shell render ----------
  function renderShell() {
    var page = document.body.getAttribute("data-page") || "home";
    var main = document.querySelector("main");
    var mainHTML = expandIcons(main ? main.innerHTML : "");
    var active = navItems().filter(function (n) { return n.id === page; })[0] || navItems()[0];

    var navHTML = NAV.map(function (g) {
      return '<div class="nav-group-label">' + g.group + '</div>' +
        g.items.map(function (n) {
          return '<a class="nav-item' + (n.id === page ? ' active' : '') + '" href="' + n.href + '">' +
            svg(n.icon) + '<span>' + n.label + '</span>' +
            (n.badge ? '<span class="badge-count">' + n.badge + '</span>' : '') +
          '</a>';
        }).join("");
    }).join("");

    document.body.innerHTML =
      '<div class="app">' +
        '<aside class="sidebar">' +
          '<a class="brand" href="home.html" title="Optimum Hub">' +
            '<img class="brand-logo" src="assets/brand/jh-logo.svg" alt="Stellars Tech AI Lab"></a>' +
          '<nav class="nav">' + navHTML + '</nav>' +
          '<div class="sidebar-foot"><div class="avatar">AD</div>' +
            '<div class="who">admin<small>Administrator</small></div>' +
            '<button class="icon-btn" style="margin-left:auto" title="Sign out">' + svg("settings") + '</button>' +
          '</div>' +
        '</aside>' +
        '<div class="main">' +
          '<header class="topbar">' +
            '<div class="crumbs"><span>Optimum Hub</span><span class="sep">/</span><b>' + active.label + '</b></div>' +
            '<div class="kbar" id="kbar-open"><span>' + svg("search") + '</span><span>Search or jump to…</span><span class="kbd">⌘K</span></div>' +
            '<button class="icon-btn" id="theme-toggle" title="Toggle theme"></button>' +
            '<button class="icon-btn" title="Notifications">' + svg("bell") + '</button>' +
          '</header>' +
          '<div class="content">' + mainHTML + '</div>' +
        '</div>' +
      '</div>' +
      paletteHTML() +
      '<div class="drawer" id="drawer"></div>' +
      '<div class="toasts" id="toasts"></div>';

    applyTheme(currentTheme());
    wire();
  }

  function paletteHTML() {
    return '<div class="scrim" id="scrim"></div>' +
      '<div class="palette" id="palette">' +
        '<div class="palette-input">' + svg("search") +
          '<input id="palette-q" placeholder="Search pages, users, actions…" autocomplete="off">' +
        '</div>' +
        '<div class="palette-list" id="palette-list"></div>' +
      '</div>';
  }

  // ---------- command palette behaviour ----------
  var pSel = 0, pRows = [];
  function buildPalette(q) {
    q = (q || "").toLowerCase();
    var nav = navItems().map(function (n) {
      return { group: "Go to", icon: n.icon, label: n.label, hint: "", run: function(){ location.href = n.href; } };
    });
    var all = nav.concat(ACTIONS).filter(function (r) { return r.label.toLowerCase().indexOf(q) > -1; });
    pRows = all;
    if (pSel >= all.length) pSel = 0;
    var byGroup = {};
    all.forEach(function (r, i) { (byGroup[r.group] = byGroup[r.group] || []).push({ r: r, i: i }); });
    var html = Object.keys(byGroup).map(function (g) {
      return '<div class="palette-group">' + g + '</div>' + byGroup[g].map(function (o) {
        return '<div class="palette-item' + (o.i === pSel ? ' sel' : '') + '" data-i="' + o.i + '">' +
          svg(o.r.icon) + '<span>' + o.r.label + '</span>' +
          (o.r.hint ? '<span class="kbd hint">' + o.r.hint + '</span>' : '') + '</div>';
      }).join("");
    }).join("");
    document.getElementById("palette-list").innerHTML = html || '<div class="empty" style="padding:24px"><p>No matches</p></div>';
    Array.prototype.forEach.call(document.querySelectorAll(".palette-item"), function (el) {
      el.addEventListener("click", function () { runPalette(+el.getAttribute("data-i")); });
    });
  }
  function openPalette() {
    document.getElementById("scrim").classList.add("open");
    document.getElementById("palette").classList.add("open");
    var q = document.getElementById("palette-q"); q.value = ""; pSel = 0; buildPalette("");
    setTimeout(function () { q.focus(); }, 10);
  }
  function closePalette() {
    document.getElementById("scrim").classList.remove("open");
    document.getElementById("palette").classList.remove("open");
  }
  function runPalette(i) { var r = pRows[i]; closePalette(); if (r) r.run(); }

  // ---------- toast ----------
  function toast(msg) {
    var t = document.createElement("div");
    t.className = "toast"; t.innerHTML = svg("check") + "<span>" + msg + "</span>";
    document.getElementById("toasts").appendChild(t);
    setTimeout(function () { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 2600);
    setTimeout(function () { t.remove(); }, 3000);
  }
  window.hubToast = toast;

  // ---------- wiring ----------
  function wire() {
    document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
    document.getElementById("kbar-open").addEventListener("click", openPalette);
    document.getElementById("scrim").addEventListener("click", closePalette);
    document.getElementById("palette-q").addEventListener("input", function (e) { buildPalette(e.target.value); });

    // demo: any [data-toast] element fires a toast (quick-action buttons, kebabs)
    Array.prototype.forEach.call(document.querySelectorAll("[data-toast]"), function (el) {
      el.addEventListener("click", function () { toast(el.getAttribute("data-toast")); });
    });
  }

  document.addEventListener("keydown", function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); return; }
    var open = document.getElementById("palette") && document.getElementById("palette").classList.contains("open");
    if (!open) return;
    if (e.key === "Escape") closePalette();
    else if (e.key === "ArrowDown") { e.preventDefault(); pSel = Math.min(pSel + 1, pRows.length - 1); buildPalette(document.getElementById("palette-q").value); }
    else if (e.key === "ArrowUp") { e.preventDefault(); pSel = Math.max(pSel - 1, 0); buildPalette(document.getElementById("palette-q").value); }
    else if (e.key === "Enter") { e.preventDefault(); runPalette(pSel); }
  });

  document.addEventListener("DOMContentLoaded", renderShell);
})();
