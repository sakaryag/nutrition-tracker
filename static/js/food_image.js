(function () {
  'use strict';

  var _styleInjected = false;

  function injectStyles() {
    if (_styleInjected) return;
    _styleInjected = true;
    var style = document.createElement('style');
    style.textContent = [
      '#fi-overlay{position:fixed;inset:0;z-index:1001;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;}',
      '#fi-card{background:#fff;border-radius:.5rem;padding:1.25rem;width:min(460px,95vw);box-shadow:0 8px 24px rgba(0,0,0,.3);max-height:90vh;overflow-y:auto;}',
      '#fi-card h3{margin:0 0 .75rem;font-size:1.1rem;}',
      '#fi-mode-row{display:flex;gap:.5rem;margin-bottom:.75rem;}',
      '#fi-video{width:100%;border-radius:.375rem;background:#000;display:block;}',
      '#fi-canvas{display:none;}',
      '#fi-thumb{width:100%;max-height:220px;object-fit:contain;border-radius:.375rem;border:1px solid #e2e8f0;display:block;}',
      '#fi-status{margin:.5rem 0 0;font-size:.875rem;color:#718096;min-height:1.25rem;}',
      '#fi-error{margin:.5rem 0 0;color:#D9534F;font-size:.875rem;min-height:1.25rem;}',
      '#fi-items-list{margin:.75rem 0 0;border-top:1px solid #e2e8f0;padding-top:.5rem;}',
      '.fi-item-row{display:flex;align-items:flex-start;gap:.5rem;padding:.4rem 0;border-bottom:1px solid #f0f0f0;}',
      '.fi-item-row:last-child{border-bottom:none;}',
      '.fi-item-info{flex:1;font-size:.875rem;}',
      '.fi-item-name{font-weight:600;}',
      '.fi-item-macros{color:#718096;font-size:.8rem;}',
      '#fi-actions{display:flex;justify-content:flex-end;gap:.5rem;margin-top:1rem;}',
      '#fi-analyse-row{display:flex;gap:.5rem;margin-top:.75rem;}',
    ].join('');
    document.head.appendChild(style);
  }

  function buildModal() {
    var overlay = document.createElement('div');
    overlay.id = 'fi-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Food Image Recognition');

    var card = document.createElement('div');
    card.id = 'fi-card';

    var title = document.createElement('h3');
    title.textContent = 'Recognise Food from Photo';
    card.appendChild(title);

    var modeRow = document.createElement('div');
    modeRow.id = 'fi-mode-row';

    var cameraBtn = document.createElement('button');
    cameraBtn.className = 'btn btn-secondary';
    cameraBtn.id = 'fi-camera-btn';
    cameraBtn.textContent = 'Take Photo';

    var uploadBtn = document.createElement('button');
    uploadBtn.className = 'btn btn-secondary';
    uploadBtn.id = 'fi-upload-btn';
    uploadBtn.textContent = 'Upload Image';

    var fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/jpeg,image/png,image/gif,image/webp';
    fileInput.style.display = 'none';
    fileInput.id = 'fi-file-input';

    modeRow.appendChild(cameraBtn);
    modeRow.appendChild(uploadBtn);
    modeRow.appendChild(fileInput);
    card.appendChild(modeRow);

    var video = document.createElement('video');
    video.id = 'fi-video';
    video.setAttribute('autoplay', '');
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    video.hidden = true;
    card.appendChild(video);

    var canvas = document.createElement('canvas');
    canvas.id = 'fi-canvas';
    card.appendChild(canvas);

    var shutterRow = document.createElement('div');
    shutterRow.id = 'fi-shutter-row';
    shutterRow.style.cssText = 'display:none;margin-top:.5rem;text-align:center;';
    var shutterBtn = document.createElement('button');
    shutterBtn.className = 'btn btn-primary';
    shutterBtn.id = 'fi-shutter-btn';
    shutterBtn.textContent = 'Capture';
    shutterRow.appendChild(shutterBtn);
    card.appendChild(shutterRow);

    var thumb = document.createElement('img');
    thumb.id = 'fi-thumb';
    thumb.alt = 'Food preview';
    thumb.hidden = true;
    card.appendChild(thumb);

    var analyseRow = document.createElement('div');
    analyseRow.id = 'fi-analyse-row';
    analyseRow.style.display = 'none';
    var analyseBtn = document.createElement('button');
    analyseBtn.className = 'btn btn-primary';
    analyseBtn.id = 'fi-analyse-btn';
    analyseBtn.textContent = 'Analyse';
    var retakeBtn = document.createElement('button');
    retakeBtn.className = 'btn btn-secondary';
    retakeBtn.id = 'fi-retake-btn';
    retakeBtn.textContent = 'Retake / Change';
    analyseRow.appendChild(analyseBtn);
    analyseRow.appendChild(retakeBtn);
    card.appendChild(analyseRow);

    var statusEl = document.createElement('p');
    statusEl.id = 'fi-status';
    card.appendChild(statusEl);

    var errorEl = document.createElement('p');
    errorEl.id = 'fi-error';
    card.appendChild(errorEl);

    var itemsList = document.createElement('div');
    itemsList.id = 'fi-items-list';
    itemsList.hidden = true;
    card.appendChild(itemsList);

    var actions = document.createElement('div');
    actions.id = 'fi-actions';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-secondary';
    cancelBtn.id = 'fi-cancel-btn';
    cancelBtn.textContent = 'Cancel';
    actions.appendChild(cancelBtn);
    card.appendChild(actions);

    overlay.appendChild(card);
    return {
      overlay: overlay, card: card, video: video, canvas: canvas,
      shutterRow: shutterRow, shutterBtn: shutterBtn,
      thumb: thumb, analyseRow: analyseRow, analyseBtn: analyseBtn, retakeBtn: retakeBtn,
      statusEl: statusEl, errorEl: errorEl, itemsList: itemsList,
      cancelBtn: cancelBtn, cameraBtn: cameraBtn, uploadBtn: uploadBtn, fileInput: fileInput,
    };
  }

  function stopTracks(stream) {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
  }

  window.openFoodImageScanner = function (onResult) {
    var apiKey = (typeof localStorage !== 'undefined') ? (localStorage.getItem('nt_anthropic_key') || '') : '';
    if (!apiKey) {
      if (typeof showToast === 'function') {
        showToast('Add your Anthropic API key in Settings to use photo recognition.', 'error', 5000);
      }
      return;
    }
    if (typeof ApiUsage !== 'undefined') {
      var budgetState = ApiUsage.checkBudget();
      if (!budgetState.ok) {
        if (typeof showToast === 'function') {
          showToast('Monthly budget of $' + budgetState.budget.toFixed(2) + ' reached. Update limit in Settings.', 'error', 5000);
        }
        return;
      }
    }
    injectStyles();
    var els = buildModal();
    document.body.appendChild(els.overlay);

    var stream = null;
    var capturedBlob = null;
    var closed = false;

    function close() {
      if (closed) return;
      closed = true;
      stopTracks(stream);
      stream = null;
      document.removeEventListener('keydown', onKeyDown);
      if (els.overlay.parentNode) els.overlay.parentNode.removeChild(els.overlay);
    }

    function onKeyDown(e) { if (e.key === 'Escape') close(); }
    document.addEventListener('keydown', onKeyDown);
    els.cancelBtn.addEventListener('click', close);

    function setStatus(msg) { els.statusEl.textContent = msg; }
    function setError(msg) { els.errorEl.textContent = msg; }
    function clearMessages() { els.statusEl.textContent = ''; els.errorEl.textContent = ''; }

    function showPreview(blob) {
      capturedBlob = blob;
      var url = URL.createObjectURL(blob);
      els.thumb.src = url;
      els.thumb.hidden = false;
      els.analyseRow.style.display = 'flex';
      els.itemsList.hidden = true;
      clearMessages();
    }

    function resetToModeSelect() {
      capturedBlob = null;
      stopTracks(stream); stream = null;
      els.video.hidden = true;
      els.video.srcObject = null;
      els.shutterRow.style.display = 'none';
      els.thumb.hidden = true;
      els.analyseRow.style.display = 'none';
      els.itemsList.hidden = true;
      clearMessages();
    }

    els.retakeBtn.addEventListener('click', resetToModeSelect);

    els.cameraBtn.addEventListener('click', function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setError('Camera not available on this device/browser.');
        return;
      }
      // Stop any existing stream before starting a new one
      stopTracks(stream); stream = null;
      els.video.hidden = true;
      els.shutterRow.style.display = 'none';
      setStatus('Starting camera...');
      navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } } })
        .then(function (s) {
          if (closed) { stopTracks(s); return; }
          stream = s;
          els.video.srcObject = stream;
          els.video.hidden = false;
          els.video.play();
          els.shutterRow.style.display = 'block';
          setStatus('Point camera at food, then press Capture.');
        })
        .catch(function () {
          if (closed) return;
          setError('Camera access denied.');
        });
    });

    els.shutterBtn.addEventListener('click', function () {
      if (!stream) return;
      var v = els.video;
      els.canvas.width = v.videoWidth || 640;
      els.canvas.height = v.videoHeight || 480;
      els.canvas.getContext('2d').drawImage(v, 0, 0);
      stopTracks(stream); stream = null;
      els.video.hidden = true;
      els.shutterRow.style.display = 'none';
      els.canvas.toBlob(function (blob) {
        if (blob) showPreview(blob);
      }, 'image/jpeg', 0.85);
    });

    els.uploadBtn.addEventListener('click', function () {
      // Stop camera if running before switching to upload
      stopTracks(stream); stream = null;
      els.video.hidden = true;
      els.video.srcObject = null;
      els.shutterRow.style.display = 'none';
      els.fileInput.value = '';
      els.fileInput.click();
    });

    els.fileInput.addEventListener('change', function () {
      var file = els.fileInput.files[0];
      if (!file) return;
      if (!file.type.match(/^image\/(jpeg|png|gif|webp)$/)) {
        setError('Please select a JPEG, PNG, GIF or WebP image.');
        return;
      }
      showPreview(file);
    });

    els.analyseBtn.addEventListener('click', function () {
      if (!capturedBlob) return;
      els.analyseBtn.disabled = true;
      els.retakeBtn.disabled = true;
      setStatus('Analysing...');
      setError('');
      els.itemsList.hidden = true;

      var lang = (typeof Lang !== 'undefined' && Lang.get) ? Lang.get() : 'en';
      var model = (typeof ApiUsage !== 'undefined') ? ApiUsage.getModel() : 'claude-haiku-4-5-20251001';

      var fd = new FormData();
      fd.append('image', capturedBlob, 'food.jpg');
      fd.append('api_key', apiKey);
      fd.append('lang', lang);
      fd.append('model', model);

      fetch('/api/foods/image', { method: 'POST', body: fd })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          els.analyseBtn.disabled = false;
          els.retakeBtn.disabled = false;
          if (!data.found) {
            setStatus('');
            setError(data.message || 'Recognition failed.');
            return;
          }
          setStatus('');
          if (data.usage && data.usage.input_tokens && typeof ApiUsage !== 'undefined') {
            ApiUsage.addCost(data.usage.input_tokens, data.usage.output_tokens, data.usage.model || model);
          }
          var items = data.items || [];
          if (items.length === 1) {
            var it = items[0];
            close();
            onResult({ name: it.food_name, protein: it.protein, fat: it.fat, carbs: it.carbs, calories: it.calories, estimated_grams: it.estimated_grams });
            return;
          }
          renderItemList(items);
        })
        .catch(function () {
          els.analyseBtn.disabled = false;
          els.retakeBtn.disabled = false;
          setStatus('');
          setError('Request failed. Check connection.');
        });
    });

    function renderItemList(items) {
      els.itemsList.hidden = false;
      els.itemsList.innerHTML = '<p style="font-size:.875rem;font-weight:600;margin:0 0 .5rem;">Select items to log:</p>';
      items.forEach(function (it, idx) {
        var row = document.createElement('div');
        row.className = 'fi-item-row';
        var chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.checked = true;
        chk.id = 'fi-chk-' + idx;
        chk.dataset.idx = idx;
        var info = document.createElement('div');
        info.className = 'fi-item-info';
        var nameEl = document.createElement('div');
        nameEl.className = 'fi-item-name';
        nameEl.textContent = it.food_name + ' (' + it.estimated_grams + 'g)';
        var macroEl = document.createElement('div');
        macroEl.className = 'fi-item-macros';
        macroEl.textContent = 'P:' + it.protein + 'g F:' + it.fat + 'g C:' + it.carbs + 'g ' + it.calories + 'kcal';
        info.appendChild(nameEl);
        info.appendChild(macroEl);
        row.appendChild(chk);
        row.appendChild(info);
        els.itemsList.appendChild(row);
      });

      var logBtn = document.createElement('button');
      logBtn.className = 'btn btn-primary';
      logBtn.style.marginTop = '.75rem';
      logBtn.textContent = 'Log Selected';
      logBtn.addEventListener('click', function () {
        var checked = Array.prototype.slice.call(els.itemsList.querySelectorAll('input[type=checkbox]:checked'));
        if (!checked.length) { setError('Select at least one item.'); return; }
        logBtn.disabled = true;
        setStatus('Logging...');
        var today = new Date().toISOString().slice(0, 10);
        // POST each item directly to /api/entries — avoids modal re-open loop
        var promises = checked.map(function (chk) {
          var it = items[parseInt(chk.dataset.idx, 10)];
          return fetch('/api/entries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              food_name: it.food_name,
              protein: it.protein,
              fat: it.fat,
              carbs: it.carbs,
              calories: it.calories,
              serving_size: it.estimated_grams,
              serving_unit: 'g',
              date: today,
            }),
          });
        });
        Promise.all(promises)
          .then(function () {
            close();
            if (typeof loadPage === 'function') loadPage();
          })
          .catch(function () {
            logBtn.disabled = false;
            setError('Some items failed to log. Try again.');
            setStatus('');
          });
      });
      els.itemsList.appendChild(logBtn);
    }
  };
})();
