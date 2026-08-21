/* recipes.js — Recipe management page */
'use strict';

(function () {
  var recipes = [];
  var editingId = null;
  var ingredients = []; // [{saved_food_id, name, quantity, unit, protein, fat, carbs, calories}]

  var modal = document.getElementById('recipe-modal');
  var form  = document.getElementById('recipe-form');
  var list  = document.getElementById('recipe-list');
  var searchEl = document.getElementById('recipe-search');
  var ingBody = document.getElementById('ing-body');
  var ingSearch = document.getElementById('ing-search');
  var ingAC = document.getElementById('ing-ac');

  // --- Load list ---
  function loadRecipes() {
    var q = searchEl.value.trim();
    api('/api/recipes' + (q ? '?q=' + encodeURIComponent(q) : ''))
      .then(function (data) {
        recipes = data;
        renderList();
      }).catch(function (e) { showToast(e.message, 'error'); });
  }

  function renderList() {
    if (!recipes.length) {
      list.innerHTML = '<p class="empty-msg">No recipes yet. Create your first recipe.</p>';
      return;
    }
    list.innerHTML = recipes.map(function (r) {
      return '<div class="card" data-id="' + r.id + '">' +
        '<div class="card-body">' +
          '<h3 class="card-title">' + esc(r.name) + '</h3>' +
          '<p class="card-meta">' + r.ingredients.length + ' ingredient(s) &nbsp;|&nbsp; ' +
            '<strong>' + (r.total_protein || 0).toFixed(1) + 'g P</strong> &nbsp; ' +
            (r.total_fat || 0).toFixed(1) + 'g F &nbsp; ' +
            (r.total_carbs || 0).toFixed(1) + 'g C &nbsp; ' +
            Math.round(r.total_calories || 0) + ' kcal</p>' +
        '</div>' +
        '<div class="card-actions">' +
          '<button class="btn btn-sm btn-outline btn-edit" data-id="' + r.id + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger btn-delete" data-id="' + r.id + '">Delete</button>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  // --- Open modal ---
  function openNew() {
    editingId = null;
    ingredients = [];
    document.getElementById('recipe-modal-title').textContent = 'New Recipe';
    document.getElementById('rf-name').value = '';
    document.getElementById('rf-name-tr').value = '';
    document.getElementById('rf-prep-notes').value = '';
    document.getElementById('rf-prep-notes-tr').value = '';
    renderIngTable();
    modal.showModal();
  }

  function openEdit(id) {
    api('/api/recipes/' + id).then(function (r) {
      editingId = id;
      ingredients = (r.ingredients || []).map(function (i) {
        return {
          saved_food_id: i.saved_food_id,
          name: i.food_name_override || i.food_name,
          quantity: i.quantity,
          unit: i.unit,
          protein: i.protein,
          fat: i.fat,
          carbs: i.carbs,
          calories: i.calories,
        };
      });
      document.getElementById('recipe-modal-title').textContent = 'Edit Recipe';
      document.getElementById('rf-name').value = r.name || '';
      document.getElementById('rf-name-tr').value = r.name_tr || '';
      document.getElementById('rf-prep-notes').value = r.prep_notes || '';
      document.getElementById('rf-prep-notes-tr').value = r.prep_notes_tr || '';
      renderIngTable();
      modal.showModal();
    }).catch(function (e) { showToast(e.message, 'error'); });
  }

  // --- Ingredient table ---
  function renderIngTable() {
    ingBody.innerHTML = ingredients.map(function (ing, idx) {
      return '<tr data-idx="' + idx + '">' +
        '<td>' + esc(ing.name || '—') + '</td>' +
        '<td><input class="form-control ing-qty" type="number" min="0" step="0.1" value="' + (ing.quantity || 0) + '" data-idx="' + idx + '" style="width:70px" /></td>' +
        '<td><select class="form-control ing-unit" data-idx="' + idx + '" style="width:70px">' +
          ['g','ml','piece','slice','serving'].map(function (u) {
            return '<option' + (ing.unit === u ? ' selected' : '') + '>' + u + '</option>';
          }).join('') +
        '</select></td>' +
        '<td>' + fmtN(ing.protein) + '</td>' +
        '<td>' + fmtN(ing.fat) + '</td>' +
        '<td>' + fmtN(ing.carbs) + '</td>' +
        '<td>' + Math.round(ing.calories || 0) + '</td>' +
        '<td><button class="btn btn-sm btn-danger ing-remove" data-idx="' + idx + '">&#x2715;</button></td>' +
      '</tr>';
    }).join('');
    updateTotals();
  }

  function fmtN(v) { return v !== null && v !== undefined ? parseFloat(v).toFixed(1) : '—'; }

  function updateTotals() {
    var p=0, f=0, c=0, k=0;
    ingredients.forEach(function (i) { p += i.protein || 0; f += i.fat || 0; c += i.carbs || 0; k += i.calories || 0; });
    document.getElementById('tot-p').textContent = p.toFixed(1);
    document.getElementById('tot-f').textContent = f.toFixed(1);
    document.getElementById('tot-c').textContent = c.toFixed(1);
    document.getElementById('tot-k').textContent = Math.round(k);
  }

  ingBody.addEventListener('change', function (e) {
    var idx = parseInt(e.target.dataset.idx, 10);
    if (isNaN(idx)) return;
    if (e.target.classList.contains('ing-qty')) {
      ingredients[idx].quantity = parseFloat(e.target.value) || 0;
      recomputeIngMacros(idx);
    } else if (e.target.classList.contains('ing-unit')) {
      ingredients[idx].unit = e.target.value;
    }
    renderIngTable();
  });

  ingBody.addEventListener('click', function (e) {
    if (e.target.classList.contains('ing-remove')) {
      var idx = parseInt(e.target.dataset.idx, 10);
      ingredients.splice(idx, 1);
      renderIngTable();
    }
  });

  function recomputeIngMacros(idx) {
    var ing = ingredients[idx];
    if (!ing._base_protein) return; // no base macros stored
    var scale = ing.quantity / 100;
    ing.protein  = round1(ing._base_protein * scale);
    ing.fat      = round1(ing._base_fat * scale);
    ing.carbs    = round1(ing._base_carbs * scale);
    ing.calories = round1(ing._base_calories * scale);
  }

  function round1(v) { return Math.round(v * 10) / 10; }

  // --- Ingredient autocomplete ---
  var acTimer;
  ingSearch.addEventListener('input', function () {
    clearTimeout(acTimer);
    var q = ingSearch.value.trim();
    if (q.length < 2) { ingAC.hidden = true; return; }
    acTimer = setTimeout(function () {
      api('/api/foods?q=' + encodeURIComponent(q) + '&limit=12')
        .then(function (data) {
          ingAC.innerHTML = '';
          if (!data.length) { ingAC.hidden = true; return; }
          data.forEach(function (food) {
            var li = document.createElement('li');
            li.role = 'option';
            li.textContent = food.name;
            li.dataset.id = food.id;
            li.dataset.p = food.protein || 0;
            li.dataset.f = food.fat || 0;
            li.dataset.c = food.carbs || 0;
            li.dataset.k = food.calories || 0;
            li.addEventListener('click', function () {
              var qty = 100;
              ingredients.push({
                saved_food_id: food.id,
                name: food.name,
                quantity: qty,
                unit: 'g',
                protein: round1((food.protein || 0) * qty / 100),
                fat:     round1((food.fat || 0) * qty / 100),
                carbs:   round1((food.carbs || 0) * qty / 100),
                calories: round1((food.calories || 0) * qty / 100),
                _base_protein: food.protein || 0,
                _base_fat: food.fat || 0,
                _base_carbs: food.carbs || 0,
                _base_calories: food.calories || 0,
              });
              ingAC.hidden = true;
              ingSearch.value = '';
              renderIngTable();
            });
            ingAC.appendChild(li);
          });
          ingAC.hidden = false;
        }).catch(function () {});
    }, 250);
  });

  document.addEventListener('click', function (e) {
    if (!ingAC.contains(e.target) && e.target !== ingSearch) ingAC.hidden = true;
  });

  // --- Save ---
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var payload = {
      name: document.getElementById('rf-name').value.trim(),
      name_tr: document.getElementById('rf-name-tr').value.trim(),
      prep_notes: document.getElementById('rf-prep-notes').value.trim(),
      prep_notes_tr: document.getElementById('rf-prep-notes-tr').value.trim(),
      ingredients: ingredients.map(function (i) {
        return { saved_food_id: i.saved_food_id, food_name_override: i.name, quantity: i.quantity, unit: i.unit };
      }),
    };
    var method = editingId ? 'PUT' : 'POST';
    var url = editingId ? '/api/recipes/' + editingId : '/api/recipes';
    api(url, { method: method, body: JSON.stringify(payload) })
      .then(function () {
        modal.close();
        loadRecipes();
        showToast('Recipe saved', 'success');
      }).catch(function (e) { showToast(e.message, 'error'); });
  });

  // --- Delete ---
  list.addEventListener('click', function (e) {
    if (e.target.classList.contains('btn-edit')) {
      openEdit(parseInt(e.target.dataset.id, 10));
    } else if (e.target.classList.contains('btn-delete')) {
      var id = parseInt(e.target.dataset.id, 10);
      if (!confirm('Delete this recipe?')) return;
      api('/api/recipes/' + id, { method: 'DELETE' })
        .then(function () { loadRecipes(); showToast('Deleted', 'success'); })
        .catch(function (e) { showToast(e.message, 'error'); });
    }
  });

  document.getElementById('btn-new-recipe').addEventListener('click', openNew);
  document.getElementById('recipe-cancel').addEventListener('click', function () { modal.close(); });
  searchEl.addEventListener('input', debounce(loadRecipes, 300));

  function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  loadRecipes();
})();
