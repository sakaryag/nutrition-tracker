(function () {
  'use strict';

  var INTRO_KEY = 'nt_scan_intro_seen';
  var _styleInjected = false;

  var ICONS = {
    close: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>',
    gallery: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="9" cy="9" r="1.8"/><path d="M21 15l-5-5L5 21"/></svg>',
    center: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><circle cx="12" cy="12" r="2.5"/></svg>',
    light: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    eye: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    plate: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/></svg>',
  };

  function injectStyles() {
    if (_styleInjected) return;
    _styleInjected = true;
    var ink = 'var(--color-ink,#18181B)';
    var primary = 'var(--color-primary,#8B68F6)';
    var muted = 'var(--color-text-secondary,#71717A)';
    var style = document.createElement('style');
    style.id = 'fi-styles';
    style.textContent = [
      '#fi-overlay{position:fixed;inset:0;z-index:1300;background:#000;display:flex;align-items:center;justify-content:center;font-family:var(--font-display,system-ui,sans-serif);}',
      '#fi-overlay *{box-sizing:border-box;}',
      '#fi-overlay [hidden]{display:none!important;}',
      '#fi-analyse-btn{grid-column:1/-1;}',
      '#fi-card{position:relative;width:100%;height:100%;overflow:hidden;overflow:clip;background:#000;color:#fff;}',
      '@media (min-width:600px){#fi-overlay{background:rgba(9,9,11,.88);}#fi-card{width:480px;height:min(900px,calc(100vh - 48px));border-radius:32px;box-shadow:0 24px 60px rgba(0,0,0,.5);}}',
      '#fi-video,#fi-thumb{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;background:#000;}',
      '#fi-canvas{display:none;}',
      '.fi-reticle{position:absolute;left:50%;top:44%;width:min(70vw,340px);aspect-ratio:1/1;transform:translate(-50%,-50%);pointer-events:none;}',
      '.fi-reticle span{position:absolute;width:44px;height:44px;border:4px solid #fff;filter:drop-shadow(0 1px 3px rgba(0,0,0,.4));}',
      '.fi-reticle span:nth-child(1){top:0;left:0;border-right:0;border-bottom:0;border-top-left-radius:24px;}',
      '.fi-reticle span:nth-child(2){top:0;right:0;border-left:0;border-bottom:0;border-top-right-radius:24px;}',
      '.fi-reticle span:nth-child(3){bottom:0;left:0;border-right:0;border-top:0;border-bottom-left-radius:24px;}',
      '.fi-reticle span:nth-child(4){bottom:0;right:0;border-left:0;border-top:0;border-bottom-right-radius:24px;}',
      '.fi-topbar{position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;padding:max(16px,env(safe-area-inset-top)) 16px 16px;z-index:3;}',
      '.fi-round{width:44px;height:44px;border-radius:50%;border:0;display:inline-flex;align-items:center;justify-content:center;background:rgba(255,255,255,.18);color:#fff;cursor:pointer;-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);padding:0;}',
      '.fi-round:hover{background:rgba(255,255,255,.28);}',
      '.fi-round:focus-visible,.fi-shutter:focus-visible{outline:3px solid ' + primary + ';outline-offset:2px;}',
      '.fi-bottombar{position:absolute;left:0;right:0;bottom:0;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:24px 28px max(28px,env(safe-area-inset-bottom));z-index:2;background:linear-gradient(to top,rgba(0,0,0,.55),transparent);}',
      '.fi-bottombar .fi-round{justify-self:start;}',
      '.fi-shutter{width:72px;height:72px;border-radius:50%;background:#fff;border:0;box-shadow:0 0 0 4px #000,0 0 0 8px #fff;cursor:pointer;padding:0;transition:transform .15s ease;}',
      '.fi-shutter:active{transform:scale(.94);}',
      '.fi-shutter:disabled{opacity:.4;cursor:default;}',
      '.fi-hint{position:absolute;left:16px;right:16px;bottom:140px;text-align:center;z-index:2;font-size:.875rem;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.6);margin:0;}',
      '.fi-hint #fi-status{color:#fff;margin:0;}',
      '.fi-hint #fi-error{color:#FCA5A5;margin:.25rem 0 0;}',
      '.fi-fallback{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:32px;text-align:center;z-index:2;}',
      '.fi-fallback p{margin:0;color:#D4D4D8;font-size:.95rem;max-width:300px;}',
      '.fi-fallback .fi-fallback-icon{width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.12);display:flex;align-items:center;justify-content:center;}',
      '.fi-pill{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:52px;padding:0 24px;border-radius:999px;border:0;font:inherit;font-weight:700;font-size:1rem;cursor:pointer;}',
      '.fi-pill:disabled{opacity:.55;cursor:default;}',
      '.fi-pill:focus-visible{outline:3px solid ' + primary + ';outline-offset:2px;}',
      '.fi-pill--ink{background:' + ink + ';color:#fff;}',
      '.fi-pill--ink:hover:not(:disabled){background:#27272A;}',
      '.fi-pill--white{background:#fff;color:' + ink + ';}',
      '.fi-pill--soft{background:#F4F4F5;color:' + ink + ';}',
      '.fi-pill--soft:hover:not(:disabled){background:#E4E4E7;}',
      '.fi-pill--ghost{background:transparent;color:#fff;min-height:44px;font-weight:600;font-size:.9rem;}',
      '.fi-link{background:none;border:0;color:' + muted + ';font:inherit;font-size:.875rem;font-weight:600;text-decoration:underline;cursor:pointer;padding:10px 4px;}',
      '.fi-link:focus-visible{outline:2px solid ' + primary + ';border-radius:6px;}',
      '.fi-scrim{position:absolute;inset:0;background:rgba(0,0,0,.55);opacity:0;pointer-events:none;transition:opacity .3s ease;z-index:4;}',
      '.fi-scrim.is-on{opacity:1;pointer-events:auto;}',
      '.fi-scrim.is-light{background:rgba(0,0,0,.25);}',
      '.fi-sheet{position:absolute;left:0;right:0;bottom:0;z-index:5;background:#fff;color:' + ink + ';border-radius:var(--radius-sheet,32px) var(--radius-sheet,32px) 0 0;padding:12px 24px max(24px,env(safe-area-inset-bottom));max-height:70vh;overflow-y:auto;overscroll-behavior:contain;box-shadow:0 -12px 40px rgba(0,0,0,.25);transform:translateY(105%);visibility:hidden;transition:transform .3s ease,visibility 0s linear .3s;}',
      '.fi-sheet.is-open{transform:translateY(0);visibility:visible;transition:transform .3s ease;}',
      '@media (min-width:600px){.fi-sheet{max-height:min(70vh,640px);}}',
      '@media (prefers-reduced-motion:reduce){.fi-sheet,.fi-sheet.is-open,.fi-scrim{transition:none;}.fi-spinner{animation:none!important;}.fi-pulse{animation:none!important;}}',
      '.fi-handle{width:40px;height:5px;border-radius:3px;background:#E4E4E7;margin:0 auto 18px;}',
      '.fi-sheet h2{font-size:1.5rem;font-weight:800;line-height:1.2;margin:0 0 16px;letter-spacing:-.01em;}',
      '.fi-tips{list-style:none;margin:0 0 24px;padding:0;display:flex;flex-direction:column;gap:14px;}',
      '.fi-tips li{display:flex;align-items:center;gap:12px;font-size:.95rem;color:#3F3F46;}',
      '.fi-tip-icon{flex:0 0 36px;width:36px;height:36px;border-radius:12px;background:var(--color-primary-light,#F3F0FF);color:' + primary + ';display:flex;align-items:center;justify-content:center;}',
      '.fi-block{width:100%;}',
      '.fi-analysing{display:flex;flex-direction:column;align-items:center;gap:14px;padding:16px 0 12px;}',
      '.fi-spinner{width:36px;height:36px;border-radius:50%;border:4px solid #EDE9FE;border-top-color:' + primary + ';animation:fi-spin .9s linear infinite;}',
      '.fi-pulse{animation:fi-pulse 1.4s ease-in-out infinite;}',
      '@keyframes fi-spin{to{transform:rotate(360deg);}}',
      '@keyframes fi-pulse{0%,100%{opacity:1;}50%{opacity:.45;}}',
      '.fi-analysing p{margin:0;font-weight:700;font-size:1.05rem;}',
      '#fi-total{font-size:2.25rem;font-weight:800;line-height:1.1;margin:0;letter-spacing:-.02em;}',
      '#fi-subtitle{margin:4px 0 16px;color:' + muted + ';font-size:.95rem;}',
      '.fi-macros{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px;}',
      '.fi-macro{border-radius:16px;padding:10px 12px;display:flex;flex-direction:column;gap:2px;}',
      '.fi-macro-head{display:flex;align-items:center;gap:6px;font-size:.78rem;color:' + muted + ';font-weight:600;}',
      '.fi-dot{width:8px;height:8px;border-radius:50%;flex:0 0 8px;}',
      '.fi-macro strong{font-size:1.1rem;font-weight:800;}',
      '.fi-macro--protein{background:var(--tint-protein,#FFF5EE);}.fi-macro--protein .fi-dot{background:var(--color-protein,#FFA86A);}',
      '.fi-macro--carbs{background:var(--tint-carbs,#F3F0FF);}.fi-macro--carbs .fi-dot{background:var(--color-carbs,#A78BFA);}',
      '.fi-macro--fat{background:var(--tint-fat,#F0FDF4);}.fi-macro--fat .fi-dot{background:var(--color-fat,#4ADE80);}',
      '.fi-health{margin-bottom:6px;}',
      '.fi-health-row{display:flex;justify-content:space-between;align-items:baseline;font-weight:700;margin-bottom:8px;}',
      '.fi-health-track{height:10px;border-radius:999px;background:#F1EEF8;overflow:hidden;}',
      '#fi-health-fill{height:100%;width:0;border-radius:999px;background:linear-gradient(90deg,#A78BFA,#8B68F6);transition:width .3s ease;}',
      '.fi-caption{font-size:.75rem;color:var(--color-text-muted,#9CA3AF);margin:6px 0 0;}',
      '.fi-msgs #fi-status{margin:.5rem 0 0;font-size:.875rem;color:' + muted + ';min-height:0;}',
      '.fi-msgs #fi-error{margin:.5rem 0 0;font-size:.875rem;color:#DC2626;min-height:0;}',
      '.fi-msgs p:empty{display:none;}',
      '#fi-items-list{margin:16px 0 0;border-top:1px solid #F4F4F5;padding-top:12px;}',
      '.fi-items-head{font-size:.8rem;font-weight:700;color:' + muted + ';text-transform:uppercase;letter-spacing:.04em;margin:0 0 8px;}',
      '.fi-item-row{display:flex;align-items:flex-start;gap:10px;padding:10px 12px;border:1px solid #F1EEF8;border-radius:16px;margin-bottom:8px;background:#FCFBFF;}',
      '.fi-item-row input[type=checkbox]{width:20px;height:20px;margin-top:8px;accent-color:' + primary + ';flex:0 0 20px;}',
      '.fi-item-info{flex:1;min-width:0;font-size:.875rem;}',
      '.fi-name-input{font-weight:700;font-size:.95rem;border:1px solid transparent;border-radius:10px;padding:6px 8px;width:100%;background:transparent;color:inherit;font-family:inherit;}',
      '.fi-name-input:hover{border-color:#E4E4E7;}',
      '.fi-grams-row{display:flex;align-items:center;gap:6px;font-size:.8rem;color:' + muted + ';margin:4px 0 0 8px;}',
      '.fi-grams-input,.fi-edit-input{font-size:.85rem;border:1px solid #E4E4E7;border-radius:10px;padding:6px 8px;text-align:right;background:#fff;color:inherit;font-family:inherit;}',
      '.fi-grams-input{width:5rem;}',
      '.fi-edit-input{width:100%;}',
      '.fi-name-input:focus,.fi-grams-input:focus,.fi-edit-input:focus{border-color:' + primary + ';outline:none;background:#fff;box-shadow:0 0 0 3px rgba(139,104,246,.18);}',
      '.fi-edit-grid{display:none;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px;}',
      '#fi-items-list.is-expanded .fi-edit-grid{display:grid;}',
      '.fi-macro-label{font-size:.7rem;color:' + muted + ';text-align:center;margin-bottom:2px;font-weight:600;}',
      '.fi-cta{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:20px;position:sticky;bottom:calc(-1 * max(24px,env(safe-area-inset-bottom)));z-index:1;background:#fff;padding:12px 0 max(24px,env(safe-area-inset-bottom));box-shadow:0 -10px 16px -8px rgba(255,255,255,.95);}',
      '.fi-cta-sub{display:flex;justify-content:center;gap:16px;margin-top:4px;}',
      '.fi-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}',
    ].join('');
    document.head.appendChild(style);
  }

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'className') n.className = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k]; // static icon markup only
      else n.setAttribute(k, attrs[k]);
    });
    if (text != null) n.textContent = text;
    return n;
  }

  function buildModal() {
    var overlay = el('div', { id: 'fi-overlay', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Scan your meal' });
    var card = el('div', { id: 'fi-card' });

    var video = el('video', { id: 'fi-video', autoplay: '', playsinline: '', muted: '', 'aria-hidden': 'true' });
    video.muted = true;
    video.hidden = true;
    var thumb = el('img', { id: 'fi-thumb', alt: 'Captured meal photo' });
    thumb.hidden = true;
    var canvas = el('canvas', { id: 'fi-canvas' });

    var reticle = el('div', { className: 'fi-reticle', 'aria-hidden': 'true' });
    for (var i = 0; i < 4; i++) reticle.appendChild(el('span'));

    var topbar = el('div', { className: 'fi-topbar' });
    var cancelBtn = el('button', { type: 'button', id: 'fi-cancel-btn', className: 'fi-round', 'aria-label': 'Close scanner', html: ICONS.close });
    var infoBtn = el('button', { type: 'button', id: 'fi-info-btn', className: 'fi-round', 'aria-label': 'Scanning tips', html: ICONS.info });
    topbar.appendChild(cancelBtn);
    topbar.appendChild(infoBtn);

    var fileInput = el('input', { type: 'file', id: 'fi-file-input', accept: 'image/jpeg,image/png,image/gif,image/webp', 'aria-hidden': 'true', tabindex: '-1' });
    fileInput.style.display = 'none';

    var fallback = el('div', { className: 'fi-fallback', id: 'fi-fallback' });
    fallback.hidden = true;
    fallback.appendChild(el('div', { className: 'fi-fallback-icon', html: ICONS.gallery }));
    var fallbackMsg = el('p', { id: 'fi-fallback-msg' }, 'Camera unavailable. Upload a photo of your meal instead.');
    var chooseBtn = el('button', { type: 'button', id: 'fi-choose-btn', className: 'fi-pill fi-pill--white' }, 'Choose Photo');
    var cameraBtn = el('button', { type: 'button', id: 'fi-camera-btn', className: 'fi-pill fi-pill--ghost' }, 'Try camera again');
    fallback.appendChild(fallbackMsg);
    fallback.appendChild(chooseBtn);
    fallback.appendChild(cameraBtn);

    var hint = el('div', { className: 'fi-hint', 'aria-live': 'polite' });
    var statusEl = el('p', { id: 'fi-status' });
    var errorEl = el('p', { id: 'fi-error', role: 'alert' });
    hint.appendChild(statusEl);
    hint.appendChild(errorEl);

    var bottombar = el('div', { className: 'fi-bottombar' });
    var uploadBtn = el('button', { type: 'button', id: 'fi-upload-btn', className: 'fi-round', 'aria-label': 'Upload photo from gallery', html: ICONS.gallery });
    var shutterBtn = el('button', { type: 'button', id: 'fi-shutter-btn', className: 'fi-shutter', 'aria-label': 'Take photo' });
    bottombar.appendChild(uploadBtn);
    bottombar.appendChild(shutterBtn);
    bottombar.appendChild(el('span'));

    var scrim = el('div', { className: 'fi-scrim', 'aria-hidden': 'true' });

    // Intro sheet
    var intro = el('div', { className: 'fi-sheet', id: 'fi-intro', role: 'group', 'aria-labelledby': 'fi-intro-title' });
    intro.appendChild(el('div', { className: 'fi-handle', 'aria-hidden': 'true' }));
    intro.appendChild(el('h2', { id: 'fi-intro-title' }, 'Ready to Scan Your Meal?'));
    var tips = el('ul', { className: 'fi-tips' });
    [['center', 'Center the meal in the scan area.'],
     ['light', 'Ensure good lighting conditions.'],
     ['eye', 'Keep the food unobstructed.'],
     ['plate', 'Include all items on the plate.']].forEach(function (t) {
      var li = el('li');
      li.appendChild(el('span', { className: 'fi-tip-icon', html: ICONS[t[0]] }));
      li.appendChild(el('span', null, t[1]));
      tips.appendChild(li);
    });
    intro.appendChild(tips);
    var gotItBtn = el('button', { type: 'button', id: 'fi-gotit-btn', className: 'fi-pill fi-pill--ink fi-block' }, 'Got It');
    intro.appendChild(gotItBtn);

    // Analysing / result sheet
    var sheet = el('div', { className: 'fi-sheet', id: 'fi-sheet', role: 'group', 'aria-label': 'Scan result' });
    sheet.appendChild(el('div', { className: 'fi-handle', 'aria-hidden': 'true' }));

    var analysing = el('div', { className: 'fi-analysing', id: 'fi-analysing' });
    analysing.appendChild(el('div', { className: 'fi-spinner', 'aria-hidden': 'true' }));
    analysing.appendChild(el('p', { className: 'fi-pulse' }, 'Analysing\u2026'));
    sheet.appendChild(analysing);

    var result = el('div', { id: 'fi-result' });
    result.hidden = true;
    var total = el('p', { id: 'fi-total', 'aria-live': 'polite' }, '0 kcal');
    var subtitle = el('p', { id: 'fi-subtitle' });
    result.appendChild(total);
    result.appendChild(subtitle);

    var macros = el('div', { className: 'fi-macros' });
    var macroVals = {};
    [['protein', 'Protein'], ['carbs', 'Carbs'], ['fat', 'Fat']].forEach(function (m) {
      var tile = el('div', { className: 'fi-macro fi-macro--' + m[0] });
      var head = el('span', { className: 'fi-macro-head' });
      head.appendChild(el('span', { className: 'fi-dot', 'aria-hidden': 'true' }));
      head.appendChild(document.createTextNode(m[1]));
      var val = el('strong', { id: 'fi-tot-' + m[0] }, '0g');
      tile.appendChild(head);
      tile.appendChild(val);
      macros.appendChild(tile);
      macroVals[m[0]] = val;
    });
    result.appendChild(macros);

    var health = el('div', { className: 'fi-health' });
    var hrow = el('div', { className: 'fi-health-row' });
    hrow.appendChild(el('span', null, 'Healthy Score'));
    var healthVal = el('span', { id: 'fi-health-val' }, '\u2013/10');
    hrow.appendChild(healthVal);
    var track = el('div', { className: 'fi-health-track', role: 'progressbar', 'aria-label': 'Healthy score', 'aria-valuemin': '0', 'aria-valuemax': '10', 'aria-valuenow': '0' });
    var healthFill = el('div', { id: 'fi-health-fill' });
    track.appendChild(healthFill);
    health.appendChild(hrow);
    health.appendChild(track);
    health.appendChild(el('p', { className: 'fi-caption' }, 'Estimate based on the meal\u2019s protein/carb/fat balance \u2014 not medical advice.'));
    result.appendChild(health);

    var itemsList = el('div', { id: 'fi-items-list' });
    result.appendChild(itemsList);
    sheet.appendChild(result);

    var msgs = el('div', { className: 'fi-msgs', 'aria-live': 'polite' });
    sheet.appendChild(msgs);

    var cta = el('div', { className: 'fi-cta', id: 'fi-actions' });
    var editBtn = el('button', { type: 'button', id: 'fi-edit-btn', className: 'fi-pill fi-pill--soft', 'aria-expanded': 'false', 'aria-controls': 'fi-items-list' }, 'Edit Details');
    var doneBtn = el('button', { type: 'button', id: 'fi-done-btn', className: 'fi-pill fi-pill--ink' }, 'Done');
    var analyseBtn = el('button', { type: 'button', id: 'fi-analyse-btn', className: 'fi-pill fi-pill--ink' }, 'Try Again');
    cta.appendChild(editBtn);
    cta.appendChild(doneBtn);
    cta.appendChild(analyseBtn);
    sheet.appendChild(cta);
    var ctaSub = el('div', { className: 'fi-cta-sub' });
    var retakeBtn = el('button', { type: 'button', id: 'fi-retake-btn', className: 'fi-link' }, 'Retake photo');
    ctaSub.appendChild(retakeBtn);
    sheet.appendChild(ctaSub);

    [video, thumb, canvas, reticle, fallback, hint, bottombar, topbar, fileInput, scrim, intro, sheet]
      .forEach(function (n) { card.appendChild(n); });
    overlay.appendChild(card);

    return {
      overlay: overlay, card: card, video: video, canvas: canvas, thumb: thumb, reticle: reticle,
      topbar: topbar, cancelBtn: cancelBtn, infoBtn: infoBtn, fileInput: fileInput,
      fallback: fallback, fallbackMsg: fallbackMsg, chooseBtn: chooseBtn, cameraBtn: cameraBtn,
      hint: hint, statusEl: statusEl, errorEl: errorEl,
      bottombar: bottombar, uploadBtn: uploadBtn, shutterBtn: shutterBtn,
      scrim: scrim, intro: intro, gotItBtn: gotItBtn,
      sheet: sheet, analysing: analysing, result: result, total: total, subtitle: subtitle,
      macroVals: macroVals, healthVal: healthVal, healthFill: healthFill, healthTrack: track,
      itemsList: itemsList, msgs: msgs, cta: cta, editBtn: editBtn, doneBtn: doneBtn,
      analyseBtn: analyseBtn, retakeBtn: retakeBtn,
    };
  }

  function stopTracks(stream) {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
  }

  function lsGet(k) { try { return localStorage.getItem(k); } catch (_) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (_) {} }

  function num(v) { var n = parseFloat(v); return isFinite(n) ? n : 0; }
  function fmt(n) { return (Math.round(n * 10) / 10).toString(); }

  // 10 minus penalties for % of macro kcal outside the ideal ranges; 1..10, null if no data.
  function healthScore(p, c, f) {
    var pk = p * 4, ck = c * 4, fk = f * 9, tot = pk + ck + fk;
    if (tot <= 0) return null;
    function dev(pct, lo, hi) { return pct < lo ? lo - pct : (pct > hi ? pct - hi : 0); }
    var penalty = dev(pk / tot * 100, 20, 35) + dev(ck / tot * 100, 40, 55) + dev(fk / tot * 100, 20, 35);
    return Math.max(1, Math.min(10, Math.round(10 - penalty / 5)));
  }

  function joinNames(names) {
    if (!names.length) return '';
    if (names.length === 1) return names[0];
    var lower = names.map(function (n, i) { return i === 0 ? n : n.charAt(0).toLowerCase() + n.slice(1); });
    return lower.slice(0, -1).join(', ') + ' & ' + lower[lower.length - 1];
  }

  function focusables(root) {
    return Array.prototype.filter.call(
      root.querySelectorAll('button,input:not([type=file]),select,textarea,a[href],[tabindex]:not([tabindex="-1"])'),
      function (n) {
        if (n.disabled || !n.getClientRects().length) return false;
        return getComputedStyle(n).visibility !== 'hidden';
      });
  }

  window.openFoodImageScanner = function (onResult) {
    var apiKey = ApiKey.get();
    if (!apiKey) {
      if (typeof showToast === 'function') {
        showToast('Add your Gemini API key in Settings to use photo recognition.', 'error', 5000);
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
    if (document.getElementById('fi-overlay')) return;

    injectStyles();
    var els = buildModal();
    var returnFocus = document.activeElement;
    var prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.body.appendChild(els.overlay);

    var stream = null;
    var capturedBlob = null;
    var thumbUrl = null;
    var items = [];
    var closed = false;
    var submitting = false;
    var analyseSeq = 0;
    var introFromInfo = false;
    var mode = 'camera'; // camera | fallback | preview

    function close() {
      if (closed) return;
      closed = true;
      analyseSeq++;
      stopTracks(stream);
      stream = null;
      els.video.srcObject = null;
      if (thumbUrl) { URL.revokeObjectURL(thumbUrl); thumbUrl = null; }
      document.removeEventListener('keydown', onKeyDown, true);
      if (els.overlay.parentNode) els.overlay.parentNode.removeChild(els.overlay);
      document.body.style.overflow = prevOverflow;
      if (returnFocus && typeof returnFocus.focus === 'function' && document.contains(returnFocus)) {
        returnFocus.focus();
      }
    }

    function openSheet() {
      return els.intro.classList.contains('is-open') ? els.intro
        : (els.sheet.classList.contains('is-open') ? els.sheet : null);
    }

    function onKeyDown(e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        if (introFromInfo && els.intro.classList.contains('is-open')) hideIntro();
        else close();
        return;
      }
      if (e.key === 'Tab') {
        var scope = openSheet() || els.card;
        var list = focusables(scope);
        if (scope !== els.card && els.cancelBtn.getClientRects().length) list.unshift(els.cancelBtn);
        if (!list.length) { e.preventDefault(); return; }
        var first = list[0], last = list[list.length - 1];
        var idx = list.indexOf(document.activeElement);
        if (idx === -1) { e.preventDefault(); first.focus(); }
        else if (e.shiftKey && idx === 0) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && idx === list.length - 1) { e.preventDefault(); first.focus(); }
      }
    }
    document.addEventListener('keydown', onKeyDown, true);

    function setStatus(msg) { els.statusEl.textContent = msg; }
    function setError(msg) { els.errorEl.textContent = msg; }
    function clearMessages() { setStatus(''); setError(''); }
    // Status/error nodes keep their ids; they move between the camera hint and the sheet.
    function placeMessages(inSheet) {
      var target = inSheet ? els.msgs : els.hint;
      if (els.statusEl.parentNode !== target) { target.appendChild(els.statusEl); target.appendChild(els.errorEl); }
    }

    function setMode(m) {
      mode = m;
      var cam = m === 'camera', fb = m === 'fallback', pv = m === 'preview';
      els.video.hidden = !cam;
      els.reticle.hidden = !cam;
      els.fallback.hidden = !fb;
      els.thumb.hidden = !pv;
      els.bottombar.hidden = pv;
      els.shutterBtn.hidden = !cam;
      els.infoBtn.hidden = pv;
      els.hint.hidden = pv;
      placeMessages(pv);
    }

    function showIntro(fromInfo) {
      introFromInfo = !!fromInfo;
      els.scrim.classList.add('is-on');
      els.scrim.classList.remove('is-light');
      els.intro.classList.add('is-open');
      setTimeout(function () { if (!closed) els.gotItBtn.focus(); }, 50);
    }
    function hideIntro() {
      var wasInfo = introFromInfo;
      els.intro.classList.remove('is-open');
      els.scrim.classList.remove('is-on');
      introFromInfo = false;
      lsSet(INTRO_KEY, '1');
      if (wasInfo) { els.infoBtn.focus(); return; }
      startCamera();
    }

    function showSheet(state) {
      els.scrim.classList.add('is-on', 'is-light');
      els.sheet.classList.add('is-open');
      var analysing = state === 'analysing', isResult = state === 'result';
      els.analysing.hidden = !analysing;
      els.result.hidden = !isResult;
      els.cta.hidden = analysing;
      els.editBtn.hidden = !isResult;
      els.doneBtn.hidden = !isResult;
      els.analyseBtn.hidden = state !== 'error';
      els.retakeBtn.disabled = false;
      els.sheet.setAttribute('aria-busy', analysing ? 'true' : 'false');
    }
    function hideSheet() {
      els.sheet.classList.remove('is-open');
      els.scrim.classList.remove('is-on', 'is-light');
    }

    function showFallback(msg) {
      stopTracks(stream); stream = null;
      els.video.srcObject = null;
      setMode('fallback');
      els.fallbackMsg.textContent = msg;
      els.cameraBtn.hidden = !(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
      setTimeout(function () { if (!closed && !openSheet()) els.chooseBtn.focus(); }, 50);
    }

    function startCamera() {
      clearMessages();
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showFallback('Camera not available on this device/browser. Upload a photo of your meal instead.');
        return;
      }
      stopTracks(stream); stream = null;
      setMode('camera');
      els.shutterBtn.disabled = true;
      setStatus('Starting camera\u2026');
      navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } } })
        .then(function (s) {
          if (closed || mode !== 'camera') { stopTracks(s); return; }
          stopTracks(stream);
          stream = s;
          els.video.srcObject = stream;
          var p = els.video.play();
          if (p && p.catch) p.catch(function () {});
          els.shutterBtn.disabled = false;
          setStatus('Center your meal in the frame.');
          if (!openSheet()) els.shutterBtn.focus();
        })
        .catch(function () {
          if (closed || mode !== 'camera') return;
          setStatus('');
          showFallback('Camera access denied. Upload a photo of your meal instead.');
        });
    }

    function openFilePicker() {
      els.fileInput.value = '';
      els.fileInput.click();
    }

    function showPreview(blob) {
      stopTracks(stream); stream = null;
      els.video.srcObject = null;
      capturedBlob = blob;
      if (thumbUrl) URL.revokeObjectURL(thumbUrl);
      thumbUrl = URL.createObjectURL(blob);
      els.thumb.src = thumbUrl;
      setMode('preview');
      clearMessages();
      analyse();
    }

    function retake() {
      analyseSeq++;
      submitting = false;
      capturedBlob = null;
      items = [];
      hideSheet();
      if (thumbUrl) { URL.revokeObjectURL(thumbUrl); thumbUrl = null; }
      els.thumb.removeAttribute('src');
      els.itemsList.textContent = '';
      els.itemsList.classList.remove('is-expanded');
      els.editBtn.setAttribute('aria-expanded', 'false');
      clearMessages();
      startCamera();
    }

    els.cancelBtn.addEventListener('click', close);
    els.infoBtn.addEventListener('click', function () { showIntro(true); });
    els.gotItBtn.addEventListener('click', hideIntro);
    els.scrim.addEventListener('click', function () { if (introFromInfo) hideIntro(); });
    els.uploadBtn.addEventListener('click', openFilePicker);
    els.chooseBtn.addEventListener('click', openFilePicker);
    els.cameraBtn.addEventListener('click', startCamera);
    els.retakeBtn.addEventListener('click', retake);
    els.analyseBtn.addEventListener('click', function () { if (capturedBlob) analyse(); });

    els.shutterBtn.addEventListener('click', function () {
      if (!stream || els.shutterBtn.disabled) return;
      var v = els.video;
      els.canvas.width = v.videoWidth || 640;
      els.canvas.height = v.videoHeight || 480;
      els.canvas.getContext('2d').drawImage(v, 0, 0, els.canvas.width, els.canvas.height);
      els.shutterBtn.disabled = true;
      els.canvas.toBlob(function (blob) {
        if (closed) return;
        if (blob) showPreview(blob);
        else { els.shutterBtn.disabled = false; setError('Could not capture photo. Try again.'); }
      }, 'image/jpeg', 0.85);
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

    // Resize blob to max 1024px on the long edge, JPEG 0.8 quality
    function resizeBlob(blob, maxPx, quality) {
      return new Promise(function (resolve) {
        var img = new Image();
        var url = URL.createObjectURL(blob);
        img.onload = function () {
          URL.revokeObjectURL(url);
          var w = img.naturalWidth, h = img.naturalHeight;
          if (w <= maxPx && h <= maxPx) { resolve(blob); return; }
          var scale = maxPx / Math.max(w, h);
          var cw = Math.round(w * scale), ch = Math.round(h * scale);
          var canvas = document.createElement('canvas');
          canvas.width = cw; canvas.height = ch;
          canvas.getContext('2d').drawImage(img, 0, 0, cw, ch);
          canvas.toBlob(function (b) { resolve(b || blob); }, 'image/jpeg', quality);
        };
        img.onerror = function () { URL.revokeObjectURL(url); resolve(blob); };
        img.src = url;
      });
    }

    function analyse() {
      if (!capturedBlob) return;
      var seq = ++analyseSeq;
      showSheet('analysing');
      clearMessages();
      els.retakeBtn.focus({ preventScroll: true });

      var lang = (typeof Lang !== 'undefined' && Lang.get) ? Lang.get() : 'en';
      var model = (typeof ApiUsage !== 'undefined') ? ApiUsage.getModel() : 'gemini-3.8-flash';

      resizeBlob(capturedBlob, 1024, 0.8).then(function (resized) {
        if (seq !== analyseSeq) return null;
        var fd = new FormData();
        fd.append('image', resized, 'food.jpg');
        fd.append('api_key', apiKey);
        fd.append('lang', lang);
        fd.append('model', model);
        return fetch('/api/foods/image', { method: 'POST', body: fd }).then(function (r) { return r.json(); });
      })
        .then(function (data) {
          if (!data || seq !== analyseSeq || closed) return;
          if (!data.found) {
            showSheet('error');
            setError(data.message || 'Recognition failed.');
            els.analyseBtn.focus({ preventScroll: true });
            return;
          }
          if (data.usage && data.usage.input_tokens && typeof ApiUsage !== 'undefined') {
            ApiUsage.addCost(data.usage.input_tokens, data.usage.output_tokens, data.usage.model || model);
          }
          items = data.items || [];
          if (!items.length) {
            showSheet('error');
            setError('No food items recognised');
            els.analyseBtn.focus({ preventScroll: true });
            return;
          }
          renderItemList(items);
          showSheet('result');
          updateTotals();
          els.doneBtn.focus({ preventScroll: true });
        })
        .catch(function () {
          if (seq !== analyseSeq || closed) return;
          showSheet('error');
          setError('Request failed. Check connection.');
          els.analyseBtn.focus({ preventScroll: true });
        });
    }

    function rowValue(row, field) {
      var inp = row.querySelector('[data-field="' + field + '"]');
      return inp ? inp.value : '';
    }

    function checkedRows() {
      return Array.prototype.map.call(
        els.itemsList.querySelectorAll('input[type=checkbox]:checked'),
        function (chk) { return chk.closest('.fi-item-row'); });
    }

    function updateTotals() {
      var t = { protein: 0, carbs: 0, fat: 0, calories: 0 };
      var names = [];
      checkedRows().forEach(function (row) {
        t.protein += num(rowValue(row, 'protein'));
        t.carbs += num(rowValue(row, 'carbs'));
        t.fat += num(rowValue(row, 'fat'));
        t.calories += num(rowValue(row, 'calories'));
        var n = rowValue(row, 'food_name').trim();
        if (n) names.push(n);
      });
      els.total.textContent = Math.round(t.calories) + ' kcal';
      els.subtitle.textContent = joinNames(names) || 'No items selected';
      els.macroVals.protein.textContent = fmt(t.protein) + 'g';
      els.macroVals.carbs.textContent = fmt(t.carbs) + 'g';
      els.macroVals.fat.textContent = fmt(t.fat) + 'g';
      var score = healthScore(t.protein, t.carbs, t.fat);
      els.healthVal.textContent = (score == null ? '\u2013' : score) + '/10';
      els.healthFill.style.width = (score == null ? 0 : score * 10) + '%';
      els.healthTrack.setAttribute('aria-valuenow', score == null ? '0' : String(score));
    }

    els.itemsList.addEventListener('input', updateTotals);
    els.itemsList.addEventListener('change', updateTotals);

    els.editBtn.addEventListener('click', function () {
      var expanded = els.itemsList.classList.toggle('is-expanded');
      els.editBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      if (expanded) {
        els.itemsList.scrollIntoView({ block: 'start', behavior: 'smooth' });
        var first = els.itemsList.querySelector('.fi-name-input');
        if (first) first.focus({ preventScroll: true });
      }
    });

    function renderItemList(list) {
      els.itemsList.textContent = '';
      els.itemsList.classList.remove('is-expanded');
      els.editBtn.setAttribute('aria-expanded', 'false');
      els.itemsList.appendChild(el('p', { className: 'fi-items-head' }, 'Recognised items'));
      list.forEach(function (it, idx) {
        var row = el('div', { className: 'fi-item-row' });

        var chk = el('input', { type: 'checkbox', id: 'fi-chk-' + idx });
        chk.checked = true;
        chk.dataset.idx = idx;

        var info = el('div', { className: 'fi-item-info' });

        var nameInput = el('input', { type: 'text', className: 'fi-name-input' });
        nameInput.value = it.food_name || '';
        nameInput.dataset.field = 'food_name';
        nameInput.setAttribute('aria-label', 'Item ' + (idx + 1) + ' name');
        chk.setAttribute('aria-label', 'Include ' + (it.food_name || 'item ' + (idx + 1)));

        var gramsRow = el('div', { className: 'fi-grams-row' });
        var gramsInput = el('input', { type: 'number', className: 'fi-grams-input', min: '1', 'aria-label': 'Grams' });
        gramsInput.value = it.estimated_grams;
        gramsInput.dataset.field = 'estimated_grams';
        gramsRow.appendChild(gramsInput);
        gramsRow.appendChild(document.createTextNode(' g estimated'));

        var macroGrid = el('div', { className: 'fi-edit-grid' });
        [['protein', 'P(g)'], ['fat', 'F(g)'], ['carbs', 'C(g)'], ['calories', 'kcal']].forEach(function (spec) {
          var cell = el('div');
          var lid = 'fi-' + spec[0] + '-' + idx;
          var lbl = el('label', { className: 'fi-macro-label', for: lid }, spec[1]);
          lbl.style.display = 'block';
          var inp = el('input', { type: 'number', className: 'fi-edit-input', id: lid, min: '0', step: '0.1' });
          inp.value = it[spec[0]];
          inp.dataset.field = spec[0];
          cell.appendChild(lbl);
          cell.appendChild(inp);
          macroGrid.appendChild(cell);
        });

        info.appendChild(nameInput);
        info.appendChild(gramsRow);
        info.appendChild(macroGrid);
        row.appendChild(chk);
        row.appendChild(info);
        els.itemsList.appendChild(row);
      });
    }

    els.doneBtn.addEventListener('click', function () {
      if (submitting) return;
      var rows = checkedRows();
      if (!rows.length) { setError('Select at least one item.'); return; }
      setError('');

      // Single recognised item: hand off to the caller (dashboard prefills its add-entry modal).
      if (items.length === 1) {
        var r0 = rows[0];
        var payload = {
          name: rowValue(r0, 'food_name') || items[0].food_name,
          protein: num(rowValue(r0, 'protein')),
          fat: num(rowValue(r0, 'fat')),
          carbs: num(rowValue(r0, 'carbs')),
          calories: num(rowValue(r0, 'calories')),
          estimated_grams: num(rowValue(r0, 'estimated_grams')) || items[0].estimated_grams,
        };
        submitting = true;
        close();
        if (typeof onResult === 'function') onResult(payload);
        return;
      }

      submitting = true;
      els.doneBtn.disabled = true;
      els.retakeBtn.disabled = true;
      setStatus('Logging\u2026');
      var today = new Date().toISOString().slice(0, 10);
      var promises = rows.map(function (row) {
        var idx = parseInt(row.querySelector('input[type=checkbox]').dataset.idx, 10);
        return fetch('/api/entries', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            food_name:    rowValue(row, 'food_name') || items[idx].food_name,
            protein:      parseFloat(rowValue(row, 'protein'))         || 0,
            fat:          parseFloat(rowValue(row, 'fat'))             || 0,
            carbs:        parseFloat(rowValue(row, 'carbs'))           || 0,
            calories:     parseFloat(rowValue(row, 'calories'))        || 0,
            serving_size: parseFloat(rowValue(row, 'estimated_grams')) || items[idx].estimated_grams,
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
          if (closed) return;
          submitting = false;
          els.doneBtn.disabled = false;
          els.retakeBtn.disabled = false;
          setError('Some items failed to log. Try again.');
          setStatus('');
        });
    });

    // Initial step
    setMode('camera');
    if (lsGet(INTRO_KEY)) {
      els.cancelBtn.focus();
      startCamera();
    } else {
      els.shutterBtn.disabled = true;
      showIntro(false);
    }
  };
})();
