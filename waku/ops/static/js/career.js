// Career forms retain local drafts while the dashboard polls other views.
let careerData = null, careerDraft = null, careerMode = null, careerBusy = false, careerError = '';
let careerJobDraft = '', careerJobId = null;
let careerReturnMode = null, careerLanguage = null;
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
  try {
    const r = await fetch('/api/career'); const result = await r.json();
    if(result.error) throw new Error(result.error);
    careerData = result; careerError = '';
  }
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
function careerOpenJob(i){
  careerReturnMode = careerMode;
  careerLanguage = careerData.jobs[i].language; careerJobId = careerData.jobs[i].id; careerMode = 'report'; careerPaint();
}
function careerReanalyze(i){
  const job = careerData.jobs[i];
  careerJobId = job.id; careerJobDraft = job.raw_jd; careerMode = null; careerPaint();
}
function careerNewJob(){ careerJobId = null; careerJobDraft = ''; careerMode = null; careerPaint(); }
function careerBack(){ careerMode = careerReturnMode; careerReturnMode = null; careerPaint(); }
function careerEditProfile(){
  careerStart(careerData.profile && careerData.profile.normalized ? 'review' : 'onboarding');
}
async function careerRun(action){
  if (careerBusy) return;
  const previousJobIds = new Set((careerData.jobs || []).map(j=>j.id));
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
    if(action === 'analyze_job'){
      payload.jd = careerJobDraft;
      if(careerJobId) payload.job_id = careerJobId;
    }
    if(action === 'generate_resume'){ payload.job_id = careerJobId; payload.language = careerLanguage; }
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
    else if(action === 'analyze_job'){
      careerJobId = result.job_id; careerLanguage = result.jobs.find(j=>j.id===careerJobId).language; careerReturnMode = null; careerMode = 'report';
    } else if(action === 'generate_resume'){ careerMode = 'resume'; }
  } catch(e){
    careerError = e.message;
    if(action === 'analyze_job'){
      try {
        const r = await fetch('/api/career'); const refreshed = await r.json();
        if(!refreshed.error){
          careerData = refreshed;
          if(!careerJobId){
            const failed = refreshed.jobs.find(j=>!previousJobIds.has(j.id) && j.raw_jd===careerJobDraft && j.status==='failed');
            if(failed) careerJobId = failed.id;
          }
        }
      } catch(_) { /* Keep the draft and the original provider error. */ }
    }
  }
  careerBusy = false; careerPaint();
}
function careerInput(label,value,handler,large=false){
  const field = large ? `<textarea oninput="${handler}">${esc(value || '')}</textarea>` :
    `<input value="${esc(value || '')}" oninput="${handler}">`;
  return `<label class="career-field">${esc(label)}${field}</label>`;
}
function careerReport(job){
  const index = careerData.jobs.indexOf(job);
  const list = values => '<ul>' + values.map(v=>`<li>${esc(v)}</li>`).join('') + '</ul>';
  let body = job.outdated ? uiNotice('warn','Your Career Profile or job description has changed. Re-run job analysis before generating a resume.') : '';
  if(job.status !== 'complete') body += uiNotice('warn','The latest analysis did not complete. Any report below comes from an earlier successful analysis.');
  body += uiCard(`<p>${esc(job.summary)}</p><p>JD Requirement Coverage: <strong>${job.coverage===null?'Insufficient information':esc(job.coverage)+'%'}</strong></p>`+
    `<p>Based on ${job.requirements.length} extracted requirements. Required requirements have weight 2; preferred requirements have weight 1. MATCH counts as full coverage, PARTIAL as half, and GAP as zero.</p>`+
    '<p>This score shows how much of the extracted job requirements your confirmed Career Profile supports. It is not a hiring or interview probability.</p>',{title:esc(job.title || 'Job Match Report')});
  body += `<details><summary>Pasted Job Description</summary><p class="career-source">${esc(job.raw_jd)}</p></details>`;
  if(job.report){
    for(const importance of ['required','preferred']){
      const rows = job.requirements.filter(r=>r.importance===importance);
      body += uiCard(rows.map(r=>{
        const evidence = r.evidence_ids.map(eid=>{
          const record = job.report.evidence[eid];
          return `<details><summary>View Evidence: ${esc(record.normalized.title)}</summary>`+
            `<p>Requirement: ${esc(r.text)}</p><p>Evidence ID: ${esc(eid)}</p>`+
            `<p>Original information and explicit corrections</p><p class="career-source">${esc(record.raw_text)}</p>`+
            `<p>Normalized information</p><p class="career-source">${esc(record.normalized.description)}</p>`+
            `<p>Skills: ${esc(record.normalized.skills.join(', '))}</p></details>`;
        }).join('');
        return uiCard(uiBadge(r.status,{MATCH:'ok',PARTIAL:'warn',GAP:'bad'}[r.status])+
          `<p>${esc(r.reason)}</p><details><summary>JD source</summary><p class="career-source">${esc(r.source_excerpt)}</p></details>`+
          evidence,{title:esc(r.text)});
      }).join('') || '<p>No requirements were extracted in this category.</p>',{title:importance==='required'?'Required Requirements':'Preferred Requirements'});
    }
    for(const [key,title] of [['strengths','Strengths'],['gaps','Gaps'],['recommended_focus','Recommended Resume Focus']]){
      body += uiCard(job.report[key].length ? list(job.report[key]) : '<p>No items were identified.</p>',{title});
    }
  }
  return body + uiButton('Re-run Job Analysis',{onclick:`careerReanalyze(${index})`,attrs:careerBusy?'disabled':''})+
    uiButton('Edit Career Profile',{level:'secondary',onclick:'careerEditProfile()',attrs:careerBusy?'disabled':''})+
    uiButton(careerReturnMode?'Back to Career Profile':'Back to Career Dashboard',{level:'secondary',onclick:'careerBack()'})+
    careerActivity(job.activity) + `<label class="career-field">Resume language<select onchange="careerLanguage=this.value" ${careerBusy?'disabled':''}>`+
    ['English','Chinese','Japanese'].map(l=>`<option ${l===(careerLanguage || job.language)?'selected':''}>${l}</option>`).join('')+'</select></label>'+
    uiButton('Generate Tailored Resume',{onclick:"careerRun('generate_resume')",attrs:careerBusy || !careerData.profile.confirmed || job.outdated || job.status!=='complete' || !job.requirements.length?'disabled':''})+
    (job.resume?uiButton('View Resume',{level:'secondary',onclick:"careerMode='resume';careerPaint()"}):'');
}
function careerSavedJobs(){
  return uiCard((careerData.jobs || []).map((job,i)=>`<p>${esc(job.title || 'Saved Job Description')} `+
    uiBadge(job.outdated?'Outdated':job.status,job.outdated?'warn':'neutral')+' '+
    (job.report?uiButton('View Report',{level:'tertiary',onclick:`careerOpenJob(${i})`,attrs:careerBusy?'disabled':''}):'')+
    uiButton('Re-run Analysis',{level:'tertiary',onclick:`careerReanalyze(${i})`,attrs:careerBusy?'disabled':''})+'</p>').join('') ||
    '<p>Your saved analyses will appear here.</p>',{title:'Saved Jobs'});
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
    (careerBusy ? uiNotice('note',careerMode==='report'?'Your Career Agent is generating a grounded resume. Please wait.':careerMode===null?'Your Career Agent is extracting job requirements, searching evidence, and assessing coverage. Please wait.':'Your Career Agent is organizing your profile. Please wait.') : '');
  const button = (text,action)=>uiButton(text,{onclick:`careerRun('${action}')`,attrs:careerBusy?'disabled':''});
  if(careerMode==='resume'){
    const job = careerData.jobs.find(j=>j.id===careerJobId);
    if(job && job.resume) return status + careerResume(job);
    careerMode = 'report';
  }
  if(careerMode==='report'){
    const job = careerData.jobs.find(j=>j.id===careerJobId);
    if(job) return status + careerReport(job);
    careerMode = null;
  }
  if(!careerMode){
    return status + uiCard(`<p>Your Career Profile is confirmed. ${careerData.evidence.length} career records are available.</p>` +
      uiButton('View / Edit Profile',{onclick:"careerStart('review')",attrs:careerBusy?'disabled':''}) +
      uiButton('Edit Original Information',{level:'secondary',onclick:"careerStart('onboarding')",attrs:careerBusy?'disabled':''}),{title:'Career Agent'}) +
      uiCard(`<fieldset class="career-fields" ${careerBusy?'disabled':''}>`+
        careerInput('Paste Job Description',careerJobDraft,'careerJobDraft=this.value',true)+
        button(careerJobId?'Re-run Job Analysis':'Analyze Job','analyze_job')+
        uiButton('Start a New Job',{level:'secondary',onclick:'careerNewJob()',attrs:careerBusy?'disabled':''})+'</fieldset>',{title:'Analyze a Job'})+
      careerSavedJobs();
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
  return status + uiCard(`<fieldset class="career-fields" ${careerBusy?'disabled':''}>${body}</fieldset>`,{title:careerMode==='onboarding'?'Tell your Career Agent about yourself':'Review your Career Profile'})+
    ((careerData.jobs || []).length ? careerSavedJobs() : '');
};

function careerActivity(activity){
  return uiCard((activity || []).map(a=>`<p>${esc(a.stage)}: ${esc(a.status)} ${esc(a.tool || '')} — ${esc(a.result)}</p>`).join('') || '<p>No activity was recorded.</p>',{title:'Career Activity'});
}
function careerDownload(){
  const job = careerData.jobs.find(j=>j.id===careerJobId);
  const url = URL.createObjectURL(new Blob([job.resume.markdown],{type:'text/markdown;charset=utf-8'}));
  const link = document.createElement('a'); link.href=url; link.download='tailored-resume.md'; link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function careerPrint(){
  const theme = document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme','light');
  document.body.classList.add('career-print');
  try { window.print(); } finally {
    document.body.classList.remove('career-print');
    if(theme) document.documentElement.setAttribute('data-theme',theme);
    else document.documentElement.removeAttribute('data-theme');
  }
}
function careerResume(job){
  const c = job.resume.content;
  const labels = {English:['Professional Summary','Skills'],Chinese:['职业概述','技能'],Japanese:['職務要約','スキル']}[job.resume.language];
  const evidence = ids=>`<details class="career-debug"><summary>View Evidence</summary>${ids.map(id=>{
    const r=c.evidence[id]; return `<p>${esc(id)}: ${esc(r.normalized.title)}</p><p class="career-source">${esc(r.raw_text)}</p>`;
  }).join('')}</details>`;
  const claims = items=>'<ul>'+items.map(claim=>`<li>${esc(claim.text)}${evidence(claim.evidence_ids)}</li>`).join('')+'</ul>';
  let body = Object.values(c.basic).filter(Boolean).map(v=>`<p>${esc(v)}</p>`).join('');
  for(const [i,key] of ['summary','skills'].entries()) if(c[key].length) body+=`<h2>${esc(labels[i])}</h2>`+claims(c[key]);
  for(const record of c.records) body+=`<section><h2>${esc(record.title)}</h2>`+
    Object.values(record.fields).filter(Boolean).map(v=>`<p>${esc(v)}</p>`).join('')+claims(record.bullets)+'</section>';
  return (job.resume.outdated || job.outdated || job.status!=='complete' || !careerData.profile.confirmed?uiNotice('warn','This draft uses an earlier confirmed profile or analysis. Confirm your profile and re-run analysis before generating a new draft.'):'')+
    `<article class="career-resume" lang="${{English:'en',Chinese:'zh',Japanese:'ja'}[job.resume.language]}">${body}</article>`+
    uiButton('Download Markdown',{onclick:'careerDownload()'})+uiButton('Print / Save as PDF',{onclick:'careerPrint()'})+
    uiButton('Back to Match Report',{level:'secondary',onclick:"careerMode='report';careerPaint()"})+careerActivity(job.resume.activity);
}
