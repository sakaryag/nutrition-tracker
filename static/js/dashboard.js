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
  async function loadPage() {
    updateDateHeading();
    await Promise.all([loadSummary(), loadEntries()]);
    updateCopyYesterdayVisibility();
    loadNote();
  }
  async function loadSummary() {
    try { var data = await api('/api/summary?date=' + currentDate); renderSummary(data); renderDonut(data); }
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

  var donutChart = null;
  function renderDonut(data) {
    var p=Math.round(data.totals?.protein??0), f=Math.round(data.totals?.fat??0), c=Math.round(data.totals?.carbs??0);
    var consumed=Math.round(data.totals?.calories??0);
    var targetCal=Math.round(data.target?.calories??0);
    var lbl=document.getElementById('donut-center-label');
    if(lbl){lbl.innerHTML=consumed+'<br><span style="font-size:0.7rem;font-weight:400;color:#718096">/ '+targetCal+' kcal</span>';}
    var ctx=document.getElementById('macro-donut'); if(!ctx) return;
    var pK=p*4,fK=f*9,cK=c*4,tot=pK+fK+cK;
    var pP=tot>0?Math.round(pK/tot*100):0, fP=tot>0?Math.round(fK/tot*100):0, cP=tot>0?100-pP-fP:0;
    var hasData=p+f+c>0;
    if(donutChart) donutChart.destroy();
    donutChart=new Chart(ctx,{type:'doughnut',data:{
      labels:hasData?[t('macro.protein')+' '+p+'g ('+pP+'%)',t('macro.fat')+' '+f+'g ('+fP+'%)',t('macro.carbs')+' '+c+'g ('+cP+'%)']:['No data'],
      datasets:[{data:hasData?[pK,fK,cK]:[1],backgroundColor:hasData?['#4A90D9','#E8913A','#5CB85C']:['#e2e8f0'],borderWidth:2,borderColor:'#fff',hoverBorderColor:'#fff'}]
    },options:{responsive:false,cutout:'65%',plugins:{legend:{position:'bottom',labels:{boxWidth:12,padding:10,font:{size:12}}},tooltip:{enabled:hasData}}}});
  }

  async function loadEntries() {
    try { var entries=await api('/api/entries?date='+currentDate); renderEntries(entries); }
    catch(err){ showToast(t('common.error')+': '+err.message,'error'); }
  }
  var MEAL_ORDER=['Breakfast','Lunch','Dinner','Snack'];
  var MEAL_I18N={Breakfast:'entry.breakfast',Lunch:'entry.lunch',Dinner:'entry.dinner',Snack:'entry.snack'};

  function renderEntries(entries) {
    if(!entries||entries.length===0){entriesList.innerHTML='<p class="empty-msg">'+escHtml(t('dash.noEntries'))+'</p>';return;}
    var groups={};MEAL_ORDER.forEach(function(m){groups[m]=[];});
    entries.forEach(function(e){var k=e.meal_type in groups?e.meal_type:'Snack';groups[k].push(e);});
    var html='';
    MEAL_ORDER.forEach(function(meal){
      if(groups[meal].length===0) return;
      var lbl=t(MEAL_I18N[meal])||meal;
      html+='<div class="meal-group" data-meal="'+escHtml(meal)+'">'
        +'<div class="meal-group__header"><p class="meal-group__title">'+escHtml(lbl)+'</p>'
        +'<div class="meal-group__actions">'
        +'<button class="btn btn-icon btn-sm" data-action="add-to-meal" data-meal="'+escHtml(meal)+'">+</button>'
        +'<button class="btn-ghost meal-clear-btn" data-action="clear-meal" data-meal="'+escHtml(meal)+'">&times; Clear</button>'
        +'</div></div>';
      groups[meal].forEach(function(e){html+=renderEntryCard(e);});
      html+='</div>';
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
    modalTitle.textContent=entry?t('entry.editEntry'):t('entry.addFood');
    entryForm.reset();
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
    } else if(pendingMealType){
      document.getElementById('entry-meal-type').value=pendingMealType;
    }
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
    manualMacroEdit=false; updateUnitHint();
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
    items.forEach(function(li,i){li.classList.toggle('focused',i===idx);});
  });
  document.addEventListener('click',function(e){
    if(!e.target.closest('.autocomplete-wrap')) autocompleteList.hidden=true;
  });

  function renderAutocomplete(foods){
    if(!foods||foods.length===0){autocompleteList.hidden=true;return;}
    autocompleteList.innerHTML=foods.slice(0,10).map(function(f){
      var brand=f.brand?' <span class="ac-sub">'+escHtml(f.brand)+'</span>':'';
      var macros='<span class="ac-sub">P:'+round1(f.protein)+'g F:'+round1(f.fat)+'g C:'+round1(f.carbs)+'g</span>';
      return '<li role="option" tabindex="-1" data-food=\''+JSON.stringify(f).replace(/'/g,"&#39;")+'\'>'+escHtml(Lang.foodName(f))+brand+' '+macros+'</li>';
    }).join('');
    autocompleteList.hidden=false;
  }
  autocompleteList.addEventListener('click',function(e){
    var li=e.target.closest('li'); if(!li) return;
    try{
      var food=JSON.parse(li.dataset.food); selectedFood=food; manualMacroEdit=false;
      foodNameInput.value=food.name;
      document.getElementById('entry-saved-food-id').value=food.id??'';
      document.getElementById('entry-protein').value=food.protein??'';
      document.getElementById('entry-fat').value=food.fat??'';
      document.getElementById('entry-carbs').value=food.carbs??'';
      document.getElementById('entry-calories').value=food.calories?Math.round(food.calories):'';
      document.getElementById('entry-serving-size').value=food.default_serving??'';
      foodGPerUnit=food.g_per_unit||null;
      var baseUnit=food.serving_unit||'g';
      populateUnitSelect(unitSelect,baseUnit,foodGPerUnit,baseUnit,food.valid_units||null);
      autocompleteList.hidden=true; updateUnitHint();
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

  entryForm.addEventListener('submit',async function(e){
    e.preventDefault();
    var protein=parseFloat(document.getElementById('entry-protein').value);
    var fat=parseFloat(document.getElementById('entry-fat').value);
    var carbs=parseFloat(document.getElementById('entry-carbs').value);
    var calRaw=document.getElementById('entry-calories').value;
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
    if (barEl) barEl.style.width = pct + '%';

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
        dashSlotItems.push({
          foodId:   it.saved_food_id || null,
          foodName: it.food_name_override || sf.name || '',
          p100: parseFloat(sf.protein) || 0,
          f100: parseFloat(sf.fat)     || 0,
          c100: parseFloat(sf.carbs)   || 0,
          k100: parseFloat(sf.calories) || (sf.protein*4 + sf.fat*9 + sf.carbs*4) || 0,
          qty:  parseFloat(it.quantity) || 100,
          unit: it.unit || 'g',
        });
      });
    } else {
      dashSlotItems.push(blankItem());
    }

    renderSlotLogRows();
    dashFulfillModal.showModal();
  }

  function blankItem() {
    return { foodId: null, foodName: '', p100: 0, f100: 0, c100: 0, k100: 0, qty: 100, unit: 'g' };
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

    var unitOpts = ['g','ml','piece','slice','serving'].map(function(u) {
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
              dashSlotItems[idx].unit = div.querySelector('.slot-log-unit').value;
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
            meal_type:    'plan',
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