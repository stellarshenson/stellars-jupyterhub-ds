/**
 * Mobile Interface Module for Stellars JupyterHub DS
 *
 * Detects mobile devices and adapts the UI:
 * - Hides desktop-only elements (volumes, named servers, admin nav items)
 * - Replaces "My Server" link with API-based start (no JupyterLab navigation)
 * - Shows server status strip with pulsating indicator and uptime
 * - Renders inline activity monitor for admin users on the home page
 * - Renders card-based activity layout on the activity page
 *
 * Detection: UA regex + viewport width + touch capability
 * Selector: [data-device="mobile"] / [data-device="desktop"] in CSS
 */
(function() {
  'use strict';

  // ── Device Detection (runs immediately, before DOM ready) ──────────
  var ua = navigator.userAgent;
  var isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua)
    || (window.innerWidth <= 768 && 'ontouchstart' in window);
  document.documentElement.setAttribute('data-device', isMobile ? 'mobile' : 'desktop');

  if (!isMobile) return;  // Desktop: nothing more to do

  // ── Dark Mode Toggle (mobile duplicate) ────────────────────────────
  document.addEventListener('DOMContentLoaded', function() {
    var mobileToggle = document.getElementById('dark-theme-toggle-mobile');
    if (mobileToggle) {
      mobileToggle.addEventListener('click', function() {
        var current = document.documentElement.getAttribute('data-bs-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem('jupyterhub-bs-theme', next);
        document.documentElement.setAttribute('data-bs-theme', next);
      });
    }
  });

  // ── Mobile Home Page Logic ─────────────────────────────────────────

  /**
   * Adapt the home page for mobile:
   * - When server running: hide "My Server" button (status strip shows state),
   *   keep Stop + Restart as compact actions
   * - When server stopped: intercept Start to use API (no JupyterLab navigation)
   */
  function setupHomePage(baseUrl, username, getCookie) {
    var startBtn = document.getElementById('start');
    if (!startBtn) return;

    var stopBtn = document.getElementById('stop');
    var serverRunning = stopBtn && stopBtn.offsetParent !== null;

    var restartBtn = document.getElementById('restart-server-btn');

    if (serverRunning) {
      // Hide the "My Server" link - status strip handles this
      startBtn.classList.add('mobile-hidden');

      // Intercept Stop button: show spinner, call API, reload on complete
      if (stopBtn) {
        stopBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopImmediatePropagation();  // prevent JupyterHub's home.js handler
          var btn = this;
          btn.classList.add('disabled');
          btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Stopping...';
          if (restartBtn) restartBtn.style.display = 'none';

          var xhr = new XMLHttpRequest();
          xhr.open('DELETE', baseUrl + 'api/users/' + encodeURIComponent(username) + '/server');
          xhr.setRequestHeader('X-XSRFToken', getCookie('_xsrf'));
          xhr.onload = function() { location.reload(); };
          xhr.onerror = function() { location.reload(); };
          xhr.send();
        });
      }
    } else {
      // Server stopped - hide Restart (Jinja may render it on edge cases)
      if (restartBtn) restartBtn.style.display = 'none';

      // Intercept Start to use API (no JupyterLab navigation)
      startBtn.addEventListener('click', function(e) {
        e.preventDefault();
        var btn = this;
        btn.classList.add('disabled');
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Starting...';

        var xhr = new XMLHttpRequest();
        xhr.open('POST', baseUrl + 'api/users/' + encodeURIComponent(username) + '/server');
        xhr.setRequestHeader('X-XSRFToken', getCookie('_xsrf'));
        xhr.onload = function() {
          if (xhr.status >= 200 && xhr.status < 400) {
            location.reload();
          } else {
            btn.classList.remove('disabled');
            btn.innerHTML = '<i class="fa fa-play" aria-hidden="true"></i> Start My Server';
          }
        };
        xhr.onerror = function() {
          btn.classList.remove('disabled');
          btn.innerHTML = '<i class="fa fa-play" aria-hidden="true"></i> Start My Server';
        };
        xhr.send();
      });
    }

    // Start uptime counter and health monitor
    initUptime();
    if (serverRunning) {
      startHealthCheck(baseUrl, username, getCookie);
    }
  }

  /**
   * Calculate and display uptime from spawner.started timestamp.
   */
  function initUptime() {
    var statusEl = document.getElementById('mobile-server-status');
    var uptimeEl = document.getElementById('mobile-uptime');
    if (!statusEl || !uptimeEl) return;

    var started = statusEl.getAttribute('data-started');
    if (!started) return;

    var startTime = new Date(started).getTime();
    if (isNaN(startTime)) return;

    function updateUptime() {
      var diff = Date.now() - startTime;
      if (diff < 0) { uptimeEl.textContent = ''; return; }
      var sec = Math.floor(diff / 1000);
      var min = Math.floor(sec / 60);
      var hr = Math.floor(min / 60);
      var day = Math.floor(hr / 24);

      var text;
      if (day > 0) text = day + 'd ' + (hr % 24) + 'h';
      else if (hr > 0) text = hr + 'h ' + (min % 60) + 'm';
      else text = min + 'm';
      uptimeEl.textContent = text;
    }

    updateUptime();
    setInterval(updateUptime, 60000);
  }

  // ── Health Check ─────────────────────────────────────────────────

  var healthState = 'online';  // online | unreachable | stopped

  /**
   * Poll server status every 15s. On failure or server stopped,
   * transition status strip to yellow blinking.
   * Uses navigator.onLine events for instant network loss detection.
   */
  function startHealthCheck(baseUrl, username, getCookie) {
    var statusEl = document.getElementById('mobile-server-status');
    if (!statusEl) return;

    function check() {
      if (!navigator.onLine) {
        setHealthState(statusEl, 'unreachable');
        return;
      }
      var xhr = new XMLHttpRequest();
      xhr.open('GET', baseUrl + 'api/users/' + encodeURIComponent(username));
      xhr.setRequestHeader('X-XSRFToken', getCookie('_xsrf'));
      xhr.timeout = 10000;
      xhr.onload = function() {
        if (xhr.status === 200) {
          try {
            var data = JSON.parse(xhr.responseText);
            // Check if default server is still active
            var servers = data.servers || {};
            var defaultServer = servers[''];
            if (defaultServer && defaultServer.ready) {
              setHealthState(statusEl, 'online');
            } else {
              setHealthState(statusEl, 'stopped');
            }
          } catch(e) {
            setHealthState(statusEl, 'unreachable');
          }
        } else {
          setHealthState(statusEl, 'unreachable');
        }
      };
      xhr.onerror = function() { setHealthState(statusEl, 'unreachable'); };
      xhr.ontimeout = function() { setHealthState(statusEl, 'unreachable'); };
      xhr.send();
    }

    // Instant detection for network changes
    window.addEventListener('offline', function() { setHealthState(statusEl, 'unreachable'); });
    window.addEventListener('online', function() { check(); });

    setInterval(check, 15000);
  }

  function setHealthState(statusEl, state) {
    if (state === healthState) return;
    healthState = state;

    var dot = statusEl.querySelector('.mobile-status-dot');
    var label = statusEl.querySelector('.mobile-status-label');
    var uptime = statusEl.querySelector('.mobile-status-uptime');

    if (state === 'online') {
      statusEl.className = 'desktop-hidden mobile-status-strip';
      dot.className = 'mobile-status-dot active';
      label.textContent = 'Server Online';
      if (uptime) uptime.style.display = '';
    } else if (state === 'unreachable') {
      statusEl.className = 'desktop-hidden mobile-status-strip unreachable';
      dot.className = 'mobile-status-dot unreachable';
      label.textContent = 'Connection Lost';
      if (uptime) uptime.style.display = 'none';
    } else if (state === 'stopped') {
      // Server state changed - reload to get correct Jinja-rendered UI
      location.reload();
    }
  }

  /**
   * Fetch activity data and render card-based list for mobile home page.
   */
  function initMobileActivityMonitor(baseUrl, getCookie) {
    var section = document.getElementById('mobile-activity-section');
    if (!section) return;

    function fetchAndRender() {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', baseUrl + 'api/activity');
      xhr.setRequestHeader('X-XSRFToken', getCookie('_xsrf'));
      xhr.onload = function() {
        if (xhr.status !== 200) return;
        var data = JSON.parse(xhr.responseText);
        renderMobileActivity(data);
      };
      xhr.send();
    }

    function renderMobileActivity(data) {
      var users = data.users || [];
      var loading = document.getElementById('mobile-activity-loading');
      var list = document.getElementById('mobile-activity-list');
      var badge = document.getElementById('mobile-active-count');

      if (loading) loading.classList.add('d-none');
      if (list) list.classList.remove('d-none');

      var activeCount = 0, idleCount = 0, offlineCount = 0;
      users.forEach(function(u) {
        if (u.server_active && u.recently_active) activeCount++;
        else if (u.server_active) idleCount++;
        else offlineCount++;
      });

      if (badge) {
        badge.textContent = activeCount + '/' + users.length;
      }

      // Sort: active first, then idle, then offline
      users.sort(function(a, b) {
        var aStatus = a.server_active ? (a.recently_active ? 2 : 1) : 0;
        var bStatus = b.server_active ? (b.recently_active ? 2 : 1) : 0;
        if (aStatus !== bStatus) return bStatus - aStatus;
        return (a.username || '').localeCompare(b.username || '');
      });

      if (!list) return;
      list.innerHTML = '';
      users.forEach(function(user) {
        var statusClass = user.server_active
          ? (user.recently_active ? 'active' : 'idle')
          : 'offline';
        var timeLeft = formatTimeShort(user.time_remaining_seconds);

        var row = document.createElement('div');
        row.className = 'mobile-user-row';
        row.innerHTML =
          '<span class="mobile-status-dot ' + statusClass + ' small"></span>' +
          '<span class="flex-grow-1 text-truncate">' + escapeHtml(user.username) + '</span>' +
          (timeLeft !== '--' ? '<span class="text-muted small">' + timeLeft + '</span>' : '');
        list.appendChild(row);
      });

      if (users.length === 0) {
        list.innerHTML = '<div class="text-muted small py-2">No users</div>';
      }
    }

    fetchAndRender();
    setInterval(fetchAndRender, 10000);
  }

  // ── Mobile Activity Page Logic ─────────────────────────────────────

  /**
   * Render activity cards for the mobile activity page.
   */
  function renderActivityCards(users, container) {
    container.innerHTML = '';

    if (users.length === 0) {
      container.innerHTML = '<div class="text-muted small py-2">No users found</div>';
      return;
    }

    users.forEach(function(user) {
      var statusClass, statusLabel;
      if (user.server_active && user.recently_active) {
        statusClass = 'active'; statusLabel = 'active';
      } else if (user.server_active) {
        statusClass = 'idle'; statusLabel = 'idle';
      } else {
        statusClass = 'offline'; statusLabel = 'offline';
      }

      var timeLeft = formatTimeShort(user.time_remaining_seconds);
      var lastActive = formatLastActiveShort(user.last_activity);
      var mem = formatMemShort(user.memory_mb);
      var cpu = user.cpu_percent != null ? user.cpu_percent.toFixed(1) + '%' : '--';
      var disk = user.container_size_rw_mb != null ? '+' + formatMemShort(user.container_size_rw_mb) : null;

      var card = document.createElement('div');
      card.className = 'mobile-activity-card';
      card.innerHTML =
        '<div class="d-flex align-items-center justify-content-between">' +
          '<div class="d-flex align-items-center text-truncate">' +
            '<span class="mobile-status-dot ' + statusClass + ' small me-2"></span>' +
            '<strong class="text-truncate">' + escapeHtml(user.username) + '</strong>' +
          '</div>' +
          '<span class="mobile-activity-badge ' + statusClass + '">' + statusLabel + '</span>' +
        '</div>' +
        '<div class="mobile-activity-meta">' +
          '<span>CPU ' + cpu + '</span>' +
          '<span>Mem ' + mem + '</span>' +
          (disk ? '<span>Disk ' + disk + '</span>' : '') +
          (timeLeft !== '--' ? '<span>TTL ' + timeLeft + '</span>' : '') +
          (lastActive !== '--' ? '<span>' + lastActive + '</span>' : '') +
        '</div>';
      container.appendChild(card);
    });
  }

  // ── Shared Formatters ──────────────────────────────────────────────

  function formatTimeShort(seconds) {
    if (seconds == null) return '--';
    if (seconds <= 0) return 'expiring';
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    if (h >= 24) return Math.floor(h / 24) + 'd ' + (h % 24) + 'h';
    if (h > 0) return h + 'h ' + m + 'm';
    return m + 'm';
  }

  function formatLastActiveShort(isoString) {
    if (!isoString) return '--';
    var diffMs = Date.now() - new Date(isoString).getTime();
    var min = Math.floor(diffMs / 60000);
    if (min < 1) return 'now';
    if (min < 60) return min + 'min ago';
    var h = Math.floor(min / 60);
    if (h < 24) return h + 'h ago';
    return Math.floor(h / 24) + 'd ago';
  }

  function formatMemShort(mb) {
    if (mb == null) return '--';
    return mb >= 1024 ? (mb / 1024).toFixed(1) + ' GB' : Math.round(mb) + ' MB';
  }

  function escapeHtml(text) {
    if (text == null) return '';
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(text));
    return d.innerHTML;
  }

  // ── Public API ─────────────────────────────────────────────────────

  window.MobileUI = {
    isMobile: isMobile,
    setupHomePage: setupHomePage,
    initMobileActivityMonitor: initMobileActivityMonitor,
    renderActivityCards: renderActivityCards
  };

})();
