(function () {
  'use strict';

  var _styleInjected = false;

  function injectStyles() {
    if (_styleInjected) return;
    _styleInjected = true;
    var style = document.createElement('style');
    style.textContent = [
      '#bc-overlay{position:fixed;inset:0;z-index:1300;background:rgba(9,9,11,.88);display:flex;align-items:flex-end;justify-content:center;font-family:var(--font-display,system-ui,sans-serif);}',
      '@media (min-width:600px){#bc-overlay{align-items:center;}#bc-card{border-radius:32px!important;}}',
      '#bc-card{background:#fff;color:var(--color-ink,#18181B);border-radius:32px 32px 0 0;padding:12px 24px max(24px,env(safe-area-inset-bottom));width:min(480px,100vw);max-height:92vh;overflow-y:auto;box-shadow:0 -12px 40px rgba(0,0,0,.3);box-sizing:border-box;}',
      '#bc-card::before{content:"";display:block;width:40px;height:5px;border-radius:3px;background:#E4E4E7;margin:0 auto 16px;}',
      '#bc-card h3{margin:0 0 1rem;font-size:1.4rem;font-weight:800;letter-spacing:-.01em;}',
      '.bc-viewfinder{position:relative;border-radius:24px;overflow:hidden;background:#000;}',
      '.bc-viewfinder[hidden]{display:none;}',
      '#bc-video{width:100%;aspect-ratio:4/3;object-fit:cover;background:#000;display:block;}',
      '.bc-reticle{position:absolute;left:50%;top:50%;width:75%;height:45%;transform:translate(-50%,-50%);pointer-events:none;}',
      '.bc-reticle span{position:absolute;width:32px;height:32px;border:4px solid #fff;}',
      '.bc-reticle span:nth-child(1){top:0;left:0;border-right:0;border-bottom:0;border-top-left-radius:18px;}',
      '.bc-reticle span:nth-child(2){top:0;right:0;border-left:0;border-bottom:0;border-top-right-radius:18px;}',
      '.bc-reticle span:nth-child(3){bottom:0;left:0;border-right:0;border-top:0;border-bottom-left-radius:18px;}',
      '.bc-reticle span:nth-child(4){bottom:0;right:0;border-left:0;border-top:0;border-bottom-right-radius:18px;}',
      '#bc-status{margin:.75rem 0 0;font-size:.875rem;color:var(--color-text-secondary,#71717A);min-height:1.25rem;}',
      '#bc-error{margin:.25rem 0 0;color:#DC2626;font-size:.875rem;min-height:1.25rem;}',
      '#bc-manual-row{display:flex;gap:.5rem;margin-top:.75rem;}',
      '#bc-manual-row input{flex:1;min-width:0;padding:.7rem 1rem;border:1px solid #E4E4E7;border-radius:999px;font:inherit;}',
      '#bc-manual-row input:focus{outline:none;border-color:var(--color-primary,#8B68F6);box-shadow:0 0 0 3px rgba(139,104,246,.18);}',
      '#bc-card .btn{border-radius:999px;min-height:44px;padding:0 1.25rem;font-weight:700;}',
      '#bc-card .btn-primary{background:var(--color-ink,#18181B);border-color:var(--color-ink,#18181B);color:#fff;}',
      '#bc-card .btn-secondary{background:#F4F4F5;border-color:#F4F4F5;color:var(--color-ink,#18181B);}',
      '#bc-actions{display:flex;justify-content:stretch;gap:.5rem;margin-top:1rem;}',
      '#bc-actions .btn{flex:1;}',
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
    video.muted = true;
    var viewfinder = document.createElement('div');
    viewfinder.className = 'bc-viewfinder';
    viewfinder.appendChild(video);
    var reticle = document.createElement('div');
    reticle.className = 'bc-reticle';
    reticle.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < 4; i++) reticle.appendChild(document.createElement('span'));
    viewfinder.appendChild(reticle);
    card.appendChild(viewfinder);
    // Logic toggles video.hidden; mirror it onto the viewfinder wrapper.
    new MutationObserver(function () { viewfinder.hidden = video.hidden; })
      .observe(video, { attributes: true, attributeFilter: ['hidden'] });

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

  // @zxing/library UMD — exposes global ZXing with BrowserMultiFormatReader
  var _zxingReady = false;
  var _zxingCbs = [];
  function loadZXing(cb) {
    if (_zxingReady) { cb(null); return; }
    _zxingCbs.push(cb);
    if (_zxingCbs.length > 1) return;
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
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
    var returnFocus = document.activeElement;
    document.body.appendChild(els.overlay);
    els.cancelBtn.focus();

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
      if (returnFocus && returnFocus.focus && document.contains(returnFocus)) returnFocus.focus();
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
      if (closed) return;
      // Stop ZXing reader before doing the lookup so it doesn't keep firing
      if (zxingReader) { try { zxingReader.reset(); } catch (_) {} zxingReader = null; }
      stopTracks(stream);
      stream = null;
      els.statusEl.textContent = 'Found: ' + code + '. Looking up…';
      lookup(code, function () {
        showRetry();
        // Restart camera on retry
        startScanning();
      });
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
            // Native API — Chrome Android, Safari 17.4+
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
            // ZXing.BrowserMultiFormatReader — all other browsers
            // decodeFromStream fires callback on every frame:
            //   result is set when a barcode is found; err is NotFoundException otherwise (normal)
            zxingReader = new ZXing.BrowserMultiFormatReader();
            var handled = false;
            zxingReader.decodeFromStream(stream, els.video, function (result, err) {
              if (closed || handled) return;
              if (result) {
                handled = true;
                handleCode(result.getText());
              }
              // err === NotFoundException on empty frames — ignore
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
          els.errorEl.textContent = 'Scanner unavailable. Enter barcode manually.';
          showManualInput(els.card, els.statusEl, els.errorEl, lookup);
          return;
        }
        startScanning();
      });
    }
  };
})();