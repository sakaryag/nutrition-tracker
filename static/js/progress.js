/* Goal Progress page — weight log, goal %, BMI. */
(function () {
  'use strict';

  const STR = {
    en: {
      title: 'Goal Progress', goalWeight: 'Goal weight', currentWeight: 'Current weight',
      updateGoal: 'Update my goal', updateWeight: 'Update weight', goalProgress: 'Goal Progress',
      range: 'Range', weekly: 'Weekly', monthly: 'Monthly', all: 'All',
      emptyChart: 'No weigh-ins yet. Tap “Update weight” to log your first one.',
      bmiTitle: 'Your BMI (Body Mass Index)', yourWeightIs: 'Your weight is',
      underweight: 'Underweight', healthy: 'Healthy', overweight: 'Overweight', obese: 'Obese',
      addHeight: 'Add height', recent: 'Recent weigh-ins', emptyHistory: 'Your weigh-ins will show up here.',
      goalWeightKg: 'Goal weight (kg)', heightCm: 'Height (cm)', weightKg: 'Weight (kg)', date: 'Date',
      save: 'Save', good: 'Good', on_track: 'On track', keep_going: 'Keep going',
      setGoal: 'Set a goal to see progress', needHeight: 'Add your height to calculate BMI.',
      needWeight: 'Log your weight to calculate BMI.', saved: 'Saved', deleted: 'Weigh-in deleted',
      del: 'Delete', weightRange: 'Enter a weight between 20 and 400 kg.',
      heightRange: 'Enter a height between 80 and 250 cm.', futureDate: 'Date cannot be in the future.',
    },
    tr: {
      title: 'Hedef İlerlemesi', goalWeight: 'Hedef kilo', currentWeight: 'Mevcut kilo',
      updateGoal: 'Hedefimi güncelle', updateWeight: 'Kiloyu güncelle', goalProgress: 'Hedef İlerlemesi',
      range: 'Aralık', weekly: 'Haftalık', monthly: 'Aylık', all: 'Tümü',
      emptyChart: 'Henüz tartı kaydı yok. İlk kaydınız için “Kiloyu güncelle”ye dokunun.',
      bmiTitle: 'Vücut Kitle İndeksiniz (VKİ)', yourWeightIs: 'Kilonuz',
      underweight: 'Zayıf', healthy: 'Sağlıklı', overweight: 'Fazla kilolu', obese: 'Obez',
      addHeight: 'Boy ekle', recent: 'Son tartılar', emptyHistory: 'Tartı kayıtlarınız burada görünecek.',
      goalWeightKg: 'Hedef kilo (kg)', heightCm: 'Boy (cm)', weightKg: 'Kilo (kg)', date: 'Tarih',
      save: 'Kaydet', good: 'İyi', on_track: 'Yolunda', keep_going: 'Devam et',
      setGoal: 'İlerlemeyi görmek için hedef belirleyin', needHeight: 'VKİ hesaplamak için boyunuzu ekleyin.',
      needWeight: 'VKİ hesaplamak için kilonuzu girin.', saved: 'Kaydedildi', deleted: 'Tartı silindi',
      del: 'Sil', weightRange: '20 ile 400 kg arasında bir değer girin.',
      heightRange: '80 ile 250 cm arasında bir değer girin.', futureDate: 'Tarih gelecekte olamaz.',
    },
  };
  const lang = () => (typeof Lang !== 'undefined' && Lang.get() === 'tr' ? 'tr' : 'en');
  const t = (k) => STR[lang()][k] || STR.en[k] || k;

  const $ = (id) => document.getElementById(id);
  const BMI_MIN = 15, BMI_MAX = 40;
  let state = null;
  let chart = null;

  const fmtKg = (v) => (v == null ? '—' : (Math.round(v * 10) / 10).toString());

  function applyStrings() {
    document.querySelectorAll('[data-pt]').forEach((el) => { el.textContent = t(el.dataset.pt); });
  }

  function fmtDate(iso, short) {
    const d = parseLocalDate(iso);
    const opts = short ? { day: 'numeric', month: 'short' } : { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' };
    return d.toLocaleDateString(lang() === 'tr' ? 'tr-TR' : 'en-US', opts);
  }

  async function load() {
    try {
      state = await api('/api/progress?range=' + encodeURIComponent($('pg-range').value));
      render();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  function render() {
    if (!state) return;
    $('pg-goal-value').textContent = fmtKg(state.goal_weight_kg);
    $('pg-current-value').textContent = fmtKg(state.current_weight_kg);
    renderProgress();
    renderChart();
    renderBmi();
    renderHistory();
  }

  function renderProgress() {
    const pct = state.progress_pct;
    $('pg-pct').textContent = pct == null ? '—' : pct + '%';
    const status = $('pg-status');
    status.className = 'pg-status';
    if (pct == null) {
      status.textContent = state.current_weight_kg == null ? '' : t('setGoal');
    } else {
      status.textContent = t(state.progress_status);
      status.classList.add('pg-status--' + state.progress_status);
    }
  }

  function renderChart() {
    const logs = state.logs || [];
    const empty = logs.length === 0;
    $('pg-chart-wrap').hidden = empty;
    $('pg-chart-empty').hidden = !empty;
    if (empty) {
      if (chart) { chart.destroy(); chart = null; }
      return;
    }
    const canvas = $('pg-chart');
    const ctx = canvas.getContext('2d');
    const labels = logs.map((l) => fmtDate(l.date, true));
    const data = logs.map((l) => l.weight_kg);
    const hi = data.length - 1;

    const gradient = (c) => {
      const area = c.chart.chartArea;
      if (!area) return 'rgba(139,104,246,0.25)';
      const g = c.chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
      g.addColorStop(0, 'rgba(139,104,246,0.25)');
      g.addColorStop(1, 'rgba(139,104,246,0)');
      return g;
    };

    const lastLabel = {
      id: 'pgLastLabel',
      afterDatasetsDraw(c) {
        const pt = c.getDatasetMeta(0).data[hi];
        if (!pt) return;
        const text = fmtKg(data[hi]) + ' kg';
        const g = c.ctx;
        g.save();
        g.font = '600 12px Inter, system-ui, sans-serif';
        const w = g.measureText(text).width + 16, h = 24;
        let x = pt.x - w / 2;
        x = Math.max(c.chartArea.left, Math.min(x, c.chartArea.right - w));
        const y = Math.max(2, pt.y - h - 12);
        g.fillStyle = '#8B68F6';
        g.beginPath();
        if (g.roundRect) g.roundRect(x, y, w, h, 12); else g.rect(x, y, w, h);
        g.fill();
        g.fillStyle = '#fff';
        g.textAlign = 'center';
        g.textBaseline = 'middle';
        g.fillText(text, x + w / 2, y + h / 2);
        g.restore();
      },
    };

    const goal = state.goal_weight_kg;
    const yVals = goal != null ? data.concat([goal]) : data;
    const yMin = Math.floor(Math.min(...yVals) - 2);
    const yMax = Math.ceil(Math.max(...yVals) + 3);

    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data,
          borderColor: '#8B68F6',
          borderWidth: 3,
          tension: 0.4,
          fill: true,
          backgroundColor: gradient,
          pointBackgroundColor: '#fff',
          pointBorderColor: '#8B68F6',
          pointBorderWidth: 2,
          pointRadius: data.map((_, i) => (i === hi ? 6 : 3.5)),
          pointHoverRadius: 7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 36, right: 8 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#8B68F6', displayColors: false, cornerRadius: 12, padding: 8,
            callbacks: { label: (c) => fmtKg(c.parsed.y) + ' kg' },
          },
        },
        scales: {
          x: {
            grid: { display: false }, border: { display: false },
            ticks: { color: '#9CA3AF', maxTicksLimit: 7, font: { size: 11 } },
          },
          y: {
            min: yMin, max: yMax,
            grid: { color: '#ECEAF3' },
            border: { display: false, dash: [4, 4] },
            ticks: { color: '#9CA3AF', maxTicksLimit: 5, font: { size: 11 } },
          },
        },
      },
      plugins: [lastLabel],
    });
  }

  function renderBmi() {
    const ok = state.bmi != null;
    $('pg-bmi-body').hidden = !ok;
    $('pg-bmi-empty').hidden = ok;
    if (!ok) {
      const noHeight = state.height_cm == null;
      $('pg-bmi-empty-msg').textContent = noHeight ? t('needHeight') : t('needWeight');
      $('pg-add-height').hidden = !noHeight;
      return;
    }
    $('pg-bmi-value').textContent = state.bmi.toFixed(1);
    const pill = $('pg-bmi-pill');
    pill.className = 'pg-bmi-pill pg-bmi-pill--' + state.bmi_category;
    pill.textContent = t(state.bmi_category);
    const clamped = Math.max(BMI_MIN, Math.min(BMI_MAX, state.bmi));
    $('pg-bmi-marker').style.left = ((clamped - BMI_MIN) / (BMI_MAX - BMI_MIN) * 100) + '%';
  }

  function renderHistory() {
    const list = $('pg-history');
    const logs = (state.logs || []).slice();
    list.innerHTML = '';
    $('pg-history-empty').hidden = logs.length > 0;
    // Newest first; delta vs the chronologically previous weigh-in.
    for (let i = logs.length - 1, shown = 0; i >= 0 && shown < 10; i--, shown++) {
      const log = logs[i];
      const prev = i > 0 ? logs[i - 1] : null;
      const li = document.createElement('li');
      li.className = 'pg-history__item';

      const date = document.createElement('span');
      date.className = 'pg-history__date';
      date.textContent = fmtDate(log.date, false);

      const kg = document.createElement('span');
      kg.className = 'pg-history__kg';
      kg.textContent = fmtKg(log.weight_kg) + ' kg';

      const delta = document.createElement('span');
      delta.className = 'pg-history__delta';
      if (prev) {
        const d = Math.round((log.weight_kg - prev.weight_kg) * 10) / 10;
        const goal = state.goal_weight_kg;
        const start = state.start_weight_kg;
        // Toward-goal changes are green; direction defaults to loss when no goal is set.
        const wantsGain = goal != null && start != null && goal > start;
        const good = d === 0 ? null : (wantsGain ? d > 0 : d < 0);
        delta.textContent = (d > 0 ? '+' : '') + d.toFixed(1);
        if (good !== null) delta.classList.add(good ? 'is-good' : 'is-bad');
      }

      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'pg-history__del';
      del.setAttribute('aria-label', t('del'));
      del.dataset.id = log.id;
      del.textContent = '×';

      li.append(date, kg, delta, del);
      list.appendChild(li);
    }
  }

  function openModal(id) {
    const m = $(id);
    m.hidden = false;
    const first = m.querySelector('input');
    if (first) setTimeout(() => first.focus(), 30);
  }
  function closeModal(m) { m.hidden = true; }

  function openGoal() {
    $('pg-goal-error').textContent = '';
    $('pg-goal-input').value = state && state.goal_weight_kg != null ? state.goal_weight_kg : '';
    $('pg-height-input').value = state && state.height_cm != null ? state.height_cm : '';
    $('pg-height-group').hidden = !!(state && state.height_cm != null);
    openModal('pg-goal-modal');
  }

  function openHeightOnly() {
    openGoal();
    $('pg-height-group').hidden = false;
    setTimeout(() => $('pg-height-input').focus(), 40);
  }

  function openWeight() {
    $('pg-weight-error').textContent = '';
    const today = formatDate(new Date());
    $('pg-weight-input').value = state && state.current_weight_kg != null ? state.current_weight_kg : '';
    $('pg-date-input').value = today;
    $('pg-date-input').max = today;
    openModal('pg-weight-modal');
  }

  const inRange = (v, lo, hi) => Number.isFinite(v) && v >= lo && v <= hi;

  async function submitGoal(e) {
    e.preventDefault();
    const err = $('pg-goal-error');
    const goalRaw = $('pg-goal-input').value.trim();
    const heightRaw = $('pg-height-input').value.trim();
    const body = {};
    if (goalRaw !== '') {
      const g = parseFloat(goalRaw);
      if (!inRange(g, 20, 400)) { err.textContent = t('weightRange'); return; }
      body.goal_weight_kg = g;
    }
    if (heightRaw !== '') {
      const h = parseFloat(heightRaw);
      if (!inRange(h, 80, 250)) { err.textContent = t('heightRange'); return; }
      body.height_cm = h;
    }
    if (!Object.keys(body).length) { err.textContent = t('weightRange'); return; }
    try {
      await api('/api/progress/goal', { method: 'PUT', body: JSON.stringify(body) });
      closeModal($('pg-goal-modal'));
      showToast(t('saved'));
      load();
    } catch (ex) {
      err.textContent = ex.message;
    }
  }

  async function submitWeight(e) {
    e.preventDefault();
    const err = $('pg-weight-error');
    const w = parseFloat($('pg-weight-input').value);
    const date = $('pg-date-input').value;
    if (!inRange(w, 20, 400)) { err.textContent = t('weightRange'); return; }
    if (date && date > formatDate(new Date())) { err.textContent = t('futureDate'); return; }
    try {
      await api('/api/progress/weight', { method: 'POST', body: JSON.stringify({ weight_kg: w, date: date || undefined }) });
      closeModal($('pg-weight-modal'));
      showToast(t('saved'));
      load();
    } catch (ex) {
      err.textContent = ex.message;
    }
  }

  async function deleteLog(id) {
    try {
      await api('/api/progress/weight/' + encodeURIComponent(id), { method: 'DELETE' });
      showToast(t('deleted'));
      load();
    } catch (ex) {
      showToast(ex.message, 'error');
    }
  }

  function init() {
    applyStrings();
    $('pg-open-goal').addEventListener('click', openGoal);
    $('pg-open-weight').addEventListener('click', openWeight);
    $('pg-add-height').addEventListener('click', openHeightOnly);
    $('pg-goal-form').addEventListener('submit', submitGoal);
    $('pg-weight-form').addEventListener('submit', submitWeight);
    $('pg-range').addEventListener('change', load);
    $('pg-history').addEventListener('click', (e) => {
      const btn = e.target.closest('.pg-history__del');
      if (btn) deleteLog(btn.dataset.id);
    });
    document.querySelectorAll('#pg-goal-modal, #pg-weight-modal').forEach((m) => {
      m.addEventListener('click', (e) => {
        if (e.target === m || e.target.closest('[data-close]')) closeModal(m);
      });
    });
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      document.querySelectorAll('#pg-goal-modal, #pg-weight-modal').forEach((m) => { if (!m.hidden) closeModal(m); });
    });
    const toggle = $('lang-toggle');
    if (toggle) toggle.addEventListener('click', () => setTimeout(() => { applyStrings(); render(); }, 0));
    load();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
