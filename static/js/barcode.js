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
    return { overlay: overlay, video: video, statusEl: statusEl, errorEl: errorEl, cancelBtn: cancelBtn };
  }

  function stopTracks(stream) {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
  }

  // Load ZXing decoder from CDN (only when BarcodeDetector not available)
  var _zxingCallbacks = [];
  function loadZXing(cb) {
    if (typeof ZXing !== 'undefined') { cb(null); return; }
    _zxingCallbacks.push(cb);
    if (_zxingCallbacks.length > 1) return;
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
    s.onload = function () { _zxingCallbacks.splice(0).forEach(function (fn) { fn(null); }); };
    s.onerror = function () { _zxingCallbacks.splice(0).forEach(function (fn) { fn(new Error('load failed')); }); };
    document.head.appendChild(s);
  }

  // Show manual barcode input inside the card
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
    // Insert before statusEl
    card.insertBefore(row, statusEl);
    function doLookup() {
      var code = input.value.trim();
      if (!code) return;
      btn.disabled = true;
      lookup(code, statusEl, errorEl, function () { btn.disabled = false; });
    }
    btn.addEventListener('click', doLookup);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') doLookup(); });
    setTimeout(function () { input.focus(); }, 50);
  }

  window.openBarcodeScanner = function (onResult) {
    injectStyles();

    // Always try camera; only fall back to text if no camera API at all
    var hasCamera = typeof navigator !== 'undefined' && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    var els = buildModal();
    document.body.appendChild(els.overlay);

    var stream = null;
    var rafId = null;
    var closed = false;

    function close() {
      if (closed) return;
      closed = true;
      if (rafId) cancelAnimationFrame(rafId);
      stopTracks(stream);
      stream = null;
      document.removeEventListener('keydown', onKeyDown);
      if (els.overlay.parentNode) els.overlay.parentNode.removeChild(els.overlay);
    }

    function onKeyDown(e) { if (e.key === 'Escape') close(); }
    document.addEventListener('keydown', onKeyDown);
    els.cancelBtn.addEventListener('click', close);

    function lookup(code, statusEl, errorEl, resetFn) {
      statusEl.textContent = 'Looking up…';
      errorEl.textContent = '';
      fetch('/api/foods/barcode?code=' + encodeURIComponent(code))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.found) { close(); onResult(data); }
          else {
            errorEl.textContent = data.message || 'Product not found.';
            statusEl.textContent = '';
            if (resetFn) resetFn();
          }
        })
        .catch(function () {
          errorEl.textContent = 'Lookup failed. Check connection.';
          statusEl.textContent = '';
          if (resetFn) resetFn();
        });
    }

    if (!hasCamera) {
      els.video.hidden = true;
      showManualInput(els.overlay.querySelector('#bc-card'), els.statusEl, els.errorEl, lookup);
      return;
    }

    function handleCode(code) {
      els.statusEl.textContent = 'Found: ' + code + '. Looking up…';
      stopTracks(stream);
      stream = null;
      lookup(code, els.statusEl, els.errorEl, function () {
        var retryBtn = document.createElement('button');
        retryBtn.className = 'btn btn-secondary';
        retryBtn.textContent = 'Try again';
        retryBtn.style.marginTop = '.5rem';
        retryBtn.addEventListener('click', function () {
          retryBtn.remove();
          els.errorEl.textContent = '';
          startCamera();
        });
        els.errorEl.parentNode.insertBefore(retryBtn, els.errorEl.nextSibling);
      });
    }

    // Native BarcodeDetector scan loop (Chrome Android, Safari 17.4+)
    function scanWithNative() {
      var detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
      var scanning = false;
      els.statusEl.textContent = 'Point camera at barcode…';
      (function loop() {
        if (closed) return;
        rafId = requestAnimationFrame(function () {
          if (closed || scanning) { if (!closed) loop(); return; }
          if (!els.video.videoWidth) { loop(); return; }
          scanning = true;
          detector.detect(els.video)
            .then(function (barcodes) {
              scanning = false;
              if (closed) return;
              if (!barcodes.length) { loop(); return; }
              handleCode(barcodes[0].rawValue);
            })
            .catch(function () { scanning = false; if (!closed) loop(); });
        });
      })();
    }

    // ZXing canvas scan loop (all other browsers)
    function scanWithZXing() {
      var reader = new ZXing.MultiFormatReader();
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d', { willReadFrequently: true });
      els.statusEl.textContent = 'Point camera at barcode…';
      (function loop() {
        if (closed) return;
        rafId = requestAnimationFrame(function () {
          if (closed) return;
          if (!els.video.videoWidth) { loop(); return; }
          canvas.width = els.video.videoWidth;
          canvas.height = els.video.videoHeight;
          ctx.drawImage(els.video, 0, 0);
          try {
            var imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            var lum = new ZXing.RGBLuminanceSource(imgData.data, canvas.width, canvas.height);
            var bmp = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
            var result = reader.decode(bmp);
            handleCode(result.getText());
          } catch (e) {
            loop();
          }
        });
      })();
    }

    function startCamera() {
      els.statusEl.textContent = 'Starting camera…';
      els.video.hidden = false;
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(function (s) {
          if (closed) { stopTracks(s); return; }
          stream = s;
          els.video.srcObject = stream;
          els.video.play();
          if (typeof BarcodeDetector !== 'undefined') {
            scanWithNative();
          } else {
            scanWithZXing();
          }
        })
        .catch(function () {
          if (closed) return;
          els.video.hidden = true;
          els.errorEl.textContent = 'Camera access denied. Enter barcode manually.';
          showManualInput(els.overlay.querySelector('#bc-card'), els.statusEl, els.errorEl, lookup);
        });
    }

    // When BarcodeDetector not native, load ZXing first then open camera
    if (typeof BarcodeDetector !== 'undefined') {
      startCamera();
    } else {
      els.statusEl.textContent = 'Loading scanner…';
      loadZXing(function (err) {
        if (closed) return;
        if (err) {
          els.video.hidden = true;
          els.errorEl.textContent = 'Scanner library failed to load. Enter barcode manually.';
          showManualInput(els.overlay.querySelector('#bc-card'), els.statusEl, els.errorEl, lookup);
          return;
        }
        startCamera();
      });
    }
  };
})();