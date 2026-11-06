/* chat.js — AI Nutrition Assistant page */

(function () {
  'use strict';

  const pageEl       = document.getElementById('aichat');
  const messagesEl   = document.getElementById('chat-messages');
  const dockEl       = document.getElementById('chat-dock');
  const form         = document.getElementById('chat-form');
  const inputEl      = document.getElementById('chat-input');
  const sendBtn      = document.getElementById('chat-send-btn');
  const statusBadge  = document.getElementById('chat-status-badge');
  const statusLabel  = document.getElementById('chat-status-label');
  const loggedBanner = document.getElementById('chat-logged-banner');
  const loggedText   = document.getElementById('chat-logged-text');
  const chipsEl      = document.getElementById('chat-chips');
  const plusBtn      = document.getElementById('chat-plus-btn');
  const plusMenu     = document.getElementById('chat-plus-menu');

  const USER_INITIAL = (pageEl && pageEl.dataset.userInitial) || 'U';
  const SPARKLE_SVG  = '<svg viewBox="0 0 24 24"><path d="M12 2.5l2.1 6.2 6.4 2.3-6.4 2.3L12 19.5l-2.1-6.2L3.5 11l6.4-2.3z"/></svg>';
  const MEAL_TYPES   = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];
  const MAX_CARDS    = 3;

  // Conversation history sent to backend on every turn
  const history = [];
  let busy = false;
  let ready = true;        // flipped by checkStatus(); stays usable if status is unreachable
  let lastStatus = null;   // {state: 'ready'|'nokey'|'offline', model}

  // ----------------------------------------------------------------
  // Local strings (EN/TR)
  // ----------------------------------------------------------------
  const STR = {
    en: {
      title: 'AI Nutrition Assistant',
      welcome: 'Hi! I\'m your AI nutrition assistant. I can help you find meals. Try: <em>Dinner under 700 calories</em> or <em>High-protein lunch</em>.',
      placeholder: 'Ask about meals or tell me what you ate…',
      connecting: 'Connecting…',
      online: 'Online',
      needKey: 'API key required',
      offline: 'Cannot reach backend',
      chips: ['High protein lunch?', 'Low carb dinner?', 'Vegetarian ideas', 'What can I still eat today?'],
      chipsLabel: 'Suggested prompts',
      scan: 'Scan a meal',
      more: 'More actions',
      send: 'Send',
      message: 'Message',
      hintStrong: 'Tip:',
      hint: 'Add your <a href="/settings">Gemini API key in Settings</a> for smarter responses, Turkish food support, and photo recognition.',
      setup: '<span aria-hidden="true" style="font-size:1.4rem;">🔑</span><br><strong>Gemini API key required</strong><br>' +
             'Get your <strong>free AI Studio key</strong> — no credit card, 1 500 req/day:<br>' +
             '<a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a><br>' +
             '<small>Paste it in <a href="/settings">Settings → AI Assistant</a></small>',
      noKey: '🔑 Gemini API key required. Add your free key in <a href="/settings">Settings</a>.',
      billing: '⚠️ <strong>API key credits depleted.</strong><br>Get a free key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> and update it in <a href="/settings">Settings</a>.',
      modelNF: '⚠️ <strong>Model not available.</strong> Pick another model in <a href="/settings">Settings → AI Assistant</a>.',
      busySrv: '⚠️ Gemini servers are busy — please try again in a moment.',
      noResp: '<em>No response received.</em>',
      logged: 'Logged: ',
      aiNote: ' — ~AI: estimated from Gemini knowledge, not from database',
      carbs: 'Carbs', protein: 'Protein', fat: 'Fat',
      kcal: 'kcal',
      minutes: function (n) { return n + ' min'; },
      servings: function (n) { return n + (n === 1 ? ' serving' : ' servings'); },
      alternatives: 'Alternatives',
      logThis: 'Log this',
      loggedBtn: 'Logged ✓',
      logOk: function (n) { return 'Logged ' + n; },
      altPrompt: function (n) { return 'Suggest alternatives to ' + n; },
      altAria: function (n) { return 'Suggest alternatives to ' + n; },
      logAria: function (n) { return 'Log ' + n + ' to today'; },
      you: 'You', assistant: 'Assistant',
    },
    tr: {
      title: 'Yapay Zeka Beslenme Asistanı',
      welcome: 'Merhaba! Ben yapay zeka beslenme asistanınım. Öğün bulmana yardım edebilirim. Dene: <em>700 kalorinin altında akşam yemeği</em> veya <em>Yüksek proteinli öğle yemeği</em>.',
      placeholder: 'Öğünleri sor ya da ne yediğini yaz…',
      connecting: 'Bağlanıyor…',
      online: 'Çevrimiçi',
      needKey: 'API anahtarı gerekli',
      offline: 'Sunucuya ulaşılamıyor',
      chips: ['Yüksek proteinli öğle?', 'Düşük karbonhidratlı akşam?', 'Vejetaryen fikirler', 'Bugün daha ne yiyebilirim?'],
      chipsLabel: 'Önerilen sorular',
      scan: 'Öğün tara',
      more: 'Diğer işlemler',
      send: 'Gönder',
      message: 'Mesaj',
      hintStrong: 'İpucu:',
      hint: 'Daha akıllı yanıtlar, Türk yemekleri desteği ve fotoğraf tanıma için <a href="/settings">Ayarlar\'a Gemini API anahtarını</a> ekle.',
      setup: '<span aria-hidden="true" style="font-size:1.4rem;">🔑</span><br><strong>Gemini API anahtarı gerekli</strong><br>' +
             '<strong>Ücretsiz AI Studio anahtarını</strong> al — kredi kartı yok, günde 1 500 istek:<br>' +
             '<a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a><br>' +
             '<small><a href="/settings">Ayarlar → Yapay Zeka Asistanı</a> bölümüne yapıştır</small>',
      noKey: '🔑 Gemini API anahtarı gerekli. Ücretsiz anahtarını <a href="/settings">Ayarlar</a>\'a ekle.',
      billing: '⚠️ <strong>API anahtarı kredisi bitti.</strong><br><a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> adresinden ücretsiz anahtar al ve <a href="/settings">Ayarlar</a>\'da güncelle.',
      modelNF: '⚠️ <strong>Model kullanılamıyor.</strong> <a href="/settings">Ayarlar → Yapay Zeka Asistanı</a>\'ndan başka bir model seç.',
      busySrv: '⚠️ Gemini sunucuları meşgul — lütfen biraz sonra tekrar dene.',
      noResp: '<em>Yanıt alınamadı.</em>',
      logged: 'Kaydedildi: ',
      aiNote: ' — ~AI: Gemini tahmini, veritabanından değil',
      carbs: 'Karb', protein: 'Protein', fat: 'Yağ',
      kcal: 'kcal',
      minutes: function (n) { return n + ' dk'; },
      servings: function (n) { return n + ' porsiyon'; },
      alternatives: 'Alternatifler',
      logThis: 'Kaydet',
      loggedBtn: 'Kaydedildi ✓',
      logOk: function (n) { return n + ' kaydedildi'; },
      altPrompt: function (n) { return n + ' yerine alternatifler öner'; },
      altAria: function (n) { return n + ' için alternatifler öner'; },
      logAria: function (n) { return n + ' bugüne kaydet'; },
      you: 'Sen', assistant: 'Asistan',
    },
  };

  function lang() { return (typeof Lang !== 'undefined' && Lang.get() === 'tr') ? 'tr' : 'en'; }
  function t(key) { return STR[lang()][key]; }

  // ----------------------------------------------------------------
  // Status check
  // ----------------------------------------------------------------
  async function checkStatus() {
    const userKey = localStorage.getItem('nt_gemini_key') || '';
    try {
      const data = await api('/api/chat/status?has_user_key=' + (userKey ? '1' : '0'));
      if (data.ready) {
        const model = (typeof ApiUsage !== 'undefined') ? ApiUsage.getModel() : (data.model || 'gemini-3.8-flash');
        lastStatus = { state: 'ready', model: model };
      } else {
        lastStatus = { state: 'nokey' };
      }
      _setInputEnabled(!!data.ready);
    } catch (_) {
      lastStatus = { state: 'offline' };
    }
    renderStatus();
  }

  function renderStatus() {
    const hintEl = document.getElementById('chat-api-hint');
    if (!lastStatus) { statusLabel.textContent = t('connecting'); return; }
    statusBadge.classList.toggle('ready', lastStatus.state === 'ready');
    statusBadge.classList.toggle('offline', lastStatus.state !== 'ready');
    if (lastStatus.state === 'ready') {
      statusLabel.textContent = t('online') + ' · Gemini · ' + lastStatus.model;
      if (hintEl) hintEl.hidden = true;
    } else if (lastStatus.state === 'nokey') {
      statusLabel.textContent = t('needKey');
      if (hintEl) hintEl.hidden = false;
    } else {
      statusLabel.textContent = t('offline');
    }
  }

  function _setInputEnabled(enabled) {
    ready = enabled;
    inputEl.disabled = !enabled;
    sendBtn.disabled = !enabled || busy;
    let setupEl = document.getElementById('chat-setup-banner');
    if (!enabled) {
      if (!setupEl) {
        setupEl = document.createElement('div');
        setupEl.id = 'chat-setup-banner';
        setupEl.className = 'aichat-setup';
        setupEl.innerHTML = t('setup');
        messagesEl.appendChild(setupEl);
      }
    } else if (setupEl) {
      setupEl.remove();
    }
    updateChips();
  }

  // ----------------------------------------------------------------
  // Render helpers
  // ----------------------------------------------------------------
  function fmtTime(d) {
    return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  }

  function scrollBottom() {
    requestAnimationFrame(function () {
      window.scrollTo({ top: document.documentElement.scrollHeight });
    });
  }

  // Creates a message row; returns the bubble element. `html` must already be safe.
  function appendBubble(role, html, extraClass) {
    const isUser = role === 'user';
    const row = document.createElement('div');
    row.className = 'aichat-row aichat-row--' + (isUser ? 'user' : 'bot');

    const avatar = document.createElement('span');
    avatar.className = 'aichat-avatar aichat-avatar--' + (isUser ? 'user' : 'bot');
    avatar.setAttribute('aria-hidden', 'true');
    if (isUser) avatar.textContent = USER_INITIAL;
    else avatar.innerHTML = SPARKLE_SVG;

    const col = document.createElement('div');
    col.className = 'aichat-col';

    const bubble = document.createElement('div');
    bubble.className = 'aichat-bubble aichat-bubble--' + (isUser ? 'user' : 'bot') + (extraClass ? ' ' + extraClass : '');
    const content = document.createElement('div');
    content.className = 'aichat-bubble__content';
    content.innerHTML = html;
    bubble.appendChild(content);

    const time = document.createElement('time');
    time.className = 'aichat-time';
    const now = new Date();
    time.dateTime = now.toISOString();
    time.textContent = fmtTime(now);

    col.appendChild(bubble);
    col.appendChild(time);
    row.appendChild(avatar);
    row.appendChild(col);
    messagesEl.appendChild(row);
    scrollBottom();
    bubble._row = row;
    return bubble;
  }

  function showTyping() {
    hideTyping();
    const row = document.createElement('div');
    row.className = 'aichat-row aichat-row--bot';
    row.id = 'typing-bubble';
    row.setAttribute('aria-hidden', 'true');
    row.innerHTML =
      '<span class="aichat-avatar aichat-avatar--bot">' + SPARKLE_SVG + '</span>' +
      '<div class="aichat-bubble aichat-bubble--bot aichat-typing"><span></span><span></span><span></span></div>';
    messagesEl.appendChild(row);
    scrollBottom();
  }

  function hideTyping() {
    const el = document.getElementById('typing-bubble');
    if (el) el.remove();
  }

  function removeBubble(bubble) {
    if (bubble && bubble._row) bubble._row.remove();
  }

  // Strip ```json ... ``` blocks (complete or partial at end of stream)
  function stripJsonBlock(text) {
    return text
      .replace(/```json[\s\S]*?```/g, '')   // complete block
      .replace(/```json[\s\S]*$/, '')        // partial block still streaming
      .trim();
  }

  function parseActionBlock(text) {
    const m = /```json\s*([\s\S]*?)\s*```/.exec(text);
    if (!m) return null;
    try {
      const obj = JSON.parse(m[1]);
      return (obj && typeof obj === 'object') ? obj : null;
    } catch (_) { return null; }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Escape first, then apply minimal formatting (bold, bullets, newlines)
  function renderText(text) {
    return escapeHtml(text)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/^[ \t]*[-*•][ \t]+/gm, '• ')
      .replace(/\n/g, '<br>');
  }

  // ----------------------------------------------------------------
  // Meal cards (built from the structured ```json action block)
  // ----------------------------------------------------------------
  function num(v) {
    const n = Number(v);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }

  function fmtG(v) {
    return (Math.round(v * 10) / 10) + 'g';
  }

  function guessMealType() {
    const h = new Date().getHours();
    if (h < 11) return 'Breakfast';
    if (h < 16) return 'Lunch';
    if (h < 21) return 'Dinner';
    return 'Snack';
  }

  // Normalise an item from either `suggestions` or log `entries`
  function normaliseItem(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const title = String(raw.title || raw.name || raw.food_name || '').trim().slice(0, 120);
    const p = num(raw.protein), f = num(raw.fat), c = num(raw.carbs);
    if (!title || p === null || f === null || c === null) return null;
    let kcal = num(raw.calories);
    if (kcal === null) kcal = p * 4 + f * 9 + c * 4;
    const emoji = typeof raw.emoji === 'string' ? raw.emoji.trim() : '';
    return {
      title: title,
      emoji: emoji && emoji.length <= 8 && !/[A-Za-z0-9<>&]/.test(emoji) ? emoji : '',
      protein: p, fat: f, carbs: c, calories: Math.round(kcal),
      servings: num(raw.servings),
      prep: num(raw.prep_minutes),
      serving_size: num(raw.serving_size),
      serving_unit: typeof raw.serving_unit === 'string' ? raw.serving_unit.slice(0, 20) : '',
      meal_type: MEAL_TYPES.indexOf(raw.meal_type) !== -1 ? raw.meal_type : guessMealType(),
      saved_food_id: Number.isInteger(raw.saved_food_id) ? raw.saved_food_id : null,
    };
  }

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function macroTile(kind, grams) {
    const tile = el('div', 'aichat-macro aichat-macro--' + kind);
    tile.appendChild(el('span', 'aichat-macro__val', fmtG(grams)));
    tile.appendChild(el('span', 'aichat-macro__lbl', t(kind)));
    return tile;
  }

  function buildCard(item, alreadyLogged) {
    const card = el('article', 'aichat-card');
    card.setAttribute('aria-label', item.title);

    const hero = el('div', 'aichat-card__hero', item.emoji || item.title.charAt(0).toUpperCase());
    hero.setAttribute('aria-hidden', 'true');
    card.appendChild(hero);

    const body = el('div', 'aichat-card__body');
    body.appendChild(el('h3', 'aichat-card__title', item.title));

    const meta = [];
    if (item.prep) meta.push('⏱ ' + t('minutes')(Math.round(item.prep)));
    if (item.servings) meta.push('🍽 ' + t('servings')(item.servings));
    if (!item.servings && item.serving_size) meta.push('⚖ ' + item.serving_size + (item.serving_unit || 'g'));
    if (meta.length) {
      const metaEl = el('div', 'aichat-card__meta');
      meta.forEach(function (m) { metaEl.appendChild(el('span', '', m)); });
      body.appendChild(metaEl);
    }

    const macros = el('div', 'aichat-macros');
    macros.appendChild(macroTile('carbs', item.carbs));
    macros.appendChild(macroTile('protein', item.protein));
    macros.appendChild(macroTile('fat', item.fat));
    body.appendChild(macros);

    const kcal = el('div', 'aichat-card__kcal');
    kcal.appendChild(el('strong', '', String(item.calories)));
    kcal.appendChild(document.createTextNode(' ' + t('kcal')));
    body.appendChild(kcal);

    const actions = el('div', 'aichat-card__actions');
    if (alreadyLogged) {
      const done = el('button', 'aichat-pill aichat-pill--done', t('loggedBtn'));
      done.type = 'button';
      done.disabled = true;
      actions.appendChild(done);
    } else {
      const alt = el('button', 'aichat-pill aichat-pill--soft', t('alternatives'));
      alt.type = 'button';
      alt.setAttribute('aria-label', t('altAria')(item.title));
      alt.addEventListener('click', function () { send(t('altPrompt')(item.title)); });

      const logBtn = el('button', 'aichat-pill aichat-pill--primary', t('logThis'));
      logBtn.type = 'button';
      logBtn.setAttribute('aria-label', t('logAria')(item.title));
      logBtn.addEventListener('click', function () { logItem(item, logBtn); });

      actions.appendChild(alt);
      actions.appendChild(logBtn);
    }
    body.appendChild(actions);
    card.appendChild(body);
    return card;
  }

  async function logItem(item, btn) {
    btn.disabled = true;
    const payload = {
      food_name: item.title,
      protein: item.protein,
      fat: item.fat,
      carbs: item.carbs,
      calories: item.calories,
      meal_type: item.meal_type,
      entry_date: (typeof formatDate === 'function') ? formatDate(new Date()) : undefined,
    };
    if (item.serving_size) {
      payload.serving_size = item.serving_size;
      payload.serving_unit = item.serving_unit || 'g';
    }
    if (item.saved_food_id) payload.saved_food_id = item.saved_food_id;
    try {
      await api('/api/entries', { method: 'POST', body: JSON.stringify(payload) });
      btn.textContent = t('loggedBtn');
      btn.classList.remove('aichat-pill--primary');
      btn.classList.add('aichat-pill--done');
      if (typeof showToast === 'function') showToast(t('logOk')(item.title), 'success');
    } catch (err) {
      btn.disabled = false;
      if (typeof showToast === 'function') showToast(err.message || String(err), 'error');
    }
  }

  // Returns a container of cards, or null if the action has no usable items
  function buildCards(action, loggedNames) {
    if (!action) return null;
    let items = [];
    let logged = false;
    if (action.action === 'suggest' && Array.isArray(action.suggestions)) {
      items = action.suggestions;
    } else if (action.action === 'log' && Array.isArray(action.entries) && loggedNames.length) {
      // Only show cards for entries the backend actually saved
      items = action.entries.filter(function (e) {
        return e && loggedNames.indexOf(String(e.food_name || '').trim()) !== -1;
      });
      logged = true;
    }
    const norm = items.map(normaliseItem).filter(Boolean).slice(0, MAX_CARDS);
    if (!norm.length) return null;
    const wrap = el('div', 'aichat-cards');
    norm.forEach(function (it) { wrap.appendChild(buildCard(it, logged)); });
    return wrap;
  }

  // ----------------------------------------------------------------
  // Suggestion chips
  // ----------------------------------------------------------------
  function renderChips() {
    chipsEl.innerHTML = '';
    chipsEl.setAttribute('aria-label', t('chipsLabel'));
    t('chips').forEach(function (label) {
      const chip = el('button', 'aichat-chip', label);
      chip.type = 'button';
      chip.addEventListener('click', function () { send(label); });
      chipsEl.appendChild(chip);
    });
    updateChips();
  }

  function updateChips() {
    chipsEl.hidden = busy || !ready || inputEl.value.trim().length > 0;
  }

  // ----------------------------------------------------------------
  // Send message — streaming SSE
  // ----------------------------------------------------------------
  async function send(override) {
    if (busy || !ready) return;
    const fromInput = typeof override !== 'string';
    const text = (fromInput ? inputEl.value : override).trim();
    if (!text) return;

    if (fromInput) {
      inputEl.value = '';
      autoResize();
    }
    loggedBanner.hidden = true;
    closeMenu();

    history.push({ role: 'user', content: text });
    appendBubble('user', renderText(text));

    busy = true;
    sendBtn.disabled = true;
    updateChips();
    showTyping();

    const lng     = lang();
    const userKey = localStorage.getItem('nt_gemini_key') || '';
    const model   = (typeof ApiUsage !== 'undefined') ? ApiUsage.getModel() : 'gemini-3.8-flash';

    let botBubble = null;
    let contentEl = null;
    let fullText  = '';

    function ensureBotBubble() {
      if (!botBubble) {
        hideTyping();
        botBubble = appendBubble('bot', '');
        contentEl = botBubble.querySelector('.aichat-bubble__content');
      }
    }

    function showError(html) {
      hideTyping();
      removeBubble(botBubble);
      botBubble = null;
      appendBubble('bot', html, 'aichat-bubble--error');
    }

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, lang: lng, api_key: userKey, model }),
      });

      // Non-2xx before streaming (e.g. 401 no-key)
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        history.pop();
        const errStr = errData.error || String(resp.status);
        if (errStr.includes('no_key')) {
          checkStatus();
          showError(t('noKey'));
        } else {
          if (resp.status === 401) checkStatus();
          showError(renderText(errData.reply || errStr));
        }
        return;
      }

      const reader  = resp.body.getReader();
      const decoder = new TextDecoder();
      let   buf     = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // Process complete SSE lines
        const lines = buf.split('\n');
        buf = lines.pop(); // keep incomplete last line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let evt;
          try { evt = JSON.parse(line.slice(6)); } catch { continue; }

          if (evt.error) {
            history.pop();
            const errStr = String(evt.error);
            let userMsg = renderText(errStr);
            if (errStr.includes('billing_depleted'))      userMsg = t('billing');
            else if (errStr.includes('model_not_found'))  userMsg = t('modelNF');
            else if (errStr.includes('busy'))             userMsg = t('busySrv');
            showError(userMsg);
            return;
          }

          if (evt.delta) {
            fullText += evt.delta;
            const visible = stripJsonBlock(fullText);
            // Keep the typing indicator until there is visible (non-JSON) text
            if (visible) {
              ensureBotBubble();
              contentEl.innerHTML = renderText(visible);
              scrollBottom();
            }
          }

          if (evt.done) {
            const cleaned = stripJsonBlock(fullText);
            const finalReply = cleaned || (evt.reply ? String(evt.reply) : '');
            const loggedList = Array.isArray(evt.logged) ? evt.logged : [];
            const loggedNames = loggedList.map(function (item) {
              return String(typeof item === 'object' && item ? item.name : item).trim();
            });
            const cards = buildCards(parseActionBlock(fullText), loggedNames);

            if (finalReply || cards) {
              ensureBotBubble();
              // Gemini may put everything in the JSON block — fall back to evt.reply
              if (!cleaned) contentEl.innerHTML = renderText(finalReply);
              if (cards) botBubble.appendChild(cards);
              scrollBottom();
            }
            if (finalReply) history.push({ role: 'assistant', content: finalReply });

            if (loggedList.length > 0) {
              let hasAI = false;
              const parts = loggedList.map(function (item) {
                const name = typeof item === 'object' && item ? item.name : item;
                const isAI = typeof item === 'object' && item && item.source === 'ai_estimate';
                if (isAI) hasAI = true;
                return isAI ? name + ' (~AI)' : name;
              });
              loggedText.textContent = t('logged') + parts.join(', ') + (hasAI ? t('aiNote') : '');
              loggedBanner.hidden = false;
              setTimeout(() => { loggedBanner.hidden = true; }, 8000);
            }
          }
        }
      }

      // If stream ended with no content at all
      if (!botBubble) {
        hideTyping();
        history.pop();
        appendBubble('bot', t('noResp'));
      }

    } catch (err) {
      history.pop();
      showError(renderText(String(err)));
    } finally {
      hideTyping();
      busy = false;
      sendBtn.disabled = !ready;
      updateChips();
      if (!inputEl.disabled) inputEl.focus();
    }
  }

  // ----------------------------------------------------------------
  // Composer: auto-resize, keyboard, "+" menu
  // ----------------------------------------------------------------
  function autoResize() {
    inputEl.style.height = 'auto';
    const lineH = parseFloat(getComputedStyle(inputEl).lineHeight) || 20;
    const max = lineH * 4 + 18;
    inputEl.style.height = Math.min(inputEl.scrollHeight, max) + 'px';
  }

  inputEl.addEventListener('input', function () {
    autoResize();
    updateChips();
  });

  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      send();
    } else if (e.key === 'Escape') {
      closeMenu();
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    send();
  });

  function openMenu() {
    plusMenu.hidden = false;
    plusBtn.setAttribute('aria-expanded', 'true');
    const first = plusMenu.querySelector('a, button');
    if (first) first.focus();
  }

  function closeMenu(returnFocus) {
    if (plusMenu.hidden) return;
    plusMenu.hidden = true;
    plusBtn.setAttribute('aria-expanded', 'false');
    if (returnFocus === true) plusBtn.focus();
  }

  plusBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    if (plusMenu.hidden) openMenu(); else closeMenu();
  });
  plusMenu.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { e.preventDefault(); closeMenu(true); }
  });
  document.addEventListener('click', function (e) {
    if (!plusMenu.hidden && !plusMenu.contains(e.target)) closeMenu();
  });

  // Keep the message list padded so the floating composer never hides content
  function syncComposerHeight() {
    pageEl.style.setProperty('--composer-h', dockEl.offsetHeight + 'px');
  }
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(syncComposerHeight).observe(dockEl);
  }
  window.addEventListener('resize', syncComposerHeight);

  // ----------------------------------------------------------------
  // i18n for static page text
  // ----------------------------------------------------------------
  function applyLang() {
    document.getElementById('chat-title').textContent = t('title');
    document.getElementById('chat-welcome-text').innerHTML = t('welcome');
    document.getElementById('chat-hint-strong').textContent = t('hintStrong');
    document.getElementById('chat-hint-text').innerHTML = t('hint');
    document.getElementById('chat-scan-label').textContent = t('scan');
    inputEl.placeholder = t('placeholder');
    inputEl.setAttribute('aria-label', t('message'));
    sendBtn.setAttribute('aria-label', t('send'));
    plusBtn.setAttribute('aria-label', t('more'));
    const setupEl = document.getElementById('chat-setup-banner');
    if (setupEl) setupEl.innerHTML = t('setup');
    renderChips();
    renderStatus();
  }

  const langToggle = document.getElementById('lang-toggle');
  if (langToggle) {
    // base.html switches the language in its own click handler; run after it
    langToggle.addEventListener('click', function () { setTimeout(applyLang, 0); });
  }

  // ----------------------------------------------------------------
  // Init
  // ----------------------------------------------------------------
  (function stampWelcome() {
    const col = document.querySelector('#chat-welcome .aichat-col');
    if (!col) return;
    const time = el('time', 'aichat-time', fmtTime(new Date()));
    col.appendChild(time);
  })();
  applyLang();
  syncComposerHeight();
  checkStatus();
  inputEl.focus();
})();
