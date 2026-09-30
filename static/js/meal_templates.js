/* ============================================================
   meal_templates.js
   ============================================================ */
(function () {
  'use strict';

  var UNIT_OPTIONS = ['g', 'ml', 'oz', 'cup', 'tbsp', 'tsp', 'glass', 'piece', 'slice', 'serving'];
  var ALL_UNIT_OPTIONS = UNIT_OPTIONS; /* full list kept for fallback */

  var templates = [];
  var editingTemplateId = null;
  var templateItems = [];
  var itemSearchFilter = 'ingredient';
  var activeCategoryFilter = '';  /* '' = All */
  var pendingLogTemplateId = null;  /* for log-to-date modal */

  var templatesList    = document.getElementById('templates-list');
  var openFormBtn      = document.getElementById('open-template-form');
  var modal            = document.getElementById('template-modal');
  var modalTitle       = document.getElementById('tpl-modal-title');
  var closeModalBtn    = document.getElementById('close-template-modal');
  var cancelBtn        = document.getElementById('cancel-template');
  var form             = document.getElementById('template-form');
  var itemsList        = document.getElementById('tpl-items-list');
  var itemSearch       = document.getElementById('tpl-item-search');
  var itemAutocomplete = document.getElementById('tpl-item-autocomplete');
  var addCustomItemBtn = document.getElementById('tpl-add-custom-item');
  var categoryFilterBar = document.getElementById('category-filter-bar');

  /* --- Log-to-date modal --- */
  var logDateModal    = document.getElementById('log-date-modal');
  var logDateInput    = document.getElementById('log-date-input');
  var closeLogDateBtn = document.getElementById('close-log-date-modal');
  var cancelLogDate   = document.getElementById('cancel-log-date');
  var confirmLogDate  = document.getElementById('confirm-log-date');

  function init() {
    loadTemplates();
    initFilterButtons();
    initLogDateModal();
  }

  function initFilterButtons() {
    var btns = document.querySelectorAll('.tpl-search-filter [data-filter]');
    btns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        btns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        itemSearchFilter = btn.dataset.filter;
        var q = itemSearch.value.trim();
        if (q.length >= 2) debouncedItemSearch(q);
        else itemAutocomplete.hidden = true;
      });
    });
  }

  function initLogDateModal() {
    function closeLogModal() {
      logDateModal.hidden = true;
      pendingLogTemplateId = null;
    }
    closeLogDateBtn.addEventListener('click', closeLogModal);
    cancelLogDate.addEventListener('click', closeLogModal);
    confirmLogDate.addEventListener('click', async function () {
      if (!pendingLogTemplateId) return;
      var d = logDateInput.value;
      if (!d) { showToast('Pick a date first.', 'error'); return; }
      try {
        var result = await api('/api/meal-templates/' + pendingLogTemplateId + '/log', {
          method: 'POST',
          body: JSON.stringify({ date: d }),
        });
        showToast('Logged ' + result.logged + ' item(s) to ' + d, 'success');
        closeLogModal();
      } catch (err) { showToast('Error: ' + err.message, 'error'); }
    });
  }

  async function loadTemplates() {
    try {
      templates = await api('/api/meal-templates');
      renderCategoryFilter();
      renderTemplates();
    } catch (_) {
      templatesList.innerHTML = '<p class="empty-msg">' + esc(t('common.loadError')) + '</p>';
    }
  }

  /* ---- Category filter bar ---- */
  function renderCategoryFilter() {
    var cats = [];
    templates.forEach(function (tpl) {
      if (tpl.category && cats.indexOf(tpl.category) === -1) cats.push(tpl.category);
    });
    if (cats.length === 0) {
      categoryFilterBar.hidden = true;
      return;
    }
    cats.sort();
    var html = '<button class="btn btn-sm btn-outline' + (activeCategoryFilter === '' ? ' active' : '') + '" data-cat="">All</button>';
    cats.forEach(function (c) {
      html += '<button class="btn btn-sm btn-outline' + (activeCategoryFilter === c ? ' active' : '') + '" data-cat="' + esc(c) + '">' + esc(c) + '</button>';
    });
    categoryFilterBar.innerHTML = html;
    categoryFilterBar.hidden = false;
    categoryFilterBar.querySelectorAll('[data-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        activeCategoryFilter = btn.dataset.cat;
        categoryFilterBar.querySelectorAll('[data-cat]').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        renderTemplates();
      });
    });
  }

  function renderTemplates() {
    var filtered = templates;
    if (activeCategoryFilter) {
      filtered = templates.filter(function (tpl) { return tpl.category === activeCategoryFilter; });
    }
    if (!filtered || filtered.length === 0) {
      templatesList.innerHTML = '<p class="empty-msg">' + esc(t('meals.noTemplates')) + '</p>';
      return;
    }
    templatesList.innerHTML = filtered.map(function (tpl) {
      var n = tpl.items ? tpl.items.length : 0;
      var itemLabel = t('meals.itemCount').replace('{n}', n);
      var pK = (tpl.total_protein || 0) * 4;
      var fK = (tpl.total_fat || 0) * 9;
      var cK = (tpl.total_carbs || 0) * 4;
      var tot = pK + fK + cK;
      var pPct = tot > 0 ? Math.round(pK / tot * 100) : 33;
      var fPct = tot > 0 ? Math.round(fK / tot * 100) : 33;
      var cPct = tot > 0 ? (100 - pPct - fPct) : 34;
      var miniBar = '<div class="mini-macro-bar">' +
        '<div class="mini-macro-bar__segment mini-macro-bar__segment--protein" style="width:' + pPct + '%"></div>' +
        '<div class="mini-macro-bar__segment mini-macro-bar__segment--fat" style="width:' + fPct + '%"></div>' +
        '<div class="mini-macro-bar__segment mini-macro-bar__segment--carbs" style="width:' + cPct + '%"></div>' +
        '</div>';
      var catBadge = tpl.category ? '<span class="category-badge">' + esc(tpl.category) + '</span>' : '';
      return '<article class="food-card" data-id="' + tpl.id + '">' +
        '<div class="food-card__info">' +
          '<p class="food-card__name">' + esc(tpl.name) + ' ' + catBadge + '</p>' +
          '<p class="food-card__meta">' + esc(tpl.meal_type) + ' &mdash; ' + esc(itemLabel) + '</p>' +
          '<div class="food-card__macros">' +
            '<span class="macro-tag macro-tag--protein">P: ' + r1(tpl.total_protein) + 'g</span>' +
            '<span class="macro-tag macro-tag--fat">F: ' + r1(tpl.total_fat) + 'g</span>' +
            '<span class="macro-tag macro-tag--carbs">C: ' + r1(tpl.total_carbs) + 'g</span>' +
            '<span class="macro-tag macro-tag--cal">' + Math.round(tpl.total_calories) + ' kcal</span>' +
          '</div>' +
          miniBar +
        '</div>' +
        '<div class="food-card__actions">' +
          '<button class="btn btn-sm btn-primary" data-action="log" data-id="' + tpl.id + '" title="Log to Today">Log Today</button>' +
          '<button class="btn btn-sm btn-outline" data-action="log-date" data-id="' + tpl.id + '" title="Log to specific date">&#128197;</button>' +
          '<button class="btn btn-sm btn-outline" data-action="duplicate" data-id="' + tpl.id + '">Duplicate</button>' +
          '<button class="btn btn-sm btn-outline" data-action="edit" data-id="' + tpl.id + '">' + esc(t('meals.edit')) + '</button>' +
          '<button class="btn btn-sm btn-danger" data-action="delete" data-id="' + tpl.id + '">' + esc(t('meals.delete')) + '</button>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  templatesList.addEventListener('click', async function (e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    var id = parseInt(btn.dataset.id, 10);
    if (btn.dataset.action === 'edit') {
      var tpl = templates.find(function (t) { return t.id === id; });
      if (tpl) openModal(tpl);
    } else if (btn.dataset.action === 'delete') {
      if (!confirm(t('meals.delete') + '?')) return;
      try {
        await api('/api/meal-templates/' + id, { method: 'DELETE' });
        showToast(t('common.success'), 'success');
        await loadTemplates();
      } catch (err) { showToast(t('common.error') + ': ' + err.message, 'error'); }
    } else if (btn.dataset.action === 'log') {
      try {
        var result = await api('/api/meal-templates/' + id + '/log', { method: 'POST', body: JSON.stringify({}) });
        showToast('Logged ' + result.logged + ' item(s) to today', 'success');
      } catch (err) { showToast('Error: ' + err.message, 'error'); }
    } else if (btn.dataset.action === 'log-date') {
      pendingLogTemplateId = id;
      var today = new Date();
      logDateInput.value = today.toISOString().slice(0, 10);
      logDateModal.hidden = false;
    } else if (btn.dataset.action === 'duplicate') {
      try {
        await api('/api/meal-templates/' + id + '/clone', { method: 'POST' });
        showToast('Template duplicated', 'success');
        await loadTemplates();
      } catch (err) { showToast('Error: ' + err.message, 'error'); }
    }
  });

  function openModal(tpl) {
    editingTemplateId = tpl ? tpl.id : null;
    modalTitle.textContent = tpl ? t('meals.editTitle') : t('meals.newTitle');
    form.reset();
    document.getElementById('tpl-id').value = '';
    document.getElementById('tpl-category').value = '';
    templateItems = [];
    itemAutocomplete.hidden = true;
    itemSearchFilter = 'ingredient';
    document.querySelectorAll('.tpl-search-filter [data-filter]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.filter === 'ingredient');
    });
    if (tpl) {
      document.getElementById('tpl-id').value = tpl.id;
      document.getElementById('tpl-name').value = tpl.name;
      document.getElementById('tpl-meal-type').value = tpl.meal_type;
      document.getElementById('tpl-category').value = tpl.category || '';
      templateItems = (tpl.items || []).map(function (i) {
        var cal = i.calories || (i.protein * 4 + i.fat * 9 + i.carbs * 4);
        var srv = i.serving_size || 100;
        return { id: i.id, food_name: i.food_name, saved_food_id: i.saved_food_id,
          protein: i.protein, fat: i.fat, carbs: i.carbs, calories: cal,
          serving_size: srv, serving_unit: i.serving_unit || 'g',
          valid_units: i.valid_units || null, sort_order: i.sort_order || 0,
          _bp: i.protein, _bf: i.fat, _bc: i.carbs, _bk: cal, _bs: srv };
      });
    }
    renderItemsList();
    modal.hidden = false;
    document.getElementById('tpl-name').focus();
  }

  function closeModal() {
    modal.hidden = true;
    form.reset();
    editingTemplateId = null;
    templateItems = [];
    itemAutocomplete.hidden = true;
    fromLogPanel.hidden = true;
    logEntriesDiv.innerHTML = '<p class="empty-msg">Pick a date and press Load.</p>';
    logActionsDiv.hidden = true;
    logDateInput2.value = '';
  }

  openFormBtn.addEventListener('click', function () { openModal(null); });
  closeModalBtn.addEventListener('click', closeModal);
  cancelBtn.addEventListener('click', closeModal);
  /* Never close on backdrop click — complex form with unsaved data */

  /* ---- render items ---- */
  function unitOpts(sel, validUnitsJson) {
    var allowed = ALL_UNIT_OPTIONS;
    if (validUnitsJson) {
      try {
        var wl = typeof validUnitsJson === 'string' ? JSON.parse(validUnitsJson) : validUnitsJson;
        if (Array.isArray(wl) && wl.length) { allowed = wl; }
      } catch (_) {}
    }
    return ALL_UNIT_OPTIONS.map(function (u) {
      var enabled = allowed.indexOf(u) !== -1;
      return '<option value="' + u + '"' + (u === sel ? ' selected' : '') + (enabled ? '' : ' disabled') + '>'
        + (enabled ? '' : '\u2717 ') + u + '</option>';
    }).join('');
  }

  function macroLine(it) {
    return 'P:' + r1(it.protein) + 'g F:' + r1(it.fat) + 'g C:' + r1(it.carbs) + 'g ' + Math.round(it.calories) + 'kcal';
  }

  function renderItemsList() {
    if (templateItems.length === 0) {
      itemsList.innerHTML = '<p class="empty-msg">' + esc(t('meals.noItems')) + '</p>';
      return;
    }
    itemsList.innerHTML = templateItems.map(function (it, idx) {
      return '<div class="tpl-item-row" data-idx="' + idx + '" draggable="true">' +
        '<span class="tpl-drag-handle" title="Drag to reorder">&#9776;</span>' +
        '<span class="tpl-item-row__name">' + esc(it.food_name) + '</span>' +
        '<input class="form-control tpl-item-serving" type="number" min="0.1" step="0.1" value="' + r1(it.serving_size) + '" data-idx="' + idx + '" data-field="serving_size" />' +
        '<select class="form-control tpl-item-unit" data-idx="' + idx + '" data-field="serving_unit">' + unitOpts(it.serving_unit, it.valid_units || null) + '</select>' +
        '<span class="tpl-item-macros" data-macros="' + idx + '">' + macroLine(it) + '</span>' +
        '<button type="button" class="btn btn-icon btn-sm" data-remove="' + idx + '" title="Remove">&times;</button>' +
      '</div>';
    }).join('');
    initDragDrop();
  }

  /* ---- Drag and Drop ---- */
  var dragSrcIdx = null;

  function initDragDrop() {
    var rows = itemsList.querySelectorAll('.tpl-item-row');
    rows.forEach(function (row) {
      row.addEventListener('dragstart', function (e) {
        dragSrcIdx = parseInt(row.dataset.idx, 10);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(dragSrcIdx));
        setTimeout(function () { row.style.opacity = '0.5'; }, 0);
      });
      row.addEventListener('dragend', function () {
        row.style.opacity = '';
        itemsList.querySelectorAll('.tpl-item-row').forEach(function (r) {
          r.classList.remove('drag-over');
        });
      });
      row.addEventListener('dragover', function (e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        itemsList.querySelectorAll('.tpl-item-row').forEach(function (r) { r.classList.remove('drag-over'); });
        row.classList.add('drag-over');
      });
      row.addEventListener('dragleave', function () {
        row.classList.remove('drag-over');
      });
      row.addEventListener('drop', function (e) {
        e.preventDefault();
        var targetIdx = parseInt(row.dataset.idx, 10);
        if (dragSrcIdx === null || dragSrcIdx === targetIdx) return;
        /* Reorder in-memory array */
        var moved = templateItems.splice(dragSrcIdx, 1)[0];
        templateItems.splice(targetIdx, 0, moved);
        dragSrcIdx = null;
        renderItemsList();
        /* Call reorder API if editing existing template */
        if (editingTemplateId) {
          var itemIds = templateItems.map(function (it) { return it.id; }).filter(function (id) { return id != null; });
          if (itemIds.length > 0) {
            api('/api/meal-templates/' + editingTemplateId + '/reorder', {
              method: 'PUT',
              body: JSON.stringify({ item_ids: itemIds }),
            }).catch(function (err) { showToast('Reorder error: ' + err.message, 'error'); });
          }
        }
      });
    });
  }

  function scaleItem(it, newServing) {
    var base = it._bs > 0 ? it._bs : newServing;
    var ratio = newServing / base;
    it.serving_size = newServing;
    it.protein  = r1(it._bp * ratio);
    it.fat      = r1(it._bf * ratio);
    it.carbs    = r1(it._bc * ratio);
    it.calories = Math.round(it._bk * ratio);
  }

  /* serving size input -> scale macros */
  itemsList.addEventListener('input', function (e) {
    var el = e.target;
    if (el.dataset.field !== 'serving_size') return;
    var idx = parseInt(el.dataset.idx, 10);
    var it = templateItems[idx];
    if (!it) return;
    var v = parseFloat(el.value);
    if (!v || v <= 0) return;
    scaleItem(it, v);
    var span = itemsList.querySelector('[data-macros="' + idx + '"]');
    if (span) span.textContent = macroLine(it);
  });

  /* unit select -> just a label, keep macros, update serving number to intuitive default */
  itemsList.addEventListener('change', function (e) {
    var el = e.target;
    if (el.dataset.field === 'serving_unit') {
      var idx = parseInt(el.dataset.idx, 10);
      var it = templateItems[idx];
      if (!it) return;
      it.serving_unit = el.value;
      var row = itemsList.querySelector('.tpl-item-row[data-idx="' + idx + '"]');
      if (row) {
        var inp = row.querySelector('[data-field="serving_size"]');
        if (inp) inp.value = r1(it.serving_size);
      }
    }
  });

  /* remove button */
  itemsList.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-remove]');
    if (!btn) return;
    templateItems.splice(parseInt(btn.dataset.remove, 10), 1);
    renderItemsList();
  });

  /* ---- food search autocomplete ---- */
  var debouncedItemSearch = debounce(async function (q) {
    if (q.length < 2) { itemAutocomplete.hidden = true; return; }
    try {
      var foods = await api('/api/foods?q=' + encodeURIComponent(q) + '&food_type=' + encodeURIComponent(itemSearchFilter) + Lang.langParam());
      renderAC(foods);
    } catch (_) { itemAutocomplete.hidden = true; }
  }, 280);

  itemSearch.addEventListener('input', function () { debouncedItemSearch(itemSearch.value.trim()); });

  function renderAC(foods) {
    if (!foods || foods.length === 0) { itemAutocomplete.hidden = true; return; }
    itemAutocomplete.innerHTML = foods.slice(0, 10).map(function (f) {
      var sub = f.brand ? ' <span class="ac-sub">' + esc(f.brand) + '</span>' : '';
      return '<li role="option" tabindex="-1" data-food=\'' + JSON.stringify(f).replace(/'/g, '&#39;') + '\'>' +
        esc(Lang.foodName(f)) + sub + ' <span class="ac-sub">P:' + r1(f.protein) + ' F:' + r1(f.fat) + ' C:' + r1(f.carbs) + 'g</span></li>';
    }).join('');
    itemAutocomplete.hidden = false;
  }

  itemAutocomplete.addEventListener('click', function (e) {
    var li = e.target.closest('li');
    if (!li) return;
    try {
      var f = JSON.parse(li.dataset.food);
      var srv = f.default_serving || 100;
      var unit = f.serving_unit || 'g';
      var cal = f.calories || (f.protein * 4 + f.fat * 9 + f.carbs * 4);
      var ord = templateItems.length;
      templateItems.push({ food_name: f.name, saved_food_id: f.id,
        protein: f.protein, fat: f.fat, carbs: f.carbs, calories: cal,
        serving_size: srv, serving_unit: unit, valid_units: f.valid_units || null,
        sort_order: ord,
        _bp: f.protein, _bf: f.fat, _bc: f.carbs, _bk: cal, _bs: srv });
      renderItemsList();
      itemSearch.value = '';
      itemAutocomplete.hidden = true;
    } catch (_) {}
  });

  document.addEventListener('click', function (e) {
    if (!e.target.closest('.autocomplete-wrap') && !e.target.closest('.tpl-add-item')) {
      itemAutocomplete.hidden = true;
    }
  });

  /* ---- From Log ---- */
  var fromLogPanel   = document.getElementById('tpl-from-log-panel');
  var fromLogBtn     = document.getElementById('tpl-from-log-btn');
  var fromLogClose   = document.getElementById('tpl-from-log-close');
  var logDateInput2  = document.getElementById('tpl-log-date');
  var logLoadBtn     = document.getElementById('tpl-log-load-btn');
  var logEntriesDiv  = document.getElementById('tpl-log-entries');
  var logActionsDiv  = document.getElementById('tpl-from-log-actions');
  var logAddSelected = document.getElementById('tpl-log-add-selected');
  var logSelectAll   = document.getElementById('tpl-log-select-all');

  fromLogBtn.addEventListener('click', function () {
    fromLogPanel.hidden = !fromLogPanel.hidden;
    if (!fromLogPanel.hidden && !logDateInput2.value) {
      var today = new Date();
      logDateInput2.value = today.toISOString().slice(0, 10);
    }
  });

  fromLogClose.addEventListener('click', function () {
    fromLogPanel.hidden = true;
  });

  logLoadBtn.addEventListener('click', async function () {
    var d = logDateInput2.value;
    if (!d) { showToast('Pick a date first.', 'error'); return; }
    logEntriesDiv.innerHTML = '<p class="empty-msg">Loading\u2026</p>';
    logActionsDiv.hidden = true;
    try {
      var entries = await api('/api/entries?date=' + encodeURIComponent(d));
      if (!entries || entries.length === 0) {
        logEntriesDiv.innerHTML = '<p class="empty-msg">No entries for this date.</p>';
        return;
      }
      logEntriesDiv.innerHTML = entries.map(function (e, idx) {
        var cal = e.calories || (e.protein * 4 + e.fat * 9 + e.carbs * 4);
        return '<label class="tpl-log-entry-row">' +
          '<input type="checkbox" class="tpl-log-cb" data-idx="' + idx + '" ' +
            'data-entry=\'' + JSON.stringify({
              food_name: e.food_name,
              saved_food_id: e.saved_food_id || null,
              protein: e.protein,
              fat: e.fat,
              carbs: e.carbs,
              calories: cal,
              serving_size: e.serving_size || 100,
              serving_unit: e.serving_unit || 'g'
            }).replace(/'/g, '&#39;') + '\' />' +
          '<span class="tpl-log-entry-name">' + esc(e.food_name) + '</span>' +
          '<span class="tpl-log-entry-meta">P:' + r1(e.protein) + ' F:' + r1(e.fat) + ' C:' + r1(e.carbs) + 'g ' + Math.round(cal) + 'kcal' +
            (e.serving_size ? ' \u00b7 ' + r1(e.serving_size) + (e.serving_unit || 'g') : '') + '</span>' +
        '</label>';
      }).join('');
      logActionsDiv.hidden = false;
    } catch (err) {
      logEntriesDiv.innerHTML = '<p class="empty-msg">Error loading entries.</p>';
    }
  });

  logSelectAll.addEventListener('click', function () {
    var cbs = logEntriesDiv.querySelectorAll('.tpl-log-cb');
    var allChecked = Array.from(cbs).every(function (cb) { return cb.checked; });
    cbs.forEach(function (cb) { cb.checked = !allChecked; });
    logSelectAll.textContent = allChecked ? 'Select All' : 'Deselect All';
  });

  logAddSelected.addEventListener('click', function () {
    var cbs = logEntriesDiv.querySelectorAll('.tpl-log-cb:checked');
    if (cbs.length === 0) { showToast('Select at least one entry.', 'error'); return; }
    cbs.forEach(function (cb) {
      try {
        var e = JSON.parse(cb.dataset.entry);
        var ord = templateItems.length;
        templateItems.push({
          food_name: e.food_name, saved_food_id: e.saved_food_id,
          protein: e.protein, fat: e.fat, carbs: e.carbs, calories: e.calories,
          serving_size: e.serving_size, serving_unit: e.serving_unit,
          valid_units: null, sort_order: ord,
          _bp: e.protein, _bf: e.fat, _bc: e.carbs, _bk: e.calories, _bs: e.serving_size
        });
      } catch (_) {}
    });
    renderItemsList();
    fromLogPanel.hidden = true;
    showToast(cbs.length + ' item(s) added.', 'success');
  });

  /* ---- custom item ---- */
  addCustomItemBtn.addEventListener('click', function () {
    var name = itemSearch.value.trim();
    if (!name) { showToast(t('meals.typeFirst'), 'error'); return; }
    var ord = templateItems.length;
    templateItems.push({ food_name: name, saved_food_id: null,
      protein: 0, fat: 0, carbs: 0, calories: 0,
      serving_size: 100, serving_unit: 'g', sort_order: ord,
      _bp: 0, _bf: 0, _bc: 0, _bk: 0, _bs: 100 });
    renderItemsList();
    itemSearch.value = '';
    itemAutocomplete.hidden = true;
  });

  /* ---- submit ---- */
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    templateItems.forEach(function (it, idx) {
      var inp = itemsList.querySelector('[data-idx="' + idx + '"][data-field="serving_size"]');
      var sel = itemsList.querySelector('[data-idx="' + idx + '"][data-field="serving_unit"]');
      if (inp) { var v = parseFloat(inp.value); if (v > 0 && v !== it.serving_size) scaleItem(it, v); }
      if (sel) it.serving_unit = sel.value;
      it.sort_order = idx;
    });
    var body = {
      name: document.getElementById('tpl-name').value.trim(),
      meal_type: document.getElementById('tpl-meal-type').value,
      category: document.getElementById('tpl-category').value.trim(),
      items: templateItems.map(function (it, idx) {
        return { food_name: it.food_name, saved_food_id: it.saved_food_id,
          protein: it.protein, fat: it.fat, carbs: it.carbs, calories: it.calories,
          serving_size: it.serving_size, serving_unit: it.serving_unit,
          sort_order: idx };
      }),
    };
    if (!body.name) { showToast(t('meals.nameRequired'), 'error'); return; }
    if (!body.items.length) { showToast(t('meals.addItem'), 'error'); return; }
    var saveBtn = document.getElementById('save-template-btn');
    saveBtn.disabled = true;
    try {
      if (editingTemplateId) {
        await api('/api/meal-templates/' + editingTemplateId, { method: 'PUT', body: JSON.stringify(body) });
        showToast(t('common.success'), 'success');
      } else {
        await api('/api/meal-templates', { method: 'POST', body: JSON.stringify(body) });
        showToast(t('common.success'), 'success');
      }
      closeModal();
      await loadTemplates();
    } catch (err) { showToast(t('common.error') + ': ' + err.message, 'error'); }
    finally { saveBtn.disabled = false; }
  });

  function esc(s) {
    return String(s != null ? s : '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function r1(n) { return Math.round((n != null ? n : 0) * 10) / 10; }

  init();
})();