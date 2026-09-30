/* ============================================================
   foods.js — My Foods page logic
   ============================================================ */

(function () {
  'use strict';

  /* ---- State ---- */
  let customFoods  = [];
  let editingFoodId = null;

  /* ---- DOM ---- */
  const tabCustom         = document.getElementById('tab-custom');
  const tabUsda           = document.getElementById('tab-usda');
  const panelCustom       = document.getElementById('panel-custom');
  const panelUsda         = document.getElementById('panel-usda');
  const searchInput       = document.getElementById('foods-search-input');
  const customFoodsList   = document.getElementById('custom-foods-list');
  const usdaFoodsList     = document.getElementById('usda-foods-list');
  const openCustomFormBtn = document.getElementById('open-custom-food-form');
  const cfModal           = document.getElementById('custom-food-modal');
  const cfModalTitle      = document.getElementById('cf-modal-title');
  const closeCfModalBtn   = document.getElementById('close-custom-food-modal');
  const cancelCfBtn       = document.getElementById('cancel-custom-food');
  const cfForm            = document.getElementById('custom-food-form');

  /* ---- Import CSV DOM ---- */
  const openImportBtn     = document.getElementById('open-import-csv');
  const importModal       = document.getElementById('import-csv-modal');
  const closeImportBtn    = document.getElementById('close-import-modal');
  const cancelImportBtn   = document.getElementById('cancel-import-csv');
  const importForm        = document.getElementById('import-csv-form');
  const importFileInput   = document.getElementById('import-csv-file');
  const importSubmitBtn   = document.getElementById('import-csv-btn');
  const importResult      = document.getElementById('import-result');
  const importTemplateLink = document.getElementById('import-template-link');

  let activeTab = 'custom';

  /* ---- Init ---- */
  async function init() {
    await loadCustomFoods();
  }

  /* ---- Tabs ---- */
  tabCustom.addEventListener('click', () => switchTab('custom'));
  tabUsda.addEventListener('click',   () => switchTab('usda'));

  function switchTab(tab) {
    activeTab = tab;
    tabCustom.classList.toggle('active', tab === 'custom');
    tabUsda.classList.toggle('active', tab === 'usda');
    tabCustom.setAttribute('aria-selected', tab === 'custom');
    tabUsda.setAttribute('aria-selected', tab === 'usda');
    panelCustom.classList.toggle('hidden', tab !== 'custom');
    panelUsda.classList.toggle('hidden', tab !== 'usda');

    if (tab === 'usda') {
      const q = searchInput.value.trim();
      if (q.length >= 2) searchUsda(q);
      else usdaFoodsList.innerHTML = '<p class="empty-msg">' + escHtml(t('foods.searchMin')) + '</p>';
    }
  }

  /* ---- Recent Search History ---- */
  const HISTORY_KEY = 'nt_food_history';
  const HISTORY_MAX = 10;

  function getHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    } catch (_) { return []; }
  }

  function saveHistory(q) {
    if (!q || q.length < 2) return;
    try {
      let hist = getHistory().filter(s => s !== q);
      hist.unshift(q);
      if (hist.length > HISTORY_MAX) hist = hist.slice(0, HISTORY_MAX);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(hist));
    } catch (_) { /* storage may be unavailable */ }
  }

  function clearHistory() {
    try { localStorage.removeItem(HISTORY_KEY); } catch (_) {}
    hideHistoryDropdown();
  }

  /* ---- History Dropdown ---- */
  let historyDropdown = null;

  function showHistoryDropdown() {
    const hist = getHistory();
    if (!hist.length) return;

    hideHistoryDropdown();

    historyDropdown = document.createElement('ul');
    historyDropdown.className = 'autocomplete-list';
    historyDropdown.setAttribute('role', 'listbox');
    historyDropdown.style.cssText = 'position:absolute;z-index:200;width:100%;background:var(--color-card);border:1px solid var(--color-border);border-radius:var(--radius);margin-top:2px;padding:0;list-style:none;box-shadow:0 4px 12px rgba(0,0,0,.1);';

    hist.slice(0, 5).forEach(q => {
      const li = document.createElement('li');
      li.className = 'autocomplete-item';
      li.style.cssText = 'padding:.5rem .75rem;cursor:pointer;display:flex;align-items:center;gap:.5rem;color:var(--color-text-muted);font-size:.9rem;';
      li.innerHTML = '<span style="opacity:.55;font-size:.8em;">&#x1F552;</span> ' + escHtml(q);
      li.addEventListener('mousedown', (e) => {
        e.preventDefault();
        searchInput.value = q;
        hideHistoryDropdown();
        debouncedSearch(q);
      });
      historyDropdown.appendChild(li);
    });

    // Clear history option
    const clearLi = document.createElement('li');
    clearLi.style.cssText = 'padding:.4rem .75rem;cursor:pointer;color:var(--color-text-muted);font-size:.8rem;border-top:1px solid var(--color-border);';
    clearLi.textContent = t('foods.clearHistory');
    clearLi.addEventListener('mousedown', (e) => {
      e.preventDefault();
      clearHistory();
    });
    historyDropdown.appendChild(clearLi);

    const wrapper = searchInput.parentElement;
    wrapper.style.position = 'relative';
    wrapper.appendChild(historyDropdown);
  }

  function hideHistoryDropdown() {
    if (historyDropdown) {
      historyDropdown.remove();
      historyDropdown = null;
    }
  }

  searchInput.addEventListener('focus', () => {
    if (!searchInput.value.trim()) showHistoryDropdown();
  });

  searchInput.addEventListener('blur', () => {
    // Small delay so mousedown on dropdown items fires first
    setTimeout(hideHistoryDropdown, 150);
  });

  /* ---- Search ---- */
  const debouncedSearch = debounce((q) => {
    hideHistoryDropdown();
    if (activeTab === 'custom') filterCustom(q);
    else searchUsda(q);
  }, 280);

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim();
    if (!q) {
      showHistoryDropdown();
    } else {
      hideHistoryDropdown();
    }
    debouncedSearch(q);
  });

  function filterCustom(q) {
    if (!q) {
      renderCustomFoods(customFoods);
      return;
    }
    const lower = q.toLowerCase();
    renderCustomFoods(customFoods.filter(f =>
      f.name.toLowerCase().includes(lower) ||
      (f.brand || '').toLowerCase().includes(lower)
    ));
  }

  async function searchUsda(q) {
    if (q.length < 2) {
      usdaFoodsList.innerHTML = '<p class="empty-msg">' + escHtml(t('foods.searchMin')) + '</p>';
      return;
    }
    usdaFoodsList.innerHTML = '<p class="empty-msg">' + t('common.loading') + '</p>';
    try {
      const foods = await api(`/api/foods?q=${encodeURIComponent(q)}${Lang.langParam()}`);
      const usda = (foods || []).filter(f => f.source === 'usda');
      renderUsdaFoods(usda);
      // Save to recent history only on a successful search with results
      if (usda.length > 0) saveHistory(q);
    } catch (err) {
      usdaFoodsList.innerHTML = '<p class="empty-msg">' + escHtml(t('common.loadError')) + '</p>';
      showToast(t('common.error') + ': ' + err.message, 'error');
    }
  }

  /* ---- Custom Foods ---- */
  async function loadCustomFoods() {
    try {
      const foods = await api('/api/foods?q=&source=custom');
      customFoods = (foods || []).filter(f => !f.is_archived);
      renderCustomFoods(customFoods);
    } catch (err) {
      customFoodsList.innerHTML = '<p class="empty-msg">' + escHtml(t('common.loadError')) + '</p>';
      showToast(t('common.error') + ': ' + err.message, 'error');
    }
  }

  function renderCustomFoods(foods) {
    if (!foods || foods.length === 0) {
      customFoodsList.innerHTML = '<p class="empty-msg">' + escHtml(t('foods.noCustom')) + '</p>';
      return;
    }
    customFoodsList.innerHTML = foods.map(f => renderFoodCard(f, true)).join('');
  }

  function renderUsdaFoods(foods) {
    if (!foods || foods.length === 0) {
      usdaFoodsList.innerHTML = '<p class="empty-msg">' + escHtml(t('foods.noUsda')) + '</p>';
      return;
    }
    usdaFoodsList.innerHTML = foods.map(f => renderFoodCard(f, false)).join('');
  }

  function renderFoodCard(f, isCustom) {
    const brand = f.brand ? ` &mdash; ${escHtml(f.brand)}` : '';
    const serving = `${f.default_serving} ${escHtml(f.serving_unit)}`;
    const mealBadge = (f.food_type === 'meal') ? ' <span class="badge badge--meal">' + escHtml(t('foods.mealBadge')) + '</span>' : '';
    const sourceBadge = isCustom
      ? '<span class="badge badge--custom">Custom</span>'
      : (f.source === 'off' ? '<span class="badge badge--off">OpenFoodFacts</span>' : '<span class="badge badge--usda">USDA</span>');

    let actions = '';
    if (isCustom) {
      actions = `
        <button class="btn btn-sm btn-outline" data-action="edit" data-id="${f.id}" title="${escHtml(t('foods.edit'))}">${escHtml(t('foods.edit'))}</button>
        <button class="btn btn-sm btn-danger" data-action="delete" data-id="${f.id}" title="${escHtml(t('foods.delete'))}">${escHtml(t('foods.delete'))}</button>`;
    } else {
      actions = `
        <button class="btn btn-sm btn-outline" data-action="clone" data-id="${f.id}" title="${escHtml(t('foods.clone'))}">${escHtml(t('foods.clone'))}</button>`;
    }

    return `<article class="food-card" data-id="${f.id}">
      <div class="food-card__info">
        <p class="food-card__name">${escHtml(f.name)}${sourceBadge}${mealBadge}${brand}</p>
        <p class="food-card__meta">${escHtml(t('foods.serving'))}: ${escHtml(serving)}</p>
        <div class="food-card__macros">
          <span class="macro-tag macro-tag--protein">P: ${r1(f.protein)}g</span>
          <span class="macro-tag macro-tag--fat">F: ${r1(f.fat)}g</span>
          <span class="macro-tag macro-tag--carbs">C: ${r1(f.carbs)}g</span>
          <span class="macro-tag macro-tag--cal">${Math.round(f.calories ?? 0)} kcal</span>
        </div>
      </div>
      <div class="food-card__actions">${actions}</div>
    </article>`;
  }

  /* ---- Event Delegation for food list actions ---- */
  customFoodsList.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const id = btn.dataset.id;
    if (btn.dataset.action === 'edit') {
      const food = customFoods.find(f => String(f.id) === String(id));
      if (food) openCfModal(food);
    } else if (btn.dataset.action === 'delete') {
      if (!confirm(t('foods.delete') + '?')) return;
      try {
        await api(`/api/foods/${id}`, { method: 'DELETE' });
        showToast(t('common.success'), 'success');
        await loadCustomFoods();
      } catch (err) {
        showToast(t('common.error') + ': ' + err.message, 'error');
      }
    }
  });

  usdaFoodsList.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn || btn.dataset.action !== 'clone') return;
    const id = btn.dataset.id;
    btn.disabled = true;
    btn.textContent = t('common.loading');
    try {
      await api(`/api/foods/${id}/clone`, { method: 'POST' });
      showToast(t('common.success'), 'success');
      await loadCustomFoods();
      switchTab('custom');
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
      btn.disabled = false;
      btn.textContent = t('foods.clone');
    }
  });

  /* ---- Custom Food Modal ---- */
  function openCfModal(food = null) {
    editingFoodId = food ? food.id : null;
    cfModalTitle.textContent = food ? t('foods.editTitle') : t('foods.addTitle');
    cfForm.reset();
    document.getElementById('cf-id').value = '';

    if (food) {
      document.getElementById('cf-id').value              = food.id;
      document.getElementById('cf-name').value            = food.name;
      document.getElementById('cf-brand').value           = food.brand ?? '';
      document.getElementById('cf-category').value        = food.category ?? '';
      document.getElementById('food-type').value          = food.food_type ?? 'ingredient';
      document.getElementById('cf-protein').value         = food.protein;
      document.getElementById('cf-fat').value             = food.fat;
      document.getElementById('cf-carbs').value           = food.carbs;
      document.getElementById('cf-calories').value        = Math.round(food.calories ?? 0);
      document.getElementById('cf-fiber').value           = food.fiber ?? '';
      document.getElementById('cf-sugar').value           = food.sugar ?? '';
      document.getElementById('cf-default-serving').value = food.default_serving;
      document.getElementById('cf-serving-unit').value    = food.serving_unit;
    }
    cfModal.hidden = false;
    document.getElementById('cf-name').focus();
  }

  function closeCfModal() {
    cfModal.hidden = true;
    cfForm.reset();
    editingFoodId = null;
  }

  openCustomFormBtn.addEventListener('click', () => openCfModal());
  closeCfModalBtn.addEventListener('click', closeCfModal);
  cancelCfBtn.addEventListener('click', closeCfModal);
  cfModal.addEventListener('click', (e) => { if (e.target === cfModal) closeCfModal(); });

  cfForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      name:            document.getElementById('cf-name').value.trim(),
      brand:           document.getElementById('cf-brand').value.trim() || undefined,
      category:        document.getElementById('cf-category').value.trim() || undefined,
      food_type:       document.getElementById('food-type').value,
      protein:         parseFloat(document.getElementById('cf-protein').value),
      fat:             parseFloat(document.getElementById('cf-fat').value),
      carbs:           parseFloat(document.getElementById('cf-carbs').value),
      calories:        parseFloat(document.getElementById('cf-calories').value),
      fiber:           document.getElementById('cf-fiber').value !== '' ? parseFloat(document.getElementById('cf-fiber').value) : undefined,
      sugar:           document.getElementById('cf-sugar').value !== '' ? parseFloat(document.getElementById('cf-sugar').value) : undefined,
      default_serving: parseFloat(document.getElementById('cf-default-serving').value),
      serving_unit:    document.getElementById('cf-serving-unit').value.trim(),
    };
    // Remove undefined keys
    Object.keys(body).forEach(k => body[k] === undefined && delete body[k]);

    const saveBtn = document.getElementById('save-custom-food-btn');
    saveBtn.disabled = true;
    try {
      if (editingFoodId) {
        await api(`/api/foods/${editingFoodId}`, { method: 'PUT', body: JSON.stringify(body) });
        showToast(t('common.success'), 'success');
      } else {
        await api('/api/foods', { method: 'POST', body: JSON.stringify(body) });
        showToast(t('common.success'), 'success');
      }
      closeCfModal();
      await loadCustomFoods();
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    } finally {
      saveBtn.disabled = false;
    }
  });

  /* ---- Import CSV Modal ---- */
  function openImportModal() {
    importForm.reset();
    importResult.style.display = 'none';
    importResult.textContent = '';
    importSubmitBtn.disabled = false;
    importModal.hidden = false;
  }

  function closeImportModal() {
    importModal.hidden = true;
    importForm.reset();
    importResult.style.display = 'none';
  }

  openImportBtn.addEventListener('click', openImportModal);
  closeImportBtn.addEventListener('click', closeImportModal);
  cancelImportBtn.addEventListener('click', closeImportModal);
  importModal.addEventListener('click', (e) => { if (e.target === importModal) closeImportModal(); });

  // Generate and download a CSV template
  importTemplateLink.addEventListener('click', (e) => {
    e.preventDefault();
    const csvContent = 'name,protein,fat,carbs,calories,serving_size,serving_unit\n' +
      'Chicken Breast,31,3.6,0,165,100,g\n' +
      'Greek Yogurt,10,0.7,3.6,59,100,g\n';
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'foods_template.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  importForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = importFileInput.files[0];
    if (!file) {
      showToast(t('common.error') + ': Please select a CSV file', 'error');
      return;
    }
    importSubmitBtn.disabled = true;
    importResult.style.display = 'none';
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/foods/import', {
        method: 'POST',
        body: formData,
        // Do NOT set Content-Type — browser sets multipart boundary automatically
      });
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try { const b = await res.json(); msg = b.error || msg; } catch (_) {}
        throw new Error(msg);
      }
      const data = await res.json();
      const msg = t('foods.importResult')
        .replace('{imported}', data.imported)
        .replace('{skipped}', data.skipped);
      importResult.textContent = msg + (data.errors && data.errors.length ? ' (' + data.errors.join('; ') + ')' : '');
      importResult.style.display = 'block';
      showToast(msg, data.imported > 0 ? 'success' : 'info');
      if (data.imported > 0) {
        await loadCustomFoods();
        switchTab('custom');
      }
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    } finally {
      importSubmitBtn.disabled = false;
    }
  });

  /* ---- Helpers ---- */
  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function r1(n) { return Math.round((n ?? 0) * 10) / 10; }

  init();
})();