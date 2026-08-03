/* ============================================================
   admin.js — Admin panel: plan CRUD + user management
   ============================================================ */

(function () {
  'use strict';

  var state = {
    plans: [],
    users: [],
    currentPlanId: null,  // plan being edited
    tasksForPlan: [],     // tasks loaded for plan editor
    activeDayOffset: 0,
  };

  // ── Init ──────────────────────────────────────────────────────────────────

  function init() {
    // Tabs
    document.querySelectorAll('.admin-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.admin-tab').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        document.querySelectorAll('.admin-panel').forEach(function (p) { p.hidden = true; });
        document.getElementById('admin-tab-' + btn.dataset.tab).hidden = false;
        if (btn.dataset.tab === 'users') loadUsers();
      });
    });

    // Plan modal
    document.getElementById('admin-create-plan-btn').addEventListener('click', openCreatePlan);
    document.getElementById('admin-plan-modal-close').addEventListener('click', closePlanModal);
    document.getElementById('admin-plan-cancel').addEventListener('click', closePlanModal);
    document.getElementById('admin-plan-modal').addEventListener('click', function (e) {
      if (e.target === this) closePlanModal();
    });
    document.getElementById('admin-plan-form').addEventListener('submit', savePlan);

    // Task form
    document.getElementById('admin-show-add-task').addEventListener('click', showAddTaskForm);
    document.getElementById('admin-cancel-task').addEventListener('click', hideAddTaskForm);
    document.getElementById('admin-save-task-btn').addEventListener('click', addTask);
    document.getElementById('admin-task-type').addEventListener('change', function () {
      document.getElementById('admin-food-fields').hidden = this.value !== 'food';
    });
    document.getElementById('admin-task-day-select').addEventListener('change', function () {
      state.activeDayOffset = parseInt(this.value, 10);
      if (state.currentPlanId) renderTasksForDay();
    });

    // Assign modal
    document.getElementById('admin-assign-modal-close').addEventListener('click', closeAssignModal);
    document.getElementById('admin-assign-cancel').addEventListener('click', closeAssignModal);
    document.getElementById('admin-assign-modal').addEventListener('click', function (e) {
      if (e.target === this) closeAssignModal();
    });
    document.getElementById('admin-assign-form').addEventListener('submit', submitAssign);

    loadPlans();
  }

  // ── Plans ─────────────────────────────────────────────────────────────────

  function loadPlans() {
    api('/api/admin/plans')
      .then(function (plans) {
        state.plans = plans;
        renderPlansList();
      })
      .catch(function (err) {
        document.getElementById('admin-plans-list').innerHTML =
          '<p class="empty-msg">' + (err.message || t('common.loadError')) + '</p>';
      });
  }

  function renderPlansList() {
    var container = document.getElementById('admin-plans-list');
    if (!state.plans.length) {
      container.innerHTML = '<p class="empty-msg">' + t('admin.noPlans') + '</p>';
      return;
    }
    container.innerHTML = '';
    state.plans.forEach(function (plan) {
      var card = document.createElement('div');
      card.className = 'admin-plan-card card';
      card.innerHTML =
        '<div class="admin-plan-card-info">' +
          '<div class="admin-plan-card-name">' + escHtml(plan.name) + '</div>' +
          '<div class="admin-plan-card-meta">' +
            plan.duration_days + ' ' + t('plans.days') + ' &bull; ' + plan.task_count + ' ' + t('admin.tasks') +
          '</div>' +
          (plan.description ? '<div class="admin-plan-card-desc">' + escHtml(plan.description) + '</div>' : '') +
        '</div>' +
        '<div class="admin-plan-card-actions">' +
          '<button class="btn btn-sm btn-outline" data-action="edit" data-id="' + plan.id + '">' + t('common.edit') + '</button>' +
          '<button class="btn btn-sm btn-danger" data-action="delete" data-id="' + plan.id + '">' + t('common.delete') + '</button>' +
        '</div>';
      card.querySelector('[data-action="edit"]').addEventListener('click', function () { openEditPlan(plan); });
      card.querySelector('[data-action="delete"]').addEventListener('click', function () { deletePlan(plan.id); });
      container.appendChild(card);
    });
  }

  function openCreatePlan() {
    state.currentPlanId = null;
    state.tasksForPlan = [];
    document.getElementById('admin-plan-id').value = '';
    document.getElementById('admin-plan-name').value = '';
    document.getElementById('admin-plan-desc').value = '';
    document.getElementById('admin-plan-duration').value = '7';
    document.getElementById('admin-plan-modal-title').textContent = t('admin.createPlan');
    document.getElementById('admin-tasks-for-day').innerHTML =
      '<p class="empty-msg">' + t('admin.savePlanFirst') + '</p>';
    document.getElementById('admin-show-add-task').hidden = true;
    rebuildDaySelect(7);
    document.getElementById('admin-plan-modal').hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function openEditPlan(plan) {
    state.currentPlanId = plan.id;
    document.getElementById('admin-plan-id').value = plan.id;
    document.getElementById('admin-plan-name').value = plan.name;
    document.getElementById('admin-plan-desc').value = plan.description || '';
    document.getElementById('admin-plan-duration').value = plan.duration_days;
    document.getElementById('admin-plan-modal-title').textContent = t('admin.editPlan');
    document.getElementById('admin-show-add-task').hidden = false;
    rebuildDaySelect(plan.duration_days);
    document.getElementById('admin-plan-modal').hidden = false;
    document.body.style.overflow = 'hidden';
    loadTasksForPlan(plan.id);
  }

  function closePlanModal() {
    document.getElementById('admin-plan-modal').hidden = true;
    document.body.style.overflow = '';
    hideAddTaskForm();
  }

  function savePlan(e) {
    e.preventDefault();
    var name = document.getElementById('admin-plan-name').value.trim();
    if (!name) { showToast(t('admin.planNameRequired'), 'error'); return; }
    var body = {
      name: name,
      description: document.getElementById('admin-plan-desc').value.trim(),
      duration_days: parseInt(document.getElementById('admin-plan-duration').value, 10) || 7,
    };
    var planId = state.currentPlanId;
    var req = planId
      ? api('/api/admin/plans/' + planId, { method: 'PUT', body: JSON.stringify(body) })
      : api('/api/admin/plans', { method: 'POST', body: JSON.stringify(body) });
    req.then(function (plan) {
      if (!planId) {
        state.currentPlanId = plan.id;
        document.getElementById('admin-plan-id').value = plan.id;
        document.getElementById('admin-show-add-task').hidden = false;
        rebuildDaySelect(plan.duration_days);
      }
      showToast(t('admin.planSaved'), 'success');
      loadPlans();
    }).catch(function (err) { showToast(err.message || t('common.error'), 'error'); });
  }

  function deletePlan(planId) {
    if (!confirm(t('admin.confirmDeletePlan'))) return;
    api('/api/admin/plans/' + planId, { method: 'DELETE' })
      .then(function () {
        showToast(t('admin.planDeleted'), 'success');
        loadPlans();
      })
      .catch(function (err) { showToast(err.message || t('common.error'), 'error'); });
  }

  // ── Tasks ─────────────────────────────────────────────────────────────────

  function rebuildDaySelect(duration) {
    var sel = document.getElementById('admin-task-day-select');
    sel.innerHTML = '';
    for (var i = 0; i < duration; i++) {
      var opt = document.createElement('option');
      opt.value = i;
      opt.textContent = t('plans.day') + ' ' + (i + 1);
      sel.appendChild(opt);
    }
    state.activeDayOffset = 0;
    sel.value = '0';
  }

  function loadTasksForPlan(planId) {
    api('/api/admin/plans/' + planId + '/tasks')
      .then(function (tasks) {
        state.tasksForPlan = tasks;
        renderTasksForDay();
      })
      .catch(function () {});
  }

  function renderTasksForDay() {
    var offset = state.activeDayOffset;
    var tasks = state.tasksForPlan.filter(function (t) { return t.day_offset === offset; });
    var container = document.getElementById('admin-tasks-for-day');
    container.innerHTML = '';
    if (!tasks.length) {
      container.innerHTML = '<p class="empty-msg">' + t('admin.noTasksForDay') + '</p>';
      return;
    }
    tasks.forEach(function (task) {
      var row = document.createElement('div');
      row.className = 'admin-task-row';
      var typeLabel = task.task_type === 'food' ? '\uD83C\uDF4E' : task.task_type === 'habit' ? '\u2705' : '\uD83D\uDCDD';
      var detail = task.food_name ? (task.food_name + (task.quantity ? ' ' + task.quantity + task.unit : '')) : task.description;
      row.innerHTML =
        '<span class="admin-task-icon">' + typeLabel + '</span>' +
        '<div class="admin-task-info">' +
          '<div class="admin-task-name">' + escHtml(task.description) + '</div>' +
          (task.food_name ? '<div class="admin-task-detail">' + escHtml(detail) + '</div>' : '') +
        '</div>' +
        '<button class="btn btn-icon btn-danger-text" data-delete-task="' + task.id + '" title="' + t('common.delete') + '">&times;</button>';
      row.querySelector('[data-delete-task]').addEventListener('click', function () {
        deleteTask(task.id);
      });
      container.appendChild(row);
    });
  }

  function showAddTaskForm() {
    document.getElementById('admin-add-task-form').hidden = false;
    document.getElementById('admin-show-add-task').hidden = true;
    document.getElementById('admin-task-desc').value = '';
    document.getElementById('admin-task-food-name').value = '';
    document.getElementById('admin-task-quantity').value = '';
    document.getElementById('admin-food-fields').hidden = false;
  }

  function hideAddTaskForm() {
    document.getElementById('admin-add-task-form').hidden = true;
    document.getElementById('admin-show-add-task').hidden = state.currentPlanId === null;
  }

  function addTask() {
    var planId = state.currentPlanId;
    if (!planId) { showToast(t('admin.savePlanFirst'), 'error'); return; }
    var desc = document.getElementById('admin-task-desc').value.trim();
    if (!desc) { showToast(t('admin.taskDescRequired'), 'error'); return; }
    var taskType = document.getElementById('admin-task-type').value;
    var qty = document.getElementById('admin-task-quantity').value;
    var body = {
      day_offset: state.activeDayOffset,
      task_type: taskType,
      description: desc,
      food_name: document.getElementById('admin-task-food-name').value.trim() || null,
      quantity: qty ? parseFloat(qty) : null,
      unit: document.getElementById('admin-task-unit').value || null,
    };
    api('/api/admin/plans/' + planId + '/tasks', { method: 'POST', body: JSON.stringify(body) })
      .then(function (task) {
        state.tasksForPlan.push(task);
        renderTasksForDay();
        hideAddTaskForm();
        showToast(t('admin.taskAdded'), 'success');
      })
      .catch(function (err) { showToast(err.message || t('common.error'), 'error'); });
  }

  function deleteTask(taskId) {
    if (!confirm(t('admin.confirmDeleteTask'))) return;
    api('/api/admin/tasks/' + taskId, { method: 'DELETE' })
      .then(function () {
        state.tasksForPlan = state.tasksForPlan.filter(function (t) { return t.id !== taskId; });
        renderTasksForDay();
      })
      .catch(function (err) { showToast(err.message || t('common.error'), 'error'); });
  }

  // ── Users ─────────────────────────────────────────────────────────────────

  function loadUsers() {
    api('/api/admin/users')
      .then(function (users) {
        state.users = users;
        renderUsersTable();
      })
      .catch(function (err) {
        document.getElementById('admin-users-body').innerHTML =
          '<tr><td colspan="5" class="empty-msg">' + (err.message || t('common.loadError')) + '</td></tr>';
      });
  }

  function renderUsersTable() {
    var tbody = document.getElementById('admin-users-body');
    if (!state.users.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-msg">' + t('admin.noUsers') + '</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    state.users.forEach(function (user) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + escHtml(user.username) + '</td>' +
        '<td><input type="checkbox" class="admin-user-cb" data-field="is_admin" data-uid="' + user.id + '"' +
          (user.is_admin ? ' checked' : '') + ' /></td>' +
        '<td><input type="checkbox" class="admin-user-cb" data-field="plan_feature_enabled" data-uid="' + user.id + '"' +
          (user.plan_feature_enabled ? ' checked' : '') + ' /></td>' +
        '<td>' + escHtml(user.active_plan_name || '—') + '</td>' +
        '<td><button class="btn btn-sm btn-outline" data-assign="' + user.id + '">' + t('admin.assignPlan') + '</button></td>';
      tr.querySelectorAll('.admin-user-cb').forEach(function (cb) {
        cb.addEventListener('change', function () {
          var upd = {};
          upd[cb.dataset.field] = cb.checked;
          api('/api/admin/users/' + cb.dataset.uid, { method: 'PUT', body: JSON.stringify(upd) })
            .then(function () { showToast(t('admin.userUpdated'), 'success'); })
            .catch(function (err) {
              cb.checked = !cb.checked;
              showToast(err.message || t('common.error'), 'error');
            });
        });
      });
      tr.querySelector('[data-assign]').addEventListener('click', function () {
        openAssignModal(user);
      });
      tbody.appendChild(tr);
    });
  }

  // ── Assign modal ──────────────────────────────────────────────────────────

  function openAssignModal(user) {
    document.getElementById('admin-assign-user-id').value = user.id;
    document.getElementById('admin-assign-username').textContent = user.username;
    var sel = document.getElementById('admin-assign-plan-select');
    sel.innerHTML = '';
    state.plans.forEach(function (p) {
      var opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      sel.appendChild(opt);
    });
    var today = new Date().toISOString().slice(0, 10);
    document.getElementById('admin-assign-start').value = today;
    document.getElementById('admin-assign-modal').hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function closeAssignModal() {
    document.getElementById('admin-assign-modal').hidden = true;
    document.body.style.overflow = '';
  }

  function submitAssign(e) {
    e.preventDefault();
    var uid = document.getElementById('admin-assign-user-id').value;
    var planId = document.getElementById('admin-assign-plan-select').value;
    var startDate = document.getElementById('admin-assign-start').value;
    api('/api/admin/users/' + uid + '/assign-plan', {
      method: 'POST',
      body: JSON.stringify({ plan_id: parseInt(planId, 10), start_date: startDate }),
    }).then(function () {
      showToast(t('admin.planAssigned'), 'success');
      closeAssignModal();
      loadUsers();
    }).catch(function (err) { showToast(err.message || t('common.error'), 'error'); });
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  function escHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  document.addEventListener('DOMContentLoaded', init);
})();