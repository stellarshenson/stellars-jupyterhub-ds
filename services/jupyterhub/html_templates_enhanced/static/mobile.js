/**
 * Mobile Interface Module for Stellars JupyterHub DS
 *
 * Detects mobile devices and adapts the UI:
 * - Hides desktop-only elements (volumes, named servers, admin nav items)
 * - Intercepts "My Server" link to start via API without navigating to JupyterLab
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

  // ── Mobile Home Page Logic ─────────────────────────────────────────

  /**
   * Intercept the "My Server" / "Start My Server" link on mobile.
   * When server is running: show disabled "Server Running" button.
   * When server is stopped: start via API POST without navigating to JupyterLab.
   */
  function interceptStartButton(baseUrl, username, getCookie) {
    var startBtn = document.getElementById('start');
    if (!startBtn) return;

    var stopBtn = document.getElementById('stop');
    var serverRunning = stopBtn && stopBtn.offsetParent !== null;

    if (serverRunning) {
      // Server is active - disable navigation, show status
      startBtn.removeAttribute('href');
      startBtn.style.cursor = 'default';
      startBtn.classList.remove('btn-primary');
      startBtn.classList.add('btn-success', 'disabled');
      startBtn.innerHTML = '<i class="fa fa-check" aria-hidden="true"></i> Server Running';
    } else {
      // Server is stopped - start via API
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
            alert('Failed to start server');
          }
        };
        xhr.onerror = function() {
          btn.classList.remove('disabled');
          btn.innerHTML = '<i class="fa fa-play" aria-hidden="true"></i> Start My Server';
          alert('Network error');
        };
        xhr.send();
      });
    }
  }

  /**
   * Fetch activity data and render card-based list for mobile home page.
   * Shows status dot, username, and time remaining per user.
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
        badge.textContent = users.length + ' users (' + activeCount + ' active, ' +
          idleCount + ' idle, ' + offlineCount + ' offline)';
      }

      // Sort: active first, then idle, then offline; alphabetical within each group
      users.sort(function(a, b) {
        var aStatus = a.server_active ? (a.recently_active ? 2 : 1) : 0;
        var bStatus = b.server_active ? (b.recently_active ? 2 : 1) : 0;
        if (aStatus !== bStatus) return bStatus - aStatus;
        return (a.username || '').localeCompare(b.username || '');
      });

      if (!list) return;
      list.innerHTML = '';
      users.forEach(function(user) {
        var statusColor = user.server_active
          ? (user.recently_active ? '#28a745' : '#ffc107')
          : '#dc3545';
        var timeLeft = formatTimeShort(user.time_remaining_seconds);

        var row = document.createElement('div');
        row.className = 'mobile-user-row d-flex align-items-center py-2 border-bottom';
        row.innerHTML =
          '<span class="me-2" style="color:' + statusColor + ';font-size:1.1em;">&#9679;</span>' +
          '<span class="flex-grow-1 text-truncate">' + escapeHtml(user.username) + '</span>' +
          '<span class="text-muted small ms-2">' + timeLeft + '</span>';
        list.appendChild(row);
      });

      if (users.length === 0) {
        list.innerHTML = '<div class="text-muted small py-2">No users found</div>';
      }
    }

    fetchAndRender();
    setInterval(fetchAndRender, 10000);
  }

  // ── Mobile Activity Page Logic ─────────────────────────────────────

  /**
   * Replace table rendering with card-based layout on the activity page.
   * Called from activity.html when mobile is detected.
   */
  function renderActivityCards(users, container, opts) {
    opts = opts || {};
    container.innerHTML = '';

    if (users.length === 0) {
      container.innerHTML = '<div class="text-muted small py-2">No users found</div>';
      return;
    }

    users.forEach(function(user) {
      var statusColor, statusLabel;
      if (user.server_active && user.recently_active) {
        statusColor = '#28a745'; statusLabel = 'active';
      } else if (user.server_active) {
        statusColor = '#ffc107'; statusLabel = 'idle';
      } else {
        statusColor = '#dc3545'; statusLabel = 'offline';
      }

      var timeLeft = formatTimeShort(user.time_remaining_seconds);
      var lastActive = formatLastActiveShort(user.last_activity);
      var mem = formatMemShort(user.memory_mb);
      var cpu = user.cpu_percent != null ? user.cpu_percent.toFixed(1) + '%' : '--';

      var card = document.createElement('div');
      card.className = 'mobile-activity-card card mb-2';
      card.innerHTML =
        '<div class="card-body py-2 px-3">' +
          '<div class="d-flex align-items-center justify-content-between">' +
            '<div class="d-flex align-items-center text-truncate">' +
              '<span class="me-2" style="color:' + statusColor + ';font-size:1em;">&#9679;</span>' +
              '<strong class="text-truncate">' + escapeHtml(user.username) + '</strong>' +
            '</div>' +
            '<span class="badge bg-' + (statusLabel === 'active' ? 'success' : statusLabel === 'idle' ? 'warning' : 'secondary') + ' ms-2">' + statusLabel + '</span>' +
          '</div>' +
          '<div class="d-flex justify-content-between mt-1 small text-muted">' +
            '<span>CPU: ' + cpu + '</span>' +
            '<span>Mem: ' + mem + '</span>' +
            (timeLeft !== '--' ? '<span>TTL: ' + timeLeft + '</span>' : '') +
            (lastActive !== '--' ? '<span>' + lastActive + '</span>' : '') +
          '</div>' +
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
    interceptStartButton: interceptStartButton,
    initMobileActivityMonitor: initMobileActivityMonitor,
    renderActivityCards: renderActivityCards
  };

})();
