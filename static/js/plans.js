/* plans.js — Patient plan view with Day/Slot/Fulfillment */
'use strict';

(function () {

var planData = null;      // full rich response from /api/plans/my-assignment/rich
var today = new Date().toISOString().slice(0, 10);
var fulfillmentStatus = {}; // slot_id -> fulfillment record

/* ── Init ─────────────────────────────────────────────────── */
function init() {
  loadRichAssignment();
}

function loadRichAssignment() {
  api('/api/plans/my-assignment/rich').then(function (data) {
    if (!data.assignment) {
      document.getElementById('plans-no-assignment').hidden = false;
      return;
    }
    planData = data;
    document.getElementById('plans-overview').hidden = false;
    renderOverview(data);
    loadFulfillmentStatus(today);
    loadCategoryProgress();
  }).catch(function (e) { showToast(e.message, 'error'); });
}

/* ── Overview bar ─────────────────────────────────────────── */
function renderOverview(data) {
  var plan = data.plan || {};
  document.getElementById('plan-name').textContent = plan.name || 'My Plan';
  document.getElementById('plan-description').textContent = plan.description || '';

  var dayIndex = data.today_day_index || 0;
  var dur = plan.duration_days || 1;
  var pct = Math.round(Math.min(dayIndex / dur, 1) * 100);
  document.getElementById('plan-days-elapsed').textContent = 'Day ' + (dayIndex + 1) + ' of ' + dur;
  document.getElementById('plan-overall-bar').style.width = pct + '%';
  document.getElementById('plan-overall-pct').textContent = pct + '%';
  document.getElementById('plan-ring-pct').textContent = pct + '%';
  var circ = 163.36;
  document.getElementById('plan-ring-fg').style.strokeDashoffset = circ - (circ * pct / 100);

  renderDayTabs(data.days || []);
  renderGuidelines(data.guidelines || []);

  // Show today's day
  var todayDay = (data.days || []).find(function (d) { return d.is_today; });
  document.getElementById('plans-today-label').textContent = todayDay
    ? 'Today — Day ' + (todayDay.day_offset + 1) + (todayDay.label ? ': ' + todayDay.label : '')
    : 'Today';
}

/* ── Day tabs ─────────────────────────────────────────────── */
function renderDayTabs(days) {
  var tabs = document.getElementById('plans-day-tabs');
  tabs.innerHTML = days.map(function (d) {
    return '<button class="btn btn-sm btn-outline plans-day-btn' + (d.is_today ? ' active' : '') + '" data-day-offset="' + d.day_offset + '" data-day-json="' + encodeURIComponent(JSON.stringify(d)) + '">' +
      'Day ' + (d.day_offset + 1) + (d.label ? ': ' + esc(d.label) : '') +
    '</button>';
  }).join('');

  tabs.querySelectorAll('.plans-day-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      tabs.querySelectorAll('.plans-day-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      renderDayDetail(JSON.parse(decodeURIComponent(btn.dataset.dayJson)));
    });
  });

  // Auto-select today
  var todayBtn = tabs.querySelector('.plans-day-btn.active');
  if (todayBtn) {
    renderDayDetail(JSON.parse(decodeURIComponent(todayBtn.dataset.dayJson)));
  }
}

/* ── Day detail with slots ────────────────────────────────── */
function renderDayDetail(day) {
  var detail = document.getElementById('plans-day-detail');
  if (!day.slots || !day.slots.length) {
    detail.innerHTML = '<p class="empty-msg">No meal slots for this day.</p>';
    return;
  }
  detail.innerHTML = day.slots.map(function (s) { return renderSlotCard(s); }).join('');
  detail.querySelectorAll('.slot-fulfill-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { openFulfillModal(JSON.parse(decodeURIComponent(btn.dataset.slotJson))); });
  });
}

function renderSlotCard(slot) {
  var isFulfilled = fulfillmentStatus[slot.id];
  var statusClass = isFulfilled ? 'slot-card--fulfilled' : '';
  var statusIcon = isFulfilled ? '&#10003; ' : '';
  return '<div class="slot-card ' + statusClass + '">' +
    '<div class="slot-card-header">' +
      '<strong>' + statusIcon + esc(slot.slot_name) + '</strong>' +
      (slot.content_pattern ? ' <span class="badge">Pattern ' + esc(slot.content_pattern) + '</span>' : '') +
      (slot.is_optional ? ' <span class="badge badge--muted">optional</span>' : '') +
      '<button class="btn btn-sm btn-primary slot-fulfill-btn" data-slot-json="' + encodeURIComponent(JSON.stringify(slot)) + '">' +
        (isFulfilled ? 'Change' : 'Log') +
      '</button>' +
    '</div>' +
    renderSlotItems(slot.items || []) +
    (isFulfilled ? '<p class="slot-fulfilled-note">Logged ✓</p>' : '') +
  '</div>';
}

