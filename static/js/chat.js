/* chat.js — NutriBot chat page */

(function () {
  const messagesEl   = document.getElementById('chat-messages');
  const form         = document.getElementById('chat-form');
  const inputEl      = document.getElementById('chat-input');
  const sendBtn      = document.getElementById('chat-send-btn');
  const statusBadge  = document.getElementById('chat-status-badge');
  const statusLabel  = document.getElementById('chat-status-label');
  const loggedBanner = document.getElementById('chat-logged-banner');
  const loggedText   = document.getElementById('chat-logged-text');

  // Conversation history sent to backend on every turn
  const history = [];
  let busy = false;

  // ----------------------------------------------------------------
  // Status check
  // ----------------------------------------------------------------
  async function checkStatus() {
    const userKey = localStorage.getItem('nt_gemini_key') || '';
    try {
      const data = await api('/api/chat/status?has_user_key=' + (userKey ? '1' : '0'));
      const ready = data.ready;
      statusBadge.classList.toggle('ready',   ready);
      statusBadge.classList.toggle('offline', !ready);
      const hintEl = document.getElementById('chat-api-hint');
      if (ready) {
        const model = (typeof ApiUsage !== 'undefined') ? ApiUsage.getModel() : (data.model || 'gemini-3.8-flash');
        statusLabel.textContent = 'Gemini · ' + model;
        if (hintEl) hintEl.hidden = true;
      } else {
        statusLabel.textContent = 'API key required';
        if (hintEl) hintEl.hidden = false;
      }
      _setInputEnabled(ready);
    } catch (_) {
      statusBadge.classList.add('offline');
      statusLabel.textContent = 'Cannot reach backend';
    }
  }

  function _setInputEnabled(enabled) {
    inputEl.disabled  = !enabled;
    sendBtn.disabled  = !enabled;
    const setupEl = document.getElementById('chat-setup-banner');
    if (!enabled) {
      if (!setupEl) {
        const banner = document.createElement('div');
        banner.id = 'chat-setup-banner';
        banner.style.cssText = 'margin:1rem;padding:1rem;background:var(--color-bg-subtle,#f8f9fa);border-radius:.5rem;text-align:center;line-height:1.7;';
        banner.innerHTML =
          '<span style="font-size:1.4rem;">🔑</span><br>' +
          '<strong>Gemini API key required</strong><br>' +
          'Get your <strong>free AI Studio key</strong> — no credit card, 1 500 req/day:<br>' +
          '<a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener" ' +
          'style="color:var(--color-primary,#3b82f6);font-weight:600;">aistudio.google.com/apikey</a><br>' +
          '<span style="font-size:.875rem;color:var(--color-text-muted,#666);">Paste it in Settings → AI Assistant</span>';
        messagesEl.appendChild(banner);
      }
    } else if (setupEl) {
      setupEl.remove();
    }
  }

  // ----------------------------------------------------------------
  // Render helpers
  // ----------------------------------------------------------------
  function appendBubble(role, html) {
    const wrap = document.createElement('div');
    wrap.className = 'chat-bubble chat-bubble--' + (role === 'user' ? 'user' : 'bot');
    const inner = document.createElement('div');
    inner.className = 'chat-bubble__content';
    inner.innerHTML = html;
    wrap.appendChild(inner);
    messagesEl.appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function showTyping() {
    const wrap = document.createElement('div');
    wrap.className = 'chat-bubble chat-bubble--bot';
    wrap.id = 'typing-bubble';
    wrap.innerHTML = '<div class="typing-indicator"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>';
    messagesEl.appendChild(wrap);
    scrollBottom();
  }

  function hideTyping() {
    const el = document.getElementById('typing-bubble');
    if (el) el.remove();
  }

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // Basic markdown-ish: newlines → <br>, **bold**
  function renderText(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  // ----------------------------------------------------------------
  // Send message — streaming SSE
  // ----------------------------------------------------------------
  async function send() {
    if (busy) return;
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = '';
    autoResize();
    loggedBanner.hidden = true;

    history.push({ role: 'user', content: text });
    appendBubble('user', renderText(text));

    busy = true;
    sendBtn.disabled = true;
    showTyping();

    const lang    = (typeof Lang !== 'undefined') ? Lang.get() : 'en';
    const userKey = localStorage.getItem('nt_gemini_key') || '';
    const model   = (typeof ApiUsage !== 'undefined') ? ApiUsage.getModel() : 'gemini-3.8-flash';

    let botBubble = null;
    let contentEl = null;
    let fullText  = '';

    function showError(msg) {
      hideTyping();
      if (botBubble) botBubble.remove();
      appendBubble('bot', '<span style="color:var(--color-danger)">' + msg + '</span>');
    }

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, lang, api_key: userKey, model }),
      });

      // Non-2xx before streaming (e.g. 401 no-key)
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        history.pop();
        const errStr = errData.error || String(resp.status);
        if (errStr.includes('no_key') || resp.status === 401) checkStatus();
        showError(renderText(errData.reply || errStr));
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
            const errStr = evt.error;
            let userMsg = renderText(errStr);
            if (errStr.includes('billing_depleted')) {
              userMsg = '⚠️ <strong>API key credits depleted.</strong><br>' +
                'Get a free key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> and update it in Settings.';
            } else if (errStr.includes('model_not_found')) {
              userMsg = '⚠️ <strong>Model not available.</strong> Pick another model in Settings → AI Assistant.';
            } else if (errStr.includes('busy')) {
              userMsg = '⚠️ Gemini servers are busy — please try again in a moment.';
            }
            showError(userMsg);
            return;
          }

          if (evt.delta) {
            hideTyping();
            if (!botBubble) {
              botBubble = appendBubble('bot', '');
              contentEl = botBubble.querySelector('.chat-bubble__content');
            }
            fullText += evt.delta;
            contentEl.innerHTML = renderText(fullText);
            scrollBottom();
          }

          if (evt.done) {
            const reply = evt.reply || fullText;
            history.push({ role: 'assistant', content: reply });
            if (evt.logged && evt.logged.length > 0) {
              var hasAI = false;
              var parts = evt.logged.map(function(item) {
                var name   = typeof item === 'object' ? item.name   : item;
                var isAI   = typeof item === 'object' && item.source === 'ai_estimate';
                if (isAI) hasAI = true;
                return isAI ? name + ' (~AI)' : name;
              });
              loggedText.textContent = 'Logged: ' + parts.join(', ') + (hasAI ? ' — ~AI: estimated from Gemini knowledge, not from database' : '');
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
        appendBubble('bot', '<em>No response received.</em>');
      }

    } catch (err) {
      history.pop();
      showError(renderText(String(err)));
    } finally {
      busy = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  // ----------------------------------------------------------------
  // Auto-resize textarea
  // ----------------------------------------------------------------
  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 96) + 'px';
  }

  inputEl.addEventListener('input', autoResize);

  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    send();
  });

  // ----------------------------------------------------------------
  // Welcome message i18n
  // ----------------------------------------------------------------
  function setWelcome() {
    const lang = (typeof Lang !== 'undefined') ? Lang.get() : 'en';
    const welcomeEl = document.getElementById('chat-welcome-text');
    const subtitleEl = document.getElementById('chat-subtitle');
    if (lang === 'tr') {
      welcomeEl.innerHTML = 'Merhaba! Yediklerinizi kaydetmenize yardım edebilirim. Örneğin: <em>"Kahvaltıda 2 yumurta ve tost yedim"</em> veya <em>"80g yulaf ve süt"</em>.';
      subtitleEl.textContent = 'Yapay Zeka Beslenme Asistanı';
    } else {
      welcomeEl.innerHTML = 'Hi! I can help you log your food. Just tell me what you ate — for example: <em>"I had 2 eggs and toast for breakfast"</em> or <em>"80g of oats with milk"</em>.';
      subtitleEl.textContent = 'AI Nutrition Assistant';
    }
  }

  // ----------------------------------------------------------------
  // Init
  // ----------------------------------------------------------------
  setWelcome();
  checkStatus();
  inputEl.focus();
})();