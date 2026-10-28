'use strict';
const $ = id => document.getElementById(id);
const DAYS = ['Hënë', 'Martë', 'Mërkurë', 'Enjte', 'Premte', 'Shtunë', 'Diel'];
const TITLES = {
  overview: ['Java shkollore, në ekuilibër.', 'Përgatit të dhënat hap pas hapi dhe krijo orarin e shkollës.', 'Përmbledhja'],
  teachers: ['Njerëzit pas çdo ore.', 'Menaxho profesorët dhe disponueshmërinë e tyre pa shkruar kode ose lista.', 'Profesorët'],
  catalog: ['Një vend për klasat dhe lëndët.', 'Organizo bazën e shkollës. Pastaj zgjidhi me një klikim në ngarkesën javore.', 'Klasat & lëndët'],
  lessons: ['Çdo lëndë, në klasën e duhur.', 'Lidh profesorët me klasat dhe përcakto saktë orët mësimore për javën.', 'Ngarkesa mësimore'],
  schedule: ['Nga të dhënat te java e plotë.', 'Gjenero, kontrollo dhe shiko orarin nga këndvështrimi që të duhet.', 'Orari javor']
};
let state = {days: 5, periods: 6, teachers: [], classes: [], subjects: [], lessons: []};
let result = null, snapshot = null, mode = 'classroom', editingTeacher = -1, editingLesson = -1;
let editingClassRule='', draftBlocks = new Set(), revision = 0, busy = false, confirmation = null;
const el = (tag, text, cls) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node; };
const action = (label, handler, cls = 'secondary') => {const node = el('button', label, cls); node.type = 'button'; node.onclick = handler; return node;};
function tell(message, error = false) { $('notice').hidden = false; $('notice').textContent = message; $('notice').className = error ? 'error' : ''; }
function ask(title, description, handler) {
  $('confirm-title').textContent = title; $('confirm-description').textContent = description;
  confirmation = handler; $('confirm-dialog').showModal(); $('confirm-cancel').focus();
}
$('confirm-cancel').onclick = () => $('confirm-dialog').close();
$('confirm-yes').onclick = () => { $('confirm-dialog').close(); if (confirmation) confirmation(); confirmation = null; };
function navigate(tab) {
  if (!TITLES[tab]) tab = 'overview';
  document.querySelectorAll('[data-panel]').forEach(n => n.hidden = n.dataset.panel !== tab);
  document.querySelectorAll('[data-tab]').forEach(n => {n.classList.toggle('active', n.dataset.tab === tab); if(n.dataset.tab===tab)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});
  const [title, description, crumb] = TITLES[tab]; $('page-title').textContent = title; $('page-description').textContent = description; $('breadcrumb').textContent = crumb;
  history.replaceState(null, '', '#' + tab);
}
document.querySelectorAll('[data-tab]').forEach(n => n.onclick = () => navigate(n.dataset.tab));
function persist() {
  try { localStorage.setItem('orari-v2', JSON.stringify(state)); }
  catch { tell('Shfletuesi nuk po lejon ruajtjen lokale. Mbaje këtë faqe hapur që të mos humbasësh të dhënat.', true); }
}
function changed(message) {
  revision++; result = null; snapshot = null;
  $('schedule').replaceChildren(); $('schedule-empty').hidden = false; $('csv').disabled = true; $('print').disabled = true;setExports(false);
  $('solve-status').replaceChildren(); $('view-select').replaceChildren();
  persist(); refresh(); if(message) tell(message);
}
function selectOptions(id, values, placeholder) {
  const select = $(id), previous = select.value; select.replaceChildren();
  if (placeholder) {const o = el('option', placeholder); o.value = ''; select.append(o);}
  values.forEach(value => {const o = el('option', value); o.value = value; select.append(o);});
  if(values.includes(previous)) select.value = previous;
}
function refresh() {
  $('source-note').hidden=!state.sourceNote;$('source-note').textContent=state.sourceNote||'';
  $('nav-teachers').textContent = state.teachers.length; $('nav-lessons').textContent = state.lessons.length;
  $('days').value = state.days; $('periods').value = state.periods;
  $('preferred-friday').value=state.preferredFriday??'';$('min-daily').value=state.minDaily??0;$('max-daily').value=state.maxDaily??'';$('max-subject').value=state.maxSubject??'';
  $('week-capacity').textContent = `${state.days * state.periods} termine në javë për çdo klasë.`;
  const total = state.lessons.reduce((n, l) => n + l.hours, 0);
  $('stats').replaceChildren();
  [['Profesorë',state.teachers.length,'♙'],['Klasa',state.classes.length,'▤'],['Lëndë',state.subjects.length,'▧'],['Orë në javë',total,'◷']].forEach(([label,value,icon]) => {
    const box = el('div', undefined, 'stat'), text = el('div'); text.append(el('span',label,'stat-label'),el('strong',value)); box.append(text,el('span',icon,'stat-icon')); $('stats').append(box);
  });
  $('checklist').replaceChildren();
  [[state.teachers.length>0,'Regjistro profesorët',`${state.teachers.length} profesorë të regjistruar`,'teachers'],[state.classes.length>0&&state.subjects.length>0,'Shto klasat dhe lëndët',`${state.classes.length} klasa · ${state.subjects.length} lëndë`,'catalog'],[state.lessons.length>0,'Përcakto ngarkesën javore',`${state.lessons.length} angazhime · ${total} orë mësimi`,'lessons'],[!!result,'Gjenero orarin','Pa përplasje, me kontroll të pavarur','schedule']].forEach(([done,title,description,tab],i) => {
    const row=el('div',undefined,'check-step'), text=el('div'); text.append(el('strong',title),el('p',description));row.append(el('span',done?'✓':String(i+1),'step-number'+(done?' done':'')),text,action(done?'Shiko':'Vazhdo',()=>navigate(tab)));$('checklist').append(row);
  });
  renderTeachers(); renderCatalog('class'); renderCatalog('subject');
  selectOptions('lesson-class',state.classes,'Zgjidh klasën'); selectOptions('lesson-subject',state.subjects,'Zgjidh lëndën'); selectOptions('lesson-teacher',state.teachers.map(t=>t.name),'Zgjidh profesorin');
  selectOptions('lesson-filter',state.classes,'Të gjitha klasat');
  const missing = !state.classes.length || !state.subjects.length || !state.teachers.length;
  $('lesson-prerequisites').hidden = !missing; $('save-lesson').disabled = missing;
  $('generate').disabled = !state.lessons.length || busy;
  renderLessons();
}
function renderTeachers() {
  const list=$('teacher-list');list.replaceChildren();
  const query=$('teacher-search').value.trim().toLocaleLowerCase();
  state.teachers.forEach((teacher,i)=>{
    if(!teacher.name.toLocaleLowerCase().includes(query))return;
    const card=el('article',undefined,'teacher-card'),info=el('div',undefined,'teacher-info'),text=el('div');
    const hours=state.lessons.filter(l=>l.teacher===teacher.name).reduce((s,l)=>s+l.hours,0);
    text.append(el('strong',teacher.name),el('small',`${hours}${teacher.maxHours!=null?' / '+teacher.maxHours:''} orë / javë`));
    if(teacher.maxHours!=null&&hours>teacher.maxHours)text.append(el('small','Tejkalohet maksimumi javor','form-error'));
    info.append(el('span',teacher.name.split(/\s+/).slice(0,2).map(n=>n[0]).join('').toUpperCase(),'avatar'),text);
    card.append(info,el('div',teacher.blocked.length?`${teacher.blocked.length} termine të bllokuara`:'I disponueshëm gjatë gjithë javës','teacher-meta'));
    const actions=el('div',undefined,'teacher-actions');actions.append(action('Disponueshmëria / Ndrysho',()=>openTeacher(i)),action('Fshi',()=>removeTeacher(i),'delete-button'));card.append(actions);list.append(card);
  });
  if(!list.children.length){const empty=el('div',undefined,'empty');empty.append(el('h3',state.teachers.length?'Nuk u gjet asnjë profesor.':'Shto profesorin e parë.'),el('p',state.teachers.length?'Provo një emër tjetër.':'Mjafton emri. Disponueshmërinë e cakton me klikim.'));list.append(empty);}
}
$('teacher-search').oninput=renderTeachers;
function openTeacher(i=-1) {
  editingTeacher=i; const teacher=state.teachers[i];$('teacher-form').reset();$('teacher-name').value=teacher?.name||'';draftBlocks=new Set(teacher?.blocked||[]);
  $('teacher-max-hours').value=teacher?.maxHours??'';
  $('working-days').replaceChildren();
  for(let d=0;d<state.days;d++){
    const label=el('label'),check=el('input');check.type='checkbox';check.value=d;
    check.checked=Array.from({length:state.periods},(_,p)=>`${d}:${p}`).some(k=>!draftBlocks.has(k));
    label.append(check,el('span',DAYS[d]));$('working-days').append(label);
  }
  const periods=Array.from({length:state.periods},(_,p)=>String(p+1));
  selectOptions('available-from',periods);selectOptions('available-to',periods);
  $('available-from').value='1';$('available-to').value=String(state.periods);
  $('teacher-dialog-title').textContent=i<0?'Shto profesor':'Ndrysho profesorin';$('teacher-error').textContent='';renderAvailability();$('teacher-dialog').showModal();$('teacher-name').focus();
}
$('new-teacher').onclick=()=>openTeacher();
['close-teacher','cancel-teacher'].forEach(id=>$(id).onclick=()=>$('teacher-dialog').close());
function renderAvailability() {
  const table=el('table',undefined,'availability-table'),head=table.createTHead().insertRow();head.append(el('th','Ora'));
  for(let d=0;d<state.days;d++){
    const cell=el('th'),button=action(DAYS[d],()=>{const all=Array.from({length:state.periods},(_,p)=>`${d}:${p}`);const blocked=all.every(k=>draftBlocks.has(k));all.forEach(k=>blocked?draftBlocks.delete(k):draftBlocks.add(k));renderAvailability();},'');button.setAttribute('aria-label',`Blloko ose liro ditën ${DAYS[d]}`);cell.append(button);head.append(cell);
  }
  const body=table.createTBody();
  for(let p=0;p<state.periods;p++){
    const row=body.insertRow();const th=el('th',p+1);th.scope='row';row.append(th);
    for(let d=0;d<state.days;d++){
      const key=`${d}:${p}`,blocked=draftBlocks.has(key),cell=row.insertCell();
      const button=action(blocked?'×':'✓',()=>{if(draftBlocks.has(key))draftBlocks.delete(key);else draftBlocks.add(key);renderAvailability();const target=$('availability').querySelector(`[data-slot="${key}"]`);target?.focus();},'slot'+(blocked?' blocked':''));
      button.dataset.slot=key;button.setAttribute('aria-pressed',String(blocked));button.setAttribute('aria-label',`${DAYS[d]}, ora ${p+1}: ${blocked?'i bllokuar':'i disponueshëm'}`);cell.append(button);
    }
  }
  $('availability').replaceChildren(table);
}
$('clear-blocks').onclick=()=>{draftBlocks.clear();renderAvailability();};
$('apply-availability').onclick=()=>{
  const from=Number($('available-from').value)-1,to=Number($('available-to').value)-1;
  if(from>to){$('teacher-error').textContent='Ora e fillimit duhet të jetë para ose e barabartë me orën e fundit.';return;}
  const days=new Set([...$('working-days').querySelectorAll('input:checked')].map(n=>Number(n.value)));
  draftBlocks.clear();
  for(let d=0;d<state.days;d++)for(let p=0;p<state.periods;p++)if(!days.has(d)||p<from||p>to)draftBlocks.add(`${d}:${p}`);
  $('teacher-error').textContent='';renderAvailability();
};
$('teacher-form').onsubmit=e=>{
  e.preventDefault();const name=$('teacher-name').value.trim();
  if(!name){$('teacher-error').textContent='Shkruaj emrin e profesorit.';return;}
  if(state.teachers.some((t,i)=>i!==editingTeacher&&t.name.toLocaleLowerCase()===name.toLocaleLowerCase())){$('teacher-error').textContent='Një profesor me këtë emër ekziston tashmë.';return;}
  const raw=$('teacher-max-hours').value,maxHours=raw===''?null:Number(raw);
  if(maxHours!==null&&(!Number.isInteger(maxHours)||maxHours<0||maxHours>84)){$('teacher-error').textContent='Maksimumi javor duhet të jetë numër i plotë nga 0 deri në 84.';return;}
  const teacher={name,blocked:[...draftBlocks],maxHours};
  if(editingTeacher<0)state.teachers.push(teacher);else{const old=state.teachers[editingTeacher].name;state.teachers[editingTeacher]=teacher;state.lessons.forEach(l=>{if(l.teacher===old)l.teacher=name;});}
  $('teacher-dialog').close();changed('Profesori u ruajt. Disponueshmëria do të respektohet gjatë gjenerimit.');
};
function removeTeacher(i){const teacher=state.teachers[i],count=state.lessons.filter(l=>l.teacher===teacher.name).length;if(count){tell(`${teacher.name} ka ${count} angazhime. Ndrysho ose fshiji ato te Ngarkesa mësimore para se ta fshish profesorin.`,true);return;}ask('Të fshihet profesori?',teacher.name,()=>{state.teachers.splice(i,1);changed('Profesori u fshi.');});}
function renderCatalog(kind){
  const isClass=kind==='class',values=isClass?state.classes:state.subjects,root=$(kind+'-list');root.replaceChildren();
  values.forEach((name,i)=>{
    const row=el('div',undefined,'catalog-item'),text=el('div');const hours=state.lessons.filter(l=>l[isClass?'classroom':'subject']===name).reduce((s,l)=>s+l.hours,0);text.append(el('strong',name),el('small',`${hours} orë të planifikuara / javë`));
    const controls=el('div');if(isClass){const rule=(state.classRules||[]).find(r=>r.classroom===name);text.append(el('small',`Ditore: ${rule?.min_daily_hours??state.minDaily??0}–${rule?.max_daily_hours??state.maxDaily??state.periods} orë`));controls.append(action('Rregullat',()=>openClassRule(name)));}controls.append(action('Ndrysho',()=>{
      const input=$(kind+'-name');input.value=name;input.dataset.edit=i;$(kind+'-form').querySelector('button').textContent='Ruaj';input.focus();
    }),action('Fshi',()=>{
      if(hours){tell('Ky element përdoret në ngarkesën mësimore. Ndrysho ose fshiji angazhimet përkatëse së pari.',true);return;}
      ask('Të fshihet ky element?',name,()=>{values.splice(i,1);if(isClass)state.classRules=(state.classRules||[]).filter(r=>r.classroom!==name);resetCatalogForm(kind);changed('Elementi u fshi.');});
    },'delete-button'));row.append(text,controls);root.append(row);
  });
  if(!values.length)root.append(el('div',isClass?'Ende nuk ke shtuar klasa.':'Ende nuk ke shtuar lëndë.','empty'));
}
function resetCatalogForm(kind){const input=$(kind+'-name');input.value='';delete input.dataset.edit;$(kind+'-form').querySelector('button').textContent=kind==='class'?'Shto klasë':'Shto lëndë';}
for(const kind of ['class','subject'])$(kind+'-form').onsubmit=e=>{
  e.preventDefault();const input=$(kind+'-name'),name=input.value.trim(),values=kind==='class'?state.classes:state.subjects,index=input.dataset.edit===undefined?-1:Number(input.dataset.edit);
  if(!name)return;
  if(values.some((n,i)=>i!==index&&n.toLocaleLowerCase()===name.toLocaleLowerCase())){tell('Ky emër ekziston tashmë.',true);return;}
  if(index<0)values.push(name);else{const old=values[index];values[index]=name;if(kind==='class')(state.classRules||[]).forEach(r=>{if(r.classroom===old)r.classroom=name;});state.lessons.forEach(l=>{const field=kind==='class'?'classroom':'subject';if(l[field]===old)l[field]=name;});}
  resetCatalogForm(kind);changed(kind==='class'?'Klasa u ruajt.':'Lënda u ruajt.');input.focus();
};
function openClassRule(name){
  editingClassRule=name;const rule=(state.classRules||[]).find(r=>r.classroom===name);
  $('class-rule-title').textContent='Rregullat · '+name;$('class-rule-error').textContent='';
  $('class-min-daily').value=rule?.min_daily_hours??'';$('class-max-daily').value=rule?.max_daily_hours??'';
  $('class-rule-dialog').showModal();
}
$('cancel-class-rule').onclick=()=>$('class-rule-dialog').close();
$('class-rule-form').onsubmit=e=>{
  e.preventDefault();const low=$('class-min-daily').value===''?null:Number($('class-min-daily').value),high=$('class-max-daily').value===''?null:Number($('class-max-daily').value);
  if((low??state.minDaily??0)>(high??state.maxDaily??state.periods)||(high??state.maxDaily??state.periods)>state.periods){$('class-rule-error').textContent='Kufij të pavlefshëm: minimumi duhet të jetë jo më i madh se maksimumi, brenda orëve të ditës.';return;}
  state.classRules=(state.classRules||[]).filter(r=>r.classroom!==editingClassRule);
  if(low!==null||high!==null)state.classRules.push({classroom:editingClassRule,min_daily_hours:low,max_daily_hours:high});
  $('class-rule-dialog').close();changed('Rregullat e klasës u ruajtën.');
};
function resetLesson(){editingLesson=-1;$('lesson-form').reset();$('lesson-hours').value=4;$('save-lesson').textContent='+ Shto angazhimin';$('cancel-lesson').hidden=true;}
$('cancel-lesson').onclick=resetLesson;
$('lesson-form').onsubmit=e=>{
  e.preventDefault();
  const lesson={classroom:$('lesson-class').value,subject:$('lesson-subject').value,teacher:$('lesson-teacher').value,hours:Number($('lesson-hours').value),room:$('lesson-room').value.trim(),max_per_day:$('lesson-max-day').value===''?null:Number($('lesson-max-day').value),double_periods:Number($('lesson-doubles').value||0)};
  if(!state.classes.includes(lesson.classroom)||!state.subjects.includes(lesson.subject)||!state.teachers.some(t=>t.name===lesson.teacher)||!Number.isInteger(lesson.hours)||lesson.hours<1||lesson.hours>40){tell('Zgjidh klasën, lëndën, profesorin dhe numrin e orëve nga 1 deri në 40.',true);return;}
  if(lesson.double_periods*2>lesson.hours){tell('Blloqet dyshe kërkojnë më shumë orë se ngarkesa javore.',true);return;}
  if(state.lessons.some((l,i)=>i!==editingLesson&&l.classroom===lesson.classroom&&l.subject===lesson.subject&&l.teacher===lesson.teacher&&l.room===lesson.room)){tell('Ky angazhim ekziston tashmë. Përdor “Ndrysho” për t’ia përditësuar orët.',true);return;}
  if(editingLesson<0)state.lessons.push(lesson);else state.lessons[editingLesson]=lesson;
  resetLesson();changed('Ngarkesa mësimore u ruajt.');
};
function renderLessons(){
  const root=$('lesson-list'),filter=$('lesson-filter').value;root.replaceChildren();$('lesson-count').textContent=state.lessons.length;
  state.lessons.forEach((l,i)=>{if(filter&&l.classroom!==filter)return;const row=el('tr');[l.classroom,l.subject,l.teacher,`${l.hours}${l.double_periods?' · '+l.double_periods+' dyshe':''}${l.max_per_day?' · max '+l.max_per_day+'/ditë':''}`,l.room||'—'].forEach(text=>row.append(el('td',text)));const cell=el('td');cell.append(action('Ndrysho',()=>{
    editingLesson=i;$('lesson-class').value=l.classroom;$('lesson-subject').value=l.subject;$('lesson-teacher').value=l.teacher;$('lesson-hours').value=l.hours;$('lesson-room').value=l.room;$('lesson-max-day').value=l.max_per_day??'';$('lesson-doubles').value=l.double_periods??0;$('save-lesson').textContent='Ruaj ndryshimin';$('cancel-lesson').hidden=false;$('lesson-class').focus();
  }),action('Fshi',()=>ask('Të fshihet angazhimi?',`${l.classroom} · ${l.subject} · ${l.hours} orë`,()=>{state.lessons.splice(i,1);resetLesson();changed('Angazhimi u fshi.');}),'delete-button'));row.append(cell);root.append(row);});
  $('lesson-empty').hidden=!!root.children.length;$('lesson-empty').textContent=state.lessons.length?'Nuk ka angazhime për këtë klasë.':'Ende nuk ke angazhime. Plotëso formularin më sipër për ta shtuar të parin.';
  $('load-summary').replaceChildren();state.classes.forEach(name=>{const hours=state.lessons.filter(l=>l.classroom===name).reduce((s,l)=>s+l.hours,0),capacity=state.days*state.periods;const chip=el('span',`${name}: ${hours} / ${capacity} orë`,'load-chip'+(hours>capacity?' over':''));$('load-summary').append(chip);});
}
$('lesson-filter').onchange=renderLessons;
$('week-form').onsubmit=e=>{
  e.preventDefault();const days=Number($('days').value),periods=Number($('periods').value);
  if(!Number.isInteger(days)||days<1||days>7||!Number.isInteger(periods)||periods<1||periods>12)return;
  const preferredFriday=$('preferred-friday').value===''?null:Number($('preferred-friday').value);
  if(preferredFriday!==null&&(days<5||preferredFriday>periods)){tell('Preferenca e së premtes kërkon të paktën 5 ditë dhe orë brenda ditës shkollore. Ndryshoje ose lëre bosh.',true);return;}
  const minDaily=Number($('min-daily').value),maxDaily=$('max-daily').value===''?null:Number($('max-daily').value),maxSubject=$('max-subject').value===''?null:Number($('max-subject').value);
  if(minDaily>(maxDaily??periods)||(maxDaily??periods)>periods){tell('Kufijtë ditorë duhet të jenë brenda orëve të ditës, me minimumin jo më të madh se maksimumi.',true);return;}
  for(const rule of state.classRules||[]){const low=rule.min_daily_hours??minDaily,high=rule.max_daily_hours??maxDaily??periods;if(low>high||high>periods){tell(`Rregullat e klasës ${rule.classroom} nuk përputhen me javën e re. Ndryshoji te Klasat.`,true);return;}}
  const discarded=state.teachers.reduce((n,t)=>n+t.blocked.filter(k=>{const[d,p]=k.split(':').map(Number);return d>=days||p>=periods;}).length,0);
  const apply=()=>{state.days=days;state.periods=periods;state.preferredFriday=preferredFriday;state.minDaily=minDaily;state.maxDaily=maxDaily;state.maxSubject=maxSubject;state.teachers.forEach(t=>t.blocked=t.blocked.filter(k=>{const[d,p]=k.split(':').map(Number);return d<days&&p<periods;}));changed('Java shkollore u përditësua. Gjenero përsëri orarin me këto termine.');};
  if(discarded)ask('Të ndryshohet java?',`${discarded} bllokime të disponueshmërisë bien jashtë javës së re dhe do të hiqen.`,apply);else apply();
};
function payload(){return {schoolName:state.schoolName||'',scheduleTitle:state.scheduleTitle||'',preferred_friday_hours:state.preferredFriday??null,min_daily_hours:state.minDaily??0,max_daily_hours:state.maxDaily??null,max_subject_per_day:state.maxSubject??null,classes:[...state.classes],class_rules:state.classRules||[],days:state.days,periods:state.periods,teachers:state.teachers.map(t=>({name:t.name,max_hours:t.maxHours??null,unavailable:t.blocked.map(k=>{const[d,p]=k.split(':').map(Number);return d*state.periods+p;})})),lessons:structuredClone(state.lessons),time_limit:10};}
function solveStatus(message,kind=''){const box=el('div',message,'status-box'+(kind?' '+kind:''));$('solve-status').replaceChildren(box);}
$('generate').onclick=async()=>{
  if(busy||!state.lessons.length)return;busy=true;const requestRevision=revision,request=payload(),requestClasses=[...state.classes];
  $('generate').disabled=true;$('generate').textContent='Duke gjeneruar…';document.body.classList.add('busy');
  result=null;snapshot=null;$('schedule').replaceChildren();$('schedule-empty').hidden=true;$('csv').disabled=true;$('print').disabled=true;setExports(false);
  solveStatus('Duke kërkuar një orar pa përplasje…\nPo kontrollohen disponueshmëria dhe shpërndarja e lëndëve.','pending');
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),45000);
  try{
    const response=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),signal:controller.signal});
    if(!response.ok){let data;try{data=await response.json();}catch{}throw Error(Array.isArray(data?.detail)?data.detail.map(d=>d.msg.replace(/^Value error, /,'')).join('\n'):'Gjenerimi dështoi. Provo përsëri pas pak.');}
    const data=await response.json();
    if(revision!==requestRevision){solveStatus('Të dhënat ndryshuan gjatë gjenerimit. Gjenero përsëri me ndryshimet e reja.','error');return;}
    if(!data.verified){solveStatus((data.status==='infeasible'?'Nuk ekziston orar me këto kufizime.':'Nuk u gjet zgjidhje brenda kohës së caktuar.')+'\n'+(data.issues||[]).join('\n'),'error');$('schedule-empty').hidden=false;return;}
    result=data;snapshot={...request,classes:requestClasses};solveStatus(`✓ Orar i verifikuar · ${data.entries.length} orë mësimi\n${data.status==='optimal'?'U provua rezultati më i mirë për preferencat e caktuara.':'U gjet zgjidhje e vlefshme; optimaliteti nuk u provua.'} Përsëritje lënde brenda ditës: ${data.penalty}.${request.preferred_friday_hours!=null?'\nE premte — synimi '+request.preferred_friday_hours+' orë/klasë: '+Object.entries(data.friday_loads||{}).map(([c,n])=>c+': '+n).join(' · ')+(data.friday_deviation===0?' ✓':' (preferenca nuk u plotësua plotësisht në këtë rezultat)'):''}`);
    $('csv').disabled=false;$('print').disabled=false;setExports(true);updateViews();refresh();
  }catch(error){solveStatus(error.name==='AbortError'?'Kërkesa zgjati shumë. Shërbimi mund të jetë duke u zgjuar; provo përsëri.':error.message,'error');$('schedule-empty').hidden=false;}
  finally{clearTimeout(timeout);busy=false;document.body.classList.remove('busy');$('generate').textContent='Gjenero orarin →';$('generate').disabled=!state.lessons.length;}
};
function updateViews(){
  const all=mode==='all';
  $('view-select').hidden=all;
  $('all-content-control').hidden=!all;
  if(!snapshot)return;
  if(!all)selectOptions('view-select',[...new Set(snapshot.lessons.map(l=>l[mode]).filter(Boolean))]);
  renderSchedule();
}
document.querySelectorAll('[data-mode]').forEach(button=>button.onclick=()=>{mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(n=>{n.classList.toggle('selected',n===button);n.setAttribute('aria-pressed',String(n===button));});updateViews();});
$('view-select').onchange=renderSchedule;
$('all-content').onchange=renderSchedule;
function renderSchedule(){
  if(!result||!snapshot)return;
  $('schedule').replaceChildren();$('schedule-empty').hidden=true;
  if(mode==='all'){renderAllClasses();return;}
  const value=$('view-select').value;if(!value){$('schedule').append(el('div','Nuk ka salla të caktuara në këtë orar.','empty'));return;}
  const table=el('table',undefined,'schedule-table');table.append(el('caption',`Orari javor · ${value}`,'sr-only'));const head=table.createTHead().insertRow();['Ora',...DAYS.slice(0,snapshot.days)].forEach(text=>{const th=el('th',text);th.scope='col';head.append(th);});const body=table.createTBody();
  const subjects=[...new Set(snapshot.lessons.map(l=>l.subject))];
  for(let p=0;p<snapshot.periods;p++){
    const row=body.insertRow();row.insertCell().textContent=String(p+1).padStart(2,'0');
    for(let d=0;d<snapshot.days;d++){
      const cell=row.insertCell(),entry=result.entries.find(e=>e.slot===d*snapshot.periods+p&&snapshot.lessons[e.lesson][mode]===value);
      if(!entry){cell.append(el('span','—','free-cell'));continue;}
      const lesson=snapshot.lessons[entry.lesson],block=el('div',undefined,'lesson-block tone-'+(subjects.indexOf(lesson.subject)%4));block.append(el('strong',lesson.subject));
      block.append(el('small',mode==='classroom'?lesson.teacher:lesson.classroom));if(mode==='room')block.append(el('small',lesson.teacher));else if(lesson.room)block.append(el('small',lesson.room));cell.append(block);
    }
  }
  $('schedule').append(table);
}
function renderAllClasses(){
  const root=el('div',undefined,'all-classes-view');
  if(snapshot.schoolName)root.append(el('h2',snapshot.schoolName,'all-classes-title'));
  root.append(el('h2',snapshot.scheduleTitle||'Orari javor · Të gjitha klasat','all-classes-title'));
  const classes=snapshot.classes||[...new Set(snapshot.lessons.map(l=>l.classroom))];
  root.style.setProperty('--class-columns',classes.length);
  const content=$('all-content').value;
  // Index the verified result once; changing views never regenerates the timetable.
  const entries=new Map(result.entries.map(e=>[`${e.slot}:${snapshot.lessons[e.lesson].classroom}`,snapshot.lessons[e.lesson]]));
  for(let day=0;day<snapshot.days;day++){
    const section=el('section',undefined,'all-day'),heading=el('h3','E '+DAYS[day].toLocaleUpperCase('sq'),'all-day-heading');
    section.append(heading);
    const table=el('table',undefined,'all-classes-table');table.style.setProperty('--class-columns',classes.length);
    table.append(el('caption',`${DAYS[day]} · të gjitha klasat`,'sr-only'));
    const head=table.createTHead().insertRow();
    ['Ora',...classes].forEach(name=>{const th=el('th',name);th.scope='col';head.append(th);});
    const body=table.createTBody();
    for(let period=0;period<snapshot.periods;period++){
      const row=body.insertRow(),hour=el('th',period+1);hour.scope='row';row.append(hour);
      for(const classroom of classes){
        const cell=row.insertCell(),lesson=entries.get(`${day*snapshot.periods+period}:${classroom}`);
        if(!lesson){cell.append(el('span','—','all-free'));continue;}
        const main=content==='subject'?lesson.subject:lesson.teacher.startsWith('Pa caktuar · ')?lesson.subject:lesson.teacher;
        cell.append(el('strong',main));
        if(content==='both')cell.append(el('small',lesson.subject));
        cell.title=`${classroom} · ${lesson.subject} · ${lesson.teacher}${lesson.room?' · '+lesson.room:''}`;
        cell.dataset.classroom=classroom;cell.dataset.slot=day*snapshot.periods+period;
      }
    }
    section.append(table);root.append(section);
  }
  $('schedule').append(root);
}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type})),link=el('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('csv').onclick=()=>{
  if(!result||!snapshot)return;
  const quote=value=>{let text=String(value);if(/^[\s]*[=+\-@]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
  const rows=[['Dita','Ora','Klasa','Lënda','Profesori','Salla'],...[...result.entries].sort((a,b)=>a.slot-b.slot).map(e=>{const l=snapshot.lessons[e.lesson];return[DAYS[Math.floor(e.slot/snapshot.periods)],e.slot%snapshot.periods+1,l.classroom,l.subject,l.teacher,l.room];})];
  download('orari-javor.csv','\ufeff'+rows.map(row=>row.map(quote).join(',')).join('\r\n'),'text/csv;charset=utf-8');
};
$('print').onclick=()=>window.print();
function setExports(enabled){for(const format of ['xlsx','docx','pdf'])$(format).disabled=!enabled;}
for(const format of ['xlsx','docx','pdf'])$(format).onclick=async()=>{
  if(!result||!snapshot)return;
  const button=$(format);button.disabled=true;
  const data={school:snapshot,entries:result.entries,classes:snapshot.classes||[],school_name:snapshot.schoolName||'',title:snapshot.scheduleTitle||'',mode,content:$('all-content').value,value:$('view-select').value};
  try{
    const response=await fetch('/api/export/'+format,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    if(!response.ok){const error=await response.json();throw Error(typeof error.detail==='string'?error.detail:'Eksporti dështoi. Kontrollo orarin dhe provo përsëri.');}
    download('orari-javor.'+format,await response.blob(),response.headers.get('content-type'));
    tell('Dokumenti '+format.toUpperCase()+' u shkarkua për pamjen e zgjedhur.');
  }catch(error){tell(error.message,true);}finally{button.disabled=!result;}
};
async function loadPhotoExample(){
  const button=$('photo-example');button.disabled=true;
  try{
    const response=await fetch('/api/examples/photo');if(!response.ok)throw Error('Shembulli nuk u ngarkua. Provo përsëri.');
    const data=await response.json();state={...data.state,sourceNote:data.note};
    resetLesson();resetCatalogForm('class');resetCatalogForm('subject');changed(data.note);
    snapshot={...payload(),classes:[...state.classes]};result={entries:data.entries,verified:data.verified,status:'reference'};
    mode='all';document.querySelectorAll('[data-mode]').forEach(n=>{n.classList.toggle('selected',n.dataset.mode==='all');n.setAttribute('aria-pressed',String(n.dataset.mode==='all'));});
    $('csv').disabled=false;$('print').disabled=false;setExports(true);updateViews();refresh();navigate('schedule');
    solveStatus('✓ Transkriptimi nga fotoja u kontrollua: '+data.entries.length+' orë, pa përplasje.\nKy është orari burimor. Ndrysho kërkesat te Profesorët ose Ngarkesa mësimore dhe shtyp “Gjenero orarin” për një zgjidhje të re.');
  }catch(error){tell(error.message,true);}finally{button.disabled=false;}
}
$('photo-example').onclick=()=>{
  if(state.teachers.length||state.classes.length||state.subjects.length||state.lessons.length)ask('Të ngarkohet shembulli nga fotoja?','Të dhënat aktuale do të zëvendësohen me 6 klasat dhe ngarkesën nga fotoja. Ndryshimet aktuale në këtë pajisje do të humbasin.',loadPhotoExample);
  else loadPhotoExample();
};

function loadExample(){
  state={days:5,periods:6,teachers:[{name:'Arta Krasniqi',blocked:['0:0','0:1']},{name:'Blerim Hoxha',blocked:[]},{name:'Drita Gashi',blocked:['4:5']}],classes:['VI-1','VI-2'],subjects:['Matematikë','Gjuhë shqipe','Biologji'],lessons:[]};
  for(const classroom of state.classes)for(const[subject,teacher,hours,room]of[['Matematikë','Arta Krasniqi',4,''],['Gjuhë shqipe','Blerim Hoxha',5,''],['Biologji','Drita Gashi',2,'Laboratori']])state.lessons.push({classroom,subject,teacher,hours,room});
  resetLesson();resetCatalogForm('class');resetCatalogForm('subject');changed('Shembulli u ngarkua: 2 klasa, 3 profesorë dhe 22 orë. Shtyp “Gjenero orarin” për ta provuar.');navigate('schedule');
}
$('example').onclick=()=>{if(state.teachers.length||state.classes.length||state.subjects.length||state.lessons.length)ask('Të ngarkohet shembulli?', 'Të dhënat aktuale në këtë pajisje do të zëvendësohen me shembullin. Ky veprim nuk mund të kthehet.',loadExample);else loadExample();};
function restore(){
  try{
    const saved=JSON.parse(localStorage.getItem('orari-v2'));
    if(saved&&Array.isArray(saved.teachers)&&Array.isArray(saved.classes)&&Array.isArray(saved.subjects)&&Array.isArray(saved.lessons)&&Number.isInteger(saved.days)&&saved.days>=1&&saved.days<=7&&Number.isInteger(saved.periods)&&saved.periods>=1&&saved.periods<=12){state=saved;return;}
    const old=JSON.parse(localStorage.getItem('orari-v1'));
    if(!old)return;
    const days=Number(old.days),periods=Number(old.periods);
    if(!Number.isInteger(days)||days<1||days>7||!Number.isInteger(periods)||periods<1||periods>12)return;
    const teachers=String(old.teachers||'').split('\n').filter(s=>s.trim()).map(line=>{const[name,blocked='']=line.split('|');return{name:name.trim(),blocked:blocked.split(',').map(k=>k.trim().split(':').map(Number)).filter(([d,p])=>Number.isInteger(d)&&Number.isInteger(p)&&d>=1&&d<=days&&p>=1&&p<=periods).map(([d,p])=>`${d-1}:${p-1}`)};});
    const lessons=Array.isArray(old.lessons)?old.lessons:[];
    for(const l of lessons)if(!teachers.some(t=>t.name===l.teacher))teachers.push({name:l.teacher,blocked:[]});
    state={days,periods,teachers,classes:[...new Set(lessons.map(l=>l.classroom))],subjects:[...new Set(lessons.map(l=>l.subject))],lessons};persist();tell('Të dhënat nga versioni i parë u bartën në formularët e rinj.');
  }catch{tell('Të dhënat e ruajtura nuk u lexuan. Mund të fillosh me formularët ose me shembullin.',true);}
}
restore();refresh();navigate(location.hash.slice(1));
