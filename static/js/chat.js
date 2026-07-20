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
    const userKey = localStorage.getItem('nt_anthropic_key') || '';
    try {
      const data = await api('/api/chat/status?has_user_key=' + (userKey ? '1' : '0'));
      const ready = data.ready;
      statusBadge.classList.toggle('ready',   ready);
      statusBadge.classList.toggle('offline', !ready);
      if (ready) {
        if (data.backend === 'anthropic') {
          const src = userKey && !data.server_key ? ' (your key)' : '';
          statusLabel.textContent = 'Anthropic · ' + (data.model || '') + src;
        } else if (data.backend === 'ollama') {
          statusLabel.textContent = 'Ollama · ' + (data.model || '');
        } else {
          statusLabel.textContent = 'Smart search mode';
        }
      } else {
        statusLabel.textContent = 'No AI key — using smart search mode';
      }
    } catch (_) {
      statusBadge.classList.add('offline');
      statusLabel.textContent = 'Cannot reach backend';
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
    const userKey = localStorage.getItem('nt_anthropic_key') || '';

    try {
      const data = await api('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, lang, api_key: userKey }),
      });

      hideTyping();
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