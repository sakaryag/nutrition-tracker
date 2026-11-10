/* ============================================================
   app.js — Shared utilities for NutriTrack
   ============================================================ */

/* Gemini API key: stored by the server in an encrypted, HttpOnly, per-user cookie on this
   device (never in the DB, never readable by JS). Survives logout / account switching. */
var ApiKey = (function () {
  var st = window.NT_GEMINI || { has: false, hint: '', server: false };

  function send(method, body) {
    return fetch('/api/chat/key', {
      method: method,
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        st.has = !!d.has_key; st.hint = d.hint || '';
        return d;
      });
    });
  }

  // One-time migration from the old localStorage storage.
  try {
    var legacyName = window.NT_USER_ID == null ? null : 'nt_gemini_key:' + window.NT_USER_ID;
    var legacy = legacyName ? localStorage.getItem(legacyName) : null;
    localStorage.removeItem('nt_gemini_key');
    if (legacy) {
      if (st.has) localStorage.removeItem(legacyName);
      else send('PUT', { key: legacy }).then(function () { localStorage.removeItem(legacyName); }, function () {});
    }
  } catch (_) {}

  return {
    has: function () { return !!st.has; },
    available: function () { return !!(st.has || st.server); },
    hint: function () { return st.hint || ''; },
    set: function (v) { return send('PUT', { key: v }); },
    clear: function () { return send('DELETE'); },
    get: function () { return ''; },
  };
})();

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

/* ---------- Gemini model selection (list comes from /api/chat/models) ---------- */
var ApiUsage = {
  _RE: /^gemini-[a-z0-9][a-z0-9.\-]{0,62}$/,
  _models: null,
  // '' means "let the server pick its current default".
  getModel: function () {
    var m = '';
    try { m = localStorage.getItem('nt_gemini_model') || ''; } catch (_) {}
    return this._RE.test(m) ? m : '';
  },
  setModel: function (m) {
    try {
      if (m && this._RE.test(m)) localStorage.setItem('nt_gemini_model', m);
      else localStorage.removeItem('nt_gemini_model');
    } catch (_) {}
  },
  loadModels: function () {
    if (!this._models) {
      this._models = fetch('/api/chat/models', { headers: { 'Accept': 'application/json' } })
        .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .catch(function (e) { ApiUsage._models = null; throw e; });
    }
    return this._models;
  },
  getBudget: function () { return 0; },
  setBudget: function () {},
  _monthKey: function () {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  },
  getSpent: function () { return 0; },
  addCost: function () { return 0; },
  checkBudget: function () { return { ok: true, spent: 0, budget: 0 }; },
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
