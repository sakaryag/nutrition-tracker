/* ============================================================
   settings.js — Settings page logic
   ============================================================ */

(function () {
  'use strict';

  // ----------------------------------------------------------------
  // Existing Daily Targets form
  // ----------------------------------------------------------------
  const form         = document.getElementById('targets-form');
  const successAlert = document.getElementById('settings-success');
  const saveBtn      = document.getElementById('save-targets-btn');

  async function init() {
    try {
      const targets = await api('/api/targets');
      if (targets) {
        document.getElementById('target-protein').value  = targets.protein  ?? '';
        document.getElementById('target-fat').value      = targets.fat      ?? '';
        document.getElementById('target-carbs').value    = targets.carbs    ?? '';
        document.getElementById('target-calories').value = targets.calories ?? '';
      }
    } catch (err) {
      showToast(t('common.loadError') + ' ' + err.message, 'error');
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    successAlert.hidden = true;
    saveBtn.disabled = true;

    const body = {
      protein:  parseFloat(document.getElementById('target-protein').value),
      fat:      parseFloat(document.getElementById('target-fat').value),
      carbs:    parseFloat(document.getElementById('target-carbs').value),
      calories: parseFloat(document.getElementById('target-calories').value),
    };

    try {
      await api('/api/targets', { method: 'POST', body: JSON.stringify(body) });
      successAlert.hidden = false;
      showToast(t('settings.targetsSaved'), 'success');
      setTimeout(() => { successAlert.hidden = true; }, 4000);
    } catch (err) {
      showToast('Error saving targets: ' + err.message, 'error');
    } finally {
      saveBtn.disabled = false;
    }
  });

  // ----------------------------------------------------------------
  // TDEE Calculator
  // ----------------------------------------------------------------
  (function initTdee() {
    const tdeeForm      = document.getElementById('tdee-form');
    const resultsEl     = document.getElementById('tdee-results');
    const customSplitEl = document.getElementById('custom-split');
    const pctTotalEl    = document.getElementById('pct-total');
    const applyBtn      = document.getElementById('apply-tdee');

    // Track the active preset
    let activePreset = 'balanced';

    // --- Preset button toggle ---
    tdeeForm.querySelectorAll('.btn-preset').forEach(function (btn) {
      btn.addEventListener('click', function () {
        tdeeForm.querySelectorAll('.btn-preset').forEach(function (b) {
          b.classList.remove('active');
        });
        btn.classList.add('active');
        activePreset = btn.dataset.preset;
        customSplitEl.hidden = (activePreset !== 'custom');
        if (activePreset === 'custom') {
          updatePctTotal();
        }
      });
    });

    // --- Custom split: live total ---
    function updatePctTotal() {
      var p = parseFloat(document.getElementById('custom-protein-pct').value) || 0;
      var f = parseFloat(document.getElementById('custom-fat-pct').value)     || 0;
      var c = parseFloat(document.getElementById('custom-carbs-pct').value)   || 0;
      var total = p + f + c;
      pctTotalEl.textContent = t('settings.macroTotal').replace('{pct}', total);
      if (Math.abs(total - 100) > 0.5) {
        pctTotalEl.classList.add('error');
      } else {
        pctTotalEl.classList.remove('error');
      }
    }

    ['custom-protein-pct', 'custom-fat-pct', 'custom-carbs-pct'].forEach(function (id) {
      document.getElementById(id).addEventListener('input', updatePctTotal);
    });

    // --- TDEE form submit ---
    tdeeForm.addEventListener('submit', async function (e) {
      e.preventDefault();

      // Validate custom split sums to 100 before sending
      if (activePreset === 'custom') {
        var p = parseFloat(document.getElementById('custom-protein-pct').value) || 0;
        var f = parseFloat(document.getElementById('custom-fat-pct').value)     || 0;
        var c = parseFloat(document.getElementById('custom-carbs-pct').value)   || 0;
        if (Math.abs(p + f + c - 100) > 0.5) {
          showToast(t('settings.macroMustAdd'), 'error');
          return;
        }
      }

      var body = {
        gender:         document.getElementById('tdee-gender').value,
        age:            parseFloat(document.getElementById('tdee-age').value),
        weight_kg:      parseFloat(document.getElementById('tdee-weight').value),
        height_cm:      parseFloat(document.getElementById('tdee-height').value),
        activity_level: document.getElementById('tdee-activity').value,
        goal:           document.getElementById('tdee-goal').value,
        preset:         activePreset,
      };

      if (activePreset === 'custom') {
        body.custom_split = {
          protein_pct: parseFloat(document.getElementById('custom-protein-pct').value),
          fat_pct:     parseFloat(document.getElementById('custom-fat-pct').value),
          carbs_pct:   parseFloat(document.getElementById('custom-carbs-pct').value),
        };
      }

      try {
        var result = await api('/api/targets/calculate', {
          method: 'POST',
          body: JSON.stringify(body),
        });

        // Cache body stats for water suggestion
        localStorage.setItem('nt_tdee_weight', body.weight_kg);
        localStorage.setItem('nt_tdee_activity', body.activity_level);

        // Populate result display
        document.getElementById('result-bmr').textContent      = result.bmr;
        document.getElementById('result-tdee').textContent     = result.tdee;
        document.getElementById('result-calories').textContent = result.calories;
        document.getElementById('result-protein').textContent  = result.protein;
        document.getElementById('result-fat').textContent      = result.fat;
        document.getElementById('result-carbs').textContent    = result.carbs;

        resultsEl.hidden = false;
        resultsEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } catch (err) {
        showToast('Calculation error: ' + err.message, 'error');
      }
    });

    // --- Apply as My Targets ---
    applyBtn.addEventListener('click', function () {
      document.getElementById('target-protein').value  = document.getElementById('result-protein').textContent;
      document.getElementById('target-fat').value      = document.getElementById('result-fat').textContent;
      document.getElementById('target-carbs').value    = document.getElementById('result-carbs').textContent;
      document.getElementById('target-calories').value = document.getElementById('result-calories').textContent;

      // Auto-submit the targets form
      form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));

      // Scroll to the targets form so the user can see it saved
      form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  })();

  init();

  // ----------------------------------------------------------------
  // Water Goal
  // ----------------------------------------------------------------
  (function () {
    var waterInput    = document.getElementById('water-goal-input');
    var waterSaveBtn  = document.getElementById('water-goal-save-btn');
    var waterSuggest  = document.getElementById('water-goal-suggest-btn');
    var waterHint     = document.getElementById('water-goal-hint');
    if (!waterInput) return;

    // Suggestion formula: 35ml × weight_kg, +500ml if active/very_active, rounded to nearest 250ml
    // We pull {weight_kg, activity_level} from localStorage (stored when TDEE form is used)
    function suggestedGoal() {
      var w = parseFloat(localStorage.getItem('nt_tdee_weight') || '0');
      var a = localStorage.getItem('nt_tdee_activity') || 'moderate';
      if (!w) return null;
      var base = 35 * w;
      if (a === 'active' || a === 'very_active') base += 500;
      // round to nearest 250
      return Math.round(base / 250) * 250;
    }

    // Load current goal from targets API
    api('/api/targets').then(function (t) {
      if (t && t.water_goal_ml) {
        waterInput.value = Math.round(t.water_goal_ml);
        waterHint.textContent = t('settings.waterGoalCurrent')
          .replace('{ml}', Math.round(t.water_goal_ml))
          .replace('{L}', (t.water_goal_ml / 1000).toFixed(1));
      } else {
        waterInput.placeholder = '2000';
        var suggested = suggestedGoal();
        if (suggested) {
          waterHint.textContent = t('settings.waterGoalNoTarget').replace('{ml}', suggested);
        }
      }
    }).catch(function () {});

    waterSuggest.addEventListener('click', function () {
      var w = parseFloat(localStorage.getItem('nt_tdee_weight') || '0');
      var a = localStorage.getItem('nt_tdee_activity') || '';
      if (!w) {
        waterHint.textContent = t('settings.waterGoalNeedWeight');
        waterHint.style.color = 'var(--color-danger)';
        return;
      }
      var goal = suggestedGoal();
      waterInput.value = goal;
      var actLabel = { sedentary: 'sedentary', light: 'light', moderate: 'moderate', active: 'active', very_active: 'very active' }[a] || a;
      waterHint.textContent = t('settings.waterGoalSuggested')
        .replace('{ml}', goal)
        .replace('{L}', (goal / 1000).toFixed(1))
        .replace('{kg}', w)
        .replace('{activity}', actLabel);
      waterHint.style.color = 'var(--color-success)';
    });

    waterSaveBtn.addEventListener('click', async function () {
      var goal = parseFloat(waterInput.value);
      if (!goal || goal < 500 || goal > 6000) {
        showToast(t('settings.waterGoalInvalid'), 'error');
        return;
      }
      waterSaveBtn.disabled = true;
      try {
        // Load current macro targets, then POST with water_goal_ml added
        var current = await api('/api/targets');
        await api('/api/targets', {
          method: 'POST',
          body: JSON.stringify({
            protein:      current.protein,
            fat:          current.fat,
            carbs:        current.carbs,
            calories:     current.calories,
            water_goal_ml: goal,
          }),
        });
        waterHint.textContent = t('settings.waterGoalCurrent')
          .replace('{ml}', goal)
          .replace('{L}', (goal / 1000).toFixed(1));
        waterHint.style.color = 'var(--color-success)';
        showToast(t('settings.waterGoalSaved'), 'success');
      } catch (err) {
        showToast('Error: ' + err.message, 'error');
      } finally {
        waterSaveBtn.disabled = false;
      }
    });
  })();

  // ----------------------------------------------------------------
  // API Key management
  // ----------------------------------------------------------------
  (function () {
    const keyInput    = document.getElementById('anthropic-api-key');
    const saveKeyBtn  = document.getElementById('save-api-key-btn');
    const clearKeyBtn = document.getElementById('clear-api-key-btn');
    const keyStatus   = document.getElementById('api-key-status');

    function updateKeyStatus() {
      const key = localStorage.getItem('nt_anthropic_key') || '';
      if (key) {
        keyStatus.textContent = '✓ Key saved (ends in …' + key.slice(-6) + ')';
        keyStatus.style.color = 'var(--color-success)';
        keyInput.value = '';
        keyInput.placeholder = '••••••••••••••••••••';
      } else {
        keyStatus.textContent = 'No key saved — AI features (chat upgrade, photo recognition) require a key.';
        keyStatus.style.color = 'var(--color-text-muted)';
        keyInput.placeholder = 'sk-ant-api03-...';
      }
    }

    saveKeyBtn.addEventListener('click', function () {
      const val = keyInput.value.trim();
      if (!val) { keyStatus.textContent = 'Please enter a key first.'; return; }
      if (!val.startsWith('sk-ant-')) { keyStatus.textContent = 'Key should start with sk-ant-'; keyStatus.style.color = 'var(--color-danger)'; return; }
      localStorage.setItem('nt_anthropic_key', val);
      updateKeyStatus();
      updateUsage();
    });

    clearKeyBtn.addEventListener('click', function () {
      localStorage.removeItem('nt_anthropic_key');
      updateKeyStatus();
      updateUsage();
    });

    updateKeyStatus();
  })();

  // ----------------------------------------------------------------
  // Model selector
  // ----------------------------------------------------------------
  (function () {
    const sel = document.getElementById('ai-model-select');
    if (!sel) return;
    sel.value = ApiUsage.getModel();
    sel.addEventListener('change', function () {
      ApiUsage.setModel(sel.value);
      showToast('Model updated', 'success');
    });
  })();

  // ----------------------------------------------------------------
  // Monthly budget
  // ----------------------------------------------------------------
  function updateUsage() {
    const spent  = ApiUsage.getSpent();
    const budget = ApiUsage.getBudget();
    const hasKey = !!(localStorage.getItem('nt_anthropic_key') || '');

    document.getElementById('usage-cost').textContent = '$' + spent.toFixed(3);

    const ofEl  = document.getElementById('usage-budget-of');
    const barWr = document.getElementById('usage-bar-wrap');
    const bar   = document.getElementById('usage-bar');

    if (budget > 0) {
      const pct = Math.min(100, (spent / budget) * 100);
      ofEl.textContent = ' of $' + budget.toFixed(2) + ' limit';
      barWr.style.display = 'block';
      bar.style.width = pct + '%';
      bar.style.background = pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : 'var(--color-primary,#3b82f6)';
    } else {
      ofEl.textContent = hasKey ? ' (no limit set)' : ' (no key)';
      barWr.style.display = 'none';
    }
  }

  (function () {
    const budgetInput = document.getElementById('monthly-budget');
    const saveBudgetBtn = document.getElementById('save-budget-btn');
    if (!budgetInput) return;
    budgetInput.value = ApiUsage.getBudget() || '';
    saveBudgetBtn.addEventListener('click', function () {
      const v = parseFloat(budgetInput.value) || 0;
      ApiUsage.setBudget(v);
      showToast(v > 0 ? 'Budget set to $' + v.toFixed(2) + '/month' : 'Budget limit removed', 'success');
      updateUsage();
    });
    updateUsage();
  })();
})();
