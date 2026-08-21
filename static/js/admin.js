/* admin.js — Program Builder + User management */
'use strict';

(function () {

/* ── Shared state ─────────────────────────────────────────── */
var activePlanId = null;
var activeDayId  = null;
var plans = [];
var recipes = [];
var exchangeCategories = [];

/* ── Tab switching ────────────────────────────────────────── */
document.querySelectorAll('.admin-tab').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.admin-tab').forEach(function (b) { b.classList.remove('active'); });
    btn.classList.add('active');
    var tab = btn.dataset.tab;
    document.querySelectorAll('.admin-panel').forEach(function (p) { p.hidden = true; });
    var panel = document.getElementById('admin-tab-' + tab);
    if (panel) panel.hidden = false;
    if (tab === 'plans')     loadPlansList();
    if (tab === 'users')     loadUsers();
    if (tab === 'templates') loadTemplates();
    if (tab === 'builder' && activePlanId) openBuilder(activePlanId);
  });
});

document.querySelectorAll('.builder-tab').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.builder-tab').forEach(function (b) { b.classList.remove('active'); });
    btn.classList.add('active');
    document.querySelectorAll('.builder-panel').forEach(function (p) { p.hidden = true; });
    document.getElementById('btab-' + btn.dataset.btab).hidden = false;
    if (btn.dataset.btab === 'guidelines') loadGuidelines();
    if (btn.dataset.btab === 'quotas')     loadQuotas();
    if (btn.dataset.btab === 'versions')   loadVersions();
  });
});

/* ── Plans list ───────────────────────────────────────────── */
function loadPlansList() {
  api('/api/admin/plans').then(function (data) {
    plans = data;
    renderPlansList(data, 'admin-plans-list');
  }).catch(function (e) { showToast(e.message, 'error'); });
}

function renderPlansList(data, containerId) {
  var el = document.getElementById(containerId);
  if (!data.length) { el.innerHTML = '<p class="empty-msg">No plans yet.</p>'; return; }
  el.innerHTML = data.map(function (p) {
    return '<div class="card admin-plan-row" data-id="' + p.id + '">' +
      '<div class="card-body">' +
        '<strong>' + esc(p.name) + '</strong>' +
        ' <span class="badge badge--' + (p.status || 'draft') + '">' + (p.status || 'draft') + '</span>' +
        (p.is_template ? ' <span class="badge badge--info">template</span>' : '') +
        '<span class="card-meta"> &nbsp; ' + (p.duration_days || 0) + ' days</span>' +
      '</div>' +
      '<div class="card-actions">' +
        '<button class="btn btn-sm btn-outline plan-open-builder" data-id="' + p.id + '">Build</button>' +
        '<button class="btn btn-sm btn-outline plan-edit" data-id="' + p.id + '">Edit</button>' +
        '<button class="btn btn-sm btn-danger plan-delete" data-id="' + p.id + '">Delete</button>' +
      '</div>' +
    '</div>';
  }).join('');
}

document.getElementById('admin-plans-list').addEventListener('click', function (e) {
  var id = parseInt(e.target.dataset.id, 10);
  if (e.target.classList.contains('plan-open-builder')) openBuilderTab(id);
  else if (e.target.classList.contains('plan-edit')) openPlanModal(id);
  else if (e.target.classList.contains('plan-delete')) deletePlan(id);
});

/* ── Plan modal ───────────────────────────────────────────── */
var planModal = document.getElementById('admin-plan-modal');
var planForm  = document.getElementById('admin-plan-form');

document.getElementById('admin-create-plan-btn').addEventListener('click', function () { openPlanModal(null); });
document.getElementById('admin-plan-cancel').addEventListener('click', function () { planModal.close(); });

function openPlanModal(id) {
  document.getElementById('admin-plan-id').value = id || '';
  if (!id) {
    document.getElementById('admin-plan-modal-title').textContent = 'Create Plan';
    document.getElementById('admin-plan-name').value = '';
    document.getElementById('admin-plan-name-tr').value = '';
    document.getElementById('admin-plan-desc').value = '';
    document.getElementById('admin-plan-duration').value = 7;
    document.getElementById('admin-plan-status').value = 'draft';
    document.getElementById('admin-plan-is-template').checked = false;
  } else {
    var p = plans.find(function (x) { return x.id === id; }) || {};
    document.getElementById('admin-plan-modal-title').textContent = 'Edit Plan';
    document.getElementById('admin-plan-name').value = p.name || '';
    document.getElementById('admin-plan-name-tr').value = p.name_tr || '';
    document.getElementById('admin-plan-desc').value = p.description || '';
    document.getElementById('admin-plan-duration').value = p.duration_days || 7;
    document.getElementById('admin-plan-status').value = p.status || 'draft';
    document.getElementById('admin-plan-is-template').checked = !!p.is_template;
  }
  planModal.showModal();
}

