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
      showToast('Could not load targets: ' + err.message, 'error');
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
      showToast('Targets saved!', 'success');
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
      pctTotalEl.textContent = 'Total: ' + total + '%';
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
          showToast('Custom macro percentages must add up to 100%', 'error');
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
})();
