// Career forms retain local drafts while the dashboard polls other views.
let careerData = null, careerDraft = null, careerMode = null, careerBusy = false, careerError = '';
const careerBasicFields = ['Name', 'Phone', 'Email', 'Current Location', 'Additional Information'];
const careerRecordFields = {work:['Company','Position','Start Date','End Date'],education:['School','Degree','Major','Start Date','End Date'],project:['Project Name'],other:[]};
const careerHelp = {
  work: 'Include company, position and dates. What did you mainly work on? What responsibilities did you have? What problems did you solve? What happened as a result? What technologies did you use?',
  project: 'What was this project about? What exactly did you do? What technologies did you use? What problems did you solve? What was the result?',
  education: 'Include school, degree, major and dates. Anything else worth mentioning: research, thesis, courses, awards or academic projects?',
  other: 'Describe skills, languages, certifications, research, publications, awards or other useful facts.'
};
function careerPaint(){
  if ((location.hash || '').split('/')[0] !== '#career') return;
  document.getElementById('view').innerHTML = VIEWS.career();
  stampSlots(document.getElementById('view'));
}
async function careerLoad(){
  try { const r = await fetch('/api/career'); careerData = await r.json(); careerError = ''; }
  catch(e){ careerError = e.message; }
  careerPaint();
}
function careerStart(mode){
  careerMode = mode;
  const p = careerData && careerData.profile;
  careerDraft = JSON.parse(JSON.stringify(mode === 'review' ? p.normalized :
    (p ? p.raw : {basic:{},records:[{type:'work',text:''}]})));
  editing = true; careerPaint();
}
function careerAdd(){ careerDraft.records.push({type:'project',text:''}); careerPaint(); }
function careerRemove(i){ careerDraft.records.splice(i,1); careerPaint(); }
function careerDetail(i,key,value){
  careerDraft.records[i].fields = careerDraft.records[i].fields || {};
  careerDraft.records[i].fields[key] = value;
}
function careerField(i,key,value){
  if (i === -1) careerDraft.basic[key] = value;
  else careerDraft.records[i][key] = key === 'skills' ? value.split(',').map(x=>x.trim()).filter(Boolean) : value;
}
async function careerRun(action){
  if (careerBusy) return;
  careerBusy = true; careerError = ''; careerPaint();
  try {
    if(action === 'normalize' && careerMode === 'onboarding'){
      const saved = await fetch('/api/career',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({action:'save_onboarding',raw:careerDraft})});
      const result = await saved.json();
      if(result.error) throw new Error(result.error);
      careerData = result; careerDraft = JSON.parse(JSON.stringify(result.profile.raw));
    }
    const payload = {action};
    if(action === 'save_onboarding') payload.raw = careerDraft;
    if(action === 'save_profile' || action === 'confirm') payload.profile = careerDraft;
    const r = await fetch('/api/career',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result = await r.json();
    if(result.error) throw new Error(result.error);
    careerData = result;
    if(action === 'save_onboarding'){
      careerDraft = JSON.parse(JSON.stringify(result.profile.raw));
      careerMode = 'onboarding';
    } else if(action === 'normalize' || action === 'save_profile'){
      careerMode = 'review'; careerDraft = JSON.parse(JSON.stringify(result.profile.normalized));
    } else if(action === 'confirm'){ careerMode = null; careerDraft = null; }
  } catch(e){ careerError = e.message; }
  careerBusy = false; careerPaint();
}
function careerInput(label,value,handler,large=false){
  const field = large ? `<textarea oninput="${handler}">${esc(value || '')}</textarea>` :
    `<input value="${esc(value || '')}" oninput="${handler}">`;
  return `<label class="career-field">${esc(label)}${field}</label>`;
}
VIEWS.career = function(){
  editing = true;
  if(!careerData && careerError) return uiNotice('failed',esc(careerError),uiButton('Retry',{onclick:'careerLoad()'}));
  if(!careerData){ if(!careerBusy){careerBusy=true; careerLoad().finally(()=>{careerBusy=false; careerPaint();});} return uiNotice('note', 'Loading your Career workspace.'); }
  const p = careerData.profile;
  if(!careerMode && (!p || !p.confirmed)){
    careerMode = p && p.normalized ? 'review' : 'onboarding';
    careerDraft = JSON.parse(JSON.stringify(p ? (p.normalized || p.raw) : {basic:{},records:[{type:'work',text:''}]}));
  }
  const status = (careerError ? uiNotice('failed',esc(careerError)) : '') +
    (careerBusy ? uiNotice('note','Your Career Agent is working. Please wait.') : '');
  const button = (text,action)=>uiButton(text,{onclick:`careerRun('${action}')`,attrs:careerBusy?'disabled':''});
  if(!careerMode){
    return status + uiCard(`<p>Your Career Profile is confirmed. ${careerData.evidence.length} career records are available.</p>` +
      uiButton('View / Edit Profile',{onclick:"careerStart('review')"}) +
      uiButton('Edit Original Information',{level:'secondary',onclick:"careerStart('onboarding')"}),{title:'Career Agent'}) +
      uiNotice('note','Job analysis will be available after Day 2.');
  }
  let body = '<p>You do not need to write like a resume. Describe what you actually did. AI organizes your wording; it must not invent facts or metrics.</p>';
  if(careerMode === 'onboarding'){
    body += careerBasicFields.map(k=>careerInput(k,careerDraft.basic[k],`careerField(-1,'${k}',this.value)`)).join('');
    body += careerDraft.records.map((r,i)=>uiCard(
      `<label class="career-field">Record type<select onchange="careerField(${i},'type',this.value);careerPaint()">`+
      Object.keys(careerHelp).map(t=>`<option value="${t}" ${r.type===t?'selected':''}>${esc(t)}</option>`).join('')+'</select></label>'+
      careerRecordFields[r.type].map(k=>careerInput(k,(r.fields || {})[k],`careerDetail(${i},'${k}',this.value)`)).join('')+
      `<p>${esc(careerHelp[r.type])}</p>`+careerInput('Tell your Career Agent',r.text,`careerField(${i},'text',this.value)`,true)+
      uiButton('Remove Record',{level:'tertiary',onclick:`careerRemove(${i})`}),{title:`Career record ${i+1}`})).join('');
    body += uiButton('Add Career Record',{level:'secondary',onclick:'careerAdd()'})+button('Save Information','save_onboarding');
    body += button('Normalize Profile','normalize');
    body += '<p>Normalize Profile saves your input first. You can also save and return later.</p>';
  } else {
    body += careerBasicFields.map(k=>careerInput(k,careerDraft.basic[k],`careerField(-1,'${k}',this.value)`)).join('');
    body += careerDraft.records.map((r,i)=>uiCard(
      careerInput('Title',r.title,`careerField(${i},'title',this.value)`)+
      careerInput('Description',r.description,`careerField(${i},'description',this.value)`,true)+
      careerInput('Skills (comma separated)',r.skills.join(', '),`careerField(${i},'skills',this.value)`)+
      `<details><summary>Original information</summary><p class="career-source">${esc(JSON.stringify(p.raw.records.find(x=>x.source_id===r.source_id).fields || {}))}\n${esc(p.raw.records.find(x=>x.source_id===r.source_id).text)}</p></details>`,{title:`Profile record ${i+1}`})).join('');
    body += button('Save Profile Edits','save_profile')+button('Confirm & Continue','confirm');
    body += '<p>Confirm & Continue saves your edits and confirms your entire profile.</p>';
  }
  return status + uiCard(`<fieldset class="career-fields" ${careerBusy?'disabled':''}>${body}</fieldset>`,{title:careerMode==='onboarding'?'Tell your Career Agent about yourself':'Review your Career Profile'});
};
