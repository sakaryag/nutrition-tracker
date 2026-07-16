/* ============================================================
   history.js — History page logic
   ============================================================ */

(function () {
  'use strict';

  const datePicker    = document.getElementById('history-date');
  const entriesList   = document.getElementById('h-entries-list');
  const trendBtns     = document.querySelectorAll('[data-days]');
  const exportForm    = document.getElementById('export-form');
  const exportStart   = document.getElementById('export-start');
  const exportEnd     = document.getElementById('export-end');

  let trendsChart = null;
  let activeDays  = 7;

  /* ---- Init ---- */
  function init() {
    const today = formatDate(new Date());
    datePicker.value  = today;
    exportEnd.value   = today;
    // Default export start = 7 days ago
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 6);
    exportStart.value = formatDate(weekAgo);

    loadDateData(today);
    loadTrends(activeDays);
  }

  /* ---- Date Picker ---- */
  datePicker.addEventListener('change', () => {
    if (datePicker.value) loadDateData(datePicker.value);
  });

  async function loadDateData(date) {
    await Promise.all([loadSummary(date), loadEntries(date)]);
  }

  /* ---- Summary ---- */
  async function loadSummary(date) {
    try {
      const data = await api(`/api/summary?date=${date}`);
      renderSummary(data);
    } catch (err) {
      showToast('Could not load summary: ' + err.message, 'error');
    }
  }

  function renderSummary(data) {
    ['protein', 'fat', 'carbs', 'calories'].forEach(m => {
      const consumed  = Math.round(data.totals?.[m] ?? 0);
      const target    = Math.round(data.target?.[m] ?? 0);
      const remaining = Math.round(data.remaining?.[m] ?? 0);
      const pct       = target > 0 ? Math.min(100, Math.round((consumed / target) * 100)) : 0;
      setText(`h-summary-${m}`, consumed);
      setText(`h-target-${m}`, target);
      setText(`h-remaining-${m}`, remaining);
      const bar = document.getElementById(`h-bar-${m}`);
      if (bar) bar.style.width = pct + '%';
    });
  }

  /* ---- Entries ---- */
  async function loadEntries(date) {
    try {
      const entries = await api(`/api/entries?date=${date}`);
      renderEntries(entries);
    } catch (err) {
      entriesList.innerHTML = '<p class="empty-msg">Could not load entries.</p>';
    }
  }

  const MEAL_ORDER = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];

  function renderEntries(entries) {
    if (!entries || entries.length === 0) {
      entriesList.innerHTML = '<p class="empty-msg">No entries for this date.</p>';
      return;
    }
    const groups = {};
    MEAL_ORDER.forEach(m => { groups[m] = []; });
    entries.forEach(e => {
      const key = e.meal_type in groups ? e.meal_type : 'Snack';
      groups[key].push(e);
    });
    let html = '';
    MEAL_ORDER.forEach(meal => {
      if (groups[meal].length === 0) return;
      html += `<div class="meal-group"><p class="meal-group__title">${meal}</p>`;
      groups[meal].forEach(e => { html += renderEntryCard(e); });
      html += '</div>';
    });
    entriesList.innerHTML = html;
  }

  function renderEntryCard(e) {
    const kcal = Math.round(e.calories ?? 0);
    return `<article class="entry-card">
      <div class="entry-card__info">
        <p class="entry-card__name">${escHtml(e.food_name)}</p>
        <p class="entry-card__meta">${escHtml(String(e.serving_size))} ${escHtml(e.serving_unit)}</p>
        <div class="entry-card__macros">
          <span class="macro-tag macro-tag--protein">P: ${r1(e.protein)}g</span>
          <span class="macro-tag macro-tag--fat">F: ${r1(e.fat)}g</span>
          <span class="macro-tag macro-tag--carbs">C: ${r1(e.carbs)}g</span>
          <span class="macro-tag macro-tag--cal">${kcal} kcal</span>
        </div>
      </div>
    </article>`;
  }

  /* ---- Trends Chart ---- */
  trendBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      trendBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeDays = parseInt(btn.dataset.days, 10);
      loadTrends(activeDays);
    });
  });

  async function loadTrends(days) {
    const end   = formatDate(new Date());
    const start = formatDate(daysAgo(days - 1));
    try {
      const rows = await api(`/api/summary/range?start=${start}&end=${end}`);
      const byDate = {};
      (rows || []).forEach(r => { byDate[r.date] = r; });
      const dateList = [];
      const results = [];
      for (let i = days - 1; i >= 0; i--) {
        const d = formatDate(daysAgo(i));
        dateList.push(d);
        results.push(byDate[d] || null);
      }
      renderTrendsChart(dateList, results);
    } catch (err) {
      showToast('Could not load trends: ' + err.message, 'error');
    }
  }

  function renderTrendsChart(labels, results) {
    const datasets = [
      { label: 'Protein (g)',  key: 'protein',  color: '#4A90D9' },
      { label: 'Fat (g)',      key: 'fat',       color: '#E8913A' },
      { label: 'Carbs (g)',    key: 'carbs',     color: '#5CB85C' },
      { label: 'Calories',     key: 'calories',  color: '#D9534F' },
    ];

    const chartData = {
      labels: labels.map(d => {
        const dt = parseLocalDate(d);
        return dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      }),
      datasets: datasets.map(ds => ({
        label: ds.label,
        data: results.map(r => r ? Math.round(r[ds.key] ?? 0) : 0),
        borderColor: ds.color,
        backgroundColor: ds.color + '22',
        tension: 0.3,
        fill: false,
        pointRadius: 3,
      })),
    };

    const ctx = document.getElementById('trends-chart').getContext('2d');
    if (trendsChart) trendsChart.destroy();
    trendsChart = new Chart(ctx, {
      type: 'line',
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, padding: 12 } },
        },
        scales: {
          x: { grid: { color: '#e2e8f0' } },
          y: { beginAtZero: true, grid: { color: '#e2e8f0' } },
        },
      },
    });
  }

  /* ---- Export ---- */
  exportForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const start = exportStart.value;
    const end   = exportEnd.value;
    if (!start || !end) { showToast('Please select a date range', 'error'); return; }
    if (start > end) { showToast('Start date must be before end date', 'error'); return; }
    window.location.href = `/api/export?start=${start}&end=${end}`;
  });

  /* ---- Helpers ---- */
  function daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d;
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function r1(n) { return Math.round((n ?? 0) * 10) / 10; }

  init();
})();
