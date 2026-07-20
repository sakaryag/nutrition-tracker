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

  function buildModal(useCamera) {
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

    var video = null;
    var manualInput = null;
    var lookupBtn = null;

    if (useCamera) {
      video = document.createElement('video');
      video.id = 'bc-video';
      video.setAttribute('autoplay', '');
      video.setAttribute('playsinline', '');
      video.setAttribute('muted', '');
      card.appendChild(video);
    } else {
      var manualRow = document.createElement('div');
      manualRow.id = 'bc-manual-row';
      manualInput = document.createElement('input');
      manualInput.type = 'text';
      manualInput.id = 'bc-manual-input';
      manualInput.placeholder = 'Enter barcode number';
      manualInput.inputMode = 'numeric';
      lookupBtn = document.createElement('button');
      lookupBtn.className = 'btn btn-primary';
      lookupBtn.textContent = 'Look up';
      manualRow.appendChild(manualInput);
      manualRow.appendChild(lookupBtn);
      card.appendChild(manualRow);
    }

    var statusEl = document.createElement('p');
    statusEl.id = 'bc-status';
    statusEl.textContent = useCamera ? 'Point camera at barcode…' : 'Enter the barcode number from the product.';
    card.appendChild(statusEl);

    var errorEl = document.createElement('p');
    errorEl.id = 'bc-error';
    card.appendChild(errorEl);

    var actions = document.createElement('div');
    actions.id = 'bc-actions';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-secondary';
    cancelBtn.id = 'bc-cancel-btn';
    cancelBtn.textContent = 'Cancel';
    actions.appendChild(cancelBtn);
    card.appendChild(actions);

    overlay.appendChild(card);
    return {
      overlay: overlay, video: video, statusEl: statusEl, errorEl: errorEl,
      cancelBtn: cancelBtn, manualInput: manualInput, lookupBtn: lookupBtn,
    };
  }

  function stopTracks(stream) {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
  }

  window.openBarcodeScanner = function (onResult) {
    injectStyles();

    var supportsCamera = typeof BarcodeDetector !== 'undefined' && typeof navigator.mediaDevices !== 'undefined';
    var els = buildModal(supportsCamera);
    document.body.appendChild(els.overlay);

    var stream = null;
    var rafId = null;
    var closed = false;

    function close() {
      if (closed) return;
      closed = true;
      if (rafId) cancelAnimationFrame(rafId);
      stopTracks(stream);
      document.removeEventListener('keydown', onKeyDown);
      if (els.overlay.parentNode) els.overlay.parentNode.removeChild(els.overlay);
    }

    function onKeyDown(e) { if (e.key === 'Escape') close(); }
    document.addEventListener('keydown', onKeyDown);
    els.cancelBtn.addEventListener('click', close);

    // Shared lookup helper used by manual-entry and camera-denied fallback
    function lookup(code, statusEl, errorEl, resetFn) {
      statusEl.textContent = 'Looking up…';
      errorEl.textContent = '';
      fetch('/api/foods/barcode?code=' + encodeURIComponent(code))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.found) {
            close();
            onResult(data);
          } else {
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

    if (!supportsCamera) {
      function doLookup() {
        var code = els.manualInput.value.trim();
        if (!code) return;
        els.lookupBtn.disabled = true;
        lookup(code, els.statusEl, els.errorEl, function () { els.lookupBtn.disabled = false; });
      }
      els.lookupBtn.addEventListener('click', doLookup);
      els.manualInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') doLookup(); });
      els.manualInput.focus();
      return;
    }

    var detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });

    function startCamera(onStream) {
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(function (s) {
          if (closed) { stopTracks(s); return; }
          onStream(s);
        })
        .catch(function () {
          if (closed) return;
          // Camera denied — hide dead video, degrade to manual input
          els.video.hidden = true;
          els.errorEl.textContent = 'Camera access denied. Enter barcode manually.';
          els.statusEl.textContent = '';
          var manualRow = document.createElement('div');
          manualRow.id = 'bc-manual-row';
          var manualInput = document.createElement('input');
          manualInput.type = 'text';
          manualInput.placeholder = 'Enter barcode number';
          manualInput.inputMode = 'numeric';
          var lookupBtn = document.createElement('button');
          lookupBtn.className = 'btn btn-primary';
          lookupBtn.textContent = 'Look up';
          manualRow.appendChild(manualInput);
          manualRow.appendChild(lookupBtn);
          els.video.parentNode.insertBefore(manualRow, els.video.nextSibling);
          function doFallbackLookup() {
            var code = manualInput.value.trim();
            if (!code) return;
            lookupBtn.disabled = true;
            lookup(code, els.statusEl, els.errorEl, function () { lookupBtn.disabled = false; });
          }
          lookupBtn.addEventListener('click', doFallbackLookup);
          manualInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') doFallbackLookup(); });
          manualInput.focus();
        });
    }

    var scanning = false;

    function scan() {
      if (closed) return;
      rafId = requestAnimationFrame(function () {
        if (closed || scanning) { if (!closed) scan(); return; }
        if (!els.video.videoWidth) { scan(); return; }
        scanning = true;
        detector.detect(els.video)
          .then(function (barcodes) {
            scanning = false;
            if (closed) return;
            if (barcodes.length === 0) { scan(); return; }
            var code = barcodes[0].rawValue;
            els.statusEl.textContent = 'Found: ' + code + '. Looking up…';
            stopTracks(stream);
            stream = null;
            lookup(code, els.statusEl, els.errorEl, function () {
              // Not found — offer retry
              var retryBtn = document.createElement('button');
              retryBtn.className = 'btn btn-secondary';
              retryBtn.textContent = 'Try again';
              retryBtn.style.marginTop = '.5rem';
              retryBtn.addEventListener('click', function () {
                retryBtn.remove();
                els.statusEl.textContent = 'Point camera at barcode…';
                startCamera(function (s) {
                  stream = s;
                  els.video.hidden = false;
                  els.video.srcObject = stream;
                  els.video.play();
                  scan();
                });
              });
              els.errorEl.parentNode.insertBefore(retryBtn, els.errorEl.nextSibling);
            });
          })
          .catch(function () {
            scanning = false;
            if (!closed) scan();
          });
      });
    }

    startCamera(function (s) {
      stream = s;
      els.video.srcObject = stream;
      els.video.play();
      scan();
    });
  };
})();