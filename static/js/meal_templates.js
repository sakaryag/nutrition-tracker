/* ============================================================
   meal_templates.js
   ============================================================ */
(function () {
  'use strict';

  var UNIT_OPTIONS = ['g', 'ml', 'piece', 'slice', 'serving'];

  var templates = [];
  var editingTemplateId = null;
  var templateItems = [];
  var itemSearchFilter = 'ingredient';

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

  function init() {
    loadTemplates();
    initFilterButtons();
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

  async function loadTemplates() {
    try {
      templates = await api('/api/meal-templates');
      renderTemplates();
    } catch (_) {
      templatesList.innerHTML = '<p class="empty-msg">Could not load templates.</p>';
    }
  }

  function renderTemplates() {
    if (!templates || templates.length === 0) {
      templatesList.innerHTML = '<p class="empty-msg">No meal templates yet. Click "+ New Template" to create one.</p>';
      return;
    }
    templatesList.innerHTML = templates.map(function (t) {
      var n = t.items ? t.items.length : 0;
      var m = 'P:' + r1(t.total_protein) + 'g F:' + r1(t.total_fat) + 'g C:' + r1(t.total_carbs) + 'g ' + Math.round(t.total_calories) + 'kcal';
      return '<article class="food-card" data-id="' + t.id + '">' +
        '<div class="food-card__info">' +
          '<p class="food-card__name">' + esc(t.name) + '</p>' +
          '<p class="food-card__meta">' + esc(t.meal_type) + ' &mdash; ' + n + ' item' + (n !== 1 ? 's' : '') + '</p>' +
          '<div class="food-card__macros">' + m + '</div>' +
        '</div>' +
        '<div class="food-card__actions">' +
          '<button class="btn btn-sm btn-outline" data-action="edit" data-id="' + t.id + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger" data-action="delete" data-id="' + t.id + '">Delete</button>' +
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
      if (!confirm('Delete this template?')) return;
      try {
        await api('/api/meal-templates/' + id, { method: 'DELETE' });
        showToast('Template deleted', 'success');
        await loadTemplates();
      } catch (err) { showToast('Error: ' + err.message, 'error'); }
    }
  });

  function openModal(tpl) {
    editingTemplateId = tpl ? tpl.id : null;
    modalTitle.textContent = tpl ? 'Edit Template' : 'New Template';
    form.reset();
    document.getElementById('tpl-id').value = '';
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
      templateItems = (tpl.items || []).map(function (i) {
        var cal = i.calories || (i.protein * 4 + i.fat * 9 + i.carbs * 4);
        var srv = i.serving_size || 100;
        return { food_name: i.food_name, saved_food_id: i.saved_food_id,
          protein: i.protein, fat: i.fat, carbs: i.carbs, calories: cal,
          serving_size: srv, serving_unit: i.serving_unit || 'g',
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
  }

  openFormBtn.addEventListener('click', function () { openModal(null); });
  closeModalBtn.addEventListener('click', closeModal);
  cancelBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });

  /* ---- render items ---- */
  function unitOpts(sel) {
    return UNIT_OPTIONS.map(function (u) {
      return '<option value="' + u + '"' + (u === sel ? ' selected' : '') + '>' + u + '</option>';
    }).join('');
  }

  function macroLine(it) {
    return 'P:' + r1(it.protein) + 'g F:' + r1(it.fat) + 'g C:' + r1(it.carbs) + 'g ' + Math.round(it.calories) + 'kcal';
  }

  function renderItemsList() {
    if (templateItems.length === 0) {
      itemsList.innerHTML = '<p class="empty-msg">No items yet. Search below or click + Custom Item.</p>';
      return;
    }
    itemsList.innerHTML = templateItems.map(function (it, idx) {
      return '<div class="tpl-item-row" data-idx="' + idx + '">' +
        '<span class="tpl-item-row__name">' + esc(it.food_name) + '</span>' +
        '<input class="form-control tpl-item-serving" type="number" min="0.1" step="0.1" value="' + r1(it.serving_size) + '" data-idx="' + idx + '" data-field="serving_size" />' +
        '<select class="form-control tpl-item-unit" data-idx="' + idx + '" data-field="serving_unit">' + unitOpts(it.serving_unit) + '</select>' +
        '<span class="tpl-item-macros" data-macros="' + idx + '">' + macroLine(it) + '</span>' +
        '<button type="button" class="btn btn-icon btn-sm" data-remove="' + idx + '" title="Remove">&times;</button>' +
      '</div>';
    }).join('');
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
      var foods = await api('/api/foods?q=' + encodeURIComponent(q) + '&food_type=' + encodeURIComponent(itemSearchFilter));
      renderAC(foods);
    } catch (_) { itemAutocomplete.hidden = true; }
  }, 280);

  itemSearch.addEventListener('input', function () { debouncedItemSearch(itemSearch.value.trim()); });

  function renderAC(foods) {
    if (!foods || foods.length === 0) { itemAutocomplete.hidden = true; return; }
    itemAutocomplete.innerHTML = foods.slice(0, 10).map(function (f) {
      var sub = f.brand ? ' <span class="ac-sub">' + esc(f.brand) + '</span>' : '';
      return '<li role="option" tabindex="-1" data-food=\'' + JSON.stringify(f).replace(/'/g, '&#39;') + '\'>' +
        esc(f.name) + sub + ' <span class="ac-sub">P:' + r1(f.protein) + ' F:' + r1(f.fat) + ' C:' + r1(f.carbs) + 'g</span></li>';
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
      templateItems.push({ food_name: f.name, saved_food_id: f.id,
        protein: f.protein, fat: f.fat, carbs: f.carbs, calories: cal,
        serving_size: srv, serving_unit: unit,
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

  /* ---- custom item ---- */
  addCustomItemBtn.addEventListener('click', function () {
    var name = itemSearch.value.trim();
    if (!name) { showToast('Type a food name first', 'error'); return; }
    templateItems.push({ food_name: name, saved_food_id: null,
      protein: 0, fat: 0, carbs: 0, calories: 0,
      serving_size: 100, serving_unit: 'g',
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
    });
    var body = {
      name: document.getElementById('tpl-name').value.trim(),
      meal_type: document.getElementById('tpl-meal-type').value,
      items: templateItems.map(function (it) {
        return { food_name: it.food_name, saved_food_id: it.saved_food_id,
          protein: it.protein, fat: it.fat, carbs: it.carbs, calories: it.calories,
          serving_size: it.serving_size, serving_unit: it.serving_unit };
      }),
    };
    if (!body.name) { showToast('Template name is required', 'error'); return; }
    if (!body.items.length) { showToast('Add at least one item', 'error'); return; }
    var saveBtn = document.getElementById('save-template-btn');
    saveBtn.disabled = true;
    try {
      if (editingTemplateId) {
        await api('/api/meal-templates/' + editingTemplateId, { method: 'PUT', body: JSON.stringify(body) });
        showToast('Template updated', 'success');
      } else {
        await api('/api/meal-templates', { method: 'POST', body: JSON.stringify(body) });
        showToast('Template created', 'success');
      }
      closeModal();
      await loadTemplates();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
    finally { saveBtn.disabled = false; }
  });

  function esc(s) {
    return String(s != null ? s : '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function r1(n) { return Math.round((n != null ? n : 0) * 10) / 10; }

  init();
})();