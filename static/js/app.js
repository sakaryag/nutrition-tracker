/* ============================================================
   app.js — Shared utilities for NutriTrack
   ============================================================ */

/**
 * Lightweight fetch wrapper.
 * Returns parsed JSON on success, throws Error with message on failure.
 */
async function api(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
  };
  const merged = { ...defaults, ...options };
  if (merged.headers && options.headers) {
    merged.headers = { ...defaults.headers, ...options.headers };
  }
  const res = await fetch(url, merged);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      msg = body.error || body.message || msg;
    } catch (_) { /* ignore */ }
    throw new Error(msg);
  }
  // Some endpoints return no body (204)
  if (res.status === 204) return null;
  return res.json();
}

/**
 * Format a Date object (or Date-like) as YYYY-MM-DD.
 * Treats the date as local time, not UTC.
 */
function formatDate(date) {
  const d = date instanceof Date ? date : new Date(date);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * Parse a YYYY-MM-DD string safely as a local date (avoids UTC midnight shift).
 */
function parseLocalDate(str) {
  const [y, m, d] = str.split('-').map(Number);
  return new Date(y, m - 1, d);
}

/**
 * Format a YYYY-MM-DD string for display (e.g. "Wednesday, July 16, 2026").
 */
function formatDateDisplay(str) {
  const d = parseLocalDate(str);
  return d.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

/**
 * Show a brief toast notification.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 * @param {number} duration ms before fade (default 3000)
 */
function showToast(message, type = 'success', duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  toast.setAttribute('role', 'alert');
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s ease forwards';
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

/**
 * Debounce a function call.
 * @param {Function} fn
 * @param {number} ms
 */
function debounce(fn, ms) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), ms);
  };
}

/* ---------- API usage & budget tracking (localStorage, resets monthly) ---------- */
var ApiUsage = {
  MODELS: {
    'claude-haiku-4-5-20251001': { label: 'Haiku (fast, cheap)', inputPer1M: 0.80, outputPer1M: 4.00 },
    'claude-sonnet-4-5':         { label: 'Sonnet (smarter)',     inputPer1M: 3.00, outputPer1M: 15.00 },
  },
  getModel: function () {
    var m = localStorage.getItem('nt_anthropic_model') || 'claude-haiku-4-5-20251001';
    return this.MODELS[m] ? m : 'claude-haiku-4-5-20251001';
  },
  setModel: function (m) { if (this.MODELS[m]) localStorage.setItem('nt_anthropic_model', m); },
  getBudget: function () { return parseFloat(localStorage.getItem('nt_monthly_budget') || '0') || 0; },
  setBudget: function (v) { localStorage.setItem('nt_monthly_budget', String(parseFloat(v) || 0)); },
  _monthKey: function () {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  },
  getSpent: function () {
    var stored = JSON.parse(localStorage.getItem('nt_usage') || '{}');
    return stored.month === this._monthKey() ? (stored.cost || 0) : 0;
  },
  addCost: function (inputTokens, outputTokens, model) {
    var pricing = this.MODELS[model] || this.MODELS['claude-haiku-4-5-20251001'];
    var cost = (inputTokens / 1e6) * pricing.inputPer1M + (outputTokens / 1e6) * pricing.outputPer1M;
    var key = this._monthKey();
    var stored = JSON.parse(localStorage.getItem('nt_usage') || '{}');
    var prev = stored.month === key ? (stored.cost || 0) : 0;
    var total = prev + cost;
    localStorage.setItem('nt_usage', JSON.stringify({ month: key, cost: total }));
    return total;
  },
  checkBudget: function () {
    var budget = this.getBudget();
    var spent = this.getSpent();
    if (!budget) return { ok: true, spent: spent, budget: 0 };
    return { ok: spent < budget, spent: spent, budget: budget };
  },
};

/* ---------- Language helpers ---------- */
const Lang = {
  get() { return localStorage.getItem('nt_lang') || 'en'; },
  set(l) { localStorage.setItem('nt_lang', l); document.documentElement.lang = l; },
  isTr() { return this.get() === 'tr'; },
  foodName(food) { return (this.isTr() && food.name_tr) ? food.name_tr : food.name; },
  langParam() { return this.isTr() ? '&lang=tr' : ''; },
};
// Apply on load
document.documentElement.lang = Lang.get();

/* ---------- Nav: mobile toggle + active link ---------- */
(function initNav() {
  const toggle = document.querySelector('.nav-toggle');
  const links  = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!toggle.contains(e.target) && !links.contains(e.target)) {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
  // Mark current page link as active
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (href !== '/' && path.startsWith(href))) {
      a.classList.add('active');
    } else if (href === '/' && path === '/') {
      a.classList.add('active');
    }
  });
})();
