const careerBasicFields = ['Name', 'Phone', 'Email', 'Current Location', 'Additional Information'];
const careerRecordFields = {work:['Company','Position','Start Date','End Date'],education:['School','Degree','Major','Start Date','End Date'],project:['Project Name'],other:[]};
const careerHelp = {
  work: 'Include company, position and dates. What did you mainly work on? What responsibilities did you have? What problems did you solve? What happened as a result? What technologies did you use?',
  project: 'What was this project about? What exactly did you do? What technologies did you use? What problems did you solve? What was the result?',
  education: 'Include school, degree, major and dates. Anything else worth mentioning: research, thesis, courses, awards or academic projects?',
  other: 'Describe skills, languages, certifications, research, publications, awards or other useful facts.'
};
function careerInput(label,value,handler,large=false){
  const field = large ? `<textarea aria-label="${esc(label)}" oninput="${handler}">${esc(value || '')}</textarea>` :
    `<input aria-label="${esc(label)}" value="${esc(value || '')}" oninput="${handler}">`;
  return `<label class="career-field">${esc(label)}${field}</label>`;
}
function careerReport(job){

  const list = values => '<ul>' + values.map(v=>`<li>${esc(v)}</li>`).join('') + '</ul>';
  let body = job.outdated ? uiNotice('warn','Your Career Profile or job description has changed. Re-run job analysis before generating a resume.') : '';
  if(job.status !== 'complete') body += uiNotice('warn','The latest analysis did not complete. Any report below comes from an earlier successful analysis.');
  body += uiCard(`<p>${esc(job.summary)}</p><p>JD Requirement Coverage: <strong>${job.coverage===null?'Insufficient information':esc(job.coverage)+'%'}</strong></p>`+
    `<p>Based on ${job.requirements.length} extracted requirements. Required requirements have weight 2; preferred requirements have weight 1. MATCH counts as full coverage, PARTIAL as half, and GAP as zero.</p>`+
    '<p>This score shows how much of the extracted job requirements your confirmed Career Profile supports. It is not a hiring or interview probability.</p>',{title:esc(job.title || 'Job Match Report')});
  body += `<details><summary>Pasted Job Description</summary><p class="career-source">${esc(job.raw_jd)}</p></details>`;
  if(job.responsibilities?.length) body += uiCard(list(job.responsibilities),{title:'Responsibilities'});
  if(!job.report && job.requirements.length) body += uiCard(job.requirements.map(r=>
    `<h3>${esc(r.text)}</h3><p>${esc(r.importance)} · Assessment unavailable</p><details><summary>JD source</summary><p class="career-source">${esc(r.source_excerpt)}</p></details>`).join(''),{title:'Extracted Requirements'});
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
  return body + uiButton('Re-run Job Analysis',{onclick:`CA.reanalyze(${JSON.stringify(job.id)})`,attrs:CA.state.request.busy?'disabled':''})+
    uiButton('Edit Career Profile',{level:'secondary',onclick:"CA.edit('review')",attrs:CA.state.request.busy?'disabled':''})+
    careerActivity(job.activity) + `<label class="career-field">Resume language<select aria-label="Resume language" onchange="CA.state.drafts.languages[CA.state.route.id]=this.value" ${CA.state.request.busy?'disabled':''}>`+
    ['English','Chinese','Japanese'].map(l=>`<option ${l===CA.language(job)?'selected':''}>${l}</option>`).join('')+'</select></label>'+
    uiButton('Generate Tailored Resume',{onclick:"CA.run('generate_resume')",attrs:CA.state.request.busy || !CA.state.snapshot.profile?.confirmed || job.outdated || job.status!=='complete' || !job.requirements.length?'disabled':''})+
    (job.resume?uiButton('View Resume',{level:'secondary',onclick:`CA.navigate(${JSON.stringify(CA.jobURL(job.id,true))})`}):'');
}
function careerActivity(activity){
  return uiCard((activity || []).map(a=>`<p>${esc(a.stage)}: ${esc(a.status)} ${esc(a.tool || '')} — ${esc(a.result)}</p>`).join('') || '<p>No activity was recorded.</p>',{title:'Career Activity'});
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
  return (job.resume.outdated || job.outdated || job.status!=='complete' || !CA.state.snapshot.profile?.confirmed?uiNotice('warn','This draft uses an earlier confirmed profile or analysis. Confirm your profile and re-run analysis before generating a new draft.'):'')+
    `<p>Resume language: ${esc(job.resume.language)}</p><article class="career-resume" lang="${{English:'en',Chinese:'zh',Japanese:'ja'}[job.resume.language]}">${body}</article>`+
    uiButton('Download Markdown',{onclick:'CA.download()'})+uiButton('Print / Save as PDF',{onclick:'CA.print()'})+
    uiButton('Back to Match Report',{level:'secondary',onclick:`CA.navigate(${JSON.stringify(CA.jobURL(job.id))})`})+careerActivity(job.resume.activity);
}
function careerProfile(){
  const p=CA.state.snapshot.profile,draft=CA.currentDraft(),mode=CA.state.drafts.editor;
  const button=(text,action)=>uiButton(text,{onclick:`CA.run('${action}')`,attrs:CA.state.request.busy?'disabled':''});
  let body = '<p>You do not need to write like a resume. Describe what you actually did. AI organizes your wording; it must not invent facts or metrics.</p>';
  if(mode === 'onboarding'){
    body += careerBasicFields.map(k=>careerInput(k,draft.basic[k],`CA.field(-1,'${k}',this.value)`)).join('');
    body += draft.records.map((r,i)=>uiCard(
      `<label class="career-field">Record type<select aria-label="Record type" onchange="CA.field(${i},'type',this.value);CA.render()">`+
      Object.keys(careerHelp).map(t=>`<option value="${t}" ${r.type===t?'selected':''}>${esc(t)}</option>`).join('')+'</select></label>'+
      careerRecordFields[r.type].map(k=>careerInput(k,(r.fields || {})[k],`CA.detail(${i},'${k}',this.value)`)).join('')+
      `<p>${esc(careerHelp[r.type])}</p>`+careerInput('Tell your Career Agent',r.text,`CA.field(${i},'text',this.value)`,true)+
      uiButton('Remove Record',{level:'tertiary',onclick:`CA.remove(${i})`}),{title:`Career record ${i+1}`})).join('');
    body += uiButton('Add Career Record',{level:'secondary',onclick:'CA.add()'})+button('Save Information','save_onboarding');
    body += button('Normalize Profile','normalize');
    body += '<p>Normalize Profile saves your input first. You can also save and return later.</p>';
  } else {
    body += careerBasicFields.map(k=>careerInput(k,draft.basic[k],`CA.field(-1,'${k}',this.value)`)).join('');
    for(const [type,title] of [['work','Work Experience'],['project','Projects'],['education','Education'],['other','Research / Certifications / Other Evidence']]){
      const records=draft.records.map((r,i)=>({r,i})).filter(({r})=>r.type===type || p.raw.records.find(x=>x.source_id===r.source_id)?.type===type);
      body += uiCard(records.map(({r,i})=>{
        const original=p.raw.records.find(x=>x.source_id===r.source_id);
        return uiCard(careerInput('Title',r.title,`CA.field(${i},'title',this.value)`)+
          careerInput('Description',r.description,`CA.field(${i},'description',this.value)`,true)+
          careerInput('Skills (comma separated)',r.skills.join(', '),`CA.field(${i},'skills',this.value)`)+
          `<details><summary>Original information</summary><p class="career-source">${esc(JSON.stringify(original?.fields || {}))}\n${esc(original?.text)}</p></details>`,{title:esc(r.title)});
      }).join('') || '<p>No records in this group.</p>',{title});
    }
    body += uiCard(`<p>${esc([...new Set(draft.records.flatMap(r=>r.skills))].join(', ') || 'Add skills within your records.')}</p>`,{title:'Skills / Technologies'});
    body += button('Save Profile Edits','save_profile')+button('Confirm & Continue','confirm');
    body += '<p>Confirm & Continue saves your edits and confirms your entire profile.</p>';
  }
  return uiCard(`<fieldset ${CA.state.request.busy?'disabled':''}>${body}</fieldset>`,{title:mode==='onboarding'?'Original Career Information':'Review Career Profile'});
}
CA.jobList = jobs => jobs.map(job=>uiCard(
  CA.link(job.title || 'Saved Job Description',CA.jobURL(job.id))+' '+uiBadge(job.status)+
  (job.outdated?uiBadge('Outdated','warn'):'')+
  `<p>JD Requirement Coverage: ${job.coverage===null?'Insufficient information':esc(job.coverage)+'%'}</p><p>${esc(CA.counts(job))}</p>`,
  {title:''})).join('') || '<p>No saved analyses yet. Paste a job description to begin.</p>';