function renderSlotItems(items) {
  if (!items.length) return '';
  return '<ul class="slot-items-list">' +
    items.map(function (it) {
      var label = it.food_name_override || (it.saved_food && it.saved_food.name) || '—';
      return '<li>' + esc(label) + (it.quantity ? ' — ' + it.quantity + ' ' + (it.unit || 'g') : '') + '</li>';
    }).join('') + '</ul>';
}

/* ── Today's slot view ────────────────────────────────────── */
function renderTodaySlots() {
  if (!planData) return;
  var todayDay = (planData.days || []).find(function (d) { return d.is_today; });
  var slotList = document.getElementById('plans-slot-list');
  if (!todayDay) { slotList.innerHTML = '<p class="empty-msg">No meal plan for today.</p>'; return; }
  slotList.innerHTML = todayDay.slots.map(function (s) { return renderSlotCard(s); }).join('');
  slotList.querySelectorAll('.slot-fulfill-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { openFulfillModal(JSON.parse(decodeURIComponent(btn.dataset.slotJson))); });
  });
}

/* ── Fulfillment status ───────────────────────────────────── */
function loadFulfillmentStatus(dateStr) {
  api('/api/plans/fulfillment-status?date=' + dateStr).then(function (data) {
    fulfillmentStatus = {};
    (data.slots || []).forEach(function (s) {
      if (s.is_fulfilled) fulfillmentStatus[s.id] = s.fulfillment;
    });
    renderTodaySlots();
    // re-render day detail if today tab is active
    var activeBtn = document.querySelector('.plans-day-btn.active');
    if (activeBtn) {
      var day = JSON.parse(decodeURIComponent(activeBtn.dataset.dayJson));
      if (day.is_today) renderDayDetail(day);
    }
  });
}

/* ── Slot fulfillment modal ───────────────────────────────── */
var sfModal = document.getElementById('slot-fulfill-modal');
var sfForm  = document.getElementById('slot-fulfill-form');
document.getElementById('sf-cancel').addEventListener('click', function () { sfModal.close(); });

function openFulfillModal(slot) {
  document.getElementById('sf-slot-id').value = slot.id;
  document.getElementById('sf-date').value = today;
  document.getElementById('slot-fulfill-title').textContent = slot.slot_name;
  document.getElementById('sf-slot-desc').textContent =
    (slot.content_pattern ? 'Pattern ' + slot.content_pattern + ' — ' : '') +
    (slot.is_optional ? 'Optional' : 'Required');
  document.getElementById('sf-food-id').value = '';
  document.getElementById('sf-custom-search').value = '';
  document.getElementById('sf-custom-ac').hidden = true;
  document.getElementById('sf-qty').value = 100;
  document.getElementById('sf-unit').value = 'g';

  // Render suggested items
  var items = slot.items || [];
  var itemsList = document.getElementById('sf-items-list');
  if (items.length) {
    itemsList.innerHTML = '<p style="margin-bottom:.5rem"><strong>Suggested:</strong></p>' +
      items.map(function (it) {
        var label = it.food_name_override || (it.saved_food && it.saved_food.name) || '—';
        return '<button class="btn btn-sm btn-outline sf-quick-food" style="margin:.25rem" ' +
          'data-food-id="' + (it.saved_food_id || '') + '" ' +
          'data-food-name="' + esc(label) + '" ' +
          'data-qty="' + (it.quantity || 100) + '" ' +
          'data-unit="' + (it.unit || 'g') + '">' +
          esc(label) + (it.quantity ? ' (' + it.quantity + ' ' + (it.unit || 'g') + ')' : '') +
        '</button>';
      }).join('');
    itemsList.querySelectorAll('.sf-quick-food').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.getElementById('sf-food-id').value = btn.dataset.foodId || '';
        document.getElementById('sf-custom-search').value = btn.dataset.foodName;
        document.getElementById('sf-qty').value = btn.dataset.qty;
        document.getElementById('sf-unit').value = btn.dataset.unit;
      });
    });
  } else {
    itemsList.innerHTML = '';
  }

  var existing = fulfillmentStatus[slot.id];
  document.getElementById('sf-unfulfill').hidden = !existing;

  sfModal.showModal();
}

// Custom food autocomplete in modal
var sfAC = document.getElementById('sf-custom-ac');
var sfTimer;
document.getElementById('sf-custom-search').addEventListener('input', function () {
  clearTimeout(sfTimer);
  var q = this.value.trim();
  if (q.length < 2) { sfAC.hidden = true; return; }
  sfTimer = setTimeout(function () {
    api('/api/foods?q=' + encodeURIComponent(q) + '&limit=10').then(function (data) {
      sfAC.innerHTML = '';
      data.forEach(function (f) {
        var li = document.createElement('li'); li.role = 'option'; li.textContent = f.name;
        li.addEventListener('click', function () {
          document.getElementById('sf-food-id').value = f.id;
          document.getElementById('sf-custom-search').value = f.name;
          sfAC.hidden = true;
        });
        sfAC.appendChild(li);
      });
      sfAC.hidden = !data.length;
    });
  }, 250);
});
document.addEventListener('click', function (e) { if (!sfAC.contains(e.target)) sfAC.hidden = true; });

