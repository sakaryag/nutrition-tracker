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
      else usdaFoodsList.innerHTML = '<p class="empty-msg">Type at least 2 characters to search USDA foods.</p>';
    }
  }

  /* ---- Search ---- */
  const debouncedSearch = debounce((q) => {
    if (activeTab === 'custom') filterCustom(q);
    else searchUsda(q);
  }, 280);

  searchInput.addEventListener('input', () => {
    debouncedSearch(searchInput.value.trim());
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
      usdaFoodsList.innerHTML = '<p class="empty-msg">Type at least 2 characters to search USDA foods.</p>';
      return;
    }
    usdaFoodsList.innerHTML = '<p class="empty-msg">' + t('common.loading') + '</p>';
    try {
      const foods = await api(`/api/foods?q=${encodeURIComponent(q)}${Lang.langParam()}`);
      const usda = (foods || []).filter(f => f.source === 'usda');
      renderUsdaFoods(usda);
    } catch (err) {
      usdaFoodsList.innerHTML = '<p class="empty-msg">Search failed.</p>';
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
      customFoodsList.innerHTML = '<p class="empty-msg">Could not load foods.</p>';
      showToast(t('common.error') + ': ' + err.message, 'error');
    }
  }

  function renderCustomFoods(foods) {
    if (!foods || foods.length === 0) {
      customFoodsList.innerHTML = '<p class="empty-msg">No custom foods yet. Click &ldquo;+ Add Custom Food&rdquo; to create one.</p>';
      return;
    }
    customFoodsList.innerHTML = foods.map(f => renderFoodCard(f, true)).join('');
  }

  function renderUsdaFoods(foods) {
    if (!foods || foods.length === 0) {
      usdaFoodsList.innerHTML = '<p class="empty-msg">No USDA foods found.</p>';
      return;
    }
    usdaFoodsList.innerHTML = foods.map(f => renderFoodCard(f, false)).join('');
  }

  function renderFoodCard(f, isCustom) {
    const brand = f.brand ? ` &mdash; ${escHtml(f.brand)}` : '';
    const macros = `P: ${r1(f.protein)}g &nbsp; F: ${r1(f.fat)}g &nbsp; C: ${r1(f.carbs)}g &nbsp; ${Math.round(f.calories ?? 0)} kcal`;
    const serving = `${f.default_serving} ${escHtml(f.serving_unit)}`;
    const mealBadge = (f.food_type === 'meal') ? ' <span class="badge badge--meal">(meal)</span>' : '';

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
        <p class="food-card__name">${escHtml(f.name)}${mealBadge}${brand}</p>
        <p class="food-card__meta">${escHtml(t('foods.serving'))}: ${escHtml(serving)}</p>
        <div class="food-card__macros">${macros}</div>
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

  /* ---- Helpers ---- */
  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function r1(n) { return Math.round((n ?? 0) * 10) / 10; }

  init();
})();