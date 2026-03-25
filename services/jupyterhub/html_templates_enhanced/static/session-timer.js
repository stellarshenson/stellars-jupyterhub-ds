/**
 * Session Timer - Compact progress bar with countdown and extension modal.
 * Stellars JupyterHub DS
 *
 * Usage:
 *   SessionTimer.init({ username: '...', baseUrl: '...', getCookie: fn });
 *   SessionTimer.hide();  // called when server stops
 */
(function (window, $) {
  'use strict';

  // ------------------------------------------------------------------ state
  var username, baseUrl, getCookie;
  var currentInfo = null;
  var countdownId = null;
  var refreshId = null;

  // ------------------------------------------------------------- DOM cache
  var $row, $loading, $bar, $progressBar, $timeText, $timeValue;
  var $error, $errorMsg;
  var $trigger;
  var $modal, $hours, $available, $feedback, $feedbackMsg, $confirmBtn;

  // mobile extend panel
  var isMobile = typeof MobileUI !== 'undefined' && MobileUI.isMobile;
  var $mobilePanel, $mobileSlider, $mobileValue, $mobileMax;
  var $mobileConfirm, $mobileCancel, $mobileFeedback, $mobileFeedbackMsg;

  function cacheElements() {
    $row          = $('#session-timer-row');
    $loading      = $('#session-timer-loading');
    $bar          = $('#session-timer-bar');
    $progressBar  = $('#session-progress-bar');
    $timeText     = $('#session-time-text');
    $timeValue    = $('#session-time-value');
    $error        = $('#session-error');
    $errorMsg     = $('#session-error-msg');
    $trigger      = $('#extend-session-trigger');

    $modal        = $('#extend-session-modal');
    $hours        = $('#extend-session-hours');
    $available    = $('#extend-available-hours');
    $feedback     = $('#extend-session-feedback');
    $feedbackMsg  = $('#extend-feedback-msg');
    $confirmBtn   = $('#confirm-extend-btn');

    // mobile extend panel
    $mobilePanel      = $('#mobile-extend-panel');
    $mobileSlider     = $('#mobile-extend-slider');
    $mobileValue      = $('#mobile-extend-value');
    $mobileMax        = $('#mobile-extend-max');
    $mobileConfirm    = $('#mobile-extend-confirm');
    $mobileCancel     = $('#mobile-extend-cancel');
    $mobileFeedback   = $('#mobile-extend-feedback');
    $mobileFeedbackMsg = $('#mobile-extend-feedback-msg');
  }

  // -------------------------------------------------------- colour helpers
  // Smooth RGB interpolation: full (100%) -> mid (30%) -> low (10%)
  // Colors read from CSS custom properties on #session-timer-row
  var COLOR_FULL, COLOR_MID, COLOR_LOW;

  function readCssColors() {
    var el = $row[0];
    var style = getComputedStyle(el);
    COLOR_FULL = parseColor(style.getPropertyValue('--timer-color-full')) || [81, 123, 177];
    COLOR_MID  = parseColor(style.getPropertyValue('--timer-color-mid'))  || [191, 163, 72];
    COLOR_LOW  = parseColor(style.getPropertyValue('--timer-color-low'))  || [175, 78, 86];
  }

  /** Parse hex (#rrggbb) or rgb triplet (r, g, b) into [r, g, b] array. */
  function parseColor(val) {
    if (!val) return null;
    val = val.trim();
    // hex: #446897
    var hex = val.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
    if (hex) return [parseInt(hex[1], 16), parseInt(hex[2], 16), parseInt(hex[3], 16)];
    // rgb triplet fallback: 68, 104, 151
    var parts = val.split(/\s*,\s*/);
    if (parts.length === 3) return [parseInt(parts[0], 10), parseInt(parts[1], 10), parseInt(parts[2], 10)];
    return null;
  }

  function lerp(a, b, t) {
    return [
      Math.round(a[0] + (b[0] - a[0]) * t),
      Math.round(a[1] + (b[1] - a[1]) * t),
      Math.round(a[2] + (b[2] - a[2]) * t)
    ];
  }

  /** Compute interpolated RGB for a given remaining percentage. */
  function getColor(pct) {
    if (pct >= 30) {
      // full at 100%, mid at 30%
      var t = Math.min(1, (pct - 30) / 70);
      return lerp(COLOR_MID, COLOR_FULL, t);
    }
    if (pct >= 10) {
      // mid at 30%, low at 10%
      var t = (pct - 10) / 20;
      return lerp(COLOR_LOW, COLOR_MID, t);
    }
    return COLOR_LOW;
  }

  function rgbStr(c) {
    return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')';
  }

  function applyColor(pct) {
    var color = getColor(pct);
    var css = rgbStr(color);

    // progress bar color via Bootstrap CSS variable
    $progressBar.removeClass('bg-success bg-warning bg-danger');
    $progressBar[0].style.setProperty('--bs-progress-bar-bg', css);

    // time text
    $timeText.css('color', css);
  }

  // ------------------------------------------------------------- formatting
  function formatTime(seconds) {
    if (seconds <= 0) return 'expiring';
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
  }

  // -------------------------------------------------------------- UI update
  function updateUI(info) {
    currentInfo = info;

    if (!info.culler_enabled || !info.server_active) {
      hide();
      return;
    }

    var remaining   = Math.max(0, info.time_remaining_seconds || 0);
    var effective   = (info.timeout_seconds || 0)
                    + ((info.extensions_used_hours || 0) * 3600);
    var pct         = effective > 0 ? (remaining / effective) * 100 : 0;

    // progress bar
    $progressBar
      .css('width', pct + '%')
      .attr('aria-valuenow', Math.round(pct));

    applyColor(pct);

    // time text
    $timeValue.text(formatTime(remaining));

    // available hours (in modal)
    var avail = info.extensions_available_hours || 0;
    $available.html('Available: <strong>' + avail + '</strong> hour(s)');

    // enable/disable extend trigger based on available hours
    if (avail > 0) {
      $trigger.prop('disabled', false).removeAttr('disabled');
      $trigger.attr('title', 'Extend session by ' + Math.floor(avail) + 'h');
    } else {
      $trigger.prop('disabled', true);
      $trigger.attr('title', 'All extension hours used');
    }

    // swap loading -> bar
    $loading.addClass('d-none');
    $bar.removeClass('d-none');

    console.log('[SessionTimer] UI updated - remaining:', remaining,
                'pct:', Math.round(pct), 'color:', rgbStr(getColor(pct)), 'available ext:', avail);
  }

  // ---------------------------------------------------------- API: fetch
  function fetchInfo() {
    var url = baseUrl + 'api/users/' + username + '/session-info';
    console.log('[SessionTimer] fetching', url);

    $.ajax({
      url: url,
      type: 'GET',
      headers: { 'X-XSRFToken': getCookie('_xsrf') },
      success: function (resp) {
        $error.addClass('d-none');
        updateUI(resp);
        if (isMobile) updateMobileSliderMax();
      },
      error: function (xhr) {
        console.error('[SessionTimer] fetch failed', xhr.status);
        $loading.addClass('d-none');
        showError('Unable to load session info', 'warning');
      }
    });
  }

  // ---------------------------------------------------------- API: extend
  function handleExtend() {
    var hours = parseInt($hours.val(), 10) || 0;
    if (hours < 1) {
      showFeedback('Enter at least 1 hour', 'warning');
      return;
    }

    var url = baseUrl + 'api/users/' + username + '/extend-session';
    console.log('[SessionTimer] extending by', hours, 'hour(s)');

    $confirmBtn.prop('disabled', true)
      .html('<span class="spinner-border spinner-border-sm" role="status"></span> Extending\u2026');

    $.ajax({
      url: url,
      type: 'POST',
      headers: { 'X-XSRFToken': getCookie('_xsrf') },
      data: JSON.stringify({ hours: hours }),
      contentType: 'application/json',
      success: function (resp) {
        resetExtendBtn();
        if (resp.success) {
          if (resp.session_info) {
            updateUI({
              culler_enabled: true,
              server_active: true,
              timeout_seconds: currentInfo ? currentInfo.timeout_seconds : 0,
              time_remaining_seconds: resp.session_info.time_remaining_seconds,
              extensions_used_hours: resp.session_info.extensions_used_hours,
              extensions_available_hours: resp.session_info.extensions_available_hours
            });
          }
          var cls = resp.truncated ? 'warning' : 'success';
          showFeedback(resp.message, cls);
          setTimeout(function () {
            var modal = bootstrap.Modal.getInstance($modal[0]);
            if (modal) modal.hide();
            fetchInfo();
          }, resp.truncated ? 2500 : 1500);
        }
      },
      error: function (xhr) {
        resetExtendBtn();
        var msg = (xhr.responseJSON && xhr.responseJSON.error) || 'Failed to extend session';
        showFeedback(msg, 'warning');
      }
    });
  }

  function resetExtendBtn() {
    $confirmBtn.prop('disabled', false)
      .html('<i class="fa fa-plus" aria-hidden="true"></i> Extend');
  }

  // --------------------------------------------------- mobile extend
  function updateSliderLabel() {
    var val = parseInt($mobileSlider.val(), 10);
    var suffix = val === 1 ? 'hour' : 'hours';
    $mobileValue.html('<strong>+' + val + ' ' + suffix + '</strong>');
  }

  function updateMobileSliderMax() {
    if (!currentInfo || !$mobileSlider.length) return;
    var avail = currentInfo.extensions_available_hours || 0;
    var noHoursLeft = avail <= 0;

    // Enable/disable slider and confirm based on available hours
    if (noHoursLeft) {
      $mobileSlider.prop('disabled', true);
      $mobileConfirm.prop('disabled', true);
    } else {
      $mobileSlider.prop('disabled', false).removeAttr('disabled');
      $mobileConfirm.prop('disabled', false).removeAttr('disabled');
    }

    if (noHoursLeft) {
      $mobileValue.html('<span class="text-muted">No extension hours available</span>');
      $mobilePanel.addClass('d-none');
      return;
    }

    var max = Math.floor(avail);
    $mobileSlider.attr('max', max);
    $mobileMax.text(max + 'h');
    if (parseInt($mobileSlider.val(), 10) > max) {
      $mobileSlider.val(max);
      updateSliderLabel();
    }
  }

  function handleMobileExtend() {
    var hours = parseInt($mobileSlider.val(), 10) || 1;
    var url = baseUrl + 'api/users/' + username + '/extend-session';

    $mobileConfirm.prop('disabled', true)
      .html('<span class="spinner-border spinner-border-sm"></span>');

    $.ajax({
      url: url,
      type: 'POST',
      headers: { 'X-XSRFToken': getCookie('_xsrf') },
      data: JSON.stringify({ hours: hours }),
      contentType: 'application/json',
      success: function (resp) {
        $mobileConfirm.prop('disabled', false)
          .html('<i class="fa fa-plus" aria-hidden="true"></i> Extend');
        if (resp.success) {
          if (resp.session_info) {
            updateUI({
              culler_enabled: true,
              server_active: true,
              timeout_seconds: currentInfo ? currentInfo.timeout_seconds : 0,
              time_remaining_seconds: resp.session_info.time_remaining_seconds,
              extensions_used_hours: resp.session_info.extensions_used_hours,
              extensions_available_hours: resp.session_info.extensions_available_hours
            });
            updateMobileSliderMax();
          }
          var cls = resp.truncated ? 'alert-warning' : 'alert-success';
          $mobileFeedback.removeClass('d-none alert-warning alert-success').addClass(cls);
          $mobileFeedbackMsg.text(resp.message);
          setTimeout(function () {
            $mobilePanel.addClass('d-none');
            $mobileFeedback.addClass('d-none');
            fetchInfo();
          }, resp.truncated ? 2500 : 1500);
        }
      },
      error: function (xhr) {
        $mobileConfirm.prop('disabled', false)
          .html('<i class="fa fa-plus" aria-hidden="true"></i> Extend');
        var msg = (xhr.responseJSON && xhr.responseJSON.error) || 'Failed to extend';
        $mobileFeedback.removeClass('d-none alert-warning alert-success').addClass('alert-warning');
        $mobileFeedbackMsg.text(msg);
      }
    });
  }

  // --------------------------------------------------------- feedback
  function showError(msg, cls) {
    cls = cls || 'warning';
    $error.removeClass('d-none alert-warning alert-success alert-danger')
      .addClass('alert-' + cls);
    $errorMsg.text(msg);
  }

  function showFeedback(msg, cls) {
    cls = cls || 'warning';
    $feedback.removeClass('d-none alert-warning alert-success alert-danger')
      .addClass('alert-' + cls);
    $feedbackMsg.text(msg);
  }

  // -------------------------------------------------------- countdown
  function startCountdown() {
    countdownId = setInterval(function () {
      if (!currentInfo || !currentInfo.time_remaining_seconds) return;

      currentInfo.time_remaining_seconds = Math.max(0, currentInfo.time_remaining_seconds - 60);
      var remaining = currentInfo.time_remaining_seconds;
      var effective = (currentInfo.timeout_seconds || 0)
                    + ((currentInfo.extensions_used_hours || 0) * 3600);
      var pct  = effective > 0 ? (remaining / effective) * 100 : 0;

      $progressBar.css('width', pct + '%').attr('aria-valuenow', Math.round(pct));
      applyColor(pct);
      $timeValue.text(formatTime(remaining));
    }, 60000);
  }

  function startServerRefresh() {
    refreshId = setInterval(fetchInfo, 300000);
  }

  // --------------------------------------------------------- public API
  function hide() {
    $row.hide();
    if (countdownId) clearInterval(countdownId);
    if (refreshId) clearInterval(refreshId);
  }

  function init(config) {
    username  = config.username;
    baseUrl   = config.baseUrl;
    getCookie = config.getCookie;

    cacheElements();

    // bail if elements not present (culler disabled or server not active)
    if ($row.length === 0) return;

    readCssColors();
    console.log('[SessionTimer] initializing for', username);

    if (isMobile && $mobilePanel.length) {
      // Mobile: override trigger to toggle inline panel instead of modal
      $trigger.removeAttr('data-bs-toggle').removeAttr('data-bs-target');
      $trigger.on('click', function () {
        var isVisible = !$mobilePanel.hasClass('d-none');
        if (isVisible) {
          $mobilePanel.addClass('d-none');
        } else {
          $mobileSlider.val(1);
          updateSliderLabel();
          $mobileFeedback.addClass('d-none');
          $mobilePanel.removeClass('d-none');
        }
      });

      // slider label update
      $mobileSlider.on('input', updateSliderLabel);

      // cancel
      $mobileCancel.on('click', function () {
        $mobilePanel.addClass('d-none');
      });

      // confirm
      $mobileConfirm.on('click', handleMobileExtend);
    } else {
      // Desktop: modal
      $modal.on('show.bs.modal', function () {
        $hours.val(1);
        $feedback.addClass('d-none');
        resetExtendBtn();
      });
      $confirmBtn.on('click', handleExtend);
    }

    // initial fetch + recurring
    fetchInfo();
    startCountdown();
    startServerRefresh();
  }

  // expose
  window.SessionTimer = { init: init, hide: hide };

})(window, jQuery);
