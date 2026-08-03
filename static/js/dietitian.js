/* ============================================================
   dietitian.js — Dietitian panel: client list + data viewer
   ============================================================ */

(function () {
  'use strict';

  var state = {
    clients: [],
    currentClientId: null,
    currentDate: new Date().toISOString().slice(0, 10),
  };

  function init() {
    document.getElementById('dietitian-modal-close').addEventListener('click', closeModal);
    document.getElementById('dietitian-client-modal').addEventListener('click', function (e) {
      if (e.target === this) closeModal();
    });
    document.getElementById('client-date-picker').addEventListener('change', function () {
      state.currentDate = this.value;
      if (state.currentClientId) loadClientData(state.currentClientId);
    });
    document.getElementById('client-date-picker').value = state.currentDate;

    loadStats();
    loadClients();
  }

  function loadStats() {
    api('/api/dietitian/stats')
      .then(function (data) {
        var line = data.client_count + ' client(s) assigned';
        if (data.client_count > 0) {
          line += ' — ' + data.access_granted_count + ' have granted data access';
        }
        document.getElementById('dietitian-stats-line').textContent = line;
      })
      .catch(function () {
        document.getElementById('dietitian-stats-line').textContent = '';
      });
  }

  function loadClients() {
    api('/api/dietitian/clients')
      .then(function (clients) {
        state.clients = clients;
        renderClients();
      })
      .catch(function (err) {
        document.getElementById('dietitian-clients-list').innerHTML =
          '<p class="empty-msg">' + (err.message || 'Could not load clients.') + '</p>';
      });
  }

  function renderClients() {
    var container = document.getElementById('dietitian-clients-list');
    if (!state.clients.length) {
      container.innerHTML = '<p class="empty-msg">No clients assigned yet. Use the Admin panel to assign plans to users — they will appear here.</p>';
      return;
    }
    container.innerHTML = '';
    state.clients.forEach(function (client) {
      var card = document.createElement('div');
      card.className = 'dietitian-client-card card';
      var accessBadge = client.access_granted
        ? '<span class="badge badge--success">Access granted</span>'
        : '<span class="badge badge--muted">Awaiting consent</span>';
      card.innerHTML =
        '<div class="dietitian-client-info">' +
          '<div class="dietitian-client-name">' + escHtml(client.username) + '</div>' +
          '<div class="dietitian-client-meta">Member since ' + (client.member_since ? client.member_since.slice(0, 10) : '—') + '</div>' +
        '</div>' +
        '<div class="dietitian-client-actions">' +
          accessBadge +
          (client.access_granted
            ? '<button class="btn btn-sm btn-primary" data-uid="' + client.user_id + '">View Data</button>'
            : '<span class="form-hint" style="font-size:.8rem;">Client must enable access in their Settings</span>') +
        '</div>';
      if (client.access_granted) {
        card.querySelector('[data-uid]').addEventListener('click', function () {
          openClientModal(client);
        });
      }
      container.appendChild(card);
    });
  }

  function openClientModal(client) {
    state.currentClientId = client.user_id;
    document.getElementById('client-modal-title').textContent = client.username + "'s Data";
    document.getElementById('client-date-picker').value = state.currentDate;
    document.getElementById('dietitian-client-modal').hidden = false;
    document.body.style.overflow = 'hidden';
    loadClientData(client.user_id);
  }

  function closeModal() {
    document.getElementById('dietitian-client-modal').hidden = true;
    document.body.style.overflow = '';
    state.currentClientId = null;
  }

  function loadClientData(clientId) {
    var body = document.getElementById('client-modal-body');
    body.innerHTML = '<p class="empty-msg">Loading…</p>';
    document.getElementById('client-modal-date').textContent = formatDate(state.currentDate);

    api('/api/dietitian/clients/' + clientId + '/data?date=' + state.currentDate)
      .then(function (data) {
        renderClientData(data);
      })
      .catch(function (err) {
        body.innerHTML = '<p class="empty-msg">' + (err.message || 'Could not load data.') + '</p>';
      });
  }

  function renderClientData(data) {
    var body = document.getElementById('client-modal-body');
    var t = data.target;
    var tot = data.totals;

    var macros = ['protein', 'fat', 'carbs', 'calories'];
    var labels = { protein: 'Protein', fat: 'Fat', carbs: 'Carbs', calories: 'Calories' };
    var units  = { protein: 'g', fat: 'g', carbs: 'g', calories: 'kcal' };

    var summaryHtml = '<div class="dietitian-summary-grid">';
    macros.forEach(function (key) {
      var val = Math.round(tot[key] || 0);
      var goal = t ? Math.round(t[key] || 0) : null;
      var pct = (goal && goal > 0) ? Math.min(100, Math.round(val / goal * 100)) : null;
      summaryHtml +=
        '<div class="dietitian-macro-card">' +
          '<div class="dietitian-macro-label">' + labels[key] + '</div>' +
          '<div class="dietitian-macro-val">' + val + '<span class="dietitian-macro-unit"> ' + units[key] + '</span></div>' +
          (goal !== null ? '<div class="dietitian-macro-goal">Goal: ' + goal + ' ' + units[key] + '</div>' : '') +
          (pct !== null
            ? '<div class="progress-bar-wrap" style="margin-top:.3rem;">' +
                '<div class="progress-bar" style="width:' + pct + '%;background:' + barColor(pct) + '"></div>' +
              '</div>'
            : '') +
        '</div>';
    });
    summaryHtml += '</div>';

    var entriesHtml = '';
    if (data.entries.length === 0) {
      entriesHtml = '<p class="empty-msg" style="margin-top:1rem;">No food entries for this date.</p>';
    } else {
      entriesHtml = '<table class="admin-table" style="margin-top:1rem;"><thead><tr>' +
        '<th>Food</th><th>Protein</th><th>Fat</th><th>Carbs</th><th>Calories</th>' +
        '</tr></thead><tbody>';
      data.entries.forEach(function (e) {
        entriesHtml +=
          '<tr>' +
            '<td>' + escHtml(e.food_name || '') + (e.serving_size ? ' <small class="text-muted">(' + e.serving_size + ' ' + (e.serving_unit || 'g') + ')</small>' : '') + '</td>' +
            '<td>' + round1(e.protein) + 'g</td>' +
            '<td>' + round1(e.fat) + 'g</td>' +
            '<td>' + round1(e.carbs) + 'g</td>' +
            '<td>' + Math.round(e.calories || 0) + '</td>' +
          '</tr>';
      });
      entriesHtml += '</tbody></table>';
    }

    body.innerHTML =
      '<div class="dietitian-visit-note"><span class="badge badge--info">Visited — client has been notified</span></div>' +
      summaryHtml +
      '<h3 class="section-title" style="margin-top:1.5rem;">Food Log</h3>' +
      entriesHtml;
  }

  function barColor(pct) {
    if (pct < 70) return '#f59e0b';
    if (pct > 110) return '#ef4444';
    return '#22c55e';
  }

  function round1(v) { return v ? Math.round(v * 10) / 10 : 0; }

  function formatDate(iso) {
    var d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }

  function escHtml(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  document.addEventListener('DOMContentLoaded', init);
})();