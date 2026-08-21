/* exchange_categories.js — Exchange Category management */
'use strict';

(function () {
  var categories = [];
  var editingId = null;
  var members = [];

  var modal = document.getElementById('cat-modal');
  var form  = document.getElementById('cat-form');
  var list  = document.getElementById('cat-list');
  var searchEl = document.getElementById('cat-search');
  var memBody = document.getElementById('mem-body');
  var memSearch = document.getElementById('mem-search');
  var memAC = document.getElementById('mem-ac');

  function loadCategories() {
    var q = searchEl.value.trim();
    api('/api/exchange-categories' + (q ? '?q=' + encodeURIComponent(q) : ''))
      .then(function (data) { categories = data; renderList(); })
      .catch(function (e) { showToast(e.message, 'error'); });
  }

  function renderList() {
    if (!categories.length) {
      list.innerHTML = '<p class="empty-msg">No exchange categories yet.</p>';
      return;
    }
    list.innerHTML = categories.map(function (c) {
      var memberCount = (c.members || []).length;
      return '<div class="card" data-id="' + c.id + '">' +
        '<div class="card-body">' +
          '<h3 class="card-title">' + esc(c.name) + (c.name_tr ? ' <small>/ ' + esc(c.name_tr) + '</small>' : '') + '</h3>' +
          (c.description ? '<p class="card-meta">' + esc(c.description) + '</p>' : '') +
          '<p class="card-meta">' + memberCount + ' food(s)</p>' +
        '</div>' +
        '<div class="card-actions">' +
          '<button class="btn btn-sm btn-outline btn-edit" data-id="' + c.id + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger btn-delete" data-id="' + c.id + '">Delete</button>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  function openNew() {
    editingId = null; members = [];
    document.getElementById('cat-modal-title').textContent = 'New Exchange Category';
    document.getElementById('cf-name').value = '';
    document.getElementById('cf-name-tr').value = '';
    document.getElementById('cf-desc').value = '';
    renderMemTable();
    modal.showModal();
  }

  function openEdit(id) {
    api('/api/exchange-categories/' + id).then(function (c) {
      editingId = id;
      members = (c.members || []).map(function (m) {
        return { saved_food_id: m.saved_food_id, name: m.food_name_override || m.food_name, equivalent_qty: m.equivalent_qty, equivalent_unit: m.equivalent_unit };
      });
      document.getElementById('cat-modal-title').textContent = 'Edit Exchange Category';
      document.getElementById('cf-name').value = c.name || '';
      document.getElementById('cf-name-tr').value = c.name_tr || '';
      document.getElementById('cf-desc').value = c.description || '';
      renderMemTable();
      modal.showModal();
    }).catch(function (e) { showToast(e.message, 'error'); });
  }

  function renderMemTable() {
    memBody.innerHTML = members.map(function (m, idx) {
      return '<tr>' +
        '<td>' + esc(m.name || '—') + '</td>' +
        '<td><input class="form-control mem-qty" type="number" min="0" step="0.1" value="' + (m.equivalent_qty || 0) + '" data-idx="' + idx + '" style="width:80px" /></td>' +
        '<td><select class="form-control mem-unit" data-idx="' + idx + '" style="width:80px">' +
          ['g','ml','piece','slice','serving'].map(function (u) {
            return '<option' + (m.equivalent_unit === u ? ' selected' : '') + '>' + u + '</option>';
          }).join('') +
        '</select></td>' +
        '<td><button class="btn btn-sm btn-danger mem-remove" data-idx="' + idx + '">&#x2715;</button></td>' +
      '</tr>';
    }).join('');
  }

  memBody.addEventListener('change', function (e) {
    var idx = parseInt(e.target.dataset.idx, 10);
    if (isNaN(idx)) return;
    if (e.target.classList.contains('mem-qty')) members[idx].equivalent_qty = parseFloat(e.target.value) || 0;
    else if (e.target.classList.contains('mem-unit')) members[idx].equivalent_unit = e.target.value;
  });

  memBody.addEventListener('click', function (e) {
    if (e.target.classList.contains('mem-remove')) {
      members.splice(parseInt(e.target.dataset.idx, 10), 1);
      renderMemTable();
    }
  });

  var acTimer;
  memSearch.addEventListener('input', function () {
    clearTimeout(acTimer);
    var q = memSearch.value.trim();
    if (q.length < 2) { memAC.hidden = true; return; }
    acTimer = setTimeout(function () {
      api('/api/foods?q=' + encodeURIComponent(q) + '&limit=12')
        .then(function (data) {
          memAC.innerHTML = '';
          data.forEach(function (food) {
            var li = document.createElement('li');
            li.role = 'option';
            li.textContent = food.name;
            li.addEventListener('click', function () {
              members.push({ saved_food_id: food.id, name: food.name, equivalent_qty: 100, equivalent_unit: 'g' });
              memAC.hidden = true;
              memSearch.value = '';
              renderMemTable();
            });
            memAC.appendChild(li);
          });
          memAC.hidden = !data.length;
        }).catch(function () {});
    }, 250);
  });

  document.addEventListener('click', function (e) {
    if (!memAC.contains(e.target) && e.target !== memSearch) memAC.hidden = true;
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var payload = {
      name: document.getElementById('cf-name').value.trim(),
      name_tr: document.getElementById('cf-name-tr').value.trim(),
      description: document.getElementById('cf-desc').value.trim(),
      members: members,
    };
    var method = editingId ? 'PUT' : 'POST';
    var url = editingId ? '/api/exchange-categories/' + editingId : '/api/exchange-categories';
    api(url, { method: method, body: JSON.stringify(payload) })
      .then(function () { modal.close(); loadCategories(); showToast('Saved', 'success'); })
      .catch(function (e) { showToast(e.message, 'error'); });
  });

  list.addEventListener('click', function (e) {
    if (e.target.classList.contains('btn-edit')) openEdit(parseInt(e.target.dataset.id, 10));
    else if (e.target.classList.contains('btn-delete')) {
      var id = parseInt(e.target.dataset.id, 10);
      if (!confirm('Delete this category?')) return;
      api('/api/exchange-categories/' + id, { method: 'DELETE' })
        .then(function () { loadCategories(); showToast('Deleted', 'success'); })
        .catch(function (e) { showToast(e.message, 'error'); });
    }
  });

  document.getElementById('btn-new-cat').addEventListener('click', openNew);
  document.getElementById('cat-cancel').addEventListener('click', function () { modal.close(); });
  searchEl.addEventListener('input', debounce(loadCategories, 300));

  function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  loadCategories();
})();