CA.render = () => {
  const s=CA.state,p=s.snapshot?.profile,r=s.route;
  const status=(s.request.error?uiNotice('failed',esc(s.request.error)):'')+
    (s.request.busy?uiNotice('note',`Working on ${esc(s.request.action.replaceAll('_',' '))}. You can navigate while this completes.`):'');
  let body='';
  if(!s.snapshot) body=uiNotice('note','Loading your Career workspace.')+uiButton('Retry',{onclick:'CA.load()'});
  else if(r.screen==='overview') body=uiCard(
    `<p>${p?.confirmed?'Your profile is confirmed.':p?.normalized?'Review and confirm your profile.':'Add your original career information to begin.'}</p>`+
    `<p>${esc(p?.normalized?.basic?.Name || p?.raw?.basic?.Name || '')} · ${s.snapshot.evidence.length} evidence records</p>`+
    `<p>${esc((p?.normalized?.records || []).slice(0,3).map(record=>record.title).join(' · '))}</p>`+
    uiButton(p?.confirmed?'View / Edit Profile':'Set Up Career Profile',{onclick:`CA.edit('${p?.normalized?'review':'onboarding'}')`})+
    uiButton('Analyze New Job',{onclick:'CA.newJob()'}),{title:'Career Profile'})+
    uiCard(CA.jobList(s.snapshot.jobs.slice(0,3)),{title:'Recent Jobs'});
  else if(r.screen==='profile') body=
    uiButton('Edit Original Information',{onclick:"CA.edit('onboarding')"})+
    (s.drafts.profile?uiButton('Review Normalized Profile',{onclick:"CA.edit('review')"}):'')+careerProfile();
  else if(r.screen==='jobs') body=uiCard(
    `<p>Confirm your Career Profile, analyze a job, inspect requirement coverage and evidence, then explicitly generate a tailored resume.</p>`+
    `<fieldset ${s.request.busy?'disabled':''}>`+
    careerInput('Paste Job Description',s.drafts.jd,'CA.state.drafts.jd=this.value',true)+
    uiButton(s.drafts.jobId?'Re-run Job Analysis':'Analyze Job',{onclick:"CA.run('analyze_job')",attrs:!p?.confirmed?'disabled':''})+
    (s.drafts.jobId?uiButton('Use as New Job',{onclick:'CA.state.drafts.jobId=null;CA.render()'}):'')+'</fieldset>'+
    (!p?.confirmed?CA.link('Set up and confirm your profile','#profile'):''),{title:'Analyze a Job'})+
    uiCard(CA.jobList(s.snapshot.jobs),{title:'Saved Jobs'});
  else if(['job','resume'].includes(r.screen)){
    const job=CA.job(r.id);
    body=!job?uiNotice('warn','This job is unavailable. Open Saved Jobs to choose an existing analysis.')+CA.link('Saved Jobs','#jobs'):
      r.screen==='resume'?(job.resume?careerResume(job):uiNotice('warn','This job has no saved resume. Generate one explicitly from its analysis.')+CA.link('Job Detail',CA.jobURL(job.id))):careerReport(job);
  }else if(r.screen==='settings')body=CA.settingsView();
  else body=uiNotice('warn','This page is unavailable.')+CA.link('Overview','#overview');
  document.getElementById('view').innerHTML=status+body;
  document.querySelectorAll('nav a').forEach(a=>a.setAttribute('aria-current',a.hash===`#${['job','resume'].includes(r.screen)?'jobs':r.screen}`?'page':'false'));
};
