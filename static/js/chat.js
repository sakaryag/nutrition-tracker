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
          'Get your <strong>free</strong> key (no credit card, no developer account needed) at<br>' +
          '<a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener" ' +
          'style="color:var(--color-primary,#3b82f6);">aistudio.google.com/apikey</a><br>' +
          '<span style="font-size:.875rem;color:var(--color-text-muted,#666);">Then paste it in Settings → AI Assistant</span>';
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
  // Send message
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

    const lang = (typeof Lang !== 'undefined') ? Lang.get() : 'en';
    const userKey = localStorage.getItem('nt_gemini_key') || '';

    const model = (typeof ApiUsage !== 'undefined') ? ApiUsage.getModel() : 'gemini-3.8-flash';

    try {
      const data = await api('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, lang, api_key: userKey, model }),
      });

      hideTyping();
      if (data.usage && data.usage.input_tokens && typeof ApiUsage !== 'undefined') {
        ApiUsage.addCost(data.usage.input_tokens, data.usage.output_tokens, data.usage.model || model);
      }
      const reply = data.reply || '(no reply)';
      history.push({ role: 'assistant', content: reply });
      appendBubble('bot', renderText(reply));

      if (data.logged && data.logged.length > 0) {
        loggedText.textContent = 'Logged: ' + data.logged.join(', ');
        loggedBanner.hidden = false;
        setTimeout(() => { loggedBanner.hidden = true; }, 6000);
      }
    } catch (err) {
      hideTyping();
      // Remove the user message from history so the next send doesn't
      // create consecutive user messages (Anthropic rejects that with 400)
      history.pop();
      // If key was rejected, re-check status so setup banner reappears if needed
      if (String(err).includes('no_key') || String(err).includes('401')) checkStatus();
      appendBubble('bot', '<em style="color:var(--color-danger)">' + renderText(String(err)) + '</em>');
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