planForm.addEventListener('submit', function (e) {
  e.preventDefault();
  var id = document.getElementById('admin-plan-id').value;
  var payload = {
    name: document.getElementById('admin-plan-name').value.trim(),
    name_tr: document.getElementById('admin-plan-name-tr').value.trim(),
    description: document.getElementById('admin-plan-desc').value.trim(),
    duration_days: parseInt(document.getElementById('admin-plan-duration').value, 10),
    status: document.getElementById('admin-plan-status').value,
    is_template: document.getElementById('admin-plan-is-template').checked,
  };
  var method = id ? 'PUT' : 'POST';
  var url = id ? '/api/admin/plans/' + id : '/api/admin/plans';
  api(url, { method: method, body: JSON.stringify(payload) })
    .then(function () { planModal.close(); loadPlansList(); showToast('Plan saved', 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

function deletePlan(id) {
  if (!confirm('Delete this plan?')) return;
  api('/api/admin/plans/' + id, { method: 'DELETE' })
    .then(function () { loadPlansList(); showToast('Deleted', 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
}

/* ── Program Builder ──────────────────────────────────────── */
function openBuilderTab(planId) {
  document.querySelectorAll('.admin-tab').forEach(function (b) { b.classList.remove('active'); });
  document.querySelector('[data-tab="builder"]').classList.add('active');
  document.querySelectorAll('.admin-panel').forEach(function (p) { p.hidden = true; });
  document.getElementById('admin-tab-builder').hidden = false;
  openBuilder(planId);
}

function openBuilder(planId) {
  activePlanId = planId;
  var plan = plans.find(function (x) { return x.id === planId; });
  document.getElementById('builder-select-prompt').hidden = true;
  document.getElementById('builder-workspace').hidden = false;
  document.getElementById('builder-plan-name').textContent = plan ? plan.name : 'Plan #' + planId;
  document.getElementById('builder-plan-status').textContent = plan ? (plan.status || 'draft') : '';
  document.querySelectorAll('.builder-panel').forEach(function (p) { p.hidden = true; });
  document.getElementById('btab-days').hidden = false;
  document.querySelectorAll('.builder-tab').forEach(function (b) { b.classList.remove('active'); });
  document.querySelector('[data-btab="days"]').classList.add('active');
  loadDays();
  loadRecipesAndCategories();
}

document.getElementById('builder-clone-plan').addEventListener('click', function () {
  if (!activePlanId || !confirm('Clone this plan?')) return;
  api('/api/admin/plans/' + activePlanId + '/clone', { method: 'POST' })
    .then(function (p) { loadPlansList(); showToast('Cloned: ' + p.name, 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

document.getElementById('builder-promote-template').addEventListener('click', function () {
  if (!activePlanId) return;
  api('/api/admin/plans/' + activePlanId + '/promote-template', { method: 'POST' })
    .then(function () { showToast('Promoted to template', 'success'); loadPlansList(); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

document.getElementById('builder-save-version').addEventListener('click', function () {
  if (!activePlanId) return;
  var summary = prompt('Version summary (optional):') || '';
  api('/api/admin/plans/' + activePlanId + '/versions', { method: 'POST', body: JSON.stringify({ change_summary: summary }) })
    .then(function () { showToast('Version saved', 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

/* ── Days ─────────────────────────────────────────────────── */
function loadDays() {
  api('/api/admin/plans/' + activePlanId + '/days').then(function (days) {
    renderDayNav(days);
    if (days.length > 0) selectDay(days[0]);
    else document.getElementById('day-editor').innerHTML = '<p class="empty-msg">No days yet. Click + Add Day.</p>';
  }).catch(function (e) { showToast(e.message, 'error'); });
}

function renderDayNav(days) {
  var nav = document.getElementById('day-nav');
  nav.innerHTML = days.map(function (d) {
    var label = 'Day ' + (d.day_offset + 1) + (d.label ? ': ' + esc(d.label) : '');
    return '<button class="btn btn-sm btn-outline day-nav-btn" data-id="' + d.id + '" data-day-json="' + encodeURIComponent(JSON.stringify(d)) + '">' + label + '</button>';
  }).join('');
}

document.getElementById('day-nav').addEventListener('click', function (e) {
  var btn = e.target.closest('.day-nav-btn');
  if (!btn) return;
  document.querySelectorAll('.day-nav-btn').forEach(function (b) { b.classList.remove('active'); });
  btn.classList.add('active');
  selectDay(JSON.parse(decodeURIComponent(btn.dataset.dayJson)));
});

function selectDay(day) {
  activeDayId = day.id;
  loadSlots(day);
}

document.getElementById('builder-add-day').addEventListener('click', function () { openDayModal(null, null); });

document.getElementById('builder-copy-to-remaining').addEventListener('click', function () {
  if (!activeDayId || !confirm('Copy this day slots to all empty days?')) return;
  api('/api/admin/days/' + activeDayId + '/copy-to-remaining', { method: 'POST' })
    .then(function () { showToast('Copied', 'success'); loadDays(); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

var dayModal = document.getElementById('day-modal');
document.getElementById('day-cancel').addEventListener('click', function () { dayModal.close(); });

function openDayModal(id, day) {
  document.getElementById('day-id').value = id || '';
  document.getElementById('day-label').value = day ? (day.label || '') : '';
  document.getElementById('day-label-tr').value = day ? (day.label_tr || '') : '';
  document.getElementById('day-notes').value = day ? (day.notes || '') : '';
  document.getElementById('day-modal-title').textContent = id ? 'Edit Day' : 'Add Day';
  dayModal.showModal();
}

document.getElementById('day-form').addEventListener('submit', function (e) {
  e.preventDefault();
  var id = document.getElementById('day-id').value;
  var payload = {
    label: document.getElementById('day-label').value.trim(),
    label_tr: document.getElementById('day-label-tr').value.trim(),
    notes: document.getElementById('day-notes').value.trim(),
  };
  var method = id ? 'PUT' : 'POST';
  var url = id ? '/api/admin/days/' + id : '/api/admin/plans/' + activePlanId + '/days';
  api(url, { method: method, body: JSON.stringify(payload) })
    .then(function () { dayModal.close(); loadDays(); showToast('Day saved', 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

/* ── Slots ────────────────────────────────────────────────── */
function loadSlots(day) {
  api('/api/admin/days/' + day.id + '/slots').then(function (slots) {
    renderDayEditor(day, slots);
  }).catch(function (e) { showToast(e.message, 'error'); });
}

function renderDayEditor(day, slots) {
  var ed = document.getElementById('day-editor');
  var hdr = '<div class="day-editor-header">' +
    '<h3>Day ' + (day.day_offset + 1) + (day.label ? ': ' + esc(day.label) : '') + '</h3>' +
    '<div class="day-editor-actions">' +
      '<button class="btn btn-sm btn-outline" id="de-edit-day">Edit Day</button>' +
      '<button class="btn btn-sm btn-danger" id="de-delete-day">Delete Day</button>' +
    '</div></div>';
  var sHtml = slots.map(function (s) {
    return '<div class="slot-card" data-slot-id="' + s.id + '">' +
      '<div class="slot-card-header">' +
        '<strong>' + esc(s.slot_name) + '</strong>' +
        (s.content_pattern ? ' <span class="badge">Pattern ' + esc(s.content_pattern) + '</span>' : '') +
        (s.is_optional ? ' <span class="badge badge--muted">optional</span>' : '') +
        '<div class="slot-actions">' +
          '<button class="btn btn-sm btn-outline slot-add-item" data-slot-id="' + s.id + '">+ Item</button>' +
          '<button class="btn btn-sm btn-outline slot-edit" data-slot-id="' + s.id + '" data-slot-json="' + encodeURIComponent(JSON.stringify(s)) + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger slot-delete" data-slot-id="' + s.id + '">Del</button>' +
        '</div>' +
      '</div>' +
      '<div class="slot-items" id="slot-items-' + s.id + '">' + renderItems(s.items || []) + '</div>' +
    '</div>';
  }).join('');
  ed.innerHTML = hdr + sHtml + '<button class="btn btn-outline btn-sm" id="de-add-slot" style="margin-top:.75rem">+ Add Slot</button>';

  document.getElementById('de-edit-day').addEventListener('click', function () { openDayModal(day.id, day); });
  document.getElementById('de-delete-day').addEventListener('click', function () {
    if (!confirm('Delete Day ' + (day.day_offset + 1) + '?')) return;
    api('/api/admin/days/' + day.id, { method: 'DELETE' })
      .then(function () { showToast('Deleted', 'success'); loadDays(); })
      .catch(function (e) { showToast(e.message, 'error'); });
  });
  document.getElementById('de-add-slot').addEventListener('click', function () { openSlotModal(null, day.id, null); });

  ed.querySelectorAll('.slot-add-item').forEach(function (btn) {
    btn.addEventListener('click', function () { openItemModal(null, btn.dataset.slotId, null); });
  });
  ed.querySelectorAll('.slot-edit').forEach(function (btn) {
    btn.addEventListener('click', function () {
      openSlotModal(btn.dataset.slotId, day.id, JSON.parse(decodeURIComponent(btn.dataset.slotJson)));
    });
  });
  ed.querySelectorAll('.slot-delete').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!confirm('Delete slot?')) return;
      api('/api/admin/slots/' + btn.dataset.slotId, { method: 'DELETE' })
        .then(function () { loadSlots(day); showToast('Deleted', 'success'); })
        .catch(function (e) { showToast(e.message, 'error'); });
    });
  });
  ed.querySelectorAll('.item-edit').forEach(function (btn) {
    btn.addEventListener('click', function () {
      openItemModal(btn.dataset.itemId, btn.dataset.slotId, JSON.parse(decodeURIComponent(btn.dataset.itemJson)));
    });
  });
  ed.querySelectorAll('.item-delete').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!confirm('Delete item?')) return;
      api('/api/admin/slot-items/' + btn.dataset.itemId, { method: 'DELETE' })
        .then(function () { loadSlots(day); showToast('Deleted', 'success'); })
        .catch(function (e) { showToast(e.message, 'error'); });
    });
  });
}

function renderItems(items) {
  if (!items.length) return '<p class="empty-msg" style="font-size:.85em;padding:.5rem">No items.</p>';
  return items.map(function (it) {
    var label = it.food_name_override || (it.saved_food && it.saved_food.name) || 'item #' + it.id;
    return '<div class="slot-item-row">' +
      '<span>' + esc(label) + ' &mdash; ' + (it.quantity || '') + ' ' + (it.unit || '') +
        (it.alternative_group ? ' [grp ' + esc(it.alternative_group) + ']' : '') + '</span>' +
      '<div>' +
        '<button class="btn btn-sm btn-outline item-edit" data-item-id="' + it.id + '" data-slot-id="' + it.slot_id + '" data-item-json="' + encodeURIComponent(JSON.stringify(it)) + '">Edit</button>' +
        '<button class="btn btn-sm btn-danger item-delete" data-item-id="' + it.id + '">&#x2715;</button>' +
      '</div>' +
    '</div>';
  }).join('');
}

/* Slot modal */
var slotModal = document.getElementById('slot-modal');
document.getElementById('slot-cancel').addEventListener('click', function () { slotModal.close(); });

function openSlotModal(id, dayId, slot) {
  document.getElementById('slot-id').value = id || '';
  document.getElementById('slot-day-id').value = dayId;
  document.getElementById('slot-name').value = slot ? (slot.slot_name || '') : '';
  document.getElementById('slot-name-tr').value = slot ? (slot.slot_name_tr || '') : '';
  document.getElementById('slot-pattern').value = slot ? (slot.content_pattern || '') : '';
  document.getElementById('slot-optional').checked = slot ? !!slot.is_optional : false;
  document.getElementById('slot-modal-title').textContent = id ? 'Edit Slot' : 'Add Slot';
  slotModal.showModal();
}

document.getElementById('slot-form').addEventListener('submit', function (e) {
  e.preventDefault();
  var id = document.getElementById('slot-id').value;
  var dayId = document.getElementById('slot-day-id').value;
  var payload = {
    slot_name: document.getElementById('slot-name').value.trim(),
    slot_name_tr: document.getElementById('slot-name-tr').value.trim(),
    content_pattern: document.getElementById('slot-pattern').value || null,
    is_optional: document.getElementById('slot-optional').checked,
  };
  var method = id ? 'PUT' : 'POST';
  var url = id ? '/api/admin/slots/' + id : '/api/admin/days/' + dayId + '/slots';
  api(url, { method: method, body: JSON.stringify(payload) }).then(function () {
    slotModal.close();
    api('/api/admin/plans/' + activePlanId + '/days').then(function (days) {
      var day = days.find(function (d) { return d.id === parseInt(activeDayId, 10); }) || days[0];
      if (day) loadSlots(day);
    });
    showToast('Slot saved', 'success');
  }).catch(function (e) { showToast(e.message, 'error'); });
});

/* Item modal */
var itemModal = document.getElementById('item-modal');
document.getElementById('item-cancel').addEventListener('click', function () { itemModal.close(); });

document.getElementById('item-type').addEventListener('change', function () {
  var v = this.value;
  document.getElementById('item-food-row').hidden = v !== 'food';
  document.getElementById('item-recipe-row').hidden = v !== 'recipe';
  document.getElementById('item-exchange-row').hidden = v !== 'exchange';
});

function openItemModal(id, slotId, item) {
  document.getElementById('item-id').value = id || '';
  document.getElementById('item-slot-id').value = slotId;
  document.getElementById('item-modal-title').textContent = id ? 'Edit Item' : 'Add Item';
  var type = 'food';
  if (item && item.recipe_id) type = 'recipe';
  else if (item && item.exchange_category_id) type = 'exchange';
  document.getElementById('item-type').value = type;
  document.getElementById('item-food-row').hidden = type !== 'food';
  document.getElementById('item-recipe-row').hidden = type !== 'recipe';
  document.getElementById('item-exchange-row').hidden = type !== 'exchange';
  document.getElementById('item-food-id').value = item ? (item.saved_food_id || '') : '';
  document.getElementById('item-food-name-display').textContent = item && item.saved_food ? item.saved_food.name : (item && item.food_name_override ? item.food_name_override : '');
  document.getElementById('item-food-search').value = '';
  document.getElementById('item-food-ac').hidden = true;
  document.getElementById('item-quantity').value = item ? (item.quantity || 100) : 100;
  document.getElementById('item-unit').value = item ? (item.unit || 'g') : 'g';
  document.getElementById('item-alt-group').value = item ? (item.alternative_group || '') : '';
  document.getElementById('item-notes').value = item ? (item.notes || '') : '';
  var recSel = document.getElementById('item-recipe-select');
  recSel.innerHTML = '<option value="">— select —</option>' +
    recipes.map(function (r) { return '<option value="' + r.id + '"' + (item && item.recipe_id === r.id ? ' selected' : '') + '>' + esc(r.name) + '</option>'; }).join('');
  var exSel = document.getElementById('item-exchange-select');
  exSel.innerHTML = '<option value="">— select —</option>' +
    exchangeCategories.map(function (c) { return '<option value="' + c.id + '"' + (item && item.exchange_category_id === c.id ? ' selected' : '') + '>' + esc(c.name) + '</option>'; }).join('');
  itemModal.showModal();
}

var itemFoodAC = document.getElementById('item-food-ac');
var itemFoodTimer;
document.getElementById('item-food-search').addEventListener('input', function () {
  clearTimeout(itemFoodTimer);
  var q = this.value.trim();
  if (q.length < 2) { itemFoodAC.hidden = true; return; }
  itemFoodTimer = setTimeout(function () {
    api('/api/foods?q=' + encodeURIComponent(q) + '&limit=10').then(function (data) {
      itemFoodAC.innerHTML = '';
      data.forEach(function (f) {
        var li = document.createElement('li'); li.role = 'option'; li.textContent = f.name;
        li.addEventListener('click', function () {
          document.getElementById('item-food-id').value = f.id;
          document.getElementById('item-food-name-display').textContent = f.name;
          document.getElementById('item-food-search').value = '';
          itemFoodAC.hidden = true;
        });
        itemFoodAC.appendChild(li);
      });
      itemFoodAC.hidden = !data.length;
    });
  }, 250);
});
document.addEventListener('click', function (e) { if (!itemFoodAC.contains(e.target)) itemFoodAC.hidden = true; });

document.getElementById('item-form').addEventListener('submit', function (e) {
  e.preventDefault();
  var id = document.getElementById('item-id').value;
  var slotId = document.getElementById('item-slot-id').value;
  var type = document.getElementById('item-type').value;
  var payload = {
    quantity: parseFloat(document.getElementById('item-quantity').value) || null,
    unit: document.getElementById('item-unit').value,
    alternative_group: document.getElementById('item-alt-group').value.trim() || null,
    notes: document.getElementById('item-notes').value.trim() || null,
    saved_food_id: type === 'food' ? (parseInt(document.getElementById('item-food-id').value, 10) || null) : null,
    recipe_id: type === 'recipe' ? (parseInt(document.getElementById('item-recipe-select').value, 10) || null) : null,
    exchange_category_id: type === 'exchange' ? (parseInt(document.getElementById('item-exchange-select').value, 10) || null) : null,
  };
  var method = id ? 'PUT' : 'POST';
  var url = id ? '/api/admin/slot-items/' + id : '/api/admin/slots/' + slotId + '/items';
  api(url, { method: method, body: JSON.stringify(payload) }).then(function () {
    itemModal.close();
    api('/api/admin/plans/' + activePlanId + '/days').then(function (days) {
      var day = days.find(function (d) { return d.id === parseInt(activeDayId, 10); }) || days[0];
      if (day) loadSlots(day);
    });
    showToast('Item saved', 'success');
  }).catch(function (e) { showToast(e.message, 'error'); });
});

/* ── Guidelines ───────────────────────────────────────────── */
var glModal = document.getElementById('gl-modal');
document.getElementById('gl-cancel').addEventListener('click', function () { glModal.close(); });
document.getElementById('gl-add-btn').addEventListener('click', function () { openGlModal(null, null); });

function openGlModal(id, gl) {
  document.getElementById('gl-id').value = id || '';
  document.getElementById('gl-type').value = gl ? (gl.guideline_type || 'general') : 'general';
  document.getElementById('gl-text').value = gl ? (gl.rule_text || '') : '';
  document.getElementById('gl-text-tr').value = gl ? (gl.rule_text_tr || '') : '';
  glModal.showModal();
}

function loadGuidelines() {
  if (!activePlanId) return;
  api('/api/admin/plans/' + activePlanId + '/guidelines').then(function (data) {
    var el = document.getElementById('gl-list');
    el.innerHTML = data.map(function (g) {
      return '<div class="card" style="margin-bottom:.5rem;padding:.75rem">' +
        '<span class="badge">' + esc(g.guideline_type) + '</span> ' + esc(g.rule_text) +
        '<div class="card-actions" style="margin-top:.5rem">' +
          '<button class="btn btn-sm btn-outline gl-edit" data-gl-json="' + encodeURIComponent(JSON.stringify(g)) + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger gl-del" data-id="' + g.id + '">Del</button>' +
        '</div>' +
      '</div>';
    }).join('') || '<p class="empty-msg">No guidelines yet.</p>';
    el.querySelectorAll('.gl-edit').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var g = JSON.parse(decodeURIComponent(btn.dataset.glJson));
        openGlModal(g.id, g);
      });
    });
    el.querySelectorAll('.gl-del').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('Delete?')) return;
        api('/api/admin/guidelines/' + btn.dataset.id, { method: 'DELETE' }).then(loadGuidelines);
      });
    });
  });
}

document.getElementById('gl-form').addEventListener('submit', function (e) {
  e.preventDefault();
  var id = document.getElementById('gl-id').value;
  var payload = {
    guideline_type: document.getElementById('gl-type').value,
    rule_text: document.getElementById('gl-text').value.trim(),
    rule_text_tr: document.getElementById('gl-text-tr').value.trim(),
  };
  var method = id ? 'PUT' : 'POST';
  var url = id ? '/api/admin/guidelines/' + id : '/api/admin/plans/' + activePlanId + '/guidelines';
  api(url, { method: method, body: JSON.stringify(payload) })
    .then(function () { glModal.close(); loadGuidelines(); showToast('Saved', 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

/* ── Quotas ───────────────────────────────────────────────── */
var quotaModal = document.getElementById('quota-modal');
document.getElementById('quota-cancel').addEventListener('click', function () { quotaModal.close(); });
document.getElementById('quota-add-btn').addEventListener('click', function () { openQuotaModal(null, null); });

function openQuotaModal(id, q) {
  document.getElementById('quota-id').value = id || '';
  document.getElementById('quota-qty').value = q ? (q.quota_per_week || 3) : 3;
  document.getElementById('quota-notes').value = q ? (q.notes || '') : '';
  var sel = document.getElementById('quota-cat-select');
  sel.innerHTML = exchangeCategories.map(function (c) {
    return '<option value="' + c.id + '"' + (q && q.exchange_category_id === c.id ? ' selected' : '') + '>' + esc(c.name) + '</option>';
  }).join('');
  quotaModal.showModal();
}

function loadQuotas() {
  if (!activePlanId) return;
  api('/api/admin/plans/' + activePlanId + '/quotas').then(function (data) {
    var el = document.getElementById('quota-list');
    el.innerHTML = data.map(function (q) {
      return '<div class="card" style="margin-bottom:.5rem;padding:.75rem">' +
        esc(q.category_name || ('Cat #' + q.exchange_category_id)) + ' — ' + q.quota_per_week + '/week' +
        (q.notes ? ' <small>(' + esc(q.notes) + ')</small>' : '') +
        '<div class="card-actions" style="margin-top:.5rem">' +
          '<button class="btn btn-sm btn-outline quota-edit" data-q-json="' + encodeURIComponent(JSON.stringify(q)) + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger quota-del" data-id="' + q.id + '">Del</button>' +
        '</div>' +
      '</div>';
    }).join('') || '<p class="empty-msg">No quotas yet.</p>';
    el.querySelectorAll('.quota-edit').forEach(function (btn) {
      btn.addEventListener('click', function () { openQuotaModal(JSON.parse(decodeURIComponent(btn.dataset.qJson)).id, JSON.parse(decodeURIComponent(btn.dataset.qJson))); });
    });
    el.querySelectorAll('.quota-del').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('Delete?')) return;
        api('/api/admin/quotas/' + btn.dataset.id, { method: 'DELETE' }).then(loadQuotas);
      });
    });
  });
}

document.getElementById('quota-form').addEventListener('submit', function (e) {
  e.preventDefault();
  var id = document.getElementById('quota-id').value;
  var payload = {
    exchange_category_id: parseInt(document.getElementById('quota-cat-select').value, 10),
    quota_per_week: parseInt(document.getElementById('quota-qty').value, 10),
    notes: document.getElementById('quota-notes').value.trim(),
  };
  var method = id ? 'PUT' : 'POST';
  var url = id ? '/api/admin/quotas/' + id : '/api/admin/plans/' + activePlanId + '/quotas';
  api(url, { method: method, body: JSON.stringify(payload) })
    .then(function () { quotaModal.close(); loadQuotas(); showToast('Saved', 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

/* ── Versions ─────────────────────────────────────────────── */
function loadVersions() {
  if (!activePlanId) return;
  api('/api/admin/plans/' + activePlanId + '/versions').then(function (data) {
    document.getElementById('versions-list').innerHTML = data.map(function (v) {
      return '<div class="card" style="margin-bottom:.5rem;padding:.75rem">' +
        '<strong>v' + v.version_number + '</strong>' +
        (v.change_summary ? ' — ' + esc(v.change_summary) : '') +
        '<span class="card-meta"> &nbsp; ' + (v.created_at ? new Date(v.created_at).toLocaleString() : '') + '</span>' +
      '</div>';
    }).join('') || '<p class="empty-msg">No versions saved yet.</p>';
  });
}

/* ── Image Upload ─────────────────────────────────────────── */
var _uploadId = null;
var _pollTimer = null;

function _setUploadMsg(msg) { document.getElementById('upload-status-msg').textContent = msg; }

function _pollExtractionStatus() {
  clearInterval(_pollTimer);
  _pollTimer = setInterval(function () {
    if (!_uploadId) { clearInterval(_pollTimer); return; }
    fetch('/api/admin/plans/upload-status/' + _uploadId)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var status = d.extraction_status;
        if (status === 'processing') { _setUploadMsg('Extracting… (10–30 s)'); return; }
        clearInterval(_pollTimer);
        var spin = document.getElementById('upload-spin');
        var procBtn = document.getElementById('upload-process-btn');
        if (spin) spin.hidden = true;
        if (procBtn) procBtn.disabled = false;
        if (status === 'failed') { _setUploadMsg('Extraction failed: ' + (d.error_message || 'unknown')); return; }
        if (status === 'draft_ready' && d.extracted) {
          var days = (d.extracted.days || []).length;
          var slots = (d.extracted.days || []).reduce(function (a, x) { return a + (x.slots || []).length; }, 0);
          var items = (d.extracted.days || []).reduce(function (a, x) { return a + (x.slots || []).reduce(function (b, s) { return b + (s.items || []).length; }, 0); }, 0);
          _setUploadMsg('Found ' + days + ' day(s), ' + slots + ' slot(s), ' + items + ' item(s). Review below.');
          try { document.getElementById('upload-draft-json').textContent = JSON.stringify(d.extracted, null, 2); } catch (_) {}
          document.getElementById('upload-draft-preview').hidden = false;
          document.getElementById('upload-confirm-btn').dataset.uploadId = _uploadId;
          document.getElementById('upload-reject-btn').dataset.uploadId = _uploadId;
        }
      }).catch(function () {});
  }, 3000);
}

document.getElementById('upload-file-input').addEventListener('change', function () {
  var file = this.files[0];
  if (!file) return;
  var fd = new FormData();
  fd.append('file', file);
  document.getElementById('upload-status').hidden = false;
  _setUploadMsg('Uploading…');
  document.getElementById('upload-draft-preview').hidden = true;
  clearInterval(_pollTimer);
  fetch('/api/admin/plans/upload-image', { method: 'POST', body: fd })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.error) { _setUploadMsg('Error: ' + d.error); return; }
      _uploadId = d.id;
      _setUploadMsg('Uploaded: ' + (d.original_filename || 'file') + '. Click "Process with AI" to extract.');
      // Inject process button once
      if (!document.getElementById('upload-process-btn')) {
        var wrap = document.createElement('div');
        wrap.style.marginTop = '1rem';
        wrap.innerHTML = '<button class="btn btn-primary" id="upload-process-btn">Process with AI</button> <span id="upload-spin" hidden>⏳ Extracting…</span>';
        document.getElementById('upload-status').appendChild(wrap);
        document.getElementById('upload-process-btn').addEventListener('click', function () {
          if (!_uploadId) return;
          this.disabled = true;
          document.getElementById('upload-spin').hidden = false;
          _setUploadMsg('Starting extraction…');
          api('/api/admin/plans/process-image/' + _uploadId, { method: 'POST' })
            .then(function () { _pollExtractionStatus(); })
            .catch(function (err) { _setUploadMsg('Error: ' + err.message); document.getElementById('upload-process-btn').disabled = false; document.getElementById('upload-spin').hidden = true; });
        });
      }
    }).catch(function (err) { _setUploadMsg('Upload error: ' + err.message); });
});

document.getElementById('upload-confirm-btn').addEventListener('click', function () {
  var uploadId = this.dataset.uploadId;
  if (!uploadId) return;
  if (!activePlanId) { showToast('Open a plan in the builder first, then apply.', 'error'); return; }
  var btn = this;
  btn.disabled = true; btn.textContent = 'Applying…';
  api('/api/admin/plans/apply-extraction/' + uploadId, { method: 'POST', body: JSON.stringify({ replace: true }) })
    .then(function (result) {
      document.getElementById('upload-draft-preview').hidden = true;
      var msg = 'Applied: ' + result.days_created + ' day(s), ' + result.slots_created + ' slot(s), ' + result.items_created + ' item(s).';
      if (result.unmatched_foods && result.unmatched_foods.length) {
        msg += ' Unmatched (added as overrides): ' + result.unmatched_foods.join(', ');
      }
      document.getElementById('upload-status-msg').textContent = msg;
      showToast('Plan structure applied!', 'success');
      btn.disabled = false; btn.textContent = 'Confirm & Apply';
      loadDays();
    }).catch(function (e) { showToast(e.message, 'error'); btn.disabled = false; btn.textContent = 'Confirm & Apply'; });
});
document.getElementById('upload-reject-btn').addEventListener('click', function () {
  document.getElementById('upload-draft-preview').hidden = true;
  document.getElementById('upload-status-msg').textContent = 'Rejected. Upload a different image or edit the plan manually.';
});

/* ── Templates tab ────────────────────────────────────────── */
function loadTemplates() {
  api('/api/admin/plans?is_template=1').then(function (data) {
    renderPlansList(data, 'admin-templates-list');
  }).catch(function (e) { showToast(e.message, 'error'); });
}

/* ── Users tab ────────────────────────────────────────────── */
function loadUsers() {
  api('/api/admin/users').then(function (data) {
    var tbody = document.getElementById('admin-users-body');
    tbody.innerHTML = data.map(function (u) {
      return '<tr>' +
        '<td>' + esc(u.username) + '</td>' +
        '<td>' + (u.is_admin ? '&#10003;' : '') + '</td>' +
        '<td><label class="checkbox-label"><input type="checkbox" class="toggle-plan-feature" data-uid="' + u.id + '"' + (u.plan_feature_enabled ? ' checked' : '') + ' /> Enabled</label></td>' +
        '<td>' + (u.active_plan_name ? esc(u.active_plan_name) : '<em>none</em>') + '</td>' +
        '<td><button class="btn btn-sm btn-outline assign-plan-btn" data-uid="' + u.id + '" data-uname="' + esc(u.username) + '">Assign Plan</button></td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="5" class="empty-msg">No users.</td></tr>';
    tbody.querySelectorAll('.toggle-plan-feature').forEach(function (cb) {
      cb.addEventListener('change', function () {
        api('/api/admin/users/' + cb.dataset.uid, { method: 'PUT', body: JSON.stringify({ plan_feature_enabled: cb.checked }) })
          .catch(function (e) { showToast(e.message, 'error'); cb.checked = !cb.checked; });
      });
    });
    tbody.querySelectorAll('.assign-plan-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { openAssignModal(btn.dataset.uid, btn.dataset.uname); });
    });
  }).catch(function (e) { showToast(e.message, 'error'); });
}

var assignModal = document.getElementById('admin-assign-modal');
document.getElementById('admin-assign-cancel').addEventListener('click', function () { assignModal.close(); });

function openAssignModal(uid, uname) {
  document.getElementById('admin-assign-user-id').value = uid;
  document.getElementById('admin-assign-username').textContent = uname;
  document.getElementById('admin-assign-start').value = new Date().toISOString().slice(0, 10);
  var sel = document.getElementById('admin-assign-plan-select');
  sel.innerHTML = plans.map(function (p) { return '<option value="' + p.id + '">' + esc(p.name) + '</option>'; }).join('');
  assignModal.showModal();
}

document.getElementById('admin-assign-form').addEventListener('submit', function (e) {
  e.preventDefault();
  var uid = document.getElementById('admin-assign-user-id').value;
  var payload = {
    plan_id: parseInt(document.getElementById('admin-assign-plan-select').value, 10),
    start_date: document.getElementById('admin-assign-start').value,
  };
  api('/api/admin/users/' + uid + '/assign-plan', { method: 'POST', body: JSON.stringify(payload) })
    .then(function () { assignModal.close(); loadUsers(); showToast('Plan assigned', 'success'); })
    .catch(function (e) { showToast(e.message, 'error'); });
});

/* ── Helpers ─────────────────────────────────────────────── */
function loadRecipesAndCategories() {
  api('/api/recipes').then(function (data) { recipes = data; });
  api('/api/exchange-categories').then(function (data) { exchangeCategories = data; });
}

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

loadPlansList();

})();
