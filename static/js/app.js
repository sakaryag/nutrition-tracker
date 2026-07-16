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
