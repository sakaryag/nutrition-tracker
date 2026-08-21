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

/* ============================================================
   Dietitian – Tab switching
   ============================================================ */

(function () {
  'use strict';

  document.querySelectorAll('.dietitian-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.dietitian-tab').forEach(function (t) { t.classList.remove('active'); });
      document.querySelectorAll('.dietitian-panel').forEach(function (p) { p.classList.remove('active'); });
      tab.classList.add('active');
      var panelId = 'dietitian-panel-' + tab.dataset.dtab;
      var panel = document.getElementById(panelId);
      if (panel) panel.classList.add('active');
      if (tab.dataset.dtab === 'builder') initBuilderOnce();
    });
  });
})();

/* ============================================================
   Dietitian – Plan Builder
   Calls /api/admin/* — requires admin or dietitian access.
   ============================================================ */

(function () {
  'use strict';

  var activePlanId = null;
  var activeDayId  = null;
  var dtPlans = [];
  var dtExchangeCategories = [];
  var _builderInitialized = false;

  function initBuilderOnce() {
    if (_builderInitialized) return;
    _builderInitialized = true;
    loadDtPlans();
  }

  function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ── Plan list ──────────────────────────────────────────── */

  function loadDtPlans() {
    document.getElementById('dt-plans-list').innerHTML = '<p class="empty-msg">Loading&hellip;</p>';
    api('/api/admin/plans').then(function (plans) {
      dtPlans = plans;
      renderDtPlanList(plans);
    }).catch(function (e) {
      document.getElementById('dt-plans-list').innerHTML =
        '<p class="empty-msg" style="color:var(--color-danger)">' + esc(e.message) + '</p>';
    });
  }

  function renderDtPlanList(plans) {
    var el = document.getElementById('dt-plans-list');
    if (!plans.length) {
      el.innerHTML = '<p class="empty-msg">No plans yet. Click &ldquo;+ New Plan&rdquo; to create one.</p>';
      return;
    }
    el.innerHTML = plans.map(function (p) {
      var statusBadge = '<span class="badge badge--' + esc(p.status || 'draft') + '">' + esc(p.status || 'draft') + '</span>';
      var tplBadge = p.is_template ? '<span class="badge" style="background:var(--color-primary);color:#fff">Template</span>' : '';
      return '<div class="card dt-plan-card">' +
        '<div style="flex:1;min-width:0">' +
          '<div class="dt-plan-card-name">' + esc(p.name) + '</div>' +
          '<div class="dt-plan-card-meta">' + statusBadge + ' ' + tplBadge + ' &nbsp;' + (p.duration_days || 7) + ' days</div>' +
          (p.description ? '<div style="font-size:.82rem;color:var(--color-text-muted);margin-top:.25rem">' + esc(p.description) + '</div>' : '') +
        '</div>' +
        '<div class="dt-plan-card-actions">' +
          '<button class="btn btn-sm btn-primary dt-build-btn" data-id="' + p.id + '">Build</button>' +
          '<button class="btn btn-sm btn-outline dt-edit-plan-btn" data-id="' + p.id + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger dt-delete-plan-btn" data-id="' + p.id + '">&times;</button>' +
        '</div>' +
      '</div>';
    }).join('');

    el.querySelectorAll('.dt-build-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { openDtBuilder(parseInt(btn.dataset.id, 10)); });
    });
    el.querySelectorAll('.dt-edit-plan-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var p = dtPlans.find(function (x) { return x.id === parseInt(btn.dataset.id, 10); });
        openDtPlanModal(p || null);
      });
    });
    el.querySelectorAll('.dt-delete-plan-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('Delete this plan?')) return;
        api('/api/admin/plans/' + btn.dataset.id, { method: 'DELETE' })
          .then(function () { showToast('Deleted', 'success'); loadDtPlans(); })
          .catch(function (e) { showToast(e.message, 'error'); });
      });
    });
  }

  /* Create-plan button */
  document.getElementById('dt-create-plan-btn').addEventListener('click', function () { openDtPlanModal(null); });

  /* ── Plan modal ─────────────────────────────────────────── */
  var dtPlanModal = document.getElementById('dt-plan-modal');
  document.getElementById('dt-plan-cancel').addEventListener('click', function () { dtPlanModal.close(); });

  function openDtPlanModal(plan) {
    document.getElementById('dt-plan-id').value = plan ? plan.id : '';
    document.getElementById('dt-plan-modal-title').textContent = plan ? 'Edit Plan' : 'Create Plan';
    document.getElementById('dt-plan-name').value = plan ? (plan.name || '') : '';
    document.getElementById('dt-plan-name-tr').value = plan ? (plan.name_tr || '') : '';
    document.getElementById('dt-plan-desc').value = plan ? (plan.description || '') : '';
    document.getElementById('dt-plan-duration').value = plan ? (plan.duration_days || 7) : 7;
    document.getElementById('dt-plan-status').value = plan ? (plan.status || 'draft') : 'draft';
    document.getElementById('dt-plan-is-template').checked = plan ? !!plan.is_template : false;
    dtPlanModal.showModal();
  }

  document.getElementById('dt-plan-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var id = document.getElementById('dt-plan-id').value;
    var payload = {
      name: document.getElementById('dt-plan-name').value.trim(),
      name_tr: document.getElementById('dt-plan-name-tr').value.trim() || null,
      description: document.getElementById('dt-plan-desc').value.trim() || null,
      duration_days: parseInt(document.getElementById('dt-plan-duration').value, 10) || 7,
      status: document.getElementById('dt-plan-status').value,
      is_template: document.getElementById('dt-plan-is-template').checked,
    };
    var method = id ? 'PUT' : 'POST';
    var url = id ? '/api/admin/plans/' + id : '/api/admin/plans';
    api(url, { method: method, body: JSON.stringify(payload) })
      .then(function () { dtPlanModal.close(); loadDtPlans(); showToast('Plan saved', 'success'); })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  /* ── Builder workspace ──────────────────────────────────── */

  function openDtBuilder(planId) {
    activePlanId = planId;
    var plan = dtPlans.find(function (x) { return x.id === planId; });
    document.getElementById('dt-plan-list-view').hidden = true;
    document.getElementById('dt-builder-workspace').hidden = false;
    document.getElementById('dt-builder-plan-name').textContent = plan ? plan.name : 'Plan #' + planId;
    document.getElementById('dt-builder-plan-status').textContent = plan ? (plan.status || 'draft') : '';
    loadDtCategories();
    loadDtDays();
  }

  document.getElementById('dt-back-btn').addEventListener('click', function () {
    document.getElementById('dt-builder-workspace').hidden = true;
    document.getElementById('dt-plan-list-view').hidden = false;
    activePlanId = null;
    activeDayId = null;
    loadDtPlans();
  });

  document.getElementById('dt-promote-tpl-btn').addEventListener('click', function () {
    if (!activePlanId) return;
    api('/api/admin/plans/' + activePlanId + '/promote-template', { method: 'POST' })
      .then(function () { showToast('Promoted to template', 'success'); loadDtPlans(); })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  document.getElementById('dt-clone-plan-btn').addEventListener('click', function () {
    if (!activePlanId || !confirm('Clone this plan?')) return;
    api('/api/admin/plans/' + activePlanId + '/clone', { method: 'POST' })
      .then(function (p) {
        showToast('Cloned: ' + p.name, 'success');
        loadDtPlans();
        document.getElementById('dt-builder-workspace').hidden = true;
        document.getElementById('dt-plan-list-view').hidden = false;
      })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  document.getElementById('dt-copy-remaining-btn').addEventListener('click', function () {
    if (!activeDayId || !confirm('Copy this day\'s slots to all empty days?')) return;
    api('/api/admin/days/' + activeDayId + '/copy-to-remaining', { method: 'POST' })
      .then(function () { showToast('Copied', 'success'); loadDtDays(); })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  document.getElementById('dt-add-day-btn').addEventListener('click', function () { openDtDayModal(null, null); });

  /* ── Days ───────────────────────────────────────────────── */

  function loadDtDays() {
    api('/api/admin/plans/' + activePlanId + '/days').then(function (days) {
      renderDtDayNav(days);
      if (days.length) selectDtDay(days[0]);
      else document.getElementById('dt-day-editor').innerHTML = '<p class="empty-msg">No days yet. Click + Add Day.</p>';
    }).catch(function (e) { showToast(e.message, 'error'); });
  }

  function renderDtDayNav(days) {
    var nav = document.getElementById('dt-day-nav');
    nav.innerHTML = days.map(function (d) {
      var label = 'Day ' + (d.day_offset + 1) + (d.label ? ': ' + esc(d.label) : '');
      return '<button class="btn btn-sm btn-outline dt-day-nav-btn" data-id="' + d.id + '" data-json="' +
        encodeURIComponent(JSON.stringify(d)) + '">' + label + '</button>';
    }).join('');
    nav.querySelectorAll('.dt-day-nav-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        nav.querySelectorAll('.dt-day-nav-btn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        selectDtDay(JSON.parse(decodeURIComponent(btn.dataset.json)));
      });
    });
    if (days.length) {
      var first = nav.querySelector('.dt-day-nav-btn');
      if (first) first.classList.add('active');
    }
  }

  function selectDtDay(day) {
    activeDayId = day.id;
    loadDtSlots(day);
  }

  /* ── Day modal ──────────────────────────────────────────── */
  var dtDayModal = document.getElementById('dt-day-modal');
  document.getElementById('dt-day-cancel').addEventListener('click', function () { dtDayModal.close(); });

  function openDtDayModal(id, day) {
    document.getElementById('dt-day-id').value = id || '';
    document.getElementById('dt-day-modal-title').textContent = id ? 'Edit Day' : 'Add Day';
    document.getElementById('dt-day-label').value = day ? (day.label || '') : '';
    document.getElementById('dt-day-notes').value = day ? (day.notes || '') : '';
    dtDayModal.showModal();
  }

  document.getElementById('dt-day-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var id = document.getElementById('dt-day-id').value;
    var payload = {
      label: document.getElementById('dt-day-label').value.trim() || null,
      notes: document.getElementById('dt-day-notes').value.trim() || null,
    };
    var url = id ? '/api/admin/days/' + id : '/api/admin/plans/' + activePlanId + '/days';
    api(url, { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) })
      .then(function () { dtDayModal.close(); loadDtDays(); showToast('Day saved', 'success'); })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  /* ── Slots ──────────────────────────────────────────────── */

  function loadDtSlots(day) {
    api('/api/admin/days/' + day.id + '/slots').then(function (slots) {
      renderDtDayEditor(day, slots);
    }).catch(function (e) { showToast(e.message, 'error'); });
  }

  function renderDtDayEditor(day, slots) {
    var ed = document.getElementById('dt-day-editor');
    var hdr = '<div class="day-editor-header">' +
      '<h3 style="font-size:1rem;font-weight:700">Day ' + (day.day_offset + 1) + (day.label ? ': ' + esc(day.label) : '') + '</h3>' +
      '<div class="day-editor-actions">' +
        '<button class="btn btn-sm btn-outline" id="dt-de-edit-day">Edit Day</button>' +
        '<button class="btn btn-sm btn-danger" id="dt-de-delete-day">Delete Day</button>' +
      '</div></div>';

    var sHtml = slots.map(function (s) {
      return '<div class="slot-card" data-slot-id="' + s.id + '">' +
        '<div class="slot-card-header">' +
          '<strong>' + esc(s.slot_name) + '</strong>' +
          (s.content_pattern ? ' <span class="badge">Pattern ' + esc(s.content_pattern) + '</span>' : '') +
          (s.is_optional ? ' <span class="badge badge--muted">optional</span>' : '') +
          '<div class="slot-actions">' +
            '<button class="btn btn-sm btn-outline dt-slot-add-item" data-slot-id="' + s.id + '">+ Item</button>' +
            '<button class="btn btn-sm btn-outline dt-slot-edit" data-slot-id="' + s.id + '" data-json="' + encodeURIComponent(JSON.stringify(s)) + '">Edit</button>' +
            '<button class="btn btn-sm btn-danger dt-slot-delete" data-slot-id="' + s.id + '">&times;</button>' +
          '</div>' +
        '</div>' +
        '<div class="slot-items" id="dt-slot-items-' + s.id + '">' + renderDtItems(s.items || []) + '</div>' +
      '</div>';
    }).join('');

    ed.innerHTML = hdr + (sHtml || '<p class="empty-msg" style="padding:.5rem">No meal slots yet.</p>') +
      '<button class="btn btn-outline btn-sm" id="dt-de-add-slot" style="margin-top:.75rem">+ Add Slot</button>';

    ed.querySelector('#dt-de-edit-day').addEventListener('click', function () { openDtDayModal(day.id, day); });
    ed.querySelector('#dt-de-delete-day').addEventListener('click', function () {
      if (!confirm('Delete Day ' + (day.day_offset + 1) + '?')) return;
      api('/api/admin/days/' + day.id, { method: 'DELETE' })
        .then(function () { showToast('Deleted', 'success'); loadDtDays(); })
        .catch(function (e) { showToast(e.message, 'error'); });
    });
    ed.querySelector('#dt-de-add-slot').addEventListener('click', function () { openDtSlotModal(null, day.id, null); });
    ed.querySelectorAll('.dt-slot-add-item').forEach(function (btn) {
      btn.addEventListener('click', function () { openDtItemModal(null, btn.dataset.slotId, null); });
    });
    ed.querySelectorAll('.dt-slot-edit').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openDtSlotModal(btn.dataset.slotId, day.id, JSON.parse(decodeURIComponent(btn.dataset.json)));
      });
    });
    ed.querySelectorAll('.dt-slot-delete').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('Delete slot?')) return;
        api('/api/admin/slots/' + btn.dataset.slotId, { method: 'DELETE' })
          .then(function () { loadDtSlots(day); showToast('Deleted', 'success'); })
          .catch(function (e) { showToast(e.message, 'error'); });
      });
    });
    ed.querySelectorAll('.dt-item-edit').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openDtItemModal(btn.dataset.itemId, btn.dataset.slotId, JSON.parse(decodeURIComponent(btn.dataset.json)));
      });
    });
    ed.querySelectorAll('.dt-item-delete').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('Delete item?')) return;
        api('/api/admin/slot-items/' + btn.dataset.itemId, { method: 'DELETE' })
          .then(function () { loadDtSlots(day); showToast('Deleted', 'success'); })
          .catch(function (e) { showToast(e.message, 'error'); });
      });
    });
  }

  function renderDtItems(items) {
    if (!items.length) return '<p class="empty-msg" style="font-size:.85em;padding:.5rem">No items. Add one with &ldquo;+ Item&rdquo;.</p>';
    return items.map(function (it) {
      var label = it.food_name_override || (it.saved_food && it.saved_food.name) || 'item #' + it.id;
      return '<div class="slot-item-row">' +
        '<span>' + esc(label) + (it.quantity ? ' &mdash; ' + it.quantity + ' ' + (it.unit || 'g') : '') +
          (it.alternative_group ? ' <small>[grp ' + esc(String(it.alternative_group)) + ']</small>' : '') + '</span>' +
        '<div>' +
          '<button class="btn btn-sm btn-outline dt-item-edit" data-item-id="' + it.id + '" data-slot-id="' + it.slot_id + '" data-json="' + encodeURIComponent(JSON.stringify(it)) + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger dt-item-delete" data-item-id="' + it.id + '">&times;</button>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* ── Slot modal ─────────────────────────────────────────── */
  var dtSlotModal = document.getElementById('dt-slot-modal');
  document.getElementById('dt-slot-cancel').addEventListener('click', function () { dtSlotModal.close(); });

  function openDtSlotModal(id, dayId, slot) {
    document.getElementById('dt-slot-id').value = id || '';
    document.getElementById('dt-slot-day-id').value = dayId;
    document.getElementById('dt-slot-modal-title').textContent = id ? 'Edit Slot' : 'Add Meal Slot';
    document.getElementById('dt-slot-name').value = slot ? (slot.slot_name || '') : '';
    document.getElementById('dt-slot-pattern').value = slot ? (slot.content_pattern || 'A') : 'A';
    document.getElementById('dt-slot-optional').checked = slot ? !!slot.is_optional : false;
    dtSlotModal.showModal();
  }

  document.getElementById('dt-slot-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var id = document.getElementById('dt-slot-id').value;
    var dayId = document.getElementById('dt-slot-day-id').value;
    var payload = {
      slot_name: document.getElementById('dt-slot-name').value.trim(),
      content_pattern: document.getElementById('dt-slot-pattern').value,
      is_optional: document.getElementById('dt-slot-optional').checked,
    };
    var url = id ? '/api/admin/slots/' + id : '/api/admin/days/' + dayId + '/slots';
    api(url, { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) }).then(function () {
      dtSlotModal.close();
      api('/api/admin/plans/' + activePlanId + '/days').then(function (days) {
        var day = days.find(function (d) { return d.id === parseInt(activeDayId, 10); }) || days[0];
        if (day) loadDtSlots(day);
      });
      showToast('Slot saved', 'success');
    }).catch(function (e) { showToast(e.message, 'error'); });
  });

  /* ── Item modal ─────────────────────────────────────────── */
  var dtItemModal = document.getElementById('dt-item-modal');
  document.getElementById('dt-item-cancel').addEventListener('click', function () { dtItemModal.close(); });

  document.getElementById('dt-item-type').addEventListener('change', function () {
    var v = this.value;
    document.getElementById('dt-item-food-row').classList.toggle('item-row-hidden', v !== 'food');
    document.getElementById('dt-item-exchange-row').classList.toggle('item-row-hidden', v !== 'exchange');
    document.getElementById('dt-item-freetext-row').classList.toggle('item-row-hidden', v !== 'freetext');
  });

  function loadDtCategories() {
    api('/api/exchange-categories').then(function (cats) {
      dtExchangeCategories = cats || [];
    }).catch(function () { dtExchangeCategories = []; });
  }

  function openDtItemModal(id, slotId, item) {
    document.getElementById('dt-item-id').value = id || '';
    document.getElementById('dt-item-slot-id').value = slotId;
    document.getElementById('dt-item-modal-title').textContent = id ? 'Edit Item' : 'Add Item';

    var type = 'food';
    if (item && item.exchange_category_id) type = 'exchange';
    else if (item && !item.saved_food_id) type = 'freetext';
    document.getElementById('dt-item-type').value = type;
    document.getElementById('dt-item-food-row').classList.toggle('item-row-hidden', type !== 'food');
    document.getElementById('dt-item-exchange-row').classList.toggle('item-row-hidden', type !== 'exchange');
    document.getElementById('dt-item-freetext-row').classList.toggle('item-row-hidden', type !== 'freetext');

    document.getElementById('dt-item-food-id').value = item ? (item.saved_food_id || '') : '';
    document.getElementById('dt-item-food-name-display').textContent =
      item && item.saved_food ? item.saved_food.name : (item && item.food_name_override ? item.food_name_override : '');
    document.getElementById('dt-item-food-search').value = '';
    document.getElementById('dt-item-food-ac').hidden = true;

    document.getElementById('dt-item-freetext').value = item ? (item.food_name_override || '') : '';
    document.getElementById('dt-item-quantity').value = item ? (item.quantity || 100) : 100;
    document.getElementById('dt-item-unit').value = item ? (item.unit || 'g') : 'g';
    document.getElementById('dt-item-alt-group').value = item ? (item.alternative_group || '') : '';
    document.getElementById('dt-item-notes').value = item ? (item.notes || '') : '';

    var exSel = document.getElementById('dt-item-exchange-select');
    exSel.innerHTML = '<option value="">&#8212; select &#8212;</option>' +
      dtExchangeCategories.map(function (c) {
        return '<option value="' + c.id + '"' + (item && item.exchange_category_id === c.id ? ' selected' : '') + '>' + esc(c.name) + '</option>';
      }).join('');

    dtItemModal.showModal();
  }

  /* Food autocomplete in item modal */
  var dtFoodAC = document.getElementById('dt-item-food-ac');
  var dtFoodTimer;
  document.getElementById('dt-item-food-search').addEventListener('input', function () {
    clearTimeout(dtFoodTimer);
    var q = this.value.trim();
    if (q.length < 2) { dtFoodAC.hidden = true; return; }
    dtFoodTimer = setTimeout(function () {
      api('/api/foods?q=' + encodeURIComponent(q) + '&limit=10').then(function (foods) {
        dtFoodAC.innerHTML = '';
        foods.forEach(function (f) {
          var li = document.createElement('li');
          li.role = 'option';
          li.textContent = f.name;
          li.addEventListener('click', function () {
            document.getElementById('dt-item-food-id').value = f.id;
            document.getElementById('dt-item-food-name-display').textContent = f.name;
            document.getElementById('dt-item-food-search').value = '';
            dtFoodAC.hidden = true;
          });
          dtFoodAC.appendChild(li);
        });
        dtFoodAC.hidden = !foods.length;
      });
    }, 250);
  });
  document.addEventListener('click', function (e) { if (dtFoodAC && !dtFoodAC.contains(e.target)) dtFoodAC.hidden = true; });

  document.getElementById('dt-item-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var id = document.getElementById('dt-item-id').value;
    var slotId = document.getElementById('dt-item-slot-id').value;
    var type = document.getElementById('dt-item-type').value;
    var freetext = document.getElementById('dt-item-freetext').value.trim();
    var payload = {
      saved_food_id: type === 'food' ? (parseInt(document.getElementById('dt-item-food-id').value, 10) || null) : null,
      exchange_category_id: type === 'exchange' ? (parseInt(document.getElementById('dt-item-exchange-select').value, 10) || null) : null,
      food_name_override: type === 'freetext' ? (freetext || null) : null,
      quantity: parseFloat(document.getElementById('dt-item-quantity').value) || null,
      unit: document.getElementById('dt-item-unit').value,
      alternative_group: document.getElementById('dt-item-alt-group').value.trim() || null,
      notes: document.getElementById('dt-item-notes').value.trim() || null,
    };
    var url = id ? '/api/admin/slot-items/' + id : '/api/admin/slots/' + slotId + '/items';
    api(url, { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) }).then(function () {
      dtItemModal.close();
      api('/api/admin/plans/' + activePlanId + '/days').then(function (days) {
        var day = days.find(function (d) { return d.id === parseInt(activeDayId, 10); }) || days[0];
        if (day) loadDtSlots(day);
      });
      showToast('Item saved', 'success');
    }).catch(function (e) { showToast(e.message, 'error'); });
  });

})();