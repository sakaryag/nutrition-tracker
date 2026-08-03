/* ============================================================
   social.js — Friends & Racing page
   Endpoints used:
     GET/POST  /api/friends
     GET       /api/friends/requests
     PUT       /api/friends/requests/<id>/accept|decline
     DELETE    /api/friends/<id>
     GET/PUT   /api/social/feed/visibility
     GET       /api/social/feed
     POST      /api/shared              (share an entry)
     GET       /api/shared/incoming     (entries shared to me)
     GET       /api/game/score
     GET       /api/game/leaderboard
     GET       /api/social/badges
   ============================================================ */
(function () {
  'use strict';

  var _friends = [];
  var _raceWeekOffset = 0;  // 0 = current week, -1 = last week, etc.

  /* ── Tab routing ─────────────────────────────────────────── */
  function initTabs() {
    document.querySelectorAll('.social-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.social-tab').forEach(function (b) { b.classList.remove('active'); });
        document.querySelectorAll('.social-panel').forEach(function (p) { p.hidden = true; });
        btn.classList.add('active');
        var panel = document.getElementById('tab-' + btn.dataset.tab);
        if (panel) panel.hidden = false;
      });
    });
  }

  /* ── Helpers ─────────────────────────────────────────────── */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmt(n) { return Math.round(n || 0); }
  function r1(n) { return Math.round((n || 0) * 10) / 10; }

  function isoWeekLabel(offset) {
    var today = new Date();
    var day = today.getDay() || 7;
    var monday = new Date(today);
    monday.setDate(today.getDate() - day + 1 + offset * 7);
    var sun = new Date(monday);
    sun.setDate(monday.getDate() + 6);
    var fmt = function (d) {
      return (d.getMonth() + 1) + '/' + d.getDate();
    };
    return fmt(monday) + ' – ' + fmt(sun);
  }

  function weekParam(offset) {
    var today = new Date();
    var day = today.getDay() || 7;
    var monday = new Date(today);
    monday.setDate(today.getDate() - day + 1 + offset * 7);
    // ISO week string YYYY-WNN
    var jan4 = new Date(monday.getFullYear(), 0, 4);
    var startOfWeek1 = new Date(jan4);
    startOfWeek1.setDate(jan4.getDate() - ((jan4.getDay() || 7) - 1));
    var weekNum = Math.round((monday - startOfWeek1) / (7 * 86400000)) + 1;
    return monday.getFullYear() + '-W' + String(weekNum).padStart(2, '0');
  }

  function todayStr() {
    return new Date().toISOString().slice(0, 10);
  }

  /* ── FRIENDS tab ─────────────────────────────────────────── */

  function loadFriends() {
    api('/api/friends').then(function (list) {
      _friends = list || [];
      renderFriendsList(list || []);
    }).catch(function (err) {
      document.getElementById('friends-list').innerHTML =
        '<p class="empty-msg color-danger">Error: ' + esc(err.message) + '</p>';
    });

    api('/api/friends/requests').then(function (list) {
      renderIncomingRequests(list || []);
    }).catch(function () {});
  }

  function renderFriendsList(list) {
    var el = document.getElementById('friends-list');
    if (!list.length) {
      el.innerHTML = '<p class="empty-msg">No friends yet. Send a request above.</p>';
      return;
    }
    el.innerHTML = list.map(function (f) {
      var init = (f.username || '?').slice(0, 2).toUpperCase();
      var score = f.weekly_score != null ? ('<span class="friend-score">' + f.weekly_score + ' pts</span>') : '';
      return '<div class="friend-card">' +
        '<div class="friend-avatar">' + esc(init) + '</div>' +
        '<div class="friend-card__info">' +
          '<span class="friend-card__name">' + esc(f.username) + '</span>' +
          score +
        '</div>' +
        '<button class="btn btn-sm btn-ghost" data-remove-friend="' + f.user_id + '" title="Remove">&#x2715;</button>' +
      '</div>';
    }).join('');
    el.querySelectorAll('[data-remove-friend]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('Remove this friend?')) return;
        api('/api/friends/' + btn.dataset.removeFriend, { method: 'DELETE' })
          .then(function () { showToast('Friend removed', 'info'); loadFriends(); })
          .catch(function (e) { showToast(e.message, 'error'); });
      });
    });
  }

  function renderIncomingRequests(list) {
    var el = document.getElementById('requests-incoming');
    var card = document.getElementById('incoming-card');
    if (!list.length) {
      el.innerHTML = '<p class="empty-msg">No pending requests.</p>';
      card.style.display = 'none';
      return;
    }
    card.style.display = '';
    el.innerHTML = list.map(function (r) {
      return '<div class="request-row">' +
        '<div class="friend-avatar friend-avatar--sm">' + (r.requester_username || '?').slice(0, 2).toUpperCase() + '</div>' +
        '<span class="request-row__name">' + esc(r.requester_username) + '</span>' +
        '<button class="btn btn-sm btn-primary req-accept" data-id="' + r.connection_id + '">Accept</button>' +
        '<button class="btn btn-sm btn-outline req-decline" data-id="' + r.connection_id + '">Decline</button>' +
      '</div>';
    }).join('');
    el.querySelectorAll('.req-accept').forEach(function (btn) {
      btn.addEventListener('click', function () {
        api('/api/friends/requests/' + btn.dataset.id + '/accept', { method: 'PUT' })
          .then(function () { showToast('Friend added!', 'success'); loadFriends(); })
          .catch(function (e) { showToast(e.message, 'error'); });
      });
    });
    el.querySelectorAll('.req-decline').forEach(function (btn) {
      btn.addEventListener('click', function () {
        api('/api/friends/requests/' + btn.dataset.id + '/decline', { method: 'PUT' })
          .then(function () { showToast('Request declined', 'info'); loadFriends(); })
          .catch(function (e) { showToast(e.message, 'error'); });
      });
    });
  }

  document.getElementById('send-request-btn').addEventListener('click', function () {
    var input = document.getElementById('friend-username-input');
    var hint = document.getElementById('friend-request-hint');
    var username = input.value.trim();
    if (!username) { hint.textContent = 'Enter a username first.'; return; }
    api('/api/friends/request', { method: 'POST', body: JSON.stringify({ username: username }) })
      .then(function () {
        showToast('Request sent to ' + username + '!', 'success');
        hint.textContent = '';
        input.value = '';
        loadFriends();
      })
      .catch(function (e) { hint.textContent = e.message; });
  });

  /* ── FEED tab ────────────────────────────────────────────── */

  function loadFeedTab() {
    api('/api/social/feed/visibility').then(function (vis) {
      document.getElementById('toggle-feed-share').checked = !!vis.show_in_feed;
      document.getElementById('toggle-show-calories').checked = vis.show_calories !== false;
      document.getElementById('toggle-show-macros').checked = vis.show_macros !== false;
    }).catch(function () {});

    api('/api/social/feed').then(function (list) {
      renderFriendFeed(list || []);
    }).catch(function (err) {
      document.getElementById('friend-feed-list').innerHTML =
        '<p class="empty-msg">Error loading feed: ' + esc(err.message) + '</p>';
    });
  }

  function renderFriendFeed(list) {
    var el = document.getElementById('friend-feed-list');
    if (!list.length) {
      el.innerHTML = '<p class="empty-msg">No friends have sharing enabled yet.</p>';
      return;
    }
    el.innerHTML = list.map(function (card) {
      var macroRow = '';
      if (card.protein_pct != null) {
        macroRow = '<div class="feed-macro-row">' +
          '<span class="macro-tag macro-tag--protein">P ' + card.protein_pct + '%</span>' +
          '<span class="macro-tag macro-tag--fat">F ' + card.fat_pct + '%</span>' +
          '<span class="macro-tag macro-tag--carbs">C ' + card.carbs_pct + '%</span>' +
        '</div>';
      }
      var calRow = card.calories_consumed != null
        ? '<p class="feed-cal">' + fmt(card.calories_consumed) +
          (card.calories_target ? ' / ' + fmt(card.calories_target) : '') + ' kcal</p>'
        : '<p class="feed-cal color-muted">Calories private</p>';
      var bigWin = card.big_win ? '<span class="feed-big-win">🎯 ' + esc(card.big_win) + ' on track</span>' : '';
      var badges = (card.badges_today || []).map(function (b) {
        return '<span class="feed-badge-pill">' + esc(b) + '</span>';
      }).join('');
      return '<div class="feed-card">' +
        '<div class="feed-card__header">' +
          '<div class="friend-avatar friend-avatar--sm">' + (card.username || '?').slice(0, 2).toUpperCase() + '</div>' +
          '<strong>' + esc(card.username) + '</strong>' +
          bigWin +
        '</div>' +
        calRow + macroRow +
        (badges ? '<div class="feed-badges">' + badges + '</div>' : '') +
      '</div>';
    }).join('');
  }

  document.getElementById('save-visibility-btn').addEventListener('click', function () {
    var body = {
      show_in_feed: document.getElementById('toggle-feed-share').checked,
      show_calories: document.getElementById('toggle-show-calories').checked,
      show_macros: document.getElementById('toggle-show-macros').checked,
    };
    api('/api/social/feed/visibility', { method: 'PUT', body: JSON.stringify(body) })
      .then(function () { showToast('Sharing settings saved', 'success'); })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  /* Share a food entry */
  var shareDatePicker = document.getElementById('share-date-picker');
  shareDatePicker.value = todayStr();

  document.getElementById('load-share-entries-btn').addEventListener('click', function () {
    var d = shareDatePicker.value;
    if (!d) { showToast('Pick a date', 'error'); return; }
    api('/api/entries?date=' + d).then(function (entries) {
      var listEl = document.getElementById('share-entries-list');
      var panelEl = document.getElementById('share-friends-panel');
      if (!entries || !entries.length) {
        listEl.innerHTML = '<p class="empty-msg">No entries for that date.</p>';
        listEl.hidden = false;
        panelEl.hidden = true;
        return;
      }
      listEl.hidden = false;
      listEl.innerHTML = '<p class="form-label" style="margin-bottom:0.4rem">Select entries:</p>' +
        entries.map(function (e) {
          return '<label class="share-entry-row">' +
            '<input type="checkbox" class="share-entry-cb" value="' + e.id + '" />' +
            '<span class="share-entry-row__name">' + esc(e.food_name) + '</span>' +
            '<span class="share-entry-row__meta">' + fmt(e.calories) + ' kcal</span>' +
          '</label>';
        }).join('');
      panelEl.hidden = false;
      var cbWrap = document.getElementById('share-friends-checkboxes');
      if (!_friends.length) {
        cbWrap.innerHTML = '<p class="empty-msg">No friends yet.</p>';
      } else {
        cbWrap.innerHTML = _friends.map(function (f) {
          return '<label class="share-friend-label">' +
            '<input type="checkbox" class="share-friend-cb" value="' + f.user_id + '" />' +
            '<span>' + esc(f.username) + '</span>' +
          '</label>';
        }).join('');
      }
    }).catch(function (e) { showToast(e.message, 'error'); });
  });

  document.getElementById('share-submit-btn').addEventListener('click', function () {
    var entryIds = Array.from(document.querySelectorAll('.share-entry-cb:checked')).map(function (cb) { return parseInt(cb.value); });
    var friendIds = Array.from(document.querySelectorAll('.share-friend-cb:checked')).map(function (cb) { return parseInt(cb.value); });
    if (!entryIds.length) { showToast('Select at least one entry', 'error'); return; }
    if (!friendIds.length) { showToast('Select at least one friend', 'error'); return; }

    var promises = entryIds.map(function (eid) {
      return api('/api/shared', { method: 'POST', body: JSON.stringify({ entry_id: eid, friend_ids: friendIds }) });
    });
    Promise.all(promises)
      .then(function () { showToast('Shared!', 'success'); document.getElementById('share-entries-list').hidden = true; document.getElementById('share-friends-panel').hidden = true; })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  /* ── RACE tab ────────────────────────────────────────────── */

  function loadRaceTab() {
    document.getElementById('race-week-label').textContent = isoWeekLabel(_raceWeekOffset);
    document.getElementById('race-next-week').disabled = _raceWeekOffset >= 0;

    // Today's score
    api('/api/game/score').then(function (data) {
      document.getElementById('race-today-score').textContent = data.score || 0;
      var bd = data.breakdown || {};
      var items = [
        { label: 'Protein', pts: bd.protein_pts || 0 },
        { label: 'Fat', pts: bd.fat_pts || 0 },
        { label: 'Carbs', pts: bd.carbs_pts || 0 },
        { label: 'Calories', pts: bd.calories_pts || 0 },
        { label: 'Water', pts: bd.water_bonus || 0 },
        { label: 'Note', pts: bd.note_bonus || 0 },
      ];
      document.getElementById('race-today-breakdown').innerHTML = items.map(function (it) {
        return '<span class="race-bd-item ' + (it.pts > 0 ? 'race-bd-item--hit' : '') + '">' +
          esc(it.label) + ' +' + it.pts + '</span>';
      }).join('');
    }).catch(function () {});

    // Leaderboard
    var wkParam = _raceWeekOffset !== 0 ? '?week=' + weekParam(_raceWeekOffset) : '';
    api('/api/game/leaderboard' + wkParam).then(function (data) {
      renderLeaderboard(data);
      renderDayBars(data);
    }).catch(function (err) {
      document.getElementById('leaderboard-list').innerHTML =
        '<p class="empty-msg">Error: ' + esc(err.message) + '</p>';
    });
  }

  function renderLeaderboard(data) {
    var el = document.getElementById('leaderboard-list');
    var scores = data.scores || [];
    if (!scores.length) {
      el.innerHTML = '<p class="empty-msg">No participants yet.</p>';
      return;
    }
    el.innerHTML = scores.map(function (s, i) {
      var medal = ['🥇', '🥈', '🥉'][i] || (i + 1 + '.');
      var isMe = s.is_me ? ' leaderboard-row--me' : '';
      var badges = (s.badges || []).slice(0, 3).map(function (b) {
        return '<span class="race-badge-pill">' + esc(b.replace(/_/g, ' ')) + '</span>';
      }).join('');
      return '<div class="leaderboard-row' + isMe + '">' +
        '<span class="leaderboard-rank">' + medal + '</span>' +
        '<div class="friend-avatar friend-avatar--sm">' + (s.username || '?').slice(0, 2).toUpperCase() + '</div>' +
        '<span class="leaderboard-name">' + esc(s.username) + (s.is_me ? ' (you)' : '') + '</span>' +
        badges +
        '<span class="leaderboard-score">' + (s.weekly_score || 0) + ' pts</span>' +
      '</div>';
    }).join('');
  }

  function renderDayBars(data) {
    var myData = (data.scores || []).find(function (s) { return s.is_me; });
    if (!myData) return;
    var days = myData.daily_scores || [];
    var labels = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
    document.getElementById('race-day-bars').innerHTML = days.map(function (score, i) {
      var h = Math.round(score / 115 * 48);
      return '<div class="race-day-col">' +
        '<div class="race-day-bar-wrap2">' +
          '<div class="race-day-bar" style="height:' + h + 'px" title="' + score + ' pts"></div>' +
        '</div>' +
        '<span class="race-day-label">' + (labels[i] || '') + '</span>' +
      '</div>';
    }).join('');
  }

  document.getElementById('race-prev-week').addEventListener('click', function () {
    _raceWeekOffset--;
    loadRaceTab();
  });
  document.getElementById('race-next-week').addEventListener('click', function () {
    if (_raceWeekOffset < 0) { _raceWeekOffset++; loadRaceTab(); }
  });

  /* ── BADGES tab ──────────────────────────────────────────── */

  var BADGE_INFO = {
    streak_7:       { icon: '🔥', label: '7-Day Streak', desc: 'Logged food 7 days in a row' },
    perfect_week:   { icon: '⭐', label: 'Perfect Week', desc: 'Hit all macro targets every day this week' },
    protein_king:   { icon: '💪', label: 'Protein King', desc: 'Hit protein target 5 days in a row' },
    hydration_hero: { icon: '💧', label: 'Hydration Hero', desc: 'Hit water goal 3 days in a row' },
    early_bird:     { icon: '🌅', label: 'Early Bird', desc: 'Logged breakfast before 8am for 3 days' },
    consistent:     { icon: '📅', label: 'Consistent', desc: 'Logged food on 30 total days' },
    '7_day_streak':  { icon: '🔥', label: '7-Day Streak', desc: 'Logged food 7 days in a row' },
    consistent_30:  { icon: '📅', label: 'Consistent', desc: 'Logged food every day for 30 days' },
  };

  function loadBadgesTab() {
    api('/api/social/badges').then(function (list) {
      var el = document.getElementById('badges-grid');
      if (!list.length) {
        el.innerHTML = '<p class="empty-msg">No badges earned yet. Keep logging to earn them!</p>';
        return;
      }
      el.innerHTML = list.map(function (b) {
        var info = BADGE_INFO[b.badge_key] || { icon: '🏅', label: b.badge_key.replace(/_/g, ' '), desc: b.description || '' };
        var date = b.earned_at ? b.earned_at.slice(0, 10) : '';
        return '<div class="badge-card">' +
          '<div class="badge-card__icon">' + info.icon + '</div>' +
          '<div class="badge-card__info">' +
            '<strong>' + esc(info.label) + '</strong>' +
            '<p class="badge-card__desc">' + esc(info.desc) + '</p>' +
            (date ? '<p class="badge-card__date color-muted">Earned ' + esc(date) + '</p>' : '') +
          '</div>' +
        '</div>';
      }).join('');
    }).catch(function (err) {
      document.getElementById('badges-grid').innerHTML =
        '<p class="empty-msg">Error loading badges: ' + esc(err.message) + '</p>';
    });
  }

  /* ── Tab-switch lazy loading ─────────────────────────────── */
  document.querySelectorAll('.social-tab').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var tab = btn.dataset.tab;
      if (tab === 'feed') loadFeedTab();
      else if (tab === 'race') loadRaceTab();
      else if (tab === 'badges') loadBadgesTab();
    });
  });

  /* ── Boot ────────────────────────────────────────────────── */
  initTabs();
  loadFriends();
})();
