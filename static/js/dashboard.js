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
      if (remEl) { remEl.textContent = over ? '+' + Math.abs(remaining) : remaining; remEl.classList.toggle('over-target', over); }
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
    var lbl=document.getElementById('donut-center-label'); if(lbl) lbl.textContent=Math.round(data.totals?.calories??0)+' kcal';
    var ctx=document.getElementById('macro-donut'); if(!ctx) return;
    var pK=p*4,fK=f*9,cK=c*4,tot=pK+fK+cK;
    var pP=tot>0?Math.round(pK/tot*100):0, fP=tot>0?Math.round(fK/tot*100):0, cP=tot>0?100-pP-fP:0;
    var hasData=p+f+c>0;
    if(donutChart) donutChart.destroy();
    donutChart=new Chart(ctx,{type:'doughnut',data:{
      labels:hasData?[t('macro.protein')+' '+p+'g ('+pP+'%)',t('macro.fat')+' '+f+'g ('+fP+'%)',t('macro.carbs')+' '+c+'g ('+cP+'%)']:['No data'],
      datasets:[{data:hasData?[pK,fK,cK]:[1],backgroundColor:hasData?['#4A90D9','#E8913A','#5CB85C']:['#e2e8f0'],borderWidth:2,borderColor:'#fff'}]
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
      return '<button class="quick-add-chip" data-food=\''+JSON.stringify(r).replace(/'/g,"&#39;")+'\'>'+escHtml(r.food_name)+'</button>';
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

  function escHtml(str){
    return String(str??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function round1(n){return Math.round((n??0)*10)/10;}

  init();
})();
