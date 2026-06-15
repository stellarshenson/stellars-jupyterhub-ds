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
    settings:'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M12 2v3M12 19v3M22 12h-3M5 12H2M19.07 4.93l-2.12 2.12M7.05 16.95l-2.12 2.12M19.07 19.07l-2.12-2.12M7.05 7.05 4.93 4.93',
    search:  'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16M21 21l-4.3-4.3',
    sun:     'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
    moon:    'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
    monitor: 'M3 4h18v12H3zM8 20h8M12 16v4',
    clock:   'M12 7v5l3 2M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
    plus:    'M12 5v14M5 12h14',
    bell:    'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
    play:    'M5 3l14 9-14 9z',
    restart: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5',
    stop:    'M6 6h12v12H6z',
    megaphone:'M3 11l18-5v12L3 14v-3z M11.6 16.8a3 3 0 1 1-5.8-1.6',
    logout:  'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
    dots:    'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2M19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2M5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2',
    key:     'M7 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M11 12h10M17 12v3M21 12v4',
    user:    'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8',
    cpu:     'M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3M5 5h14v14H5zM9 9h6v6H9z',
    check:   'M20 6L9 17l-5-5',
    arrowup: 'M12 19V5M5 12l7-7 7 7',
    arrowdown:'M12 5v14M5 12l7 7 7-7',
    chevron: 'M9 18l6-6-6-6',
    close:   'M18 6 6 18M6 6l12 12',
    grip:    'M9 5h.01M9 12h.01M9 19h.01M15 5h.01M15 12h.01M15 19h.01',
    disk:    'M22 12H2M5.45 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.9A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.1z M6 16h.01M10 16h.01',
    gpu:     'M3 6h18v12H3zM8 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M14 10h4M14 14h4',
    memory:  'M3 8h18v8H3zM7 11v2M11 11v2M15 11v2M6 16v2M10 16v2M14 16v2M18 16v2',
    download:'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
    box:     'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16zM3.27 6.96 12 12.01l8.73-5.05M12 22.08V12',
    code:    'm18 16 4-4-4-4M6 8l-4 4 4 4M14.5 4l-5 16'
  };
  function svg(name) {
    return '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="' + (I[name] || '') + '"/></svg>';
  }
  // expand {ic:name} tokens placed in page markup, using the shared icon set
  function expandIcons(html) {
    return html.replace(/\{ic:(\w+)\}/g, function (m, n) { return svg(n); });
  }

  // ---------- role ----------
  // The portal is role-aware: an admin watches the fleet and administers it;
  // a plain user only operates their own server. <body data-role="user">
  // collapses the chrome to the personal launchpad.
  function role() { return document.body.getAttribute("data-role") || "admin"; }
  function isAdmin() { return role() !== "user"; }

  // ---------- navigation model ----------
  // Overview is the dashboard; a single admin-only Administration section holds
  // everything you manage. One entity, one destination: Servers absorbs live
  // activity, Groups absorbs policy editing - no standalone Activity or Policies
  // page.
  var NAV_ADMIN = [
    { group: "", items: [
      { id: "home",    label: "Home",    icon: "grid", href: "home.html" },
      { id: "profile", label: "Profile", icon: "user", href: "profile.html" }
    ]},
    { group: "Administration", items: [
      { id: "servers",  label: "Servers",  icon: "server",   href: "servers.html" },
      { id: "users",    label: "Users",    icon: "users",    href: "users.html", badge: "2" },
      { id: "groups",   label: "Groups",   icon: "group",    href: "groups.html" },
      { id: "lab-container", label: "Lab Container", icon: "box", href: "lab-container.html" },
      { id: "events",   label: "Events",   icon: "activity", href: "events.html" },
      { id: "notifications", label: "Notifications", icon: "megaphone", href: "notifications.html" },
      { id: "advanced", label: "Advanced", icon: "dots", children: [
        { id: "settings", label: "Settings", icon: "settings", href: "settings.html" },
        { id: "tokens",   label: "Tokens",   icon: "key",      href: "tokens.html" }
      ]}
    ]}
  ];
  // a user has one server, so it lives on their Home - no fleet pages; they
  // still get a personal Profile to edit their own details
  var NAV_USER = [
    { group: "", items: [
      { id: "home",    label: "Home",    icon: "grid", href: "home-user.html" },
      { id: "profile", label: "Profile", icon: "user", href: "profile-user.html" }
    ]}
  ];
  function NAV() { return isAdmin() ? NAV_ADMIN : NAV_USER; }

  // command palette actions, scoped to the role
  var ACTIONS_ADMIN = [
    { group: "Create", icon: "plus", label: "Add user",        hint: "U", run: function(){ location.href = "new-user.html"; } },
    { group: "Create", icon: "plus", label: "Create group",    hint: "G", run: function(){ location.href = "new-group.html"; } },
    { group: "Actions", icon: "stop", label: "Stop server: jupyterlab-alice", run: function(){ toast("Stopping jupyterlab-alice (mock)"); } },
    { group: "Navigate", icon: "activity", label: "Events log", run: function(){ location.href = "events.html"; } }
  ];
  var ACTIONS_USER = [
    { group: "My server", icon: "play",    label: "Open my server",    run: function(){ toast("Opening your lab (mock)"); } },
    { group: "My server", icon: "restart", label: "Restart my server", run: function(){ toast("Restarting your lab (mock)"); } },
    { group: "My server", icon: "server",  label: "Manage volumes",    run: function(){ toast("Manage-volumes (stop server first) (mock)"); } }
  ];
  function ACTIONS() { return isAdmin() ? ACTIONS_ADMIN : ACTIONS_USER; }

  function navItems() {
    var out = [];
    NAV().forEach(function (g) {
      g.items.forEach(function (n) {
        if (n.children) n.children.forEach(function (c) { out.push(c); });
        else out.push(n);
      });
    });
    return out;
  }

  // ---------- theme ----------
  // theme has three modes - light / dark / system (follow the OS). The stored
  // value is the MODE; the resolved theme is applied to <html data-theme>.
  var THEMES = { dark: "optimum-hub-dark", light: "optimum-hub-light" };
  function systemTheme() { return (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) ? THEMES.dark : THEMES.light; }
  function currentMode() {
    var m; try { m = localStorage.getItem("optimum-hub-theme"); } catch (e) {}
    if (m === "light" || m === "dark" || m === "system") return m;
    if (m === THEMES.light) return "light";   // legacy stored value
    if (m === THEMES.dark) return "dark";
    return "system";
  }
  function resolveTheme(mode) { return mode === "system" ? systemTheme() : (mode === "light" ? THEMES.light : THEMES.dark); }
  function applyMode(mode) {
    document.documentElement.setAttribute("data-theme", resolveTheme(mode));
    try { localStorage.setItem("optimum-hub-theme", mode); } catch (e) {}
    forEach(document.querySelectorAll("#theme-changer [data-mode]"), function (b) { b.classList.toggle("on", b.getAttribute("data-mode") === mode); });
  }
  // in system mode, track live OS changes
  if (window.matchMedia) { try { matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () { if (currentMode() === "system") applyMode("system"); }); } catch (e) {} }

  // ---------- shell render ----------
  function renderShell() {
    var page = document.body.getAttribute("data-page") || "home";
    var main = document.querySelector("main");
    var mainHTML = expandIcons(main ? main.innerHTML : "");
    var match = navItems().filter(function (n) { return n.id === page; })[0];
    // Breadcrumb chain. A sub-page reached from a list (New user, Bulk add,
    // Configure user/group, Settings reference) sets data-crumb-parent="Label|href"
    // so the trail reads Optimum Hub / <parent, clickable> / <data-title>, and the
    // parent crumb lets you abandon the action and return to the list. Other pages
    // show the nav label (or data-title for off-nav pages like Events).
    var parentAttr = document.body.getAttribute("data-crumb-parent");
    var crumb = parentAttr ? (document.body.getAttribute("data-title") || "")
              : (match ? match.label : (document.body.getAttribute("data-title") || ""));
    var crumbsHTML = '<span>Optimum Hub</span><span class="sep">/</span>';
    if (parentAttr) {
      var pcut = parentAttr.indexOf("|");
      var plabel = pcut >= 0 ? parentAttr.slice(0, pcut) : parentAttr;
      var phref = pcut >= 0 ? parentAttr.slice(pcut + 1) : "#";
      crumbsHTML += '<a href="' + phref + '">' + plabel + '</a><span class="sep">/</span>';
    }
    crumbsHTML += '<b>' + crumb + '</b>';
    var home = isAdmin() ? "home.html" : "home-user.html";
    var who = isAdmin()
      ? '<div class="who">admin<small>Administrator</small></div>'
      : '<div class="who">alice<small>Data scientist</small></div>';

    var multiGroup = NAV().length > 1;
    function navItemHTML(n) {
      if (n.children) {
        var openCls = n.children.some(function (c) { return c.id === page; }) ? ' expanded' : '';
        return '<div class="nav-item nav-parent' + openCls + '" data-nav-toggle>' +
            svg(n.icon) + '<span>' + n.label + '</span>' +
            '<span class="caret">' + svg("chevron") + '</span>' +
          '</div>' +
          '<div class="nav-sub' + (openCls ? ' open' : '') + '">' +
            n.children.map(function (c) {
              return '<a class="nav-item' + (c.id === page ? ' active' : '') + '" href="' + c.href + '">' +
                svg(c.icon) + '<span>' + c.label + '</span></a>';
            }).join("") +
          '</div>';
      }
      return '<a class="nav-item' + (n.id === page ? ' active' : '') + '" href="' + n.href + '">' +
        svg(n.icon) + '<span>' + n.label + '</span>' +
        (n.badge ? '<span class="badge-count">' + n.badge + '</span>' : '') + '</a>';
    }
    var navHTML = NAV().map(function (g) {
      return ((multiGroup && g.group) ? '<div class="nav-group-label">' + g.group + '</div>' : '') +
        g.items.map(navItemHTML).join("");
    }).join("");

    document.body.innerHTML =
      '<div class="app">' +
        '<aside class="sidebar">' +
          '<a class="brand" href="' + home + '" title="Optimum Hub">' +
            '<img class="brand-logo" src="assets/brand/jh-logo.svg" alt="Stellars Tech AI Lab"></a>' +
          '<nav class="nav">' + navHTML + '</nav>' +
          '<div class="sidebar-foot">' + who +
            '<button class="list-icon-secondary" style="margin-left:auto" title="Sign out">' + svg("logout") + '</button>' +
          '</div>' +
        '</aside>' +
        '<div class="main">' +
          '<header class="topbar">' +
            '<div class="crumbs">' + crumbsHTML + '</div>' +
            themeChangerHTML() +
          '</header>' +
          '<div class="content">' + mainHTML + '</div>' +
        '</div>' +
      '</div>' +
      paletteHTML() +
      '<div class="toasts" id="toasts"></div>' +
      '<div class="version-badge" title="OptimumHub version">OptimumHub 1.0.0</div>' +
      (page === "home" ? mockSwitchHTML() : '');

    applyMode(currentMode());
    wire();
  }

  // topbar theme changer - light / dark / system (segmented, mock + real)
  function themeChangerHTML() {
    return '<div class="theme-changer" id="theme-changer" style="margin-left:auto">' +
      '<button data-mode="light" title="Light">' + svg("sun") + '</button>' +
      '<button data-mode="dark" title="Dark">' + svg("moon") + '</button>' +
      '<button data-mode="system" title="System">' + svg("monitor") + '</button>' +
      '</div>';
  }

  // mock-only: a role-view switcher on the Overview, NOT part of the design -
  // it just lets a reviewer hop between the admin and user home without URLs
  function mockSwitchHTML() {
    return '<div class="mock-switch" title="Mock navigation helper - not part of the design">' +
      '<b>mock</b>' +
      '<a href="home.html"' + (isAdmin() ? ' class="on"' : '') + '>Admin</a>' +
      '<a href="home-user.html"' + (isAdmin() ? '' : ' class="on"') + '>User</a>' +
      '<a href="design-system.html" title="Design language palette - mock only">design</a>' +
      '</div>';
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
    var all = nav.concat(ACTIONS()).filter(function (r) { return r.label.toLowerCase().indexOf(q) > -1; });
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

  // ---------- helpers ----------
  function forEach(list, fn) { Array.prototype.forEach.call(list, fn); }

  // ---------- scale behaviours (lists, comboboxes, capped chips) ----------
  // Demonstrated for real over the static sample rows / in-script corpora so
  // the scale story is credible: search, scope and sort actually work. The
  // pager (in markup) is illustrative - nothing pages a real dataset here.
  var SAMPLE_GROUPS = ['research','data-science','gpu','keys-openai','interns','admins','staff','students','ml-platform','vision-lab','nlp','robotics','finance','bioinformatics','physics'];
  var SAMPLE_USERS = ['alice','milan','nina','jakub','konrad','ola','piotr','marta','ewa','tomek','dawid','kasia','marek','agnieszka','bartek','sofia','hugo','lena'];
  var CORPORA = { groups: SAMPLE_GROUPS, users: SAMPLE_USERS };

  function debounce(fn, ms) {
    var t;
    return function () { var a = arguments, c = this; clearTimeout(t); t = setTimeout(function () { fn.apply(c, a); }, ms || 120); };
  }

  // data-list: a .tbl whose rows carry data-text (searchable) + data-scope
  // (space-separated state tokens). The enclosing .card supplies an optional
  // [data-list-search] input and [data-list-scope] filter pills; one pill may
  // start .active to set the default scope. Sortable columns use
  // th.sortable[data-sort][data-sort-type] with matching data-sort-<key> on the
  // row (falls back to data-text). An optional [data-list-empty] tr shows when
  // nothing matches.
  function applyList(root) {
    forEach(root.querySelectorAll("[data-list]"), function (table) {
      if (table.getAttribute("data-list-done")) return;
      table.setAttribute("data-list-done", "1");
      var card = table.closest(".card") || document;
      var search = card.querySelector("[data-list-search]");
      var scopes = card.querySelectorAll("[data-list-scope]");
      var tbody = table.tBodies[0];
      if (!tbody) return;
      var emptyRow = table.querySelector("[data-list-empty]");
      var st = { q: "", scope: "all" };
      var act = card.querySelector("[data-list-scope].active");
      if (act) st.scope = act.getAttribute("data-list-scope");
      function dataRows() { return Array.prototype.slice.call(tbody.querySelectorAll("tr[data-text]")); }
      function refresh() {
        var q = st.q.toLowerCase(), sc = st.scope, shown = 0;
        dataRows().forEach(function (r) {
          var okT = !q || (r.getAttribute("data-text") || "").toLowerCase().indexOf(q) > -1;
          var okS = sc === "all" || (" " + (r.getAttribute("data-scope") || "") + " ").indexOf(" " + sc + " ") > -1;
          var vis = okT && okS; r.hidden = !vis; if (vis) shown++;
        });
        if (emptyRow) emptyRow.hidden = shown > 0;
        stripe(tbody);
      }
      if (search) search.addEventListener("input", debounce(function () { st.q = search.value; refresh(); }));
      forEach(scopes, function (p) {
        p.addEventListener("click", function () {
          forEach(scopes, function (x) { x.classList.toggle("active", x === p); });
          st.scope = p.getAttribute("data-list-scope"); refresh();
        });
      });
      forEach(table.querySelectorAll("th.sortable"), function (th) {
        th.addEventListener("click", function () {
          var key = th.getAttribute("data-sort"), type = th.getAttribute("data-sort-type") || "text";
          var asc = th.getAttribute("data-dir") !== "asc";
          forEach(table.querySelectorAll("th.sortable"), function (x) { x.removeAttribute("data-dir"); });
          th.setAttribute("data-dir", asc ? "asc" : "desc");
          function val(r) {
            var v = r.getAttribute("data-sort-" + key);
            if (v === null) v = r.getAttribute("data-text") || "";
            return type === "num" ? (parseFloat(v) || 0) : ("" + v).toLowerCase();
          }
          var rs = dataRows().sort(function (a, b) { var av = val(a), bv = val(b); return (av < bv ? -1 : av > bv ? 1 : 0) * (asc ? 1 : -1); });
          rs.forEach(function (r) { tbody.appendChild(r); });
          if (emptyRow) tbody.appendChild(emptyRow);
          stripe(tbody);
        });
      });
      refresh();
    });
  }

  // data-combo="groups|users": typeahead chip-input (port of the live hub's
  // admin chip editor). Pre-seed chosen chips inside [data-combo-chips]. Type to
  // filter the corpus, Enter/Tab/click adds, x removes, Backspace on empty pops
  // the last. Replaces every <select>/fake-autocomplete membership picker.
  function applyCombo(root) {
    forEach(root.querySelectorAll("[data-combo]"), function (box) {
      if (box.getAttribute("data-combo-done")) return;
      box.setAttribute("data-combo-done", "1");
      var corpus = CORPORA[box.getAttribute("data-combo")] || [];
      var label = box.getAttribute("data-combo");
      var chipsEl = box.querySelector("[data-combo-chips]");
      var input = box.querySelector(".combo-input");
      var pop = box.querySelector("[data-combo-pop]");
      if (!chipsEl || !input || !pop) return;
      var sel = -1, matches = [];
      function chosen() { return Array.prototype.map.call(chipsEl.querySelectorAll(".chip"), function (c) { return c.getAttribute("data-val"); }); }
      function wireRemove(c) { var x = c.querySelector(".x"); if (x) x.addEventListener("click", function () { c.remove(); }); }
      function addChip(v) {
        if (!v || chosen().indexOf(v) > -1) return;
        var c = document.createElement("span");
        c.className = "chip"; c.setAttribute("data-val", v);
        c.innerHTML = "<span>" + v + "</span><span class=\"x\">" + svg("close") + "</span>";
        wireRemove(c); chipsEl.appendChild(c);
      }
      function close() { pop.classList.remove("open"); pop.innerHTML = ""; matches = []; sel = -1; }
      function paint() { forEach(pop.querySelectorAll(".combo-opt"), function (el, i) { el.classList.toggle("sel", i === sel); }); }
      function render() {
        var q = (input.value || "").trim().toLowerCase();
        if (!q) { close(); return; }
        var have = chosen();
        matches = corpus.filter(function (g) { return have.indexOf(g) < 0 && g.toLowerCase().indexOf(q) > -1; }).slice(0, 8);
        sel = matches.length ? 0 : -1;
        pop.innerHTML = matches.length
          ? matches.map(function (g, i) { return '<div class="combo-opt' + (i === sel ? " sel" : "") + '" data-v="' + g + '">' + g + "</div>"; }).join("")
          : '<div class="combo-opt" data-empty>No matching ' + label + "</div>";
        pop.classList.add("open");
        forEach(pop.querySelectorAll("[data-v]"), function (el) {
          el.addEventListener("mousedown", function (e) { e.preventDefault(); addChip(el.getAttribute("data-v")); input.value = ""; close(); input.focus(); });
        });
      }
      input.addEventListener("input", render);
      input.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" && matches.length) { e.preventDefault(); sel = (sel + 1) % matches.length; paint(); }
        else if (e.key === "ArrowUp" && matches.length) { e.preventDefault(); sel = (sel - 1 + matches.length) % matches.length; paint(); }
        else if ((e.key === "Enter" || e.key === "Tab") && sel > -1 && matches[sel]) { e.preventDefault(); addChip(matches[sel]); input.value = ""; close(); }
        else if (e.key === "Backspace" && !input.value) { var cs = chipsEl.querySelectorAll(".chip"); if (cs.length) cs[cs.length - 1].remove(); }
        else if (e.key === "Escape") { close(); }
      });
      input.addEventListener("blur", function () { setTimeout(close, 150); });
      forEach(chipsEl.querySelectorAll(".chip"), wireRemove);
    });
  }

  // data-chips[="N"]: cap a DISPLAY chip list at N (default 3); the rest collapse
  // behind a +N pill that reveals them in place. Keeps a many-membership cell
  // from overflowing the row.
  function applyChips(root) {
    forEach(root.querySelectorAll("[data-chips]"), function (box) {
      if (box.getAttribute("data-chips-done")) return;
      box.setAttribute("data-chips-done", "1");
      var cap = parseInt(box.getAttribute("data-chips"), 10) || 3;
      var chips = Array.prototype.slice.call(box.querySelectorAll(".chip, .tag"));
      if (chips.length <= cap) return;
      chips.forEach(function (c, i) { if (i >= cap) c.hidden = true; });
      var more = document.createElement("button");
      more.type = "button"; more.className = "chip-more"; more.textContent = "+" + (chips.length - cap);
      more.title = chips.slice(cap).map(function (c) { return c.textContent.trim(); }).join(", ");
      more.addEventListener("click", function () { chips.forEach(function (c) { c.hidden = false; }); more.remove(); });
      box.appendChild(more);
    });
  }

  // data-fill: a chip/tag row that fills one line, then collapses the overflow
  // into a "(N)" counter (N = total) whose tooltip lists every item. Width-driven
  // (unlike data-chips' fixed cap) - if everything fits, nothing collapses.
  function applyFill(root) {
    forEach(root.querySelectorAll("[data-fill]"), function (box) {
      if (box.getAttribute("data-fill-done")) return;
      if (box.offsetParent === null) return; // hidden (e.g. an inactive tab) - defer until shown
      box.setAttribute("data-fill-done", "1");
      var chips = Array.prototype.slice.call(box.querySelectorAll(".chip, .tag"));
      if (chips.length < 2) return;
      var firstTop = chips[0].offsetTop;
      if (!chips.some(function (c) { return c.offsetTop > firstTop; })) return; // all fit on one line
      var more = document.createElement("span");
      more.className = "tag-more";
      more.textContent = "(" + chips.length + ")";
      more.title = chips.map(function (c) { return c.textContent.trim(); }).join(", ");
      box.appendChild(more);
      var vis = chips.slice();
      while (vis.length && more.offsetTop > firstTop) { vis.pop().hidden = true; }
    });
  }

  // zebra: tag every other VISIBLE row .alt so striping survives filter/sort
  // (CSS nth-child counts hidden rows). Run on load and after any list change.
  function stripe(tbody) {
    if (!tbody) return;
    var i = 0;
    forEach(tbody.querySelectorAll("tr"), function (r) {
      if (r.hidden || r.hasAttribute("data-list-empty")) { r.classList.remove("alt"); return; }
      r.classList.toggle("alt", i % 2 === 1); i++;
    });
  }

  // ---------- wiring ----------
  function tabClick(e) {
    var box = e.currentTarget;
    var b = e.target.closest ? e.target.closest(".tab") : null;
    if (!b || !box.contains(b)) return;
    var k = b.getAttribute("data-tab");
    forEach(box.querySelectorAll(".tab"), function (x) { x.classList.toggle("active", x === b); });
    forEach(box.querySelectorAll(".tab-panel"), function (p) { p.classList.toggle("active", p.getAttribute("data-panel") === k); });
    applyFill(box); // the newly shown panel can now be measured for data-fill
  }
  // wire toasts, tabs and the scale behaviours within a subtree (document on load)
  function wireRoot(root) {
    forEach(root.querySelectorAll("[data-toast]"), function (el) { el.addEventListener("click", function () { toast(el.getAttribute("data-toast")); }); });
    // data-confirm: a Save (or similar) reveals an inline success notice right
    // above its form-foot - the persistent confirmation pattern after saving
    forEach(root.querySelectorAll("[data-confirm]"), function (el) {
      el.addEventListener("click", function () {
        var anchor = el.closest(".form-foot") || el;
        var slot = anchor.previousElementSibling;
        if (!slot || !slot.hasAttribute || !slot.hasAttribute("data-confirm-slot")) {
          slot = document.createElement("div");
          slot.className = "notice success";
          slot.setAttribute("data-confirm-slot", "");
          slot.innerHTML = svg("check") + "<span></span>";
          anchor.parentNode.insertBefore(slot, anchor);
        }
        slot.querySelector("span").textContent = el.getAttribute("data-confirm");
        slot.style.display = "";
      });
    });
    forEach(root.querySelectorAll("[data-tabs]"), function (box) { box.addEventListener("click", tabClick); });
    applyList(root);
    applyCombo(root);
    applyChips(root);
    applyFill(root);
    forEach(root.querySelectorAll("table.tbl"), function (t) { stripe(t.tBodies[0]); });
  }
  function wire() {
    forEach(document.querySelectorAll("#theme-changer [data-mode]"), function (b) {
      b.addEventListener("click", function () { applyMode(b.getAttribute("data-mode")); });
    });
    document.getElementById("scrim").addEventListener("click", closePalette);
    document.getElementById("palette-q").addEventListener("input", function (e) { buildPalette(e.target.value); });

    // expandable nav parents (Advanced)
    forEach(document.querySelectorAll("[data-nav-toggle]"), function (el) {
      el.addEventListener("click", function () {
        el.classList.toggle("expanded");
        var sub = el.nextElementSibling;
        if (sub && sub.classList.contains("nav-sub")) sub.classList.toggle("open");
      });
    });

    wireRoot(document);
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
