/* ============================================================
   dashboard.js — Daily tracking dashboard logic
   ============================================================ */

(function () {
  'use strict';

  /* ---- State ---- */
  let currentDate = formatDate(new Date());
  let editingId = null;
  let selectedFood = null; // food from autocomplete

  /* ---- DOM refs ---- */
  const dateHeading       = document.getElementById('date-heading');
  const prevDayBtn        = document.getElementById('prev-day');
  const nextDayBtn        = document.getElementById('next-day');
  const openAddFormBtn    = document.getElementById('open-add-form');
  const entryModal        = document.getElementById('entry-modal');
  const closeModalBtn     = document.getElementById('close-modal');
  const cancelEntryBtn    = document.getElementById('cancel-entry');
  const entryForm         = document.getElementById('entry-form');
  const modalTitle        = document.getElementById('modal-title');
  const quickAddList      = document.getElementById('quick-add-list');
  const entriesList       = document.getElementById('entries-list');
  const foodNameInput     = document.getElementById('entry-food-name');
  const autocompleteList  = document.getElementById('food-autocomplete');

  /* ---- Init ---- */
  async function init() {
    await loadPage();
    await Promise.all([loadRecents(), loadTemplateChips()]);
  }

  /* ---- Date Navigation ---- */
  function updateDateHeading() {
    dateHeading.textContent = formatDateDisplay(currentDate);
    // Disable next-day if it's today
    const today = formatDate(new Date());
    nextDayBtn.disabled = currentDate >= today;
  }

  prevDayBtn.addEventListener('click', () => {
    const d = parseLocalDate(currentDate);
    d.setDate(d.getDate() - 1);
    currentDate = formatDate(d);
    loadPage();
  });

  nextDayBtn.addEventListener('click', () => {
    const today = formatDate(new Date());
    if (currentDate >= today) return;
    const d = parseLocalDate(currentDate);
    d.setDate(d.getDate() + 1);
    currentDate = formatDate(d);
    loadPage();
  });

  /* ---- Load summary + entries ---- */
  async function loadPage() {
    updateDateHeading();
    await Promise.all([loadSummary(), loadEntries()]);
  }

  async function loadSummary() {
    try {
      const data = await api(`/api/summary?date=${currentDate}`);
      renderSummary(data);
      renderDonut(data);
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    }
  }

  function renderSummary(data) {
    const macros = ['protein', 'fat', 'carbs', 'calories'];
    const multiplier = { protein: 4, fat: 9, carbs: 4 };

    macros.forEach(m => {
      const consumed  = Math.round(data.totals?.[m] ?? 0);
      const target    = Math.round(data.target?.[m] ?? 0);
      const remaining = Math.round(data.remaining?.[m] ?? 0);
      const pct       = target > 0 ? Math.min(100, Math.round((consumed / target) * 100)) : 0;

      const elConsumed   = document.getElementById(`summary-${m}`);
      const elTarget     = document.getElementById(`target-${m}`);
      const elRemaining  = document.getElementById(`remaining-${m}`);
      const elBar        = document.getElementById(`bar-${m}`);
      const elPct        = document.getElementById(`pct-${m}`);

      if (elConsumed)  elConsumed.textContent  = consumed;
      if (elTarget)    elTarget.textContent     = target;
      if (elRemaining) elRemaining.textContent  = remaining;
      if (elBar)       elBar.style.width        = pct + '%';
      if (elPct)       elPct.textContent        = '(' + pct + '%)';
    });

    const tp = data.totals?.protein ?? 0, tf = data.totals?.fat ?? 0, tc = data.totals?.carbs ?? 0;
    const totalKcal = (tp * 4) + (tf * 9) + (tc * 4);
    const gp = data.target?.protein ?? 0, gf = data.target?.fat ?? 0, gc = data.target?.carbs ?? 0;
    const targetKcal = (gp * 4) + (gf * 9) + (gc * 4);

    ['protein', 'fat', 'carbs'].forEach(m => {
      const curVal = data.totals?.[m] ?? 0;
      const tgtVal = data.target?.[m] ?? 0;
      const mul = multiplier[m];
      const curPct = totalKcal > 0 ? Math.round((curVal * mul / totalKcal) * 100) : 0;
      const tgtPct = targetKcal > 0 ? Math.round((tgtVal * mul / targetKcal) * 100) : 0;
      const elSplit = document.getElementById(`split-${m}`);
      if (elSplit) elSplit.textContent = curPct + '% eaten / ' + tgtPct + '% target';
    });
  }

  /* ---- Macro Donut Chart ---- */
  let donutChart = null;

  function renderDonut(data) {
    const p = Math.round(data.totals?.protein ?? 0);
    const f = Math.round(data.totals?.fat ?? 0);
    const c = Math.round(data.totals?.carbs ?? 0);
    const cal = Math.round(data.totals?.calories ?? 0);

    const label = document.getElementById('donut-center-label');
    if (label) label.textContent = cal + ' kcal';

    const ctx = document.getElementById('macro-donut');
    if (!ctx) return;

    const pKcal = p * 4, fKcal = f * 9, cKcal = c * 4;
    const totalMacroKcal = pKcal + fKcal + cKcal;
    const pPct = totalMacroKcal > 0 ? Math.round((pKcal / totalMacroKcal) * 100) : 0;
    const fPct = totalMacroKcal > 0 ? Math.round((fKcal / totalMacroKcal) * 100) : 0;
    const cPct = totalMacroKcal > 0 ? 100 - pPct - fPct : 0;

    const hasData = p + f + c > 0;
    const chartData = hasData
      ? [pKcal, fKcal, cKcal]
      : [1];
    const colors = hasData
      ? ['#4A90D9', '#E8913A', '#5CB85C']
      : ['#e2e8f0'];
    const labels = hasData
      ? [t('macro.protein') + ' ' + p + 'g (' + pPct + '%)', t('macro.fat') + ' ' + f + 'g (' + fPct + '%)', t('macro.carbs') + ' ' + c + 'g (' + cPct + '%)']
      : ['No data'];

    if (donutChart) donutChart.destroy();
    donutChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: chartData,
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: '#fff',
        }],
      },
      options: {
        responsive: false,
        cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10, font: { size: 12 } } },
          tooltip: { enabled: hasData },
        },
      },
    });
  }

  async function loadEntries() {
    try {
      const entries = await api(`/api/entries?date=${currentDate}`);
      renderEntries(entries);
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    }
  }

  const MEAL_ORDER = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];
  const MEAL_I18N  = { 'Breakfast': 'entry.breakfast', 'Lunch': 'entry.lunch', 'Dinner': 'entry.dinner', 'Snack': 'entry.snack' };

  function renderEntries(entries) {
    if (!entries || entries.length === 0) {
      entriesList.innerHTML = '<p class="empty-msg">' + escHtml(t('dash.noEntries')) + '</p>';
      return;
    }

    // Group by meal type
    const groups = {};
    MEAL_ORDER.forEach(m => { groups[m] = []; });
    entries.forEach(e => {
      const key = e.meal_type in groups ? e.meal_type : 'Snack';
      groups[key].push(e);
    });

    let html = '';
    MEAL_ORDER.forEach(meal => {
      if (groups[meal].length === 0) return;
      const mealLabel = t(MEAL_I18N[meal]) || meal;
      html += `<div class="meal-group">
        <p class="meal-group__title">${escHtml(mealLabel)}</p>`;
      groups[meal].forEach(e => {
        html += renderEntryCard(e);
      });
      html += '</div>';
    });
    entriesList.innerHTML = html;
  }

  function renderEntryCard(e) {
    const kcal = Math.round(e.calories ?? 0);
    return `<article class="entry-card" data-id="${e.id}">
      <div class="entry-card__info">
        <p class="entry-card__name">${escHtml(e.food_name)}</p>
        <p class="entry-card__meta">${escHtml(String(e.serving_size))} ${escHtml(e.serving_unit)}</p>
        <div class="entry-card__macros">
          <span class="macro-tag macro-tag--protein">P: ${round1(e.protein)}g</span>
          <span class="macro-tag macro-tag--fat">F: ${round1(e.fat)}g</span>
          <span class="macro-tag macro-tag--carbs">C: ${round1(e.carbs)}g</span>
          <span class="macro-tag macro-tag--cal">${kcal} kcal</span>
        </div>
      </div>
      <div class="entry-card__actions">
        <button class="btn btn-icon" title="${escHtml(t('common.edit'))}" data-action="edit" data-id="${e.id}">&#9998;</button>
        <button class="btn btn-icon" title="${escHtml(t('common.delete'))}" data-action="delete" data-id="${e.id}">&#128465;</button>
      </div>
    </article>`;
  }

  /* ---- Recent Foods ---- */
  async function loadRecents() {
    try {
      const recents = await api('/api/entries/recent');
      renderRecents(recents);
    } catch (_) {
      quickAddList.innerHTML = '<p class="empty-msg">Could not load recent foods.</p>';
    }
  }

  function renderRecents(recents) {
    if (!recents || recents.length === 0) {
      quickAddList.innerHTML = '<p class="empty-msg">No recent foods yet.</p>';
      return;
    }
    quickAddList.innerHTML = recents.map(r =>
      `<button class="quick-add-chip" data-food='${JSON.stringify(r).replace(/'/g, "&#39;")}'>${escHtml(r.food_name)}</button>`
    ).join('');
  }

  quickAddList.addEventListener('click', (e) => {
    const chip = e.target.closest('.quick-add-chip');
    if (!chip) return;
    try {
      const food = JSON.parse(chip.dataset.food);
      openModal();
      prefillFromFood(food);
    } catch (_) {}
  });

  /* ---- Modal ---- */
  function openModal(entry = null) {
    editingId = entry ? entry.id : null;
    selectedFood = null;
    manualMacroEdit = false;
    modalTitle.textContent = entry ? t('entry.editEntry') : t('entry.addFood');
    entryForm.reset();
    document.getElementById('entry-id').value = '';
    document.getElementById('entry-saved-food-id').value = '';
    autocompleteList.hidden = true;

    if (entry) {
      document.getElementById('entry-id').value           = entry.id;
      document.getElementById('entry-saved-food-id').value = entry.saved_food_id ?? '';
      foodNameInput.value                                  = entry.food_name;
      document.getElementById('entry-protein').value       = entry.protein;
      document.getElementById('entry-fat').value           = entry.fat;
      document.getElementById('entry-carbs').value         = entry.carbs;
      document.getElementById('entry-calories').value      = Math.round(entry.calories ?? 0);
      document.getElementById('entry-meal-type').value     = entry.meal_type;
      document.getElementById('entry-serving-size').value  = entry.serving_size;
      document.getElementById('entry-serving-unit').value  = entry.serving_unit;
      selectedFood = {
        protein: entry.protein ?? 0,
        fat: entry.fat ?? 0,
        carbs: entry.carbs ?? 0,
        calories: entry.calories ?? 0,
        default_serving: entry.serving_size ?? 100,
        serving_unit: entry.serving_unit ?? 'g',
      };
    }
    // Update modal option labels for current language
    applyTranslations();
    entryModal.hidden = false;
    foodNameInput.focus();
  }

  function closeModal() {
    entryModal.hidden = true;
    entryForm.reset();
    editingId = null;
    selectedFood = null;
    autocompleteList.hidden = true;
  }

  openAddFormBtn.addEventListener('click', () => openModal());
  closeModalBtn.addEventListener('click', closeModal);
  cancelEntryBtn.addEventListener('click', closeModal);
  entryModal.addEventListener('click', (e) => {
    if (e.target === entryModal) closeModal();
  });

  /* Prefill from a saved food / recent object */
  function prefillFromFood(food) {
    foodNameInput.value = food.food_name ?? food.name ?? '';
    document.getElementById('entry-protein').value      = food.protein ?? '';
    document.getElementById('entry-fat').value          = food.fat ?? '';
    document.getElementById('entry-carbs').value        = food.carbs ?? '';
    document.getElementById('entry-calories').value     = food.calories ? Math.round(food.calories) : '';
    document.getElementById('entry-serving-size').value = food.serving_size ?? food.default_serving ?? '';
    document.getElementById('entry-serving-unit').value = food.serving_unit ?? '';
    if (food.id) {
      document.getElementById('entry-saved-food-id').value = food.id;
    }
    selectedFood = {
      protein: food.protein ?? 0,
      fat: food.fat ?? 0,
      carbs: food.carbs ?? 0,
      calories: food.calories ?? 0,
      default_serving: food.default_serving ?? food.serving_size ?? 100,
      serving_unit: food.serving_unit ?? 'g',
    };
    manualMacroEdit = false;
  }

  /* ---- Food Name Autocomplete ---- */
  const debouncedSearch = debounce(async (q) => {
    if (q.length < 2) { autocompleteList.hidden = true; return; }
    try {
      const foods = await api(`/api/foods?q=${encodeURIComponent(q)}${Lang.langParam()}`);
      renderAutocomplete(foods);
    } catch (_) {
      autocompleteList.hidden = true;
    }
  }, 280);

  foodNameInput.addEventListener('input', () => {
    selectedFood = null;
    document.getElementById('entry-saved-food-id').value = '';
    debouncedSearch(foodNameInput.value.trim());
  });

  foodNameInput.addEventListener('keydown', (e) => {
    if (autocompleteList.hidden) return;
    const items = autocompleteList.querySelectorAll('li');
    const focused = autocompleteList.querySelector('li.focused');
    let idx = Array.from(items).indexOf(focused);
    if (e.key === 'ArrowDown') { e.preventDefault(); idx = Math.min(idx + 1, items.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); idx = Math.max(idx - 1, 0); }
    else if (e.key === 'Enter' && focused) { e.preventDefault(); focused.click(); return; }
    else if (e.key === 'Escape') { autocompleteList.hidden = true; return; }
    items.forEach((li, i) => li.classList.toggle('focused', i === idx));
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrap')) autocompleteList.hidden = true;
  });

  function renderAutocomplete(foods) {
    if (!foods || foods.length === 0) { autocompleteList.hidden = true; return; }
    autocompleteList.innerHTML = foods.slice(0, 10).map(f => {
      const brand = f.brand ? ` <span class="ac-sub">${escHtml(f.brand)}</span>` : '';
      const macros = `<span class="ac-sub">P:${round1(f.protein)}g F:${round1(f.fat)}g C:${round1(f.carbs)}g</span>`;
      return `<li role="option" tabindex="-1" data-food='${JSON.stringify(f).replace(/'/g, "&#39;")}'>${escHtml(Lang.foodName(f))}${brand} ${macros}</li>`;
    }).join('');
    autocompleteList.hidden = false;
  }

  autocompleteList.addEventListener('click', (e) => {
    const li = e.target.closest('li');
    if (!li) return;
    try {
      const food = JSON.parse(li.dataset.food);
      selectedFood = food;
      manualMacroEdit = false;
      foodNameInput.value = food.name;
      document.getElementById('entry-saved-food-id').value = food.id ?? '';
      document.getElementById('entry-protein').value       = food.protein ?? '';
      document.getElementById('entry-fat').value           = food.fat ?? '';
      document.getElementById('entry-carbs').value         = food.carbs ?? '';
      document.getElementById('entry-calories').value      = food.calories ? Math.round(food.calories) : '';
      document.getElementById('entry-serving-size').value  = food.default_serving ?? '';
      document.getElementById('entry-serving-unit').value  = food.serving_unit ?? '';
      autocompleteList.hidden = true;
    } catch (_) {}
  });

  /* ---- Serving-size scaling ---- */
  let manualMacroEdit = false;
  ['entry-protein', 'entry-fat', 'entry-carbs', 'entry-calories'].forEach(id => {
    document.getElementById(id).addEventListener('input', () => { manualMacroEdit = true; });
  });

  document.getElementById('entry-serving-size').addEventListener('input', () => {
    if (manualMacroEdit || !selectedFood) return;
    const baseServing = selectedFood.default_serving ?? selectedFood.serving_size;
    if (!baseServing || baseServing <= 0) return;
    const newServing = parseFloat(document.getElementById('entry-serving-size').value);
    if (!newServing || newServing <= 0) return;
    const ratio = newServing / baseServing;
    document.getElementById('entry-protein').value  = round1(selectedFood.protein * ratio);
    document.getElementById('entry-fat').value      = round1(selectedFood.fat * ratio);
    document.getElementById('entry-carbs').value    = round1(selectedFood.carbs * ratio);
    const baseCal = selectedFood.calories ?? ((selectedFood.protein * 4) + (selectedFood.fat * 9) + (selectedFood.carbs * 4));
    document.getElementById('entry-calories').value = Math.round(baseCal * ratio);
  });

  /* ---- Form Submit ---- */
  entryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const protein  = parseFloat(document.getElementById('entry-protein').value);
    const fat      = parseFloat(document.getElementById('entry-fat').value);
    const carbs    = parseFloat(document.getElementById('entry-carbs').value);
    const calRaw   = document.getElementById('entry-calories').value;
    const calories = calRaw !== '' ? parseFloat(calRaw) : (protein * 4) + (fat * 9) + (carbs * 4);

    const body = {
      food_name:    foodNameInput.value.trim(),
      protein,
      fat,
      carbs,
      calories,
      meal_type:    document.getElementById('entry-meal-type').value,
      serving_size: parseFloat(document.getElementById('entry-serving-size').value),
      serving_unit: document.getElementById('entry-serving-unit').value.trim(),
    };
    const sfId = document.getElementById('entry-saved-food-id').value;
    if (sfId) body.saved_food_id = parseInt(sfId, 10);

    const saveBtn = document.getElementById('save-entry-btn');
    saveBtn.disabled = true;
    try {
      if (editingId) {
        await api(`/api/entries/${editingId}`, { method: 'PUT', body: JSON.stringify(body) });
        showToast(t('common.success'), 'success');
      } else {
        body.entry_date = currentDate;
        const hadSavedFoodId = !!sfId;
        const result = await api('/api/entries', { method: 'POST', body: JSON.stringify(body) });
        showToast(t('common.success'), 'success');
        if (!hadSavedFoodId && result && result.food_auto_saved) {
          showToast('Food saved to library', 'success');
        }
      }
      closeModal();
      await loadPage();
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    } finally {
      saveBtn.disabled = false;
    }
  });

  /* ---- Edit / Delete via event delegation ---- */
  entriesList.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const id = btn.dataset.id;
    if (btn.dataset.action === 'edit') {
      try {
        const entries = await api(`/api/entries?date=${currentDate}`);
        const entry = entries.find(en => String(en.id) === String(id));
        if (entry) openModal(entry);
      } catch (err) {
        showToast(t('common.error') + ': ' + err.message, 'error');
      }
    } else if (btn.dataset.action === 'delete') {
      if (!confirm(t('common.delete') + '?')) return;
      try {
        await api(`/api/entries/${id}`, { method: 'DELETE' });
        showToast(t('common.success'), 'success');
        await loadPage();
      } catch (err) {
        showToast(t('common.error') + ': ' + err.message, 'error');
      }
    }
  });

  /* ---- Meal Template Chips ---- */
  const templateChipsList = document.getElementById('template-chips');

  async function loadTemplateChips() {
    try {
      const templates = await api('/api/meal-templates');
      if (!templates || templates.length === 0) {
        templateChipsList.innerHTML = '<p class="empty-msg">No templates yet. <a href="/meals">Create one</a></p>';
        return;
      }
      templateChipsList.innerHTML = templates.map(tpl =>
        `<button class="quick-add-chip" data-template-id="${tpl.id}">${escHtml(tpl.name)} <span class="chip-sub">${Math.round(tpl.total_calories)} kcal</span></button>`
      ).join('');
    } catch (_) {
      templateChipsList.innerHTML = '<p class="empty-msg">Could not load templates.</p>';
    }
  }

  templateChipsList.addEventListener('click', async (e) => {
    const chip = e.target.closest('[data-template-id]');
    if (!chip) return;
    chip.disabled = true;
    try {
      const result = await api(`/api/meal-templates/${chip.dataset.templateId}/log`, {
        method: 'POST',
        body: JSON.stringify({ date: currentDate }),
      });
      showToast(`Logged "${result.template}" (${result.logged} items)`, 'success');
      await loadPage();
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    } finally {
      chip.disabled = false;
    }
  });

  /* ---- Helpers ---- */
  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function round1(n) { return Math.round((n ?? 0) * 10) / 10; }

  /* ---- Start ---- */
  init();
})();