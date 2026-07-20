(function () {
  'use strict';

  var _styleInjected = false;

  function injectStyles() {
    if (_styleInjected) return;
    _styleInjected = true;
    var style = document.createElement('style');
    style.textContent = [
      '#bc-overlay{position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;}',
      '#bc-card{background:#fff;border-radius:.5rem;padding:1.25rem;width:min(420px,95vw);box-shadow:0 8px 24px rgba(0,0,0,.25);}',
      '#bc-card h3{margin:0 0 .75rem;font-size:1.1rem;}',
      '#bc-video{width:100%;border-radius:.375rem;background:#000;display:block;}',
      '#bc-status{margin:.5rem 0 0;font-size:.875rem;color:#718096;min-height:1.25rem;}',
      '#bc-error{margin:.5rem 0 0;color:#D9534F;font-size:.875rem;min-height:1.25rem;}',
      '#bc-manual-row{display:flex;gap:.5rem;margin-top:.75rem;}',
      '#bc-manual-row input{flex:1;padding:.4rem .6rem;border:1px solid #e2e8f0;border-radius:.375rem;font:inherit;}',
      '#bc-actions{display:flex;justify-content:flex-end;gap:.5rem;margin-top:1rem;}',
    ].join('');
    document.head.appendChild(style);
  }

  function buildModal() {
    var overlay = document.createElement('div');
    overlay.id = 'bc-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Barcode Scanner');

    var card = document.createElement('div');
    card.id = 'bc-card';

    var title = document.createElement('h3');
    title.textContent = 'Scan Barcode';
    card.appendChild(title);

    var video = document.createElement('video');
    video.id = 'bc-video';
    video.setAttribute('autoplay', '');
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    card.appendChild(video);

    var statusEl = document.createElement('p');
    statusEl.id = 'bc-status';
    statusEl.textContent = 'Loading scanner…';
    card.appendChild(statusEl);

    var errorEl = document.createElement('p');
    errorEl.id = 'bc-error';
    card.appendChild(errorEl);

    var actions = document.createElement('div');
    actions.id = 'bc-actions';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-secondary';
    cancelBtn.textContent = 'Cancel';
    actions.appendChild(cancelBtn);
    card.appendChild(actions);

    overlay.appendChild(card);
    return { overlay: overlay, card: card, video: video, statusEl: statusEl, errorEl: errorEl, cancelBtn: cancelBtn };
  }

  function stopTracks(stream) {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
  }

  var _zxingReady = false;
  var _zxingCbs = [];
  function loadZXing(cb) {
    if (_zxingReady) { cb(null); return; }
    _zxingCbs.push(cb);
    if (_zxingCbs.length > 1) return;
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/@zxing/browser@0.1.5/umd/index.min.js';
    s.onload = function () {
      _zxingReady = true;
      _zxingCbs.splice(0).forEach(function (fn) { fn(null); });
    };
    s.onerror = function () {
      _zxingCbs.splice(0).forEach(function (fn) { fn(new Error('load failed')); });
    };
    document.head.appendChild(s);
  }

  function showManualInput(card, statusEl, errorEl, lookup) {
    statusEl.textContent = 'Enter the barcode number from the product.';
    var row = document.createElement('div');
    row.id = 'bc-manual-row';
    var input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Enter barcode number';
    input.inputMode = 'numeric';
    var btn = document.createElement('button');
    btn.className = 'btn btn-primary';
    btn.textContent = 'Look up';
    row.appendChild(input);
    row.appendChild(btn);
    card.insertBefore(row, statusEl);
    function doLookup() {
      var code = input.value.trim();
      if (!code) return;
      btn.disabled = true;
      lookup(code, function () { btn.disabled = false; });
    }
    btn.addEventListener('click', doLookup);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') doLookup(); });
    setTimeout(function () { input.focus(); }, 50);
  }

  window.openBarcodeScanner = function (onResult) {
    injectStyles();
    var hasCamera = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    var els = buildModal();
    document.body.appendChild(els.overlay);

    var stream = null;
    var zxingReader = null;
    var closed = false;

    function close() {
      if (closed) return;
      closed = true;
      if (zxingReader) { try { zxingReader.reset(); } catch (_) {} zxingReader = null; }
      stopTracks(stream);
      stream = null;
      document.removeEventListener('keydown', onKeyDown);
      if (els.overlay.parentNode) els.overlay.parentNode.removeChild(els.overlay);
    }

    function onKeyDown(e) { if (e.key === 'Escape') close(); }
    document.addEventListener('keydown', onKeyDown);
    els.cancelBtn.addEventListener('click', close);

    function lookup(code, resetFn) {
      els.statusEl.textContent = 'Looking up…';
      els.errorEl.textContent = '';
      fetch('/api/foods/barcode?code=' + encodeURIComponent(code))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.found) { close(); onResult(data); }
          else {
            els.errorEl.textContent = data.message || 'Product not found.';
            els.statusEl.textContent = '';
            if (resetFn) resetFn();
          }
        })
        .catch(function () {
          els.errorEl.textContent = 'Lookup failed. Check connection.';
          els.statusEl.textContent = '';
          if (resetFn) resetFn();
        });
    }

    if (!hasCamera) {
      els.video.hidden = true;
      showManualInput(els.card, els.statusEl, els.errorEl, lookup);
      return;
    }

    function showRetry() {
      var btn = document.createElement('button');
      btn.className = 'btn btn-secondary';
      btn.textContent = 'Try again';
      btn.style.marginTop = '.5rem';
      btn.addEventListener('click', function () {
        btn.remove();
        els.errorEl.textContent = '';
        startScanning();
      });
      els.errorEl.parentNode.insertBefore(btn, els.errorEl.nextSibling);
    }

    function handleCode(code) {
      els.statusEl.textContent = 'Found: ' + code + '. Looking up…';
      stopTracks(stream);
      stream = null;
      lookup(code, showRetry);
    }

    function startScanning() {
      els.statusEl.textContent = 'Starting camera…';
      els.video.hidden = false;

      navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } } })
        .then(function (s) {
          if (closed) { stopTracks(s); return; }
          stream = s;
          els.video.srcObject = stream;
          els.video.play();
          els.statusEl.textContent = 'Point camera at barcode…';

          if (typeof BarcodeDetector !== 'undefined') {
            // Native API (Chrome Android, Safari 17.4+)
            var detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
            (function loop() {
              if (closed) return;
              requestAnimationFrame(function () {
                if (closed) return;
                if (!els.video.videoWidth) { loop(); return; }
                detector.detect(els.video)
                  .then(function (barcodes) {
                    if (closed) return;
                    if (!barcodes.length) { loop(); return; }
                    handleCode(barcodes[0].rawValue);
                  })
                  .catch(function () { if (!closed) loop(); });
              });
            })();
          } else {
            // ZXing BrowserMultiFormatReader (all other browsers)
            zxingReader = new ZXingBrowser.BrowserMultiFormatReader();
            zxingReader.decodeFromStream(stream, els.video, function (result, err) {
              if (closed) return;
              if (result) {
                zxingReader.reset();
                zxingReader = null;
                handleCode(result.getText());
              }
              // err is NotFoundException on every empty frame — normal, ignore
            });
          }
        })
        .catch(function () {
          if (closed) return;
          els.video.hidden = true;
          els.errorEl.textContent = 'Camera access denied. Enter barcode manually.';
          showManualInput(els.card, els.statusEl, els.errorEl, lookup);
        });
    }

    if (typeof BarcodeDetector !== 'undefined') {
      startScanning();
    } else {
      loadZXing(function (err) {
        if (closed) return;
        if (err) {
          els.video.hidden = true;
          els.errorEl.textContent = 'Scanner library failed to load.';
          showManualInput(els.card, els.statusEl, els.errorEl, lookup);
          return;
        }
        startScanning();
      });
    }
  };
})();