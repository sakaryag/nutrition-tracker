/* recipes.js — Recipe Builder page */
'use strict';

(function () {
  var recipes = [];
  var editingId = null;
  var ingredients = [];  // {saved_food_id, name, quantity, unit, protein, fat, carbs, calories, _bp, _bf, _bc, _bk}
  var showPerServing = false;
  var pendingLogRecipeId = null;

  // DOM refs — modal
  var modal          = document.getElementById('recipe-modal');
  var modalTitle     = document.getElementById('recipe-modal-title');
  var closeModalBtn  = document.getElementById('close-recipe-modal');
  var cancelBtn      = document.getElementById('cancel-recipe');
  var form           = document.getElementById('recipe-form');
  var rfId           = document.getElementById('rf-id');
  var rfName         = document.getElementById('rf-name');
  var rfServings     = document.getElementById('rf-servings');
  var rfNotes        = document.getElementById('rf-prep-notes');
  var ingBody        = document.getElementById('ing-body');
  var ingSearch      = document.getElementById('ing-search');
  var ingAC          = document.getElementById('ing-ac');
  var togglePerServ  = document.getElementById('toggle-per-serving');
  var totalsLabel    = document.getElementById('totals-label');
  var totP           = document.getElementById('tot-p');
  var totF           = document.getElementById('tot-f');
  var totC           = document.getElementById('tot-c');
  var totK           = document.getElementById('tot-k');

  // DOM refs — list
  var recipeList  = document.getElementById('recipe-list');
  var searchEl    = document.getElementById('recipe-search');

  // DOM refs — log-to-date modal
  var logDateModal   = document.getElementById('log-date-modal');
  var logDateInput   = document.getElementById('log-date-input');
  var logMealType    = document.getElementById('log-meal-type');
  var closeLogDate   = document.getElementById('close-log-date-modal');
  var cancelLogDate  = document.getElementById('cancel-log-date');
  var confirmLogDate = document.getElementById('confirm-log-date');

  // ---------------------------------------------------------------------------
  // List
  // ---------------------------------------------------------------------------

  function loadRecipes() {
    var q = searchEl.value.trim();
    api('/api/recipes' + (q ? '?q=' + encodeURIComponent(q) : ''))
      .then(function (data) {
        recipes = data;
        renderList();
      })
      .catch(function (e) {
        recipeList.innerHTML = '<p class="empty-msg">Could not load recipes: ' + esc(e.message) + '</p>';
      });
  }

  function renderList() {
    if (!recipes.length) {
      recipeList.innerHTML = '<p class="empty-msg">No recipes yet. Create your first recipe!</p>';
      return;
    }
    recipeList.innerHTML = recipes.map(function (r) {
      var ingCount = r.ingredient_count || (r.ingredients ? r.ingredients.length : 0);
      var svgs = r.servings > 1 ? ' &middot; ' + r.servings + ' servings' : '';
      return '<article class="food-card" data-id="' + r.id + '">' +
        '<div class="food-card__info">' +
          '<p class="food-card__name">' + esc(r.name) + '</p>' +
          '<p class="food-card__meta">' + ingCount + ' ingredient' + (ingCount !== 1 ? 's' : '') + svgs + '</p>' +
          '<div class="food-card__macros">' +
            '<span class="macro-tag macro-tag--protein">P: ' + fmt1(r.total_protein) + 'g</span>' +
            '<span class="macro-tag macro-tag--fat">F: ' + fmt1(r.total_fat) + 'g</span>' +
            '<span class="macro-tag macro-tag--carbs">C: ' + fmt1(r.total_carbs) + 'g</span>' +
            '<span class="macro-tag macro-tag--cal">' + Math.round(r.total_calories || 0) + ' kcal</span>' +
          '</div>' +
        '</div>' +
        '<div class="food-card__actions">' +
          '<button class="btn btn-sm btn-primary" data-action="log" data-id="' + r.id + '">Log Today</button>' +
          '<button class="btn btn-sm btn-outline" data-action="log-date" data-id="' + r.id + '" title="Log to specific date">&#128197;</button>' +
          '<button class="btn btn-sm btn-outline" data-action="save-food" data-id="' + r.id + '" title="Save as custom food">Save as Food</button>' +
          '<button class="btn btn-sm btn-outline" data-action="edit" data-id="' + r.id + '">Edit</button>' +
          '<button class="btn btn-sm btn-danger" data-action="delete" data-id="' + r.id + '">Delete</button>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  // ---------------------------------------------------------------------------
  // Card action delegation
  // ---------------------------------------------------------------------------

  recipeList.addEventListener('click', async function (e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    var id = parseInt(btn.dataset.id, 10);

    if (btn.dataset.action === 'edit') {
      var recipe = recipes.find(function (r) { return r.id === id; });
      if (recipe) openModal(recipe);
    } else if (btn.dataset.action === 'delete') {
      if (!confirm('Delete this recipe?')) return;
      try {
        await api('/api/recipes/' + id, { method: 'DELETE' });
        showToast('Recipe deleted', 'success');
        await loadRecipes();
      } catch (err) { showToast(err.message, 'error'); }

    } else if (btn.dataset.action === 'log') {
      try {
        var result = await api('/api/recipes/' + id + '/log', {
          method: 'POST', body: JSON.stringify({ date: todayStr(), meal_type: 'Snack' }),
        });
        showToast('Logged ' + result.logged + ' ingredient(s) to today', 'success');
      } catch (err) { showToast(err.message, 'error'); }

    } else if (btn.dataset.action === 'log-date') {
      pendingLogRecipeId = id;
      logDateInput.value = todayStr();
      logDateModal.hidden = false;

    } else if (btn.dataset.action === 'save-food') {
      try {
        var res = await api('/api/recipes/' + id + '/save-as-food', { method: 'POST' });
        var msg = res.created ? 'Saved "' + res.food.name + '" to My Foods' : 'Updated "' + res.food.name + '" in My Foods';
        showToast(msg, 'success');
      } catch (err) { showToast(err.message, 'error'); }
    }
  });

  // ---------------------------------------------------------------------------
  // Log-to-date modal
  // ---------------------------------------------------------------------------

  function closeLogModal() {
    logDateModal.hidden = true;
    pendingLogRecipeId = null;
  }

  closeLogDate.addEventListener('click', closeLogModal);
  cancelLogDate.addEventListener('click', closeLogModal);

  confirmLogDate.addEventListener('click', async function () {
    if (!pendingLogRecipeId) return;
    var d = logDateInput.value;
    if (!d) { showToast('Pick a date first.', 'error'); return; }
    try {
      var result = await api('/api/recipes/' + pendingLogRecipeId + '/log', {
        method: 'POST',
        body: JSON.stringify({ date: d, meal_type: logMealType.value }),
      });
      showToast('Logged ' + result.logged + ' ingredient(s) to ' + d, 'success');
      closeLogModal();
    } catch (err) { showToast(err.message, 'error'); }
  });

  // ---------------------------------------------------------------------------
  // Recipe modal — open / close
  // ---------------------------------------------------------------------------

  function openModal(recipe) {
    editingId = recipe ? recipe.id : null;
    showPerServing = false;
    updatePerServingBtn();

    modalTitle.textContent = recipe ? 'Edit Recipe' : 'New Recipe';
    rfId.value = recipe ? recipe.id : '';
    rfName.value = recipe ? recipe.name : '';
    rfServings.value = recipe ? (recipe.servings || 1) : 1;
    rfNotes.value = recipe ? (recipe.prep_notes || recipe.description || '') : '';

    ingredients = [];
    if (recipe && recipe.ingredients) {
      ingredients = recipe.ingredients.map(function (i) {
        return {
          saved_food_id: i.saved_food_id,
          name: i.food_name_override || i.food_name || '',
          quantity: i.quantity,
          unit: i.unit || 'g',
          protein: i.protein || 0,
          fat: i.fat || 0,
          carbs: i.carbs || 0,
          calories: i.calories || 0,
          _bp: i.protein || 0,
          _bf: i.fat || 0,
          _bc: i.carbs || 0,
          _bk: i.calories || 0,
        };
      });
    }

    ingSearch.value = '';
    ingAC.hidden = true;
    renderIngTable();
    modal.hidden = false;
    rfName.focus();
  }

  function closeModal() {
    modal.hidden = true;
    editingId = null;
    ingredients = [];
  }

  closeModalBtn.addEventListener('click', closeModal);
  cancelBtn.addEventListener('click', closeModal);

  modal.addEventListener('click', function (e) {
    if (e.target === modal) closeModal();
  });
  logDateModal.addEventListener('click', function (e) {
    if (e.target === logDateModal) closeLogModal();
  });

  document.getElementById('btn-new-recipe').addEventListener('click', function () { openModal(null); });

  // ---------------------------------------------------------------------------
  // Ingredient table rendering
  // ---------------------------------------------------------------------------

  var UNIT_OPTIONS = ['g', 'ml', 'piece', 'slice', 'serving', 'oz', 'cup', 'tbsp', 'tsp'];

  function renderIngTable() {
    ingBody.innerHTML = ingredients.map(function (ing, idx) {
      var unitOpts = UNIT_OPTIONS.map(function (u) {
        return '<option' + (ing.unit === u ? ' selected' : '') + '>' + u + '</option>';
      }).join('');
      return '<tr data-idx="' + idx + '" style="border-bottom:1px solid var(--color-border)">' +
        '<td style="padding:.35rem .5rem">' + esc(ing.name || '—') + '</td>' +
        '<td style="padding:.35rem .5rem;text-align:right">' +
          '<input class="form-control ing-qty" type="number" min="0" step="0.1" value="' + (ing.quantity || 0) + '" ' +
          'data-idx="' + idx + '" style="width:70px;text-align:right" />' +
        '</td>' +
        '<td style="padding:.35rem .5rem">' +
          '<select class="form-control ing-unit" data-idx="' + idx + '" style="width:80px">' + unitOpts + '</select>' +
        '</td>' +
        '<td style="text-align:right;padding:.35rem .5rem">' + fmt1(ing.protein) + '</td>' +
        '<td style="text-align:right;padding:.35rem .5rem">' + fmt1(ing.fat) + '</td>' +
        '<td style="text-align:right;padding:.35rem .5rem">' + fmt1(ing.carbs) + '</td>' +
        '<td style="text-align:right;padding:.35rem .5rem">' + Math.round(ing.calories || 0) + '</td>' +
        '<td style="padding:.35rem .5rem">' +
          '<button type="button" class="btn btn-sm btn-danger ing-remove" data-idx="' + idx + '" aria-label="Remove">&#x2715;</button>' +
        '</td>' +
      '</tr>';
    }).join('');
    updateTotals();
  }

  function updateTotals() {
    var p = 0, f = 0, c = 0, k = 0;
    ingredients.forEach(function (i) { p += i.protein || 0; f += i.fat || 0; c += i.carbs || 0; k += i.calories || 0; });
    var div = showPerServing ? Math.max(1, parseInt(rfServings.value, 10) || 1) : 1;
    totP.textContent = fmt1(p / div);
    totF.textContent = fmt1(f / div);
    totC.textContent = fmt1(c / div);
    totK.textContent = Math.round(k / div);
  }

  ingBody.addEventListener('change', function (e) {
    var idx = parseInt(e.target.dataset.idx, 10);
    if (isNaN(idx)) return;
    if (e.target.classList.contains('ing-qty')) {
      ingredients[idx].quantity = parseFloat(e.target.value) || 0;
      recomputeIngMacros(idx);
    } else if (e.target.classList.contains('ing-unit')) {
      ingredients[idx].unit = e.target.value;
      recomputeIngMacros(idx);
    }
    renderIngTable();
  });

  ingBody.addEventListener('click', function (e) {
    if (e.target.classList.contains('ing-remove')) {
      var idx = parseInt(e.target.dataset.idx, 10);
      if (!isNaN(idx)) {
        ingredients.splice(idx, 1);
        renderIngTable();
      }
    }
  });

  rfServings.addEventListener('change', updateTotals);

  // ---------------------------------------------------------------------------
  // Per-serving toggle
  // ---------------------------------------------------------------------------

  togglePerServ.addEventListener('click', function () {
    showPerServing = !showPerServing;
    updatePerServingBtn();
    updateTotals();
  });

  function updatePerServingBtn() {
    if (showPerServing) {
      togglePerServ.textContent = 'Show Total';
      totalsLabel.textContent = 'Per Serving';
    } else {
      togglePerServ.textContent = 'Per Serving';
      totalsLabel.textContent = 'Totals';
    }
  }

  // ---------------------------------------------------------------------------
  // Macro recompute when qty/unit changes
  // ---------------------------------------------------------------------------

  function recomputeIngMacros(idx) {
    var ing = ingredients[idx];
    if (ing._bp === undefined) return;
    // Base macros are per 100 g. Recompute from base.
    var scale = ing.quantity / 100.0;
    ing.protein  = round1(ing._bp * scale);
    ing.fat      = round1(ing._bf * scale);
    ing.carbs    = round1(ing._bc * scale);
    ing.calories = round1(ing._bk * scale);
  }

  // ---------------------------------------------------------------------------
  // Food autocomplete
  // ---------------------------------------------------------------------------

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
            li.innerHTML = esc(food.name) +
              '<span class="ac-sub"> ' + fmt1(food.protein) + 'P / ' + fmt1(food.fat) + 'F / ' + fmt1(food.carbs) + 'C per 100g</span>';
            li.addEventListener('click', function () {
              var qty = 100;
              ingredients.push({
                saved_food_id: food.id,
                name: food.name,
                quantity: qty,
                unit: 'g',
                protein:  round1((food.protein  || 0) * qty / 100),
                fat:      round1((food.fat      || 0) * qty / 100),
                carbs:    round1((food.carbs    || 0) * qty / 100),
                calories: round1((food.calories || 0) * qty / 100),
                _bp: food.protein  || 0,
                _bf: food.fat      || 0,
                _bc: food.carbs    || 0,
                _bk: food.calories || 0,
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

  // ---------------------------------------------------------------------------
  // Save recipe
  // ---------------------------------------------------------------------------

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var name = rfName.value.trim();
    if (!name) { showToast('Recipe name is required', 'error'); return; }

    var payload = {
      name: name,
      prep_notes: rfNotes.value.trim() || null,
      servings: Math.max(1, parseInt(rfServings.value, 10) || 1),
      ingredients: ingredients.map(function (i) {
        return {
          saved_food_id: i.saved_food_id,
          food_name_override: i.name,
          quantity: i.quantity,
          unit: i.unit,
        };
      }),
    };

    var method = editingId ? 'PUT' : 'POST';
    var url = editingId ? '/api/recipes/' + editingId : '/api/recipes';

    try {
      await api(url, { method: method, body: JSON.stringify(payload) });
      closeModal();
      showToast('Recipe saved', 'success');
      await loadRecipes();
    } catch (err) { showToast(err.message, 'error'); }
  });

  // ---------------------------------------------------------------------------
  // Search
  // ---------------------------------------------------------------------------

  searchEl.addEventListener('input', debounce(loadRecipes, 300));

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function fmt1(v) { return v !== null && v !== undefined ? parseFloat(v).toFixed(1) : '0.0'; }
  function round1(v) { return Math.round(v * 10) / 10; }
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function todayStr() {
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------

  loadRecipes();
})();
