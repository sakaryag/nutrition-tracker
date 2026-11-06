/* ============================================================
   dashboard.js
   ============================================================ */
(function () {
  'use strict';

  var UNITS = {
    g:       { group: 'weight',  toG: 1 },
    oz:      { group: 'weight',  toG: 28.3495 },
    ml:      { group: 'volume',  toG: 1 },
    cup:     { group: 'volume',  toG: 240 },
    tbsp:    { group: 'volume',  toG: 15 },
    tsp:     { group: 'volume',  toG: 5 },
    glass:   { group: 'volume',  toG: 200 },
    piece:   { group: 'count',   toG: null },
    slice:   { group: 'count',   toG: null },
    serving: { group: 'count',   toG: null },
  };
  var UNIT_LABELS = {
    g:'g (gram)', ml:'ml (millilitre)', oz:'oz (ounce)', cup:'cup (~240 ml)',
    tbsp:'tbsp (tablespoon)', tsp:'tsp (teaspoon)', glass:'glass (200 ml)',
    piece:'piece', slice:'slice', serving:'serving',
  };

  function toGrams(amount, unit, gPerUnit) {
    var u = UNITS[unit];
    if (!u) return null;
    if (u.toG != null) return amount * u.toG;
    if (gPerUnit) return amount * gPerUnit;
    return null;
  }

  function unitOptions(baseUnit, gPerUnit, validUnitsJson) {
    /* If the food has a valid_units whitelist, use it exclusively */
    if (validUnitsJson) {
      var whitelist;
      try { whitelist = typeof validUnitsJson === 'string' ? JSON.parse(validUnitsJson) : validUnitsJson; } catch (_) { whitelist = null; }
      if (whitelist && whitelist.length) {
        return Object.keys(UNITS).map(function (u) {
          return { unit: u, enabled: whitelist.indexOf(u) !== -1 };
        });
      }
    }
    /* Fallback: group-based logic */
    var base = UNITS[baseUnit] || UNITS['g'];
    var baseGroup = base.group;
    return Object.keys(UNITS).map(function (u) {
      var ug = UNITS[u].group;
      var enabled = false;
      if (ug === baseGroup) { enabled = true; }
      /* weight ↔ count: always ok (bread→slice makes sense; scale if g_per_unit known) */
      else if (ug === 'count' && baseGroup === 'weight') { enabled = true; }
      else if (ug === 'weight' && baseGroup === 'count') { enabled = !!gPerUnit; }
      /* volume ↔ count and weight ↔ volume: never (milk→slice, bread→cup make no sense) */
      return { unit: u, enabled: enabled };
    });
  }

  function populateUnitSelect(sel, baseUnit, gPerUnit, currentVal, validUnitsJson) {
    var opts = unitOptions(baseUnit || 'g', gPerUnit, validUnitsJson);
    sel.innerHTML = opts.map(function (o) {
      return '<option value="' + o.unit + '"' + (o.enabled ? '' : ' disabled') + '>'
        + (o.enabled ? '' : String.fromCharCode(10005) + ' ') + UNIT_LABELS[o.unit] + '</option>';
    }).join('');
    var enabled = opts.filter(function (o) { return o.enabled; }).map(function (o) { return o.unit; });
    sel.value = (currentVal && enabled.indexOf(currentVal) !== -1) ? currentVal : (enabled[0] || 'g');
  }

  function unitHintStr(amount, unit, gPerUnit) {
    var g = toGrams(amount, unit, gPerUnit);
    if (g == null || unit === 'g' || unit === 'ml') return '';
    var suffix = (UNITS[unit] && UNITS[unit].group === 'volume') ? ' ml' : ' g';
    return amount + ' ' + unit + ' ≈ ' + Math.round(g) + suffix;
  }

  var currentDate = formatDate(new Date());
  var editingId = null;
  var selectedFood = null;
  var manualMacroEdit = false;
  var pendingMealType = null;
  var foodGPerUnit = null;

  var dateHeading      = document.getElementById('date-heading');
  var prevDayBtn       = document.getElementById('prev-day');
  var nextDayBtn       = document.getElementById('next-day');
  var openAddFormBtn   = document.getElementById('open-add-form');
  var entryModal       = document.getElementById('entry-modal');
  var closeModalBtn    = document.getElementById('close-modal');
  var cancelEntryBtn   = document.getElementById('cancel-entry');
  var entryForm        = document.getElementById('entry-form');
  var modalTitle       = document.getElementById('modal-title');
  var quickAddList     = document.getElementById('quick-add-list');
  var entriesList      = document.getElementById('entries-list');
  var foodNameInput    = document.getElementById('entry-food-name');
  var autocompleteList = document.getElementById('food-autocomplete');
  var unitSelect       = document.getElementById('entry-serving-unit');
  var unitHintEl       = document.getElementById('unit-equiv-hint');
  var mealSelect       = document.getElementById('entry-meal-type');
  var servingInput     = document.getElementById('entry-serving-size');
  var mealRadios       = Array.from(document.querySelectorAll('#entry-modal input[name="lf_meal"]'));
  var lfRecents        = document.getElementById('lf-recents');
  var lfRecentsRow     = document.getElementById('lf-recents-row');
  var lfQuick          = document.getElementById('lf-quick');
  var lfManual         = document.getElementById('lf-manual');
  var lfStepDec        = document.getElementById('lf-step-dec');
  var lfStepInc        = document.getElementById('lf-step-inc');
  var recentFoods = [];
  var acFoods = [];
  var clearRecentsBtn  = document.getElementById('clear-recents-btn');
  var copyYesterdayBtn  = document.getElementById('copy-yesterday-btn');
  var copyConfirmModal  = document.getElementById('copy-confirm-modal');
  var closeCopyModal    = document.getElementById('close-copy-modal');
  var cancelCopyBtn     = document.getElementById('cancel-copy-btn');
  var confirmCopyBtn    = document.getElementById('confirm-copy-btn');
  var copyPreviewList   = document.getElementById('copy-preview-list');

  var notesSection      = document.getElementById('notes-section');
  var notesToggle       = document.getElementById('notes-toggle');
  var notesPanel        = document.getElementById('notes-panel');
  var notesTextarea     = document.getElementById('notes-textarea');
  var notesSaveStatus   = document.getElementById('notes-save-status');

  var tplAdjustModal  = document.getElementById('tpl-adjust-modal');
  var tplAdjustTitle  = document.getElementById('tpl-adjust-title');
  var tplAdjustItems  = document.getElementById('tpl-adjust-items');
  var tplAdjustTotals = document.getElementById('tpl-adjust-totals');
  var closeTplAdjust    = document.getElementById('close-tpl-adjust');
  var cancelTplAdjust   = document.getElementById('cancel-tpl-adjust');
  var confirmTplLog     = document.getElementById('confirm-tpl-log');
  var tplItemSearch     = document.getElementById('tpl-item-search');
  var tplItemAutoList   = document.getElementById('tpl-item-autocomplete');
  var tplSaveChk        = document.getElementById('tpl-save-changes');
  var currentTpl = null;
  var currentEditEntryId = null; /* set when editing an existing template entry */
  var allTemplates = [];
  var templateChipsList = document.getElementById('template-chips');

  async function init() {
    await loadPage();
    await Promise.all([loadRecents(), loadTemplateChips()]);
    setRemainingLabels();
    initCopyYesterday();
    initNotes();
    handleScanDeepLink();
  }

  function handleScanDeepLink() {
    var params = new URLSearchParams(location.search);
    if (params.get('scan') !== '1') return;
    var btn = document.getElementById('photo-food-btn');
    if (btn) btn.click();
    params.delete('scan');
    var qs = params.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash);
  }

  function setRemainingLabels() {
    var txt = (Lang && Lang.isTr && Lang.isTr()) ? 'kalan' : 'remaining';
    ['protein','fat','carbs','calories'].forEach(function (m) {
      var el = document.getElementById('lbl-remaining-' + m);
      if (el) el.textContent = txt;
    });
  }

  function updateDateHeading() {
    dateHeading.textContent = formatDateDisplay(currentDate);
    nextDayBtn.disabled = currentDate >= formatDate(new Date());
  }
  prevDayBtn.addEventListener('click', function () {
    var d = parseLocalDate(currentDate); d.setDate(d.getDate() - 1);
    currentDate = formatDate(d); loadPage();
  });
  nextDayBtn.addEventListener('click', function () {
    if (currentDate >= formatDate(new Date())) return;
    var d = parseLocalDate(currentDate); d.setDate(d.getDate() + 1);
    currentDate = formatDate(d); loadPage();
  });
  /* ---- Weekly date scroller ---- */
  var weekEl = document.getElementById('dash-week');
  var weekReq = 0;
  function addDays(str, n) { var d = parseLocalDate(str); d.setDate(d.getDate() + n); return formatDate(d); }

  async function loadWeek() {
    if (!weekEl) return;
    var today = formatDate(new Date());
    var end = addDays(currentDate, 3); if (end > today) end = today;
    var start = addDays(end, -6);
    var days = []; for (var i = 0; i < 7; i++) days.push(addDays(start, i));
    var req = ++weekReq;
    renderWeek(days, {});
    try {
      var rows = await api('/api/summary/range?start=' + start + '&end=' + end);
      if (req !== weekReq) return;
      var logged = {};
      (rows || []).forEach(function (r) { logged[r.date] = true; });
      renderWeek(days, logged);
    } catch (_) { /* dots are decorative */ }
  }

  function renderWeek(days, logged) {
    var today = formatDate(new Date());
    var loc = (Lang && Lang.isTr && Lang.isTr()) ? 'tr-TR' : 'en-US';
    weekEl.innerHTML = days.map(function (ds) {
      var d = parseLocalDate(ds), sel = ds === currentDate, has = !!logged[ds];
      var wd = d.toLocaleDateString(loc, { weekday: 'short' });
      var full = d.toLocaleDateString(loc, { weekday: 'long', day: 'numeric', month: 'long' });
      return '<button type="button" class="dash-day' + (sel ? ' is-selected' : '') + (has ? ' has-entries' : '') + '"'
        + ' data-date="' + ds + '" aria-pressed="' + sel + '"' + (ds === today ? ' aria-current="date"' : '')
        + ' aria-label="' + escHtml(full + (has ? ' \u00b7 ' + t('dash.hasEntries') : '')) + '">'
        + '<span class="dash-day__wd">' + escHtml(wd) + '</span>'
        + '<span class="dash-day__num">' + d.getDate() + '</span>'
        + '<span class="dash-day__dot" aria-hidden="true"></span></button>';
    }).join('');
    var s = weekEl.querySelector('.is-selected');
    if (s) weekEl.scrollLeft = s.offsetLeft - (weekEl.clientWidth - s.offsetWidth) / 2;
  }

  if (weekEl) weekEl.addEventListener('click', function (e) {
    var b = e.target.closest('[data-date]');
    if (!b || b.dataset.date === currentDate) return;
    currentDate = b.dataset.date;
    loadPage();
  });

  async function loadPage() {
    updateDateHeading();
    await Promise.all([loadSummary(), loadEntries(), loadWeek()]);
    updateCopyYesterdayVisibility();
    loadNote();
  }
  async function loadSummary() {
    try { var data = await api('/api/summary?date=' + currentDate); renderSummary(data); renderHero(data); renderRemainingPanel(data); }
    catch (err) { showToast(t('common.error') + ': ' + err.message, 'error'); }
  }

  function renderSummary(data) {
    var isTr = Lang && Lang.isTr && Lang.isTr();
    var remainingTxt = isTr ? 'kalan' : 'remaining';
    var overTxt      = isTr ? 'Aştınız!' : 'Over!';
    ['protein','fat','carbs','calories'].forEach(function (m) {
      var consumed  = Math.round(data.totals?.[m] ?? 0);
      var target    = Math.round(data.target?.[m] ?? 0);
      var remaining = Math.round(data.remaining?.[m] ?? 0);
      var pct       = target > 0 ? Math.min(100, Math.round((consumed / target) * 100)) : 0;
      var over      = target > 0 && consumed > target;
      var sumEl = document.getElementById('summary-' + m); if (sumEl) sumEl.textContent = consumed;
      var tgtEl = document.getElementById('target-' + m);  if (tgtEl) tgtEl.textContent = target;
      var remEl = document.getElementById('remaining-' + m);
      if (remEl) {
        remEl.textContent = over ? '+' + Math.abs(remaining) : remaining;
        remEl.classList.toggle('over-target', over);
        /* color-code the entire remaining paragraph */
        var remP = remEl.closest('.summary-card__remaining');
        if (remP) {
          remP.classList.remove('remaining--under','remaining--close','remaining--over');
          if (over) { remP.classList.add('remaining--over'); }
          else if (target > 0 && remaining / target <= 0.10) { remP.classList.add('remaining--close'); }
          else if (!over) { remP.classList.add('remaining--under'); }
        }
      }
      var lbl = document.getElementById('lbl-remaining-' + m);
      if (lbl) lbl.textContent = over ? overTxt : remainingTxt;
      var barEl = document.getElementById('bar-' + m);
      if (barEl) { barEl.style.width = pct + '%'; barEl.classList.toggle('bar--over', over); }
      var pctEl = document.getElementById('pct-' + m); if (pctEl) pctEl.textContent = '(' + pct + '%)';
    });
    var tp=data.totals?.protein??0, tf=data.totals?.fat??0, tc=data.totals?.carbs??0;
    var totalKcal=tp*4+tf*9+tc*4;
    var gp=data.target?.protein??0, gf=data.target?.fat??0, gc=data.target?.carbs??0;
    var targetKcal=gp*4+gf*9+gc*4;
    var mul={protein:4,fat:9,carbs:4};
    ['protein','fat','carbs'].forEach(function(m){
      var curPct=totalKcal>0?Math.round((data.totals?.[m]??0)*mul[m]/totalKcal*100):0;
      var tgtPct=targetKcal>0?Math.round((data.target?.[m]??0)*mul[m]/targetKcal*100):0;
      var el=document.getElementById('split-'+m); if(el) el.textContent=curPct+'% eaten / '+tgtPct+'% target';
    });
  }

  /* ---- Hero gauges (calorie arc + macro rings) ---- */
  var ARC_LEN = 150.8, RING_LEN = 113.1, DROP_RING_LEN = 182.2;
  function pctOf(c, g) { return g > 0 ? c / g * 100 : 0; }

  function renderHero(data) {
    var tot = data.totals || {}, tgt = data.target || {}, rem = data.remaining || {};
    var kc = Math.round(tot.calories || 0), kt = Math.round(tgt.calories || 0), kp = pctOf(kc, kt);
    var arc = document.getElementById('cal-arc-fill');
    if (arc) {
      arc.style.strokeDasharray = ARC_LEN;
      arc.style.strokeDashoffset = ARC_LEN * (1 - Math.min(100, kp) / 100);
      arc.classList.toggle('is-over', kt > 0 && kc > kt);
    }
    var gauge = document.getElementById('cal-arc');
    if (gauge) gauge.setAttribute('aria-label', t('macro.calories') + ': ' + kc + ' / ' + kt + ' kcal (' + Math.round(kp) + '%)');

    ['protein', 'carbs', 'fat'].forEach(function (m) {
      var c = tot[m] || 0, g = tgt[m] || 0, over = g > 0 && c > g, p = pctOf(c, g);
      var fill = document.getElementById('ring-fill-' + m);
      if (fill) {
        fill.style.strokeDasharray = RING_LEN;
        fill.style.strokeDashoffset = RING_LEN * (1 - Math.min(100, p) / 100);
      }
      var val = document.getElementById('dash-left-' + m);
      if (val) val.textContent = Math.round(Math.abs(rem[m] || 0));
      var cap = document.getElementById('dash-cap-' + m);
      if (cap) cap.textContent = t('macro.' + m) + ' ' + t(over ? 'macro.over' : 'macro.left');
      var card = document.getElementById('dash-macro-' + m);
      if (card) card.classList.toggle('is-over', over);
      var ring = document.getElementById('ring-' + m);
      if (ring) ring.setAttribute('aria-label', t('macro.' + m) + ': ' + Math.round(c) + ' / ' + Math.round(g) + ' g (' + Math.round(p) + '%)');
    });
    renderHealth(tot, tgt);
  }

  /* ---- Health score (macro adherence only; no micronutrient data exists) ---- */
  function healthStatus(c, g) {
    if (!(g > 0) || !(c > 0)) return 'none';
    var r = c / g;
    if (r >= 0.9 && r <= 1.1) return 'good';
    if (r >= 0.7 && r <= 1.3) return 'warn';
    return 'bad';
  }

  function renderHealth(tot, tgt) {
    var keys = ['protein', 'fat', 'carbs', 'calories'];
    var hasEntries = keys.some(function (k) { return (tot[k] || 0) > 0; });
    var scores = [];
    keys.forEach(function (k) {
      var g = tgt[k] || 0;
      if (g > 0) scores.push(10 * Math.max(0, 1 - Math.abs((tot[k] || 0) / g - 1)));
    });
    var score = (hasEntries && scores.length)
      ? Math.round(scores.reduce(function (a, b) { return a + b; }, 0) / scores.length) : null;

    var labelKey = score == null ? 'dash.noData'
      : score >= 9 ? 'health.great' : score >= 7 ? 'health.good' : score >= 4 ? 'health.fair' : 'health.poor';
    var tone = score == null ? 'none' : score >= 7 ? 'good' : score >= 4 ? 'warn' : 'bad';
    var lblEl = document.getElementById('health-label');
    if (lblEl) lblEl.textContent = t(labelKey);
    var scoreEl = document.getElementById('health-score');
    if (scoreEl) scoreEl.textContent = score == null ? '\u2013' : score;
    var badge = document.getElementById('health-badge');
    if (badge) {
      badge.className = 'dash-health__badge is-' + tone;
      badge.setAttribute('aria-label', t('dash.healthScore') + ': ' + (score == null ? '\u2013' : score) + '/10 \u2013 ' + t(labelKey));
    }

    var listEl = document.getElementById('health-list');
    if (!listEl) return;
    listEl.innerHTML = ['protein', 'carbs', 'fat', 'calories'].map(function (k) {
      var c = tot[k] || 0, g = tgt[k] || 0, st = healthStatus(c, g);
      var unit = k === 'calories' ? ' kcal' : 'g';
      return '<li class="dash-health__row">'
        + '<span class="dash-dot dash-dot--' + st + '" aria-hidden="true"></span>'
        + '<span class="dash-health__name">' + escHtml(t('macro.' + k)) + '</span>'
        + '<span class="dash-health__val">' + Math.round(c) + unit + '</span>'
        + '<span class="dash-health__pct">' + (g > 0 ? Math.round(c / g * 100) + '%' : '\u2013') + '</span>'
        + '</li>';
    }).join('');
  }

  async function loadEntries() {
    try { var entries=await api('/api/entries?date='+currentDate); renderEntries(entries); }
    catch(err){ showToast(t('common.error')+': '+err.message,'error'); }
  }
  var MEAL_ORDER=['Breakfast','Lunch','Dinner','Snack','Other'];
  var MEAL_I18N={Breakfast:'entry.breakfast',Lunch:'entry.lunch',Dinner:'entry.dinner',Snack:'entry.snack',Other:'entry.other'};

  var MEAL_ICONS={Breakfast:'\uD83C\uDF73',Lunch:'\uD83E\uDD57',Dinner:'\uD83C\uDF72',Snack:'\uD83C\uDF4E',Other:'\uD83C\uDF7D\uFE0F'};
  var AVATAR_TONES=['protein','carbs','fat','water'];
  var FLAME_SVG='<svg class="ico-flame" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12 2.5c.6 3.2-1.4 5-3 6.8C7.6 10.9 6.5 12.6 6.5 15a5.5 5.5 0 0 0 11 0c0-2.3-1.1-4-2.3-5.2.1 1.6-.6 2.8-1.7 3.3.4-3.6-.4-7.3-1.5-10.6z"/></svg>';
  var expandedMeals={};

  function mealAvatar(name){
    var n=String(name||'').trim(), h=0;
    for(var i=0;i<n.length;i++) h=(h*31+n.charCodeAt(i))>>>0;
    var ch=n?Array.from(n)[0].toUpperCase():'?';
    return '<span class="meal-ava meal-ava--'+AVATAR_TONES[h%AVATAR_TONES.length]+'" title="'+escHtml(n)+'">'+escHtml(ch)+'</span>';
  }

  function renderEntries(entries) {
    entries=entries||[];
    var groups={};MEAL_ORDER.forEach(function(m){groups[m]=[];});
    entries.forEach(function(e){var mt=e.meal_type;var k=(mt&&mt in groups)?mt:'Other';groups[k].push(e);});
    var html='';
    MEAL_ORDER.forEach(function(meal){
      var list=groups[meal];
      if(meal==='Other'&&list.length===0) return;
      var lbl=t(MEAL_I18N[meal])||meal;
      var sp=0,sf=0,sc=0,sk=0;
      list.forEach(function(e){sp+=e.protein||0;sf+=e.fat||0;sc+=e.carbs||0;sk+=e.calories||0;});
      var open=!!expandedMeals[meal];
      var bodyId='meal-body-'+meal.toLowerCase();
      var avatars=list.slice(0,3).map(function(e){return mealAvatar(e.food_name);}).join('')
        +(list.length>3?'<span class="meal-ava meal-ava--more">+'+(list.length-3)+'</span>':'');
      html+='<div class="meal-group meal-row'+(open?' is-open':'')+(list.length?'':' is-empty')+'" data-meal="'+escHtml(meal)+'">'
        +'<div class="meal-row__head">'
        +'<button type="button" class="meal-row__toggle" data-action="toggle-meal" data-meal="'+escHtml(meal)+'" aria-expanded="'+open+'" aria-controls="'+bodyId+'">'
        +'<span class="meal-row__icon" aria-hidden="true">'+MEAL_ICONS[meal]+'</span>'
        +'<span class="meal-row__text"><span class="meal-row__title">'+escHtml(lbl)+'</span>'
        +'<span class="meal-row__kcal">'+FLAME_SVG+Math.round(sk)+' Kcal</span></span>'
        +'<span class="meal-row__avatars" aria-hidden="true">'+avatars+'</span>'
        +'<span class="meal-row__chev" aria-hidden="true"></span>'
        +'</button>'
        +(meal!=='Other'?'<button type="button" class="meal-row__add" data-action="add-to-meal" data-meal="'+escHtml(meal)+'" aria-label="'+escHtml(t('dash.addToMeal').replace('{meal}',lbl))+'">+</button>':'')
        +'</div>'
        +'<div class="meal-row__body" id="'+bodyId+'"'+(open?'':' hidden')+'>';
      if(list.length){
        html+='<div class="meal-group__header">'
          +'<p class="meal-group__subtotal">P '+round1(sp)+'g \u00b7 F '+round1(sf)+'g \u00b7 C '+round1(sc)+'g \u00b7 '+Math.round(sk)+' kcal</p>'
          +(meal!=='Other'?'<button type="button" class="meal-clear-btn" data-action="clear-meal" data-meal="'+escHtml(meal)+'">&times; '+escHtml(t('common.clearLabel'))+'</button>':'')
          +'</div>';
        list.forEach(function(e){html+=renderEntryCard(e);});
      }else{
        html+='<p class="meal-row__empty">'+escHtml(t('dash.mealEmpty'))+'</p>';
      }
      html+='</div></div>';
    });
    entriesList.innerHTML=html;
  }

  function renderEntryCard(e) {
    var kcal=Math.round(e.calories??0);
    return '<article class="entry-card" data-id="'+e.id+'">'
      +'<div class="entry-card__info"><p class="entry-card__name">'+escHtml(e.food_name)+'</p>'
      +'<p class="entry-card__meta">'+escHtml(String(e.serving_size))+' '+escHtml(e.serving_unit)+'</p>'
      +'<div class="entry-card__macros">'
      +'<span class="macro-tag macro-tag--protein">P: '+round1(e.protein)+'g</span>'
      +'<span class="macro-tag macro-tag--fat">F: '+round1(e.fat)+'g</span>'
      +'<span class="macro-tag macro-tag--carbs">C: '+round1(e.carbs)+'g</span>'
      +'<span class="macro-tag macro-tag--cal">'+kcal+' kcal</span>'
      +'</div></div>'
      +'<div class="entry-card__actions">'
      +'<button class="btn btn-icon" title="Copy" data-action="copy" data-id="'+e.id+'">&#x2398;</button>'
      +'<button class="btn btn-icon" title="'+escHtml(t('common.edit'))+'" data-action="edit" data-id="'+e.id+'">&#9998;</button>'
      +'<button class="btn btn-icon" title="'+escHtml(t('common.delete'))+'" data-action="delete" data-id="'+e.id+'">&#128465;</button>'
      +'</div></article>';
  }

  async function loadRecents() {
    try { var r=await api('/api/entries/recent'); renderRecents(r); }
    catch(_){ quickAddList.innerHTML='<p class="empty-msg">'+escHtml(t('common.loadError'))+'</p>'; }
  }
  function renderRecents(recents) {
    recentFoods=recents||[]; renderSheetRecents();
    if(!recents||recents.length===0){quickAddList.innerHTML='<p class="empty-msg">No recent foods yet.</p>';return;}
    quickAddList.innerHTML=recents.map(function(r){
      var kcal=Math.round(r.calories??((r.protein||0)*4+(r.fat||0)*9+(r.carbs||0)*4));
      var hint='P:'+round1(r.protein)+'g F:'+round1(r.fat)+'g · '+kcal+' kcal';
      return '<button class="quick-add-chip" data-food=\''+JSON.stringify(r).replace(/'/g,"&#39;")+'\'>'
        +'<span class="chip-name">'+escHtml(r.food_name)+'</span>'
        +'<span class="chip-macro-hint">'+hint+'</span>'
        +'</button>';
    }).join('');
  }
  quickAddList.addEventListener('click',function(e){
    var chip=e.target.closest('.quick-add-chip'); if(!chip) return;
    try{var food=JSON.parse(chip.dataset.food);openModal();prefillFromFood(food);}catch(_){}
  });
  if(clearRecentsBtn) clearRecentsBtn.addEventListener('click',function(){
    recentFoods=[]; renderSheetRecents();
    quickAddList.innerHTML='<p class="empty-msg">No recent foods yet.</p>';
  });

  function updateUnitHint() {
    if(!unitHintEl) return;
    var amt=parseFloat(document.getElementById('entry-serving-size').value);
    var unit=unitSelect?unitSelect.value:'g';
    if(!amt||amt<=0){unitHintEl.hidden=true;return;}
    var hint=unitHintStr(amt,unit,foodGPerUnit);
    if(hint){unitHintEl.textContent=hint;unitHintEl.hidden=false;}
    else{unitHintEl.hidden=true;}
  }

  function openModal(entry) {
    editingId=entry?entry.id:null; selectedFood=null; manualMacroEdit=false; foodGPerUnit=null;
    modalTitle.textContent=entry?t('entry.editEntry'):t('entry.logFood');
    entryForm.reset();
    if(lfManual) lfManual.open=false;
    document.getElementById('entry-id').value='';
    document.getElementById('entry-saved-food-id').value='';
    autocompleteList.hidden=true;
    if(unitHintEl) unitHintEl.hidden=true;
    populateUnitSelect(unitSelect,'g',null,'g');
    if(entry){
      document.getElementById('entry-id').value=entry.id;
      document.getElementById('entry-saved-food-id').value=entry.saved_food_id??'';
      foodNameInput.value=entry.food_name;
      document.getElementById('entry-protein').value=entry.protein;
      document.getElementById('entry-fat').value=entry.fat;
      document.getElementById('entry-carbs').value=entry.carbs;
      document.getElementById('entry-calories').value=Math.round(entry.calories??0);
      document.getElementById('entry-meal-type').value=entry.meal_type;
      document.getElementById('entry-serving-size').value=entry.serving_size;
      var baseUnit=entry.serving_unit||'g';
      foodGPerUnit=null;
      if(entry.saved_food_id){
        api('/api/foods/'+entry.saved_food_id).then(function(f){
          if(f){foodGPerUnit=f.g_per_unit||null;populateUnitSelect(unitSelect,f.serving_unit||baseUnit,foodGPerUnit,baseUnit,f.valid_units||null);}
        }).catch(function(){});
      } else {
        populateUnitSelect(unitSelect,baseUnit,null,baseUnit);
      }
      selectedFood={protein:entry.protein??0,fat:entry.fat??0,carbs:entry.carbs??0,
        calories:entry.calories??0,default_serving:entry.serving_size??100,serving_unit:entry.serving_unit??'g'};
    } else {
      mealSelect.value=pendingMealType||defaultMeal();
    }
    refreshSheet();
    entryModal.hidden=false; foodNameInput.focus();
  }

  function closeModal(){
    entryModal.hidden=true; entryForm.reset();
    editingId=null; selectedFood=null; pendingMealType=null; foodGPerUnit=null;
    autocompleteList.hidden=true; if(unitHintEl) unitHintEl.hidden=true;
  }

  openAddFormBtn.addEventListener('click',function(){pendingMealType=null;openModal();});
  closeModalBtn.addEventListener('click',closeModal);
  cancelEntryBtn.addEventListener('click',closeModal);

  var scanBarcodeBtn = document.getElementById('scan-barcode-btn');
  if(scanBarcodeBtn) scanBarcodeBtn.addEventListener('click',function(){
    openBarcodeScanner(function(food){
      pendingMealType=null;
      openModal();
      prefillFromFood({
        food_name: food.name,
        name: food.name,
        protein: food.protein,
        fat: food.fat,
        carbs: food.carbs,
        calories: food.calories,
        default_serving: 100,
        serving_unit: 'g',
      });
    });
  });

  var photoFoodBtn = document.getElementById('photo-food-btn');
  if(photoFoodBtn) photoFoodBtn.addEventListener('click',function(){
    openFoodImageScanner(function(food){
      pendingMealType=null;
      openModal();
      prefillFromFood({
        food_name: food.name,
        name: food.name,
        protein: food.protein,
        fat: food.fat,
        carbs: food.carbs,
        calories: food.calories,
        default_serving: food.estimated_grams||100,
        serving_unit: 'g',
      });
    });
  });

  function prefillFromFood(food) {
    foodNameInput.value=food.food_name??food.name??'';
    document.getElementById('entry-protein').value=food.protein??'';
    document.getElementById('entry-fat').value=food.fat??'';
    document.getElementById('entry-carbs').value=food.carbs??'';
    document.getElementById('entry-calories').value=food.calories?Math.round(food.calories):'';
    document.getElementById('entry-serving-size').value=food.serving_size??food.default_serving??'';
    if(food.id) document.getElementById('entry-saved-food-id').value=food.id;
    foodGPerUnit=food.g_per_unit||null;
    var baseUnit=food.serving_unit||'g';
    populateUnitSelect(unitSelect,baseUnit,foodGPerUnit,baseUnit,food.valid_units||null);
    selectedFood={protein:food.protein??0,fat:food.fat??0,carbs:food.carbs??0,
      calories:food.calories??0,default_serving:food.default_serving??food.serving_size??100,
      serving_unit:baseUnit,g_per_unit:foodGPerUnit};
    manualMacroEdit=false; updateUnitHint(); refreshSheet();
  }

  var debouncedSearch=debounce(async function(q){
    if(q.length<2){autocompleteList.hidden=true;return;}
    try{var foods=await api('/api/foods?q='+encodeURIComponent(q)+Lang.langParam());renderAutocomplete(foods);}
    catch(_){autocompleteList.hidden=true;}
  },280);

  foodNameInput.addEventListener('input',function(){
    /* Only reset unit select when user clears the food name (deselects a food) */
    if(selectedFood){
      selectedFood=null; foodGPerUnit=null;
      document.getElementById('entry-saved-food-id').value='';
      populateUnitSelect(unitSelect,'g',null,'g');
    }
    debouncedSearch(foodNameInput.value.trim());
  });
  foodNameInput.addEventListener('keydown',function(e){
    if(autocompleteList.hidden) return;
    var items=autocompleteList.querySelectorAll('li');
    var focused=autocompleteList.querySelector('li.focused');
    var idx=Array.from(items).indexOf(focused);
    if(e.key==='ArrowDown'){e.preventDefault();idx=Math.min(idx+1,items.length-1);}
    else if(e.key==='ArrowUp'){e.preventDefault();idx=Math.max(idx-1,0);}
    else if(e.key==='Enter'&&focused){e.preventDefault();focused.click();return;}
    else if(e.key==='Escape'){autocompleteList.hidden=true;return;}
    items.forEach(function(li,i){
      li.classList.toggle('focused',i===idx); li.setAttribute('aria-selected',String(i===idx));
      if(i===idx) li.scrollIntoView({block:'nearest'});
    });
  });
  document.addEventListener('click',function(e){
    if(!e.target.closest('.autocomplete-wrap')) autocompleteList.hidden=true;
  });

  function renderAutocomplete(foods){
    if(!foods||foods.length===0){autocompleteList.hidden=true;return;}
    acFoods=foods.slice(0,10);
    autocompleteList.innerHTML=acFoods.map(function(f,i){
      // Hide "generic" brand label — it's a seed-data artefact, not useful info
      var brand=(f.brand&&f.brand!=='generic')?' · '+escHtml(f.brand):'';
      // Scale macros to default_serving so the hint matches what fills the form
      var baseUnit=f.serving_unit||'g';
      var gpu=f.g_per_unit||null;
      var serving=f.default_serving||100;
      var initG=toGrams(serving,baseUnit,gpu);
      var scale=(initG!=null)?initG/100:1;
      var servLabel=(initG!=null)?round1(initG)+' g':'100 g';
      var kcal=Math.round((f.calories??((f.protein||0)*4+(f.fat||0)*9+(f.carbs||0)*4))*scale);
      var nm=Lang.foodName(f)||f.name||'';
      return '<li role="option" tabindex="-1" aria-selected="false" class="lf-ac__row" data-idx="'+i+'">'
        +avatarHtml(nm)
        +'<span class="lf-ac__main"><span class="lf-ac__name">'+escHtml(nm)+'</span>'
        +'<span class="lf-ac__cap">'+servLabel+' · '+kcal+' kcal'+brand+'</span></span>'
        +'<span class="lf-ac__mac"><span class="lf-m--p">P '+round1(f.protein*scale)+'</span>'
        +'<span class="lf-m--c">C '+round1(f.carbs*scale)+'</span>'
        +'<span class="lf-m--f">F '+round1(f.fat*scale)+'</span></span></li>';
    }).join('');
    autocompleteList.hidden=false;
  }
  autocompleteList.addEventListener('click',function(e){
    var li=e.target.closest('li'); if(!li) return;
    try{
      var food=acFoods[parseInt(li.dataset.idx,10)]; if(!food) return;
      manualMacroEdit=false;
      foodNameInput.value=food.name;
      document.getElementById('entry-saved-food-id').value=food.id??'';
      document.getElementById('entry-serving-size').value=food.default_serving??'';
      foodGPerUnit=food.g_per_unit||null;
      var baseUnit=food.serving_unit||'g';
      // Scale from per-100g storage to default_serving so scaleFromServing works like the edit path
      var initG=toGrams(food.default_serving||100,baseUnit,foodGPerUnit);
      var scale=(initG!=null)?initG/100:1;
      var rawP=(food.protein||0)*scale;
      var rawF=(food.fat||0)*scale;
      var rawC=(food.carbs||0)*scale;
      var rawK=(food.calories??((food.protein*4)+(food.fat*9)+(food.carbs*4)))*scale;
      document.getElementById('entry-protein').value=round1(rawP);
      document.getElementById('entry-fat').value=round1(rawF);
      document.getElementById('entry-carbs').value=round1(rawC);
      document.getElementById('entry-calories').value=Math.round(rawK);
      // selectedFood holds scaled macros — same contract as openModal(entry)
      selectedFood=Object.assign({},food,{protein:rawP,fat:rawF,carbs:rawC,calories:rawK,
        default_serving:food.default_serving||100,serving_unit:baseUnit});
      populateUnitSelect(unitSelect,baseUnit,foodGPerUnit,baseUnit,food.valid_units||null);
      autocompleteList.hidden=true; updateUnitHint(); refreshSheet();
    }catch(_){}
  });

  ['entry-protein','entry-fat','entry-carbs','entry-calories'].forEach(function(id){
    document.getElementById(id).addEventListener('input',function(){manualMacroEdit=true;});
  });
  document.getElementById('entry-serving-size').addEventListener('input',function(){
    updateUnitHint(); if(manualMacroEdit||!selectedFood) return; scaleFromServing();
  });
  if(unitSelect) unitSelect.addEventListener('change',function(){
    updateUnitHint(); if(manualMacroEdit||!selectedFood) return; scaleFromServing();
  });

  function scaleFromServing(){
    var baseServing=selectedFood.default_serving??selectedFood.serving_size;
    if(!baseServing||baseServing<=0) return;
    var newServing=parseFloat(document.getElementById('entry-serving-size').value);
    if(!newServing||newServing<=0) return;
    var currentUnit=unitSelect?unitSelect.value:(selectedFood.serving_unit||'g');
    var baseUnit=selectedFood.serving_unit||'g';
    var gpu=foodGPerUnit||selectedFood.g_per_unit||null;
    var baseG=toGrams(baseServing,baseUnit,gpu)??baseServing;
    var newG=toGrams(newServing,currentUnit,gpu)??newServing;
    var ratio=baseG>0?newG/baseG:1;
    document.getElementById('entry-protein').value=round1(selectedFood.protein*ratio);
    document.getElementById('entry-fat').value=round1(selectedFood.fat*ratio);
    document.getElementById('entry-carbs').value=round1(selectedFood.carbs*ratio);
    var baseCal=selectedFood.calories??((selectedFood.protein*4)+(selectedFood.fat*9)+(selectedFood.carbs*4));
    document.getElementById('entry-calories').value=Math.round(baseCal*ratio);
  }

  /* ---------- Log Food sheet helpers ---------- */
  var MEAL_KEYS={Breakfast:'entry.breakfast',Lunch:'entry.lunch',Dinner:'entry.dinner',Snack:'entry.snack'};
  function defaultMeal(){
    var h=new Date().getHours();
    return h<11?'Breakfast':h<16?'Lunch':h<21?'Dinner':'Snack';
  }
  function avatarHtml(name){
    var s=String(name||'').trim(), h=0;
    for(var i=0;i<s.length;i++) h=(h+s.charCodeAt(i))%5;
    return '<span class="lf-av lf-av--'+h+'" aria-hidden="true">'+escHtml((s.charAt(0)||'?').toUpperCase())+'</span>';
  }
  function syncMealPills(){
    mealRadios.forEach(function(r){r.checked=(r.value===mealSelect.value);});
    updateSaveLabel();
  }
  function updateSaveLabel(){
    var btn=document.getElementById('save-entry-btn');
    if(editingId) btn.textContent=t('entry.saveChanges');
    else if(MEAL_KEYS[mealSelect.value]) btn.textContent=t('entry.addTo').replace('{meal}',t(MEAL_KEYS[mealSelect.value]));
    else btn.textContent=t('entry.save');
  }
  function numVal(id){var v=parseFloat(document.getElementById(id).value);return isFinite(v)&&v>0?v:0;}
  function updatePreview(){
    var p=numVal('entry-protein'), f=numVal('entry-fat'), c=numVal('entry-carbs');
    var k=document.getElementById('entry-calories').value!==''?numVal('entry-calories'):p*4+f*9+c*4;
    document.getElementById('lf-kcal').textContent=Math.round(k);
    document.getElementById('lf-p').textContent=round1(p);
    document.getElementById('lf-c').textContent=round1(c);
    document.getElementById('lf-f').textContent=round1(f);
    var name=foodNameInput.value.trim(), amt=parseFloat(servingInput.value);
    document.getElementById('lf-preview-name').textContent=name
      ?name+(amt>0?' · '+round1(amt)+' '+(unitSelect?unitSelect.value:'g'):'')
      :t('entry.noFood');
    var pk=p*4, ck=c*4, fk=f*9, tot=pk+ck+fk;
    document.getElementById('lf-bar-p').style.width=(tot?pk/tot*100:0)+'%';
    document.getElementById('lf-bar-c').style.width=(tot?ck/tot*100:0)+'%';
    document.getElementById('lf-bar-f').style.width=(tot?fk/tot*100:0)+'%';
  }
  function updateQuick(){
    if(!lfQuick) return;
    var base=selectedFood?(selectedFood.default_serving??selectedFood.serving_size):null;
    lfQuick.hidden=!(base>0);
    if(lfQuick.hidden) return;
    var bu=selectedFood.serving_unit||'g', cur=parseFloat(servingInput.value);
    lfQuick.querySelectorAll('[data-mult]').forEach(function(b){
      var on=unitSelect.value===bu&&Math.abs(cur-base*parseFloat(b.dataset.mult))<0.05;
      b.setAttribute('aria-pressed',String(on));
    });
  }
  function updateRecentsVisibility(){
    if(lfRecents) lfRecents.hidden=!!editingId||!recentFoods.length||foodNameInput.value.trim()!=='';
  }
  function renderSheetRecents(){
    if(!lfRecentsRow) return;
    lfRecentsRow.innerHTML=recentFoods.slice(0,10).map(function(r,i){
      var kcal=Math.round(r.calories??((r.protein||0)*4+(r.fat||0)*9+(r.carbs||0)*4));
      return '<button type="button" class="lf-rchip" data-idx="'+i+'">'+avatarHtml(r.food_name)
        +'<span class="lf-rchip__txt"><span class="lf-rchip__name">'+escHtml(r.food_name)+'</span>'
        +'<span class="lf-rchip__cap">'+kcal+' kcal</span></span></button>';
    }).join('');
    updateRecentsVisibility();
  }
  function refreshSheet(){
    syncMealPills(); updatePreview(); updateQuick(); updateRecentsVisibility();
  }
  function stepServing(dir){
    var u=unitSelect?unitSelect.value:'g';
    var s=(u==='g'||u==='ml')?10:(u==='oz'?1:0.5);
    var nv=round1((parseFloat(servingInput.value)||0)+dir*s);
    if(nv<=0) return;
    servingInput.value=nv;
    servingInput.dispatchEvent(new Event('input',{bubbles:true}));
  }

  mealRadios.forEach(function(r){
    r.addEventListener('change',function(){if(r.checked){mealSelect.value=r.value;updateSaveLabel();}});
  });
  if(lfStepDec){lfStepDec.setAttribute('aria-label',t('entry.decrease'));lfStepDec.addEventListener('click',function(){stepServing(-1);});}
  if(lfStepInc){lfStepInc.setAttribute('aria-label',t('entry.increase'));lfStepInc.addEventListener('click',function(){stepServing(1);});}
  if(lfQuick){
    lfQuick.setAttribute('aria-label',t('entry.quickPortions'));
    lfQuick.addEventListener('click',function(e){
      var b=e.target.closest('[data-mult]'); if(!b||!selectedFood) return;
      var base=selectedFood.default_serving??selectedFood.serving_size; if(!(base>0)) return;
      var bu=selectedFood.serving_unit||'g';
      var opt=Array.from(unitSelect.options).find(function(o){return o.value===bu;});
      if(opt&&!opt.disabled) unitSelect.value=bu;
      servingInput.value=round1(base*parseFloat(b.dataset.mult));
      servingInput.dispatchEvent(new Event('input',{bubbles:true}));
    });
  }
  if(lfRecentsRow) lfRecentsRow.addEventListener('click',function(e){
    var b=e.target.closest('.lf-rchip'); if(!b) return;
    var food=recentFoods[parseInt(b.dataset.idx,10)]; if(!food) return;
    prefillFromFood(food); servingInput.focus();
  });
  var lfBar=document.getElementById('lf-bar');
  if(lfBar) lfBar.setAttribute('aria-label',t('entry.kcalSplit'));
  ['close-modal','close-copy-modal','close-tpl-adjust'].forEach(function(id){
    var b=document.getElementById(id); if(b) b.setAttribute('aria-label',t('common.close'));
  });
  /* Bubble-phase: runs after the field-level handlers above have rescaled macros */
  entryForm.addEventListener('input',function(){updatePreview();updateQuick();updateRecentsVisibility();});
  entryForm.addEventListener('change',function(){updatePreview();updateQuick();});

  entryForm.addEventListener('submit',async function(e){
    e.preventDefault();
    var protein=parseFloat(document.getElementById('entry-protein').value);
    var fat=parseFloat(document.getElementById('entry-fat').value);
    var carbs=parseFloat(document.getElementById('entry-carbs').value);
    var calRaw=document.getElementById('entry-calories').value;
    if(isNaN(protein)||isNaN(fat)||isNaN(carbs)){
      if(lfManual) lfManual.open=true;
      var bad=['entry-protein','entry-carbs','entry-fat'].map(function(id){return document.getElementById(id);})
        .find(function(el){return isNaN(parseFloat(el.value));});
      if(bad) bad.focus();
      showToast(t('entry.macrosRequired'),'error'); return;
    }
    if(!mealSelect.value){mealSelect.value=defaultMeal();syncMealPills();}
    var calories=calRaw!==''?parseFloat(calRaw):(protein*4)+(fat*9)+(carbs*4);
    var unit=unitSelect?unitSelect.value:'g';
    var body={food_name:foodNameInput.value.trim(),protein:protein,fat:fat,carbs:carbs,calories:calories,
      meal_type:document.getElementById('entry-meal-type').value,
      serving_size:parseFloat(document.getElementById('entry-serving-size').value),serving_unit:unit};
    var sfId=document.getElementById('entry-saved-food-id').value;
    if(sfId) body.saved_food_id=parseInt(sfId,10);
    var uInfo=UNITS[unit];
    if(sfId&&uInfo&&uInfo.group==='count'&&selectedFood&&!foodGPerUnit){
      var baseUnitStr=selectedFood.serving_unit||'g';
      var baseU=UNITS[baseUnitStr];
      if(baseU&&baseU.toG!=null&&body.serving_size>0){
        var gramsInEntry=toGrams(selectedFood.default_serving,baseUnitStr,null);
        if(gramsInEntry){
          var gPerOne=gramsInEntry/body.serving_size;
          if(gPerOne>0){
            api('/api/foods/'+sfId,{method:'PUT',body:JSON.stringify({g_per_unit:round1(gPerOne)})}).catch(function(){});
            foodGPerUnit=gPerOne;
          }
        }
      }
    }
    var saveBtn=document.getElementById('save-entry-btn'); saveBtn.disabled=true;
    try{
      if(editingId){
        await api('/api/entries/'+editingId,{method:'PUT',body:JSON.stringify(body)});
        showToast(t('common.success'),'success');
      }else{
        body.entry_date=currentDate;
        await api('/api/entries',{method:'POST',body:JSON.stringify(body)});
        showToast(t('common.success'),'success');
      }
      closeModal(); await loadPage();
    }catch(err){showToast(t('common.error')+': '+err.message,'error');}
    finally{saveBtn.disabled=false;}
  });

  entriesList.addEventListener('click',async function(e){
    var btn=e.target.closest('[data-action]'); if(!btn) return;
    var id=btn.dataset.id, meal=btn.dataset.meal;
    if(btn.dataset.action==='toggle-meal'){
      var row=btn.closest('.meal-row'), body=row?row.querySelector('.meal-row__body'):null;
      var open=btn.getAttribute('aria-expanded')!=='true';
      expandedMeals[meal]=open;
      btn.setAttribute('aria-expanded',String(open));
      if(body) body.hidden=!open;
      if(row) row.classList.toggle('is-open',open);
      return;
    }
    if(btn.dataset.action==='edit'){
      try{
        var entries=await api('/api/entries?date='+currentDate);
        var entry=entries.find(function(en){return String(en.id)===String(id);});
        if(!entry) return;
        /* If this entry was logged from a template, reopen the adjust modal */
        if(entry.template_id){
          var tpl=allTemplates.find(function(t){return t.id===entry.template_id;});
          if(!tpl){
            /* templates may not be loaded yet or was deleted — refresh */
            try{ tpl=await api('/api/meal-templates/'+entry.template_id); }catch(_){}
          }
          if(tpl){
            /* After adjust+confirm, delete the old entry and create the new one */
            currentEditEntryId=entry.id;
            openTplAdjust(tpl);
            return;
          }
        }
        openModal(entry);
      }catch(err){showToast(t('common.error')+': '+err.message,'error');}
    }else if(btn.dataset.action==='delete'){
      if(!confirm(t('common.delete')+'?')) return;
      try{
        await api('/api/entries/'+id,{method:'DELETE'});
        showToast(t('common.success'),'success'); await loadPage();
      }catch(err){showToast(t('common.error')+': '+err.message,'error');}
    }else if(btn.dataset.action==='copy'){
      try{
        var all=await api('/api/entries?date='+currentDate);
        var src=all.find(function(en){return String(en.id)===String(id);}); if(!src) return;
        pendingMealType=null; openModal();
        prefillFromFood({food_name:src.food_name,name:src.food_name,protein:src.protein,fat:src.fat,
          carbs:src.carbs,calories:src.calories,serving_size:src.serving_size,default_serving:src.serving_size,
          serving_unit:src.serving_unit,id:src.saved_food_id});
        document.getElementById('entry-meal-type').value=src.meal_type;
        syncMealPills();
      }catch(err){showToast(t('common.error')+': '+err.message,'error');}
    }else if(btn.dataset.action==='add-to-meal'){
      pendingMealType=meal; openModal();
    }else if(btn.dataset.action==='clear-meal'){
      if(!confirm(t('dash.clearMeal').replace('{meal}',meal))) return;
      try{
        await api('/api/entries/clear-meal?date='+currentDate+'&meal_type='+encodeURIComponent(meal),{method:'DELETE'});
        showToast(t('dash.mealCleared').replace('{meal}',meal),'success'); await loadPage();
      }catch(err){showToast(t('common.error')+': '+err.message,'error');}
    }
  });

  async function loadTemplateChips(){
    try{
      allTemplates=await api('/api/meal-templates');
      if(!allTemplates||allTemplates.length===0){
        templateChipsList.innerHTML='<p class="empty-msg">'+escHtml(t('dash.noTemplates'))+' <a href="/meals">Create one</a></p>';
        return;
      }
      templateChipsList.innerHTML=allTemplates.map(function(tpl){
        var itemNames=(tpl.items||[]).map(function(i){return escHtml(i.food_name);}).join(', ');
        return '<button class="quick-add-chip tpl-chip" data-template-id="'+tpl.id+'">'
          +'<span class="chip-name">'+escHtml(tpl.name)+'</span>'
          +(itemNames?'<span class="chip-items">'+itemNames+'</span>':'')
          +'<span class="chip-sub">'+Math.round(tpl.total_calories)+' kcal</span>'
          +'</button>';
      }).join('');
    }catch(_){templateChipsList.innerHTML='<p class="empty-msg">'+escHtml(t('common.loadError'))+'</p>';}
  }

  templateChipsList.addEventListener('click',function(e){
    var chip=e.target.closest('[data-template-id]'); if(!chip) return;
    var tpl=allTemplates.find(function(t){return String(t.id)===chip.dataset.templateId;});
    if(tpl) openTplAdjust(tpl);
  });

  function renderTplItems(){
    tplAdjustItems.innerHTML=(currentTpl.items||[]).map(function(item,idx){
      return '<div class="tpl-adjust-row" data-idx="'+idx+'">'
        +'<span class="tpl-adjust-name">'+escHtml(item.food_name)+'</span>'
        +'<input class="form-control tpl-adj-srv" type="number" min="0.1" step="0.1" value="'
        +round1(item.serving_size||100)+'" data-idx="'+idx+'" />'
        +'<span class="tpl-adjust-unit">'+escHtml(item.serving_unit||'g')+'</span>'
        +'<span class="tpl-adjust-macros" data-idx="'+idx+'">'+itemMacroStr(item)+'</span>'
        +'<button class="btn btn-icon btn-sm tpl-remove-item" data-idx="'+idx+'" title="Remove">&times;</button>'
        +'</div>';
    }).join('');
    updateTplTotals();
  }

  function openTplAdjust(tpl){
    currentTpl=JSON.parse(JSON.stringify(tpl));
    tplAdjustTitle.textContent=tpl.name;
    tplItemSearch.value='';
    tplItemAutoList.hidden=true;
    if(tplSaveChk) tplSaveChk.checked=false;
    renderTplItems();
    tplAdjustModal.hidden=false;
  }

  function closeTplAdjustModal(){tplAdjustModal.hidden=true;currentTpl=null;currentEditEntryId=null;}
  closeTplAdjust.addEventListener('click',closeTplAdjustModal);
  cancelTplAdjust.addEventListener('click',closeTplAdjustModal);

  /* Serving size change → scale macros */
  tplAdjustItems.addEventListener('input',function(e){
    if(!e.target.classList.contains('tpl-adj-srv')) return;
    var idx=parseInt(e.target.dataset.idx,10);
    var item=currentTpl.items[idx]; if(!item) return;
    var newServing=parseFloat(e.target.value); if(!newServing||newServing<=0) return;
    if(!item._base_serving){
      item._base_serving=item.serving_size||100;
      item._bp=item.protein; item._bf=item.fat; item._bc=item.carbs; item._bk=item.calories;
    }
    var ratio=newServing/item._base_serving;
    item.serving_size=newServing;
    item.protein=round1(item._bp*ratio); item.fat=round1(item._bf*ratio);
    item.carbs=round1(item._bc*ratio); item.calories=round1(item._bk*ratio);
    var macroEl=tplAdjustItems.querySelector('[data-idx="'+idx+'"].tpl-adjust-macros');
    if(macroEl) macroEl.textContent=itemMacroStr(item);
    updateTplTotals();
  });

  /* Remove item */
  tplAdjustItems.addEventListener('click',function(e){
    var btn=e.target.closest('.tpl-remove-item'); if(!btn) return;
    var idx=parseInt(btn.dataset.idx,10);
    currentTpl.items.splice(idx,1);
    renderTplItems();
  });

  /* Add item search autocomplete */
  var debouncedTplSearch=debounce(async function(q){
    if(q.length<2){tplItemAutoList.hidden=true;return;}
    try{
      var foods=await api('/api/foods?q='+encodeURIComponent(q)+Lang.langParam());
      if(!foods||foods.length===0){tplItemAutoList.hidden=true;return;}
      tplItemAutoList.innerHTML=foods.slice(0,8).map(function(f){
        var macros='<span class="ac-sub">P:'+round1(f.protein)+' F:'+round1(f.fat)+' C:'+round1(f.carbs)+'</span>';
        return '<li role="option" tabindex="-1" data-food=\''+JSON.stringify(f).replace(/'/g,"&#39;")+'\'>'+escHtml(Lang.foodName(f))+' '+macros+'</li>';
      }).join('');
      tplItemAutoList.hidden=false;
    }catch(_){tplItemAutoList.hidden=true;}
  },280);

  tplItemSearch.addEventListener('input',function(){debouncedTplSearch(tplItemSearch.value.trim());});

  tplItemAutoList.addEventListener('click',function(e){
    var li=e.target.closest('li'); if(!li) return;
    try{
      var food=JSON.parse(li.dataset.food);
      var newItem={
        food_name: food.name||food.food_name,
        saved_food_id: food.id||null,
        protein: food.protein||0, fat: food.fat||0, carbs: food.carbs||0,
        calories: food.calories||(food.protein*4+food.fat*9+food.carbs*4),
        serving_size: food.default_serving||100,
        serving_unit: food.serving_unit||'g',
      };
      currentTpl.items.push(newItem);
      renderTplItems();
      tplItemSearch.value='';
      tplItemAutoList.hidden=true;
    }catch(_){}
  });

  document.addEventListener('click',function(e){
    if(!e.target.closest('.tpl-add-item-row')) tplItemAutoList.hidden=true;
  });

  function itemMacroStr(item){
    return 'P:'+round1(item.protein)+' F:'+round1(item.fat)+' C:'+round1(item.carbs)+' '+Math.round(item.calories||0)+'kcal';
  }
  function updateTplTotals(){
    if(!currentTpl) return;
    var tp=0,tf=0,tc=0,tk=0;
    currentTpl.items.forEach(function(i){tp+=i.protein;tf+=i.fat;tc+=i.carbs;tk+=(i.calories||0);});
    tplAdjustTotals.textContent='Total: P:'+round1(tp)+'g F:'+round1(tf)+'g C:'+round1(tc)+'g '+Math.round(tk)+' kcal';
  }

  confirmTplLog.addEventListener('click',async function(){
    if(!currentTpl) return; confirmTplLog.disabled=true;
    try{
      var tp=0,tf=0,tc=0,tk=0,ts=0;
      currentTpl.items.forEach(function(i){tp+=i.protein;tf+=i.fat;tc+=i.carbs;tk+=(i.calories||0);ts+=(i.serving_size||0);});
      var body={food_name:currentTpl.name,protein:round1(tp),fat:round1(tf),carbs:round1(tc),calories:round1(tk),
        meal_type:currentTpl.meal_type,serving_size:round1(ts)||null,serving_unit:'g',entry_date:currentDate,
        template_id:currentTpl.id};
      if(currentEditEntryId){
        await api('/api/entries/'+currentEditEntryId,{method:'PUT',body:JSON.stringify(body)});
      }else{
        await api('/api/entries',{method:'POST',body:JSON.stringify(body)});
      }
      /* Optionally update the saved template with the modified items */
      if(tplSaveChk&&tplSaveChk.checked){
        var tplBody={
          name:currentTpl.name, meal_type:currentTpl.meal_type,
          items:currentTpl.items.map(function(i){return {
            food_name:i.food_name, saved_food_id:i.saved_food_id||null,
            protein:i.protein, fat:i.fat, carbs:i.carbs, calories:i.calories,
            serving_size:i.serving_size, serving_unit:i.serving_unit||'g',
          };}),
        };
        await api('/api/meal-templates/'+currentTpl.id,{method:'PUT',body:JSON.stringify(tplBody)});
        await loadTemplateChips(); /* refresh chips with updated item list */
      }
      showToast('"'+currentTpl.name+'" logged ('+Math.round(tk)+' kcal)','success');
      closeTplAdjustModal(); await loadPage();
    }catch(err){showToast(t('common.error')+': '+err.message,'error');}
    finally{confirmTplLog.disabled=false;}
  });

  /* ============================================================
     Copy Yesterday
     ============================================================ */
  function initCopyYesterday() {
    if (!copyYesterdayBtn) return;
    copyYesterdayBtn.addEventListener('click', handleCopyYesterdayClick);
    if (closeCopyModal) closeCopyModal.addEventListener('click', closeCopyConfirmModal);
    if (cancelCopyBtn) cancelCopyBtn.addEventListener('click', closeCopyConfirmModal);
    if (confirmCopyBtn) confirmCopyBtn.addEventListener('click', confirmCopyYesterday);
  }

  function updateCopyYesterdayVisibility() {
    if (!copyYesterdayBtn) return;
    var isToday = currentDate === formatDate(new Date());
    copyYesterdayBtn.hidden = !isToday;
  }

  async function handleCopyYesterdayClick() {
    copyYesterdayBtn.disabled = true;
    try {
      var data = await api('/api/entries/copy-yesterday', {
        method: 'POST',
        body: JSON.stringify({target_date: currentDate}),
      });
      if (!data.count || data.count === 0) {
        showToast(t('dash.copyYesterdayEmpty'), 'info');
        return;
      }
      renderCopyPreview(data.preview);
      copyConfirmModal.hidden = false;
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    } finally {
      copyYesterdayBtn.disabled = false;
    }
  }

  function renderCopyPreview(items) {
    if (!copyPreviewList) return;
    var MEAL_ORDER_LOCAL = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];
    var groups = {};
    MEAL_ORDER_LOCAL.forEach(function(m) { groups[m] = []; });
    items.forEach(function(item) {
      var key = item.meal_type in groups ? item.meal_type : 'Snack';
      groups[key].push(item);
    });
    var html = '';
    MEAL_ORDER_LOCAL.forEach(function(meal) {
      if (groups[meal].length === 0) return;
      var lbl = t(MEAL_I18N[meal]) || meal;
      html += '<li class="copy-preview-meal"><strong>' + escHtml(lbl) + '</strong><ul>';
      groups[meal].forEach(function(item) {
        html += '<li>' + escHtml(item.food_name)
          + ' <span class="copy-preview-macros">P:' + round1(item.protein)
          + 'g F:' + round1(item.fat)
          + 'g C:' + round1(item.carbs)
          + 'g ' + Math.round(item.calories || 0) + 'kcal</span></li>';
      });
      html += '</ul></li>';
    });
    copyPreviewList.innerHTML = html;
  }

  function closeCopyConfirmModal() {
    if (copyConfirmModal) copyConfirmModal.hidden = true;
  }

  async function confirmCopyYesterday() {
    confirmCopyBtn.disabled = true;
    try {
      var result = await api('/api/entries/copy-yesterday/confirm', {
        method: 'POST',
        body: JSON.stringify({target_date: currentDate}),
      });
      closeCopyConfirmModal();
      showToast(t('dash.copyYesterdayDone').replace('{n}', result.copied), 'success');
      await loadPage();
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    } finally {
      confirmCopyBtn.disabled = false;
    }
  }

  /* ============================================================
     Daily Notes
     ============================================================ */
  var _notesSaveTimer = null;
  var _notesExpanded = false;

  function initNotes() {
    if (!notesToggle) return;
    notesToggle.addEventListener('click', function() {
      _notesExpanded = !_notesExpanded;
      notesPanel.hidden = !_notesExpanded;
      notesToggle.setAttribute('aria-expanded', String(_notesExpanded));
      notesToggle.querySelector('.notes-chevron').textContent = _notesExpanded ? '▲' : '▼';
    });
    if (notesTextarea) {
      notesTextarea.addEventListener('input', function() {
        autoResizeTextarea(notesTextarea);
        if (_notesSaveTimer) clearTimeout(_notesSaveTimer);
        _notesSaveTimer = setTimeout(saveNote, 500);
      });
    }
  }

  function autoResizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  async function loadNote() {
    if (!notesSection) return;
    try {
      var data = await api('/api/notes?date=' + currentDate);
      var content = data.content || '';
      if (notesTextarea) {
        notesTextarea.value = content;
        autoResizeTextarea(notesTextarea);
      }
      /* Show preview in toggle button if there's content */
      var preview = notesSection.querySelector('.notes-preview');
      if (preview) {
        if (content) {
          preview.textContent = content.length > 60 ? content.slice(0, 60) + '…' : content;
          preview.hidden = false;
        } else {
          preview.hidden = true;
        }
      }
    } catch (_) {
      /* Notes failing silently is acceptable */
    }
  }

  async function saveNote() {
    if (!notesTextarea) return;
    var content = notesTextarea.value;
    try {
      await api('/api/notes', {
        method: 'POST',
        body: JSON.stringify({date: currentDate, content: content}),
      });
      if (notesSaveStatus) {
        notesSaveStatus.textContent = t('dash.notesSaved');
        notesSaveStatus.hidden = false;
        setTimeout(function() { notesSaveStatus.hidden = true; }, 2000);
      }
      /* Update preview */
      var preview = notesSection ? notesSection.querySelector('.notes-preview') : null;
      if (preview) {
        if (content) {
          preview.textContent = content.length > 60 ? content.slice(0, 60) + '…' : content;
          preview.hidden = false;
        } else {
          preview.hidden = true;
        }
      }
    } catch (_) { /* Silent fail — user can retry by typing again */ }
  }

  /* ============================================================
     Enhancement 1 — Remaining Macros Panel
     ============================================================ */

  var _remainingPanelExpanded = true;
  (function initRemainingPanel() {
    try { _remainingPanelExpanded = localStorage.getItem('nt_remaining_panel') !== 'collapsed'; } catch(_) {}
    var toggle = document.getElementById('remaining-panel-toggle');
    var body   = document.getElementById('remaining-panel-body');
    var chev   = document.getElementById('remaining-panel-chevron');
    if (!toggle || !body) return;

    function applyState() {
      body.hidden = !_remainingPanelExpanded;
      if (toggle) toggle.setAttribute('aria-expanded', String(_remainingPanelExpanded));
      if (chev)   chev.textContent = _remainingPanelExpanded ? '▲' : '▼';
    }
    applyState();

    toggle.addEventListener('click', function() {
      _remainingPanelExpanded = !_remainingPanelExpanded;
      try { localStorage.setItem('nt_remaining_panel', _remainingPanelExpanded ? 'expanded' : 'collapsed'); } catch(_) {}
      applyState();
    });
    toggle.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle.click(); }
    });
  })();

  var _MACRO_SUGGESTIONS = {
    protein: {
      en: 'eggs, chicken breast, Greek yogurt, cottage cheese, tuna',
      tr: 'yumurta, tavuk göğsü, Yunan yoğurdu, lor peyniri, ton balığı',
    },
    fat: {
      en: 'avocado, nuts, olive oil, cheese, salmon',
      tr: 'avokado, fındık, zeytinyağı, peynir, somon',
    },
    carbs: {
      en: 'oats, brown rice, banana, whole grain bread, sweet potato',
      tr: 'yulaf, esmer pirinç, muz, tam tahıllı ekmek, tatlı patates',
    },
    calories: {
      en: 'a balanced meal with protein and complex carbs',
      tr: 'protein ve kompleks karbonhidrat içeren dengeli bir öğün',
    },
  };

  function renderRemainingPanel(data) {
    var rowsEl = document.getElementById('remaining-macro-rows');
    var suggEl = document.getElementById('remaining-suggestions');
    if (!rowsEl) return;

    var isTr = Lang && Lang.isTr && Lang.isTr();
    var lang  = isTr ? 'tr' : 'en';

    var MACROS = [
      { key: 'protein',  unit: 'g',    labelKey: 'remaining.protein'  },
      { key: 'fat',      unit: 'g',    labelKey: 'remaining.fat'      },
      { key: 'carbs',    unit: 'g',    labelKey: 'remaining.carbs'    },
      { key: 'calories', unit: 'kcal', labelKey: 'remaining.calories' },
    ];

    var html = '';
    var bestMacro = null;
    var bestRatio  = -Infinity;

    MACROS.forEach(function(m) {
      var consumed  = data.totals   ? (data.totals[m.key]   || 0) : 0;
      var target    = data.target   ? (data.target[m.key]   || 0) : 0;
      var remaining = data.remaining? (data.remaining[m.key]|| 0) : 0;
      var over      = target > 0 && consumed > target;
      var pct       = target > 0 ? Math.min(100, Math.round((consumed / target) * 100)) : 0;
      var remRound  = Math.abs(Math.round(remaining));
      var remText   = (over ? '+' : '') + remRound + ' ' + m.unit;
      var valueClass = over ? 'over' : 'good';

      /* Track which macro has most room (for suggestion) */
      if (!over && target > 0) {
        var ratio = remaining / target;
        if (ratio > bestRatio) { bestRatio = ratio; bestMacro = m.key; }
      }

      html += '<div class="remaining-macro-row">'
        + '<span class="remaining-label">' + escHtml(t(m.labelKey)) + '</span>'
        + '<div class="remaining-bar" role="progressbar" aria-valuenow="' + pct + '" aria-valuemin="0" aria-valuemax="100">'
        + '<div class="remaining-bar-fill' + (over ? ' over' : '') + '" style="width:' + pct + '%"></div>'
        + '</div>'
        + '<span class="remaining-value ' + valueClass + '">' + escHtml(remText) + '</span>'
        + '</div>';
    });

    rowsEl.innerHTML = html;

    /* Suggestions */
    if (suggEl) {
      var suggText = '';
      if (!bestMacro) {
        suggText = isTr ? 'Tüm hedeflerinize ulaştınız! Harika iş!' : 'You\'ve hit all your targets! Great job!';
      } else {
        var remVal  = Math.round(Math.abs((data.remaining && data.remaining[bestMacro]) || 0));
        var unit    = bestMacro === 'calories' ? ' kcal' : 'g';
        var mLabel  = t('remaining.' + bestMacro).toLowerCase().replace(isTr ? ' kaldı' : ' remaining', '');
        var foods   = _MACRO_SUGGESTIONS[bestMacro][lang];
        if (isTr) {
          suggText = 'Yaklaşık ~' + remVal + unit + ' daha ' + mLabel + ' alabilirsiniz. Önerilenler: ' + foods;
        } else {
          suggText = 'You have room for ~' + remVal + unit + ' more ' + mLabel + '. Consider: ' + foods;
        }
      }
      suggEl.innerHTML = '<strong>' + escHtml(t('remaining.suggestions')) + '</strong>' + escHtml(suggText);
      suggEl.hidden = false;
    }
  }

  /* ============================================================
     Enhancement 3 — Daily Insight Button
     ============================================================ */
  (function initInsight() {
    var insightBtn    = document.getElementById('insight-btn');
    var insightResult = document.getElementById('insight-result');
    if (!insightBtn || !insightResult) return;

    insightBtn.addEventListener('click', async function() {
      var apiKey = '';
      try { apiKey = localStorage.getItem('nt_gemini_key') || ''; } catch(_) {}

      if (!apiKey) {
        insightResult.textContent = t('insight.noKey');
        insightResult.className = 'insight-result no-key';
        insightResult.hidden = false;
        return;
      }

      /* Gather today's summary data from the DOM */
      var consumed = {
        protein:  parseFloat((document.getElementById('summary-protein')  || {}).textContent) || 0,
        fat:      parseFloat((document.getElementById('summary-fat')      || {}).textContent) || 0,
        carbs:    parseFloat((document.getElementById('summary-carbs')    || {}).textContent) || 0,
        calories: parseFloat((document.getElementById('summary-calories') || {}).textContent) || 0,
      };
      var targets = {
        protein:  parseFloat((document.getElementById('target-protein')   || {}).textContent) || 0,
        fat:      parseFloat((document.getElementById('target-fat')       || {}).textContent) || 0,
        carbs:    parseFloat((document.getElementById('target-carbs')     || {}).textContent) || 0,
        calories: parseFloat((document.getElementById('target-calories')  || {}).textContent) || 0,
      };

      var content = 'Today I ate: ' + consumed.protein + 'g protein, '
        + consumed.fat + 'g fat, ' + consumed.carbs + 'g carbs, '
        + consumed.calories + ' kcal. My targets are: '
        + targets.protein + 'g protein, ' + targets.fat + 'g fat, '
        + targets.carbs + 'g carbs, ' + targets.calories + ' kcal. '
        + 'Give me a brief 2-3 sentence analysis of my day and one practical suggestion.';

      insightBtn.disabled = true;
      insightResult.textContent = t('insight.loading');
      insightResult.className = 'insight-result loading';
      insightResult.hidden = false;

      try {
        var isTr = Lang && Lang.isTr && Lang.isTr();
        var resp = await api('/api/chat', {
          method: 'POST',
          body: JSON.stringify({
            messages: [{ role: 'user', content: content }],
            lang: isTr ? 'tr' : 'en',
            api_key: apiKey,
          }),
        });
        insightResult.textContent = resp.reply || '';
        insightResult.className = 'insight-result';
      } catch (err) {
        insightResult.textContent = t('common.error') + ': ' + err.message;
        insightResult.className = 'insight-result error';
      } finally {
        insightBtn.disabled = false;
      }
    });
  })();

  function escHtml(str){
    return String(str??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function round1(n){return Math.round((n??0)*10)/10;}

  /* ============================================================
     Water Tracker
     ============================================================ */
  var waterGoal = 2000;
  var waterLogs = [];

  async function loadWater() {
    try {
      var data = await api('/api/water?date=' + currentDate);
      waterGoal = data.goal_ml || 2000;
      waterLogs = data.logs || [];
      renderWater(data.total_ml || 0);
    } catch (_) { /* non-fatal */ }
  }

  function renderWater(totalMl) {
    var totalEl = document.getElementById('water-total');
    var goalEl  = document.getElementById('water-goal');
    var barEl   = document.getElementById('water-bar');
    var logsRow = document.getElementById('water-logs-row');
    if (!totalEl) return;

    totalEl.textContent = Math.round(totalMl);
    if (goalEl) goalEl.textContent = waterGoal;

    var pct = waterGoal > 0 ? Math.min(100, Math.round((totalMl / waterGoal) * 100)) : 0;
    if (barEl) {
      barEl.style.width = pct + '%';
      if (barEl.parentElement) barEl.parentElement.setAttribute('aria-valuenow', pct);
    }
    var ringEl = document.getElementById('water-ring-fill');
    if (ringEl) {
      ringEl.style.strokeDasharray = DROP_RING_LEN;
      ringEl.style.strokeDashoffset = DROP_RING_LEN * (1 - pct / 100);
    }
    /* drop spans y=12..50 in the SVG; park the wave below the tip when empty */
    var levelEl = document.getElementById('water-level');
    if (levelEl) levelEl.style.transform = 'translateY(' + (pct > 0 ? 50 - 38 * pct / 100 : 54) + 'px)';
    var dropEl = document.getElementById('water-drop');
    if (dropEl) dropEl.setAttribute('aria-label', t('dash.water') + ': ' + Math.round(totalMl) + ' / ' + waterGoal + ' ml (' + pct + '%)');

    if (logsRow) {
      if (waterLogs.length === 0) {
        logsRow.innerHTML = '';
      } else {
        logsRow.innerHTML = waterLogs.map(function (log) {
          var time = log.logged_at ? new Date(log.logged_at + 'Z').toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '';
          return '<span class="water-log-chip">'
            + Math.round(log.amount_ml) + ' ml'
            + (time ? ' <span style="opacity:.6">' + time + '</span>' : '')
            + '<button class="water-log-chip__del" data-water-id="' + log.id + '" title="' + t('common.delete') + '">&times;</button>'
            + '</span>';
        }).join('');
      }
    }
  }

  async function addWater(ml) {
    try {
      await api('/api/water', {method:'POST', body: JSON.stringify({date: currentDate, amount_ml: ml})});
      await loadWater();
      showToast('+' + Math.round(ml) + ' ml ' + t('water.added'), 'success');
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    }
  }

  async function deleteWater(id) {
    try {
      await api('/api/water/' + id, {method:'DELETE'});
      await loadWater();
    } catch (err) {
      showToast(t('common.error') + ': ' + err.message, 'error');
    }
  }

  /* Quick-add buttons */
  var waterBtnsEl = document.getElementById('water-btns');
  if (waterBtnsEl) {
    waterBtnsEl.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-ml]');
      if (btn) { addWater(parseFloat(btn.dataset.ml)); return; }

      if (e.target.id === 'water-custom-toggle') {
        var row = document.getElementById('water-custom-row');
        if (row) row.classList.toggle('hidden');
        var inp = document.getElementById('water-custom-input');
        if (inp && !document.getElementById('water-custom-row').classList.contains('hidden')) inp.focus();
      }
    });
  }

  var waterCustomAdd = document.getElementById('water-custom-add');
  if (waterCustomAdd) {
    waterCustomAdd.addEventListener('click', function () {
      var inp = document.getElementById('water-custom-input');
      var ml = inp ? parseFloat(inp.value) : NaN;
      if (!ml || ml <= 0) { showToast(t('water.invalidAmount'), 'error'); return; }
      addWater(ml);
      if (inp) inp.value = '';
      var row = document.getElementById('water-custom-row');
      if (row) row.classList.add('hidden');
    });
  }

  var waterCustomInput = document.getElementById('water-custom-input');
  if (waterCustomInput) {
    waterCustomInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); if (waterCustomAdd) waterCustomAdd.click(); }
    });
  }

  /* Delete individual log entries */
  var waterLogsRow = document.getElementById('water-logs-row');
  if (waterLogsRow) {
    waterLogsRow.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-water-id]');
      if (btn) deleteWater(btn.dataset.waterId);
    });
  }

  /* Extend loadPage to also refresh water */
  var _origLoadPage = loadPage;
  loadPage = async function () {
    await _origLoadPage();
    await loadWater();
  };
  /* ============================================================
   Today's Plan - inline slot cards, adaptable per-item logging
   ============================================================ */

  var dashPlanFulfilled = {};   // slot_id -> true
  var dashSlotItems = [];       // [{foodId,foodName,p100,f100,c100,k100,qty,unit}]
  var dashFulfillModal = document.getElementById('dash-fulfill-modal');
  var dashSlotCurrentId = null;

  function loadTodayPlan() {
    var todayStr = formatDate(new Date());
    var sec = document.getElementById('today-plan-section');
    if (currentDate !== todayStr) { if (sec) sec.hidden = true; return; }
    api('/api/plans/my-assignment/rich').then(function (data) {
      if (!data || !data.assignment) { if (sec) sec.hidden = true; return; }
      var todayDay = (data.days || []).find(function (d) { return d.is_today; });
      if (!todayDay || !(todayDay.slots || []).length) { if (sec) sec.hidden = true; return; }
      dashPlanFulfilled = {};
      (data.today_fulfillments || []).forEach(function (f) { dashPlanFulfilled[f.slot_id] = true; });
      if (sec) sec.hidden = false;
      renderTodayPlanSlots(todayDay.slots);
    }).catch(function () { if (sec) sec.hidden = true; });
  }

  function renderTodayPlanSlots(slots) {
    var container = document.getElementById('today-plan-slots');
    if (!container) return;
    container.innerHTML = slots.map(function (s) {
      var done = !!dashPlanFulfilled[s.id];
      var hint = (s.items || []).slice(0, 2).map(function (it) {
        return escHtml(it.food_name_override || (it.saved_food && it.saved_food.name) || '');
      }).filter(Boolean).join(' · ');
      return '<div class="today-slot-card' + (done ? ' today-slot-card--done' : '') + '">' +
        '<div class="today-slot-info">' +
          '<strong class="today-slot-name">' + (done ? '&#10003; ' : '') + escHtml(s.slot_name) + '</strong>' +
          (hint ? '<span class="today-slot-items">' + hint + '</span>' : '') +
        '</div>' +
        '<button class="btn btn-sm ' + (done ? 'btn-outline' : 'btn-primary') + ' dash-slot-log" ' +
          'data-slot-json="' + encodeURIComponent(JSON.stringify(s)) + '">' +
          (done ? 'Change' : 'Log') +
        '</button>' +
      '</div>';
    }).join('');
    container.querySelectorAll('.dash-slot-log').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openDashFulfillModal(JSON.parse(decodeURIComponent(btn.dataset.slotJson)));
      });
    });
  }

  /* ---- Slot fulfillment modal ------------------------------------------- */

  function openDashFulfillModal(slot) {
    if (!dashFulfillModal) return;
    dashSlotCurrentId = slot.id;
    document.getElementById('dash-sf-slot-id').value = slot.id;
    document.getElementById('dash-sf-title').textContent = slot.slot_name;
    document.getElementById('dash-sf-desc').textContent =
      (slot.content_pattern ? 'Pattern ' + slot.content_pattern + (slot.is_optional ? ' · Optional' : ' · Required') : (slot.is_optional ? 'Optional' : ''));

    // Build rows from slot template items; empty row if none
    dashSlotItems = [];
    var items = slot.items || [];
    if (items.length) {
      items.forEach(function (it) {
        var sf = it.saved_food || {};
        // For free-text items (no saved_food), fall back to dietitian-entered macros on the slot item.
        // Use explicit null check — protein/fat/carbs can legitimately be 0 (e.g. sugar, water).
        var p100 = sf.protein  != null ? parseFloat(sf.protein)  : (parseFloat(it.protein)  || 0);
        var f100 = sf.fat      != null ? parseFloat(sf.fat)      : (parseFloat(it.fat)      || 0);
        var c100 = sf.carbs    != null ? parseFloat(sf.carbs)    : (parseFloat(it.carbs)    || 0);
        var k100 = sf.calories != null ? parseFloat(sf.calories) : (parseFloat(it.calories) || (p100*4 + f100*9 + c100*4) || 0);
        dashSlotItems.push({
          foodId:     it.saved_food_id || null,
          foodName:   it.food_name_override || sf.name || '',
          p100:       p100,
          f100:       f100,
          c100:       c100,
          k100:       k100,
          qty:        parseFloat(it.quantity) || 100,
          unit:       it.unit || 'g',
          validUnits: sf.valid_units ? JSON.parse(sf.valid_units) : null,
        });
      });
    } else {
      dashSlotItems.push(blankItem());
    }

    renderSlotLogRows();

    // Auto-select meal type based on time of day
    var hour = new Date().getHours();
    var autoMeal = hour < 10 ? 'Breakfast' : hour < 14 ? 'Lunch' : hour < 19 ? 'Dinner' : 'Snack';
    var mealTypeSel = document.getElementById('dash-sf-meal-type');
    if (mealTypeSel) mealTypeSel.value = autoMeal;

    dashFulfillModal.showModal();
  }

  function blankItem() {
    return { foodId: null, foodName: '', p100: 0, f100: 0, c100: 0, k100: 0, qty: 100, unit: 'g', validUnits: null };
  }

  function slotItemMacros(it) {
    var scale = (parseFloat(it.qty) || 0) / 100;
    return {
      p: Math.round(it.p100 * scale * 10) / 10,
      f: Math.round(it.f100 * scale * 10) / 10,
      c: Math.round(it.c100 * scale * 10) / 10,
      k: Math.round(it.k100 * scale),
    };
  }

  function macroLabel(m) {
    return 'P\u2009' + m.p + 'g\u2009·\u2009F\u2009' + m.f + 'g\u2009·\u2009C\u2009' + m.c + 'g\u2009·\u2009' + m.k + '\u2009kcal';
  }

  function renderSlotLogRows() {
    var container = document.getElementById('dash-sf-items');
    if (!container) return;
    container.innerHTML = '';
    dashSlotItems.forEach(function (item, idx) {
      container.appendChild(buildSlotRow(item, idx));
    });
    recalcSlotTotals();
  }

  function buildSlotRow(item, idx) {
    var m = slotItemMacros(item);
    var div = document.createElement('div');
    div.className = 'slot-log-row';
    div.dataset.idx = idx;

    var ALL_UNITS = ['g','ml','piece','slice','serving','tbsp','tsp','cup','oz'];
    var allowedUnits = (item.validUnits && item.validUnits.length) ? item.validUnits : ALL_UNITS;
    var unitOpts = allowedUnits.map(function(u) {
      return '<option' + (u === item.unit ? ' selected' : '') + '>' + escHtml(u) + '</option>';
    }).join('');

    div.innerHTML =
      '<div class="slot-log-food">' +
        '<button type="button" class="slot-log-food-name btn btn-ghost" title="Click to change food">' +
          escHtml(item.foodName || '— select food') + '</button>' +
        '<div class="slot-log-search-wrap" hidden style="position:relative;flex:1">' +
          '<input type="text" class="form-control form-control--sm slot-log-search" placeholder="Search food\u2026" autocomplete="off" />' +
          '<ul class="autocomplete-list slot-log-ac" role="listbox" hidden></ul>' +
        '</div>' +
      '</div>' +
      '<div class="slot-log-qty-wrap">' +
        '<input type="number" class="form-control form-control--sm slot-log-qty" value="' + escHtml(String(item.qty)) + '" min="0" step="0.1" style="width:62px" />' +
        '<select class="form-control form-control--sm slot-log-unit" style="width:72px">' + unitOpts + '</select>' +
      '</div>' +
      '<span class="slot-log-macros">' + macroLabel(m) + '</span>' +
      '<button type="button" class="btn btn-icon slot-log-del" title="Remove" style="flex-shrink:0">&times;</button>';

    var foodNameBtn = div.querySelector('.slot-log-food-name');
    var searchWrap  = div.querySelector('.slot-log-search-wrap');
    var searchInput = div.querySelector('.slot-log-search');
    var acList      = div.querySelector('.slot-log-ac');

    function showSearch() {
      foodNameBtn.hidden = true;
      searchWrap.hidden = false;
      searchInput.value = dashSlotItems[idx].foodName || '';
      searchInput.focus();
    }
    function hideSearch() {
      searchWrap.hidden = true;
      foodNameBtn.hidden = false;
      acList.hidden = true;
    }

    foodNameBtn.addEventListener('click', showSearch);

    var srTimer;
    searchInput.addEventListener('input', function () {
      clearTimeout(srTimer);
      var q = this.value.trim();
      if (q.length < 2) { acList.hidden = true; return; }
      srTimer = setTimeout(function () {
        api('/api/foods?q=' + encodeURIComponent(q) + '&limit=12').then(function (foods) {
          acList.innerHTML = '';
          foods.forEach(function (fd) {
            var li = document.createElement('li');
            li.role = 'option';
            li.textContent = fd.name;
            li.addEventListener('mousedown', function (e) {
              e.preventDefault();
              dashSlotItems[idx].foodId   = fd.id;
              dashSlotItems[idx].foodName = fd.name;
              dashSlotItems[idx].p100 = parseFloat(fd.protein) || 0;
              dashSlotItems[idx].f100 = parseFloat(fd.fat)     || 0;
              dashSlotItems[idx].c100 = parseFloat(fd.carbs)   || 0;
              dashSlotItems[idx].k100 = parseFloat(fd.calories) || (fd.protein*4+fd.fat*9+fd.carbs*4) || 0;
              dashSlotItems[idx].qty  = parseFloat(div.querySelector('.slot-log-qty').value) || 100;
              // Update valid_units on the item and refresh the unit dropdown
              var vu = null;
              try { vu = fd.valid_units ? JSON.parse(fd.valid_units) : null; } catch(e) {}
              dashSlotItems[idx].validUnits = vu;
              var unitSel = div.querySelector('.slot-log-unit');
              var ALL_UNITS_SEL = ['g','ml','piece','slice','serving','tbsp','tsp','cup','oz'];
              var allowed = (vu && vu.length) ? vu : ALL_UNITS_SEL;
              var curUnit = unitSel.value;
              unitSel.innerHTML = allowed.map(function(u) {
                return '<option' + (u === curUnit ? ' selected' : '') + '>' + escHtml(u) + '</option>';
              }).join('');
              if (!allowed.includes(curUnit)) unitSel.value = allowed[0];
              dashSlotItems[idx].unit = unitSel.value;
              hideSearch();
              foodNameBtn.textContent = fd.name;
              updateRowMacros(div, idx);
              recalcSlotTotals();
            });
            acList.appendChild(li);
          });
          acList.hidden = !foods.length;
        });
      }, 220);
    });
    searchInput.addEventListener('blur', function () { setTimeout(hideSearch, 200); });

    div.querySelector('.slot-log-qty').addEventListener('input', function () {
      dashSlotItems[idx].qty = parseFloat(this.value) || 0;
      updateRowMacros(div, idx);
      recalcSlotTotals();
    });
    div.querySelector('.slot-log-unit').addEventListener('change', function () {
      dashSlotItems[idx].unit = this.value;
      updateRowMacros(div, idx);
      recalcSlotTotals();
    });
    div.querySelector('.slot-log-del').addEventListener('click', function () {
      dashSlotItems.splice(idx, 1);
      renderSlotLogRows();
    });

    return div;
  }

  function updateRowMacros(div, idx) {
    var m = slotItemMacros(dashSlotItems[idx]);
    var el = div.querySelector('.slot-log-macros');
    if (el) el.textContent = macroLabel(m);
  }

  function recalcSlotTotals() {
    var totals = { p: 0, f: 0, c: 0, k: 0 };
    dashSlotItems.forEach(function (it) {
      var m = slotItemMacros(it);
      totals.p += m.p; totals.f += m.f; totals.c += m.c; totals.k += m.k;
    });
    var el = document.getElementById('dash-sf-totals');
    if (el) el.innerHTML = '<strong>Total: </strong>' + macroLabel({
      p: Math.round(totals.p*10)/10, f: Math.round(totals.f*10)/10,
      c: Math.round(totals.c*10)/10, k: Math.round(totals.k),
    });
  }

  /* ---- Modal wire-up ------------------------------------------------------- */

  if (dashFulfillModal) {
    document.getElementById('dash-sf-cancel').addEventListener('click',  function () { dashFulfillModal.close(); });
    document.getElementById('dash-sf-cancel2').addEventListener('click', function () { dashFulfillModal.close(); });

    document.getElementById('dash-sf-add').addEventListener('click', function () {
      dashSlotItems.push(blankItem());
      renderSlotLogRows();
      var rows = document.querySelectorAll('#dash-sf-items .slot-log-row');
      var last = rows[rows.length - 1];
      if (last) last.querySelector('.slot-log-food-name').click();
    });

    document.getElementById('dash-fulfill-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var slotId = parseInt(document.getElementById('dash-sf-slot-id').value, 10);
      var valid  = dashSlotItems.filter(function (it) { return it.foodName || it.foodId; });
      if (!valid.length) { showToast('Add at least one food', 'error'); return; }

      var submitBtn = document.getElementById('dash-sf-submit');
      if (submitBtn) submitBtn.disabled = true;

      // Create one FoodEntry per item so macros count toward daily totals
      var promises = valid.map(function (it) {
        var m = slotItemMacros(it);
        return api('/api/entries', {
          method: 'POST',
          body: JSON.stringify({
            food_name:    it.foodName || 'Plan food',
            protein:      m.p,
            fat:          m.f,
            carbs:        m.c,
            calories:     m.k,
            serving_size: it.qty,
            serving_unit: it.unit,
            meal_type:    (document.getElementById('dash-sf-meal-type') || {}).value || 'plan',
            date:         currentDate,
            saved_food_id: it.foodId || null,
          }),
        });
      });

      Promise.all(promises)
        .then(function () {
          return api('/api/plans/fulfill-slot', {
            method: 'POST',
            body: JSON.stringify({
              slot_id: slotId,
              date: currentDate,
              saved_food_id: valid[0].foodId || null,
            }),
          });
        })
        .then(function () {
          dashFulfillModal.close();
          showToast('Slot logged!', 'success');
          return loadPage();
        })
        .then(function () { loadTodayPlan(); })
        .catch(function (err) { showToast(err.message, 'error'); })
        .finally(function () { if (submitBtn) submitBtn.disabled = false; });
    });
  }

  /* ---- Hook into loadPage so plan slots refresh with the page -------------- */
  var _origLoadPage2 = loadPage;
  loadPage = async function () {
    await _origLoadPage2();
    loadTodayPlan();
  };

  init();
  loadWater();
  loadTodayPlan();

})();
