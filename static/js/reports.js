/* ============================================================
   reports.js — Reports page logic
   ============================================================ */

(function () {
  'use strict';

  /* ---- State ---- */
  let activeDays  = 30;
  let trendChart  = null;
  let statsCache  = null;

  /* ---- DOM refs ---- */
  const periodBtns      = document.querySelectorAll('[data-days]');
  const heatmapGrid     = document.getElementById('rep-heatmap');
  const heatmapLabels   = document.getElementById('rep-heatmap-week-labels');

  /* ---- Init ---- */
  function init() {
    periodBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        periodBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        activeDays = parseInt(btn.dataset.days, 10);
        loadStats();
      });
    });

    loadStats();
    buildHeatmap();
  }

  /* ---- Date helpers ---- */
  function formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function daysAgo(n) {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() - n);
    return d;
  }

  /* ---- Load stats from API ---- */
  async function loadStats() {
    const end   = formatDate(new Date());
    const start = formatDate(daysAgo(activeDays - 1));
    try {
      const data = await api(`/api/summary/stats?start=${start}&end=${end}`);
      statsCache = data;
      renderStatCards(data);
      renderStreaks(data);
      renderCompliance(data);
      renderTrendChart(data);
    } catch (err) {
      showToast(t('common.loadError') + ' ' + err.message, 'error');
    }
  }

  /* ---- Stat Cards ---- */
  function renderStatCards(data) {
    const macros = [
      { key: 'protein',  unit: 'g',    targetKey: 'target_protein' },
      { key: 'fat',      unit: 'g',    targetKey: 'target_fat' },
      { key: 'carbs',    unit: 'g',    targetKey: 'target_carbs' },
      { key: 'calories', unit: 'kcal', targetKey: 'target_calories' },
    ];

    macros.forEach(function (m) {
      const avgEl = document.getElementById('rep-avg-' + m.key);
      const subEl = document.getElementById('rep-sub-' + m.key);
      if (!avgEl) return;

      const avg = data['avg_' + m.key] || 0;
      avgEl.textContent = Math.round(avg);

      // Determine target from last day in daily array (most recent target)
      const lastDay = (data.daily || []).filter(function (d) { return d[m.targetKey] > 0; }).slice(-1)[0];
      const target  = lastDay ? lastDay[m.targetKey] : 0;

      subEl.className = 'reports-stat-sub';
      if (target > 0) {
        const pct = Math.round((avg / target) * 100);
        if (pct >= 90 && pct <= 120) {
          subEl.textContent = pct + '% ' + t('rep.ofTarget');
          subEl.classList.add('on-target');
        } else if (pct > 120) {
          subEl.textContent = pct + '% ' + t('rep.ofTarget');
          subEl.classList.add('over-target');
        } else {
          subEl.textContent = pct + '% ' + t('rep.ofTarget');
          subEl.classList.add('under-target');
        }
      } else {
        subEl.textContent = t('rep.perDay');
      }
    });
  }

  /* ---- Streaks ---- */
  function renderStreaks(data) {
    setText('rep-current-streak', data.current_streak || 0);
    setText('rep-longest-streak', data.longest_streak || 0);
    setText('rep-days-logged', data.days_logged || 0);

    const denomEl = document.getElementById('rep-days-logged-denom');
    if (denomEl) denomEl.textContent = '/ ' + (data.total_days_in_range || activeDays);

    // Animate fire emoji for current streak > 0
    const fireEl = document.querySelector('.streak-badge--fire .streak-badge__number');
    if (fireEl && data.current_streak > 0) {
      fireEl.classList.add('streak-pulse');
    }
  }

  /* ---- Compliance Bars ---- */
  function renderCompliance(data) {
    const c = data.compliance || {};
    const map = [
      { key: 'protein',  pct: c.protein_pct  || 0 },
      { key: 'fat',      pct: c.fat_pct       || 0 },
      { key: 'carbs',    pct: c.carbs_pct     || 0 },
      { key: 'calories', pct: c.calories_pct  || 0 },
    ];
    map.forEach(function (m) {
      const bar    = document.getElementById('rep-bar-' + m.key);
      const pctEl  = document.getElementById('rep-pct-' + m.key);
      if (bar) {
        // Use rAF so transition fires after paint
        requestAnimationFrame(function () {
          bar.style.width = Math.min(100, m.pct) + '%';
        });
      }
      if (pctEl) pctEl.textContent = m.pct + '%';
    });
  }

  /* ---- Trend Chart ---- */
  function renderTrendChart(data) {
    const daily = data.daily || [];
    const labels = daily.map(function (d) {
      const dt = new Date(d.date + 'T00:00:00');
      return dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    });

    const datasets = [
      {
        label: t('rep.protein'),
        data: daily.map(function (d) { return Math.round(d.protein || 0); }),
        backgroundColor: '#4A90D9cc',
        borderColor: '#4A90D9',
        borderWidth: 1,
        stack: 'macros',
      },
      {
        label: t('rep.fat'),
        data: daily.map(function (d) { return Math.round(d.fat || 0); }),
        backgroundColor: '#E8913Acc',
        borderColor: '#E8913A',
        borderWidth: 1,
        stack: 'macros',
      },
      {
        label: t('rep.carbs'),
        data: daily.map(function (d) { return Math.round(d.carbs || 0); }),
        backgroundColor: '#5CB85Ccc',
        borderColor: '#5CB85C',
        borderWidth: 1,
        stack: 'macros',
      },
    ];

    const ctx = document.getElementById('rep-trend-chart').getContext('2d');
    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
      type: 'bar',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { boxWidth: 12, padding: 12 },
          },
          tooltip: {
            callbacks: {
              footer: function (items) {
                const total = items.reduce(function (sum, i) { return sum + i.parsed.y; }, 0);
                return 'Total: ' + Math.round(total) + 'g macros';
              },
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            grid: { color: '#e2e8f0' },
            ticks: { maxTicksLimit: 15, maxRotation: 45 },
          },
          y: {
            stacked: true,
            beginAtZero: true,
            grid: { color: '#e2e8f0' },
          },
        },
      },
    });
  }

  /* ---- Heatmap (always last 30 days, independent of period selector) ---- */
  async function buildHeatmap() {
    const end   = formatDate(new Date());
    const start = formatDate(daysAgo(29));

    try {
      const data = await api('/api/summary/stats?start=' + start + '&end=' + end);
      renderHeatmap(data.daily || []);
    } catch (err) {
      // Heatmap failure is non-critical — show empty grid
      renderHeatmap([]);
    }
  }

  function renderHeatmap(daily) {
    if (!heatmapGrid) return;

    // Build a lookup: date -> day data
    const byDate = {};
    daily.forEach(function (d) { byDate[d.date] = d; });

    // Determine the grid start: the Sunday on or before the start date
    const startDate = daysAgo(29);
    const endDate   = new Date();
    endDate.setHours(0, 0, 0, 0);

    // Grid starts from the first Sunday <= startDate
    const gridStart = new Date(startDate);
    gridStart.setDate(gridStart.getDate() - gridStart.getDay()); // back to Sunday

    // Build week day labels (Sun - Sat)
    const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    if (heatmapLabels) {
      heatmapLabels.innerHTML = DAY_LABELS.map(function (d) {
        return '<span class="heatmap-day-label">' + d + '</span>';
      }).join('');
    }

    heatmapGrid.innerHTML = '';

    const today = formatDate(new Date());
    const cursor = new Date(gridStart);

    while (cursor <= endDate) {
      const ds = formatDate(cursor);
      const cell = document.createElement('div');
      cell.className = 'heatmap-cell';

      const isBeforeRange = cursor < startDate;
      const isFuture = ds > today;

      if (isFuture || isBeforeRange) {
        cell.classList.add('heatmap-cell--future');
        cell.setAttribute('aria-hidden', 'true');
      } else {
        const dayData = byDate[ds];
        if (!dayData || (dayData.calories === 0 && dayData.protein === 0)) {
          cell.classList.add('heatmap-cell--empty');
          cell.setAttribute('title', formatHeatmapDate(cursor) + ': no data');
        } else {
          const targetCal = dayData.target_calories || 0;
          const cal       = dayData.calories || 0;
          const pct       = targetCal > 0 ? cal / targetCal : 0;

          if (pct >= 0.9) {
            cell.classList.add('heatmap-cell--over');
          } else if (pct >= 0.5) {
            cell.classList.add('heatmap-cell--mid');
          } else {
            cell.classList.add('heatmap-cell--under');
          }

          const pctDisplay = targetCal > 0 ? Math.round(pct * 100) + '%' : Math.round(cal) + ' kcal';
          cell.setAttribute('title', formatHeatmapDate(cursor) + ': ' + Math.round(cal) + ' kcal (' + pctDisplay + ' of target)');
        }
      }

      heatmapGrid.appendChild(cell);
      cursor.setDate(cursor.getDate() + 1);
    }
  }

  function formatHeatmapDate(d) {
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  /* ---- Helpers ---- */
  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  init();
})();
