/* ============================================================
   plans.js — User plan tracking page
   ============================================================ */

(function () {
  'use strict';

  var state = {
    assignment: null,
    plan: null,
    tasksByDay: {},
    completedSet: [],     // [{task_id, date}]
    todayDayIndex: 0,
    startDate: null,
    viewMode: 'calendar', // 'calendar' | 'list'
    progressData: null,
  };

  // ── Init ──────────────────────────────────────────────────────────────────

  function init() {
    document.getElementById('plans-view-toggle').addEventListener('click', toggleView);
    document.getElementById('plans-task-modal-close').addEventListener('click', closeModal);
    document.getElementById('plans-task-modal').addEventListener('click', function (e) {
      if (e.target === this) closeModal();
    });
    loadAssignment();
  }

  // ── Data loading ──────────────────────────────────────────────────────────

  function loadAssignment() {
    api('/api/plans/my-assignment')
      .then(function (data) {
        if (!data.assignment) {
          document.getElementById('plans-no-assignment').hidden = false;
          return;
        }
        state.assignment = data.assignment;
        state.plan = data.plan;
        state.tasksByDay = data.tasks_by_day || {};
        state.completedSet = data.completed_set || [];
        state.todayDayIndex = data.today_day_index;
        state.startDate = data.start_date;
        document.getElementById('plans-overview').hidden = false;
        renderOverview();
        renderCalendar();
        renderListDayTabs();
        loadProgress();
      })
      .catch(function () {
        document.getElementById('plans-no-assignment').hidden = false;
      });
  }

  function loadProgress() {
    var days = state.plan ? state.plan.duration_days : 7;
    api('/api/plans/progress?days=' + days)
      .then(function (data) {
        state.progressData = data;
        updateProgressUI(data.overall_pct);
      })
      .catch(function () {});
  }

  // ── Render overview ───────────────────────────────────────────────────────

  function renderOverview() {
    var plan = state.plan;
    var elapsed = Math.max(0, Math.min(state.todayDayIndex + 1, plan.duration_days));
    document.getElementById('plan-name').textContent = plan.name;
    var desc = document.getElementById('plan-description');
    desc.textContent = plan.description || '';
    desc.hidden = !plan.description;
    document.getElementById('plan-days-elapsed').textContent =
      t('plans.day') + ' ' + elapsed + ' / ' + plan.duration_days;
  }

  function updateProgressUI(pct) {
    pct = Math.max(0, Math.min(100, pct || 0));
    document.getElementById('plan-overall-bar').style.width = pct + '%';
    document.getElementById('plan-overall-pct').textContent = pct + '%';
    document.getElementById('plan-ring-pct').textContent = pct + '%';
    var circumference = 163.36;
    var offset = circumference - (pct / 100) * circumference;
    document.getElementById('plan-ring-fg').setAttribute('stroke-dashoffset', offset.toFixed(2));
  }

  // ── Calendar render ───────────────────────────────────────────────────────

  function renderCalendar() {
    var plan = state.plan;
    var duration = plan.duration_days;
    var startDate = new Date(state.startDate + 'T00:00:00');
    var today = new Date();
    today.setHours(0, 0, 0, 0);

    // Determine grid start (Monday of the week containing startDate)
    var gridStart = new Date(startDate);
    var dow = gridStart.getDay(); // 0=Sun
    var daysToMon = (dow === 0) ? 6 : dow - 1;
    gridStart.setDate(gridStart.getDate() - daysToMon);

    // Build rows of 7
    var rows = [];
    var cursor = new Date(gridStart);
    var totalCells = Math.ceil((daysToMon + duration) / 7) * 7;
    for (var i = 0; i < totalCells; i += 7) {
      var week = [];
      for (var j = 0; j < 7; j++) {
        week.push(new Date(cursor));
        cursor.setDate(cursor.getDate() + 1);
      }
      rows.push(week);
    }

    var tbody = document.getElementById('plans-calendar-body');
    tbody.innerHTML = '';
    rows.forEach(function (week) {
      var tr = document.createElement('tr');
      week.forEach(function (cellDate) {
        var dayOffset = Math.round((cellDate - startDate) / 86400000);
        var isInPlan = dayOffset >= 0 && dayOffset < duration;
        var td = document.createElement('td');
        if (!isInPlan) {
          td.classList.add('cal-out');
          tr.appendChild(td);
          return;
        }
        var isToday = cellDate.getTime() === today.getTime();
        var isPast = cellDate < today;
        var isFuture = cellDate > today;
        if (isToday) td.classList.add('cal-today');
        if (isPast) td.classList.add('cal-past');
        if (isFuture) td.classList.add('cal-future');

        var tasks = state.tasksByDay[String(dayOffset)] || [];
        var totalTasks = tasks.length;
        var doneTasks = tasks.filter(function (task) {
          return isCompletedOn(task.id, cellDate);
        }).length;

        if (totalTasks > 0) {
          if (doneTasks === totalTasks) td.classList.add('cal-complete');
          else if (doneTasks > 0) td.classList.add('cal-partial');
        }

        var dayNum = document.createElement('div');
        dayNum.className = 'cal-day-num';
        dayNum.textContent = 'D' + (dayOffset + 1);
        td.appendChild(dayNum);

        if (totalTasks > 0) {
          var badge = document.createElement('div');
          badge.className = 'cal-task-badge';
          badge.textContent = doneTasks + '/' + totalTasks;
          td.appendChild(badge);
        }

        // First 2 task names as preview
        tasks.slice(0, 2).forEach(function (task) {
          var pill = document.createElement('div');
          pill.className = 'cal-task-pill';
          if (isCompletedOn(task.id, cellDate)) pill.classList.add('cal-task-done');
          pill.textContent = task.food_name || task.description.substring(0, 18);
          td.appendChild(pill);
        });
        if (tasks.length > 2) {
          var more = document.createElement('div');
          more.className = 'cal-task-more';
          more.textContent = '+' + (tasks.length - 2) + ' ' + t('plans.more');
          td.appendChild(more);
        }

        td.style.cursor = 'pointer';
        td.addEventListener('click', function () { openDayModal(dayOffset, cellDate, tasks); });
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  // ── List view ─────────────────────────────────────────────────────────────

  function renderListDayTabs() {
    var plan = state.plan;
    var startDate = new Date(state.startDate + 'T00:00:00');
    var tabs = document.getElementById('plans-day-tabs');
    tabs.innerHTML = '';
    for (var i = 0; i < plan.duration_days; i++) {
      (function (offset) {
        var btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-outline plans-day-tab';
        if (offset === state.todayDayIndex) btn.classList.add('active');
        btn.textContent = 'D' + (offset + 1);
        btn.addEventListener('click', function () {
          document.querySelectorAll('.plans-day-tab').forEach(function (b) { b.classList.remove('active'); });
          btn.classList.add('active');
          renderListDay(offset, startDate);
        });
        tabs.appendChild(btn);
      })(i);
    }
    renderListDay(Math.max(0, Math.min(state.todayDayIndex, plan.duration_days - 1)), startDate);
  }

  function renderListDay(dayOffset, startDate) {
    var cellDate = new Date(startDate);
    cellDate.setDate(cellDate.getDate() + dayOffset);
    var tasks = state.tasksByDay[String(dayOffset)] || [];
    var container = document.getElementById('plans-day-tasks');
    container.innerHTML = '';
    if (tasks.length === 0) {
      container.innerHTML = '<p class="empty-msg">' + t('plans.noTasks') + '</p>';
      return;
    }
    tasks.forEach(function (task) {
      container.appendChild(buildTaskRow(task, cellDate));
    });
  }

  // ── Day modal ─────────────────────────────────────────────────────────────

  function openDayModal(dayOffset, cellDate, tasks) {
    var modal = document.getElementById('plans-task-modal');
    document.getElementById('plans-task-modal-title').textContent =
      t('plans.day') + ' ' + (dayOffset + 1) + ' — ' + cellDate.toLocaleDateString();
    var body = document.getElementById('plans-task-modal-body');
    body.innerHTML = '';
    if (tasks.length === 0) {
      body.innerHTML = '<p class="empty-msg">' + t('plans.noTasks') + '</p>';
    } else {
      tasks.forEach(function (task) {
        body.appendChild(buildTaskRow(task, cellDate));
      });
    }
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    document.getElementById('plans-task-modal').hidden = true;
    document.body.style.overflow = '';
  }

  // ── Task row ──────────────────────────────────────────────────────────────

  function buildTaskRow(task, cellDate) {
    var dateStr = toISODate(cellDate);
    var done = isCompletedOn(task.id, cellDate);

    var row = document.createElement('div');
    row.className = 'plans-task-row' + (done ? ' plans-task-done' : '');
    row.dataset.taskId = task.id;
    row.dataset.date = dateStr;

    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = done;
    cb.className = 'plans-task-cb';
    cb.addEventListener('change', function () {
      toggleTask(task.id, dateStr, row, cb);
    });

    var icon = document.createElement('span');
    icon.className = 'plans-task-icon';
    icon.textContent = task.task_type === 'food' ? '\uD83C\uDF4E' : task.task_type === 'habit' ? '\u2705' : '\uD83D\uDCDD';

    var info = document.createElement('div');
    info.className = 'plans-task-info';

    var name = document.createElement('div');
    name.className = 'plans-task-name';
    name.textContent = task.food_name || task.description;

    var desc = document.createElement('div');
    desc.className = 'plans-task-desc';
    var parts = [];
    if (task.food_name && task.description !== task.food_name) parts.push(task.description);
    if (task.quantity) parts.push(task.quantity + ' ' + (task.unit || 'g'));
    desc.textContent = parts.join(' · ');

    info.appendChild(name);
    if (parts.length > 0) info.appendChild(desc);

    row.appendChild(cb);
    row.appendChild(icon);
    row.appendChild(info);
    return row;
  }

  // ── Task completion toggle ────────────────────────────────────────────────

  function toggleTask(taskId, dateStr, row, cb) {
    api('/api/plans/complete-task', {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId, date: dateStr }),
    }).then(function (res) {
      var done = res.status === 'completed';
      if (done) {
        state.completedSet.push({ task_id: taskId, date: dateStr });
      } else {
        state.completedSet = state.completedSet.filter(function (c) {
          return !(c.task_id === taskId && c.date === dateStr);
        });
      }
      cb.checked = done;
      row.classList.toggle('plans-task-done', done);
      // Re-render calendar to update badges
      renderCalendar();
      loadProgress();
    }).catch(function (err) {
      cb.checked = !cb.checked;
      showToast(err.message || t('common.error'), 'error');
    });
  }

  // ── View toggle ───────────────────────────────────────────────────────────

  function toggleView() {
    var btn = document.getElementById('plans-view-toggle');
    if (state.viewMode === 'calendar') {
      state.viewMode = 'list';
      document.getElementById('plans-calendar-view').hidden = true;
      document.getElementById('plans-list-view').hidden = false;
      btn.querySelector('[data-i18n]').setAttribute('data-i18n', 'plans.calendarView');
      btn.querySelector('[data-i18n]').textContent = t('plans.calendarView');
    } else {
      state.viewMode = 'calendar';
      document.getElementById('plans-calendar-view').hidden = false;
      document.getElementById('plans-list-view').hidden = true;
      btn.querySelector('[data-i18n]').setAttribute('data-i18n', 'plans.listView');
      btn.querySelector('[data-i18n]').textContent = t('plans.listView');
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  function isCompletedOn(taskId, cellDate) {
    var dateStr = toISODate(cellDate);
    return state.completedSet.some(function (c) {
      return c.task_id === taskId && c.date === dateStr;
    });
  }

  function toISODate(d) {
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  document.addEventListener('DOMContentLoaded', init);
})();