sfForm.addEventListener('submit', function (e) {
  e.preventDefault();
  var slotId = parseInt(document.getElementById('sf-slot-id').value, 10);
  var dateStr = document.getElementById('sf-date').value;
  var foodId = parseInt(document.getElementById('sf-food-id').value, 10) || null;
  var qty = parseFloat(document.getElementById('sf-qty').value) || null;
  var unit = document.getElementById('sf-unit').value;
  api('/api/plans/fulfill-slot', {
    method: 'POST',
    body: JSON.stringify({ slot_id: slotId, date: dateStr, saved_food_id: foodId, quantity: qty, unit: unit }),
  }).then(function () {
    sfModal.close();
    showToast('Logged!', 'success');
    loadFulfillmentStatus(today);
  }).catch(function (e) { showToast(e.message, 'error'); });
});

document.getElementById('sf-unfulfill').addEventListener('click', function () {
  var slotId = parseInt(document.getElementById('sf-slot-id').value, 10);
  api('/api/plans/fulfill-slot', {
    method: 'POST',
    body: JSON.stringify({ slot_id: slotId, date: today, saved_food_id: fulfillmentStatus[slotId] && fulfillmentStatus[slotId].saved_food_id }),
  }).then(function () {
    sfModal.close();
    showToast('Removed', 'success');
    loadFulfillmentStatus(today);
  }).catch(function (e) { showToast(e.message, 'error'); });
});

/* ── Guidelines ───────────────────────────────────────────── */
function renderGuidelines(guidelines) {
  var section = document.getElementById('plans-guidelines-section');
  var list = document.getElementById('plans-guidelines-list');
  if (!guidelines.length) { section.hidden = true; return; }
  section.hidden = false;
  list.innerHTML = guidelines.map(function (g) {
    return '<div class="guideline-row">' +
      '<span class="badge">' + esc(g.guideline_type) + '</span> ' + esc(g.rule_text) +
    '</div>';
  }).join('');
}

/* ── Category quota progress ─────────────────────────────── */
function loadCategoryProgress() {
  var now = new Date();
  var week = now.getFullYear() + '-W' + String(getISOWeek(now)).padStart(2, '0');
  api('/api/plans/category-progress?week=' + week).then(function (data) {
    var quotas = data.quotas || [];
    var section = document.getElementById('plans-quota-section');
    if (!quotas.length) { section.hidden = true; return; }
    section.hidden = false;
    document.getElementById('plans-quota-list').innerHTML = quotas.map(function (q) {
      var pct = q.pct || 0;
      return '<div class="quota-row">' +
        '<span>' + esc(q.category_name || 'Category') + '</span>' +
        '<div class="progress-bar-wrap" style="flex:1;margin:0 .75rem">' +
          '<div class="progress-bar" style="width:' + pct + '%"></div>' +
        '</div>' +
        '<span>' + q.consumed + ' / ' + q.quota_per_week + '</span>' +
      '</div>';
    }).join('');
  }).catch(function () {});
}

function getISOWeek(d) {
  var date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  var yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
}

/* ── View toggle ─────────────────────────────────────────── */
document.getElementById('plans-view-toggle').addEventListener('click', function () {
  var slotView = document.getElementById('plans-slot-view');
  var calView  = document.getElementById('plans-calendar-view');
  var isSlots  = !slotView.hidden;
  slotView.hidden = isSlots;
  calView.hidden = !isSlots;
  this.textContent = isSlots ? 'Slot View' : 'Calendar';
  if (!isSlots && planData) renderCalendar(planData);
});

/* ── Calendar ─────────────────────────────────────────────── */
function renderCalendar(data) {
  var start = new Date(data.start_date);
  var dur = data.plan.duration_days || 14;
  var body = document.getElementById('plans-calendar-body');
  var days = (data.days || []);
  var weeks = [];
  var week = [];
  var startDow = (start.getDay() + 6) % 7; // Mon=0

  for (var i = 0; i < startDow; i++) week.push(null);
  for (var d = 0; d < dur; d++) {
    week.push({ day_offset: d, day: days[d] || null });
    if (week.length === 7) { weeks.push(week); week = []; }
  }
  while (week.length && week.length < 7) week.push(null);
  if (week.length) weeks.push(week);

  var todayIndex = data.today_day_index;
  body.innerHTML = weeks.map(function (w) {
    return '<tr>' + w.map(function (cell) {
      if (!cell) return '<td></td>';
      var cls = cell.day_offset === todayIndex ? 'plans-cal-today' : '';
      var label = 'Day ' + (cell.day_offset + 1);
      return '<td class="plans-cal-cell ' + cls + '">' + label + '</td>';
    }).join('') + '</tr>';
  }).join('');
}

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

init();

})();
