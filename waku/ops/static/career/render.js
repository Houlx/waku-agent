// Storage keys remain English even when their interface labels change.
const careerBasicFields = {'Name':'name','Phone':'phone','Email':'email','Current Location':'location','Additional Information':'additional'};
const careerRecordFields = {work:{Company:'company',Position:'position','Start Date':'start','End Date':'end'},education:{School:'school',Degree:'degree',Major:'major','Start Date':'start','End Date':'end'},project:{'Project Name':'projectName'},other:{}};
const careerHelp = {work:'helpWork',project:'helpProject',education:'helpEducation',other:'helpOther'};
function careerInput(label,value,handler,large=false){
  const field=large?`<textarea aria-label="${esc(label)}" oninput="${handler}">${esc(value || '')}</textarea>`:
    `<input aria-label="${esc(label)}" value="${esc(value || '')}" oninput="${handler}">`;
  return `<label class="career-field">${esc(label)}${field}</label>`;
}
function careerActions(body){return `<div class="career-actions" role="group" aria-label="${esc(CA.t('actions'))}">${body}</div>`;}
function careerDelete(job){return uiButton(CA.t('delete'),{level:'tertiary destructive',onclick:`CA.askDelete(${JSON.stringify(job.id)})`,attrs:CA.state.request.busy || CA.state.provider.busy?'disabled':''});}
function careerReport(job){
  const list=values=>'<ul>'+values.map(v=>`<li>${esc(v)}</li>`).join('')+'</ul>';
  const disabled=CA.state.request.busy || CA.state.provider.busy;
  let body=careerActions(`<label>${esc(CA.t('resumeLanguage'))}<select aria-label="${esc(CA.t('resumeLanguage'))}" onchange="CA.state.drafts.languages[CA.state.route.id]=this.value" ${disabled?'disabled':''}>`+
    ['English','Chinese','Japanese'].map(l=>`<option value="${l}" ${l===CA.language(job)?'selected':''}>${esc(CA.t(l))}</option>`).join('')+'</select></label>'+
    uiButton(CA.t('generate'),{onclick:"CA.run('generate_resume')",attrs:disabled || !CA.state.snapshot.profile?.confirmed || job.outdated || job.status!=='complete' || !job.requirements.length?'disabled':''})+
    (job.resume?uiButton(CA.t('viewResume'),{level:'secondary',onclick:`CA.navigate(${JSON.stringify(CA.jobURL(job.id,true))})`}):''));
  if(job.outdated)body+=uiNotice('warn',esc(CA.t('staleJob')));
  if(job.status!=='complete')body+=uiNotice('warn',esc(CA.t('incomplete')));
  body+=uiCard(`<p>${esc(job.summary)}</p><p>${esc(CA.t('coverage'))}: <strong>${esc(CA.coverage(job.coverage))}</strong></p>`+
    `<p>${esc(CA.t('weights',{number:CA.number(job.requirements.length)}))}</p><p>${esc(CA.t('coverageHelp'))}</p>`,{title:esc(job.title || CA.t('report'))});
  body+=`<details><summary>${esc(CA.t('pastedJD'))}</summary><p class="career-source">${esc(job.raw_jd)}</p></details>`;
  if(job.responsibilities?.length)body+=uiCard(list(job.responsibilities),{title:esc(CA.t('responsibilities'))});
  if(!job.report && job.requirements.length)body+=uiCard(job.requirements.map(r=>
    `<h3>${esc(r.text)}</h3><p>${esc(CA.t(r.importance))} · ${esc(CA.t('assessmentMissing'))}</p><details><summary>${esc(CA.t('jdSource'))}</summary><p class="career-source">${esc(r.source_excerpt)}</p></details>`).join(''),{title:esc(CA.t('extracted'))});
  if(job.report){
    for(const importance of ['required','preferred']){
      const rows=job.requirements.filter(r=>r.importance===importance);
      body+=uiCard(rows.map(r=>{
        const evidence=r.evidence_ids.map(eid=>{
          const record=job.report.evidence[eid];
          return `<details><summary>${esc(CA.t('viewEvidence'))}: ${esc(record.normalized.title)}</summary>`+
            `<p>${esc(CA.t('requirement'))}: ${esc(r.text)}</p><p>${esc(CA.t('evidenceId'))}: ${esc(eid)}</p>`+
            `<p>${esc(CA.t('corrections'))}</p><p class="career-source">${esc(record.raw_text)}</p>`+
            `<p>${esc(CA.t('normalized'))}</p><p class="career-source">${esc(record.normalized.description)}</p>`+
            `<p>${esc(CA.t('skills'))}: ${esc(record.normalized.skills.join(', '))}</p></details>`;
        }).join('');
        return uiCard(uiBadge(CA.t(r.status),{MATCH:'ok',PARTIAL:'warn',GAP:'bad'}[r.status])+
          `<p>${esc(r.reason)}</p><details><summary>${esc(CA.t('jdSource'))}</summary><p class="career-source">${esc(r.source_excerpt)}</p></details>`+evidence,{title:esc(r.text)});
      }).join('') || `<p>${esc(CA.t('noRequirements'))}</p>`,{title:esc(CA.t(importance==='required'?'requiredHeading':'preferredHeading'))});
    }
    for(const [key,title] of [['strengths','strengths'],['gaps','gaps'],['recommended_focus','focus']])body+=uiCard(job.report[key].length?list(job.report[key]):`<p>${esc(CA.t('noItems'))}</p>`,{title:esc(CA.t(title))});
  }
  return body+uiButton(CA.t('reanalyze'),{level:'secondary',onclick:`CA.reanalyze(${JSON.stringify(job.id)})`,attrs:disabled?'disabled':''})+
    uiButton(CA.t('editCareer'),{level:'secondary',onclick:"CA.edit('review')",attrs:disabled?'disabled':''})+careerDelete(job)+careerActivity(job.activity);
}
function careerActivity(activity){
  // Diagnostic strings retain their stored language; they are not translated artifacts.
  return uiCard((activity || []).map(a=>`<p>${esc(a.stage)}: ${esc(a.status)} ${esc(a.tool || '')} — ${esc(a.result)}</p>`).join('') || `<p>${esc(CA.t('noActivity'))}</p>`,{title:esc(CA.t('activity'))});
}
function careerResume(job){
  const c=job.resume.content;
  const labels={English:['Professional Summary','Skills'],Chinese:['职业概述','技能'],Japanese:['職務要約','スキル']}[job.resume.language];
  const evidence=ids=>`<details class="career-debug"><summary>${esc(CA.t('viewEvidence'))}</summary>${ids.map(id=>{
    const r=c.evidence[id];return `<p>${esc(id)}: ${esc(r.normalized.title)}</p><p class="career-source">${esc(r.raw_text)}</p>`;
  }).join('')}</details>`;
  const claims=items=>'<ul>'+items.map(claim=>`<li>${esc(claim.text)}${evidence(claim.evidence_ids)}</li>`).join('')+'</ul>';
  let body=Object.values(c.basic).filter(Boolean).map(v=>`<p>${esc(v)}</p>`).join('');
  for(const [i,key] of ['summary','skills'].entries())if(c[key].length)body+=`<h2>${esc(labels[i])}</h2>`+claims(c[key]);
  for(const record of c.records)body+=`<section><h2>${esc(record.title)}</h2>`+Object.values(record.fields).filter(Boolean).map(v=>`<p>${esc(v)}</p>`).join('')+claims(record.bullets)+'</section>';
  return careerActions(uiButton(CA.t('download'),{onclick:'CA.download()'})+uiButton(CA.t('print'),{onclick:'CA.print()'}))+
    (job.resume.outdated || job.outdated || job.status!=='complete' || !CA.state.snapshot.profile?.confirmed?uiNotice('warn',esc(CA.t('staleResume'))):'')+
    `<p>${esc(CA.t('resumeLanguage'))}: ${esc(CA.t(job.resume.language))}</p><article class="career-resume" lang="${{English:'en',Chinese:'zh',Japanese:'ja'}[job.resume.language]}">${body}</article>`+
    uiButton(CA.t('backReport'),{level:'secondary',onclick:`CA.navigate(${JSON.stringify(CA.jobURL(job.id))})`})+careerDelete(job)+careerActivity(job.resume.activity);
}
function careerProfile(){
  const p=CA.state.snapshot.profile,draft=CA.currentDraft(),mode=CA.state.drafts.editor;
  const button=(key,action)=>uiButton(CA.t(key),{onclick:`CA.run('${action}')`,attrs:CA.state.request.busy || CA.state.provider.busy?'disabled':''});
  let body=careerActions(mode==='onboarding'?button('saveRaw','save_onboarding')+button('normalize','normalize'):button('saveProfile','save_profile')+button('confirm','confirm'));
  body+=`<p>${esc(CA.t('profileHelp'))}</p>`;
  body+=Object.entries(careerBasicFields).map(([k,label])=>careerInput(CA.t(label),draft.basic[k],`CA.field(-1,'${k}',this.value)`)).join('');
  if(mode==='onboarding'){
    body+=draft.records.map((r,i)=>uiCard(
      `<label>${esc(CA.t('recordType'))}<select aria-label="${esc(CA.t('recordType'))}" onchange="CA.field(${i},'type',this.value);CA.render()">`+
      Object.keys(careerHelp).map(t=>`<option value="${t}" ${r.type===t?'selected':''}>${esc(CA.t(t))}</option>`).join('')+'</select></label>'+
      Object.entries(careerRecordFields[r.type]).map(([k,label])=>careerInput(CA.t(label),(r.fields || {})[k],`CA.detail(${i},'${k}',this.value)`)).join('')+
      `<p>${esc(CA.t(careerHelp[r.type]))}</p>`+careerInput(CA.t('tell'),r.text,`CA.field(${i},'text',this.value)`,true)+
      uiButton(CA.t('removeRecord'),{level:'tertiary',onclick:`CA.remove(${i})`}),{title:esc(CA.t('record',{number:CA.number(i+1)}))})).join('');
    body+=uiButton(CA.t('addRecord'),{level:'secondary',onclick:'CA.add()'})+`<p>${esc(CA.t('normalizeHelp'))}</p>`;
  }else{
    for(const [type,title] of [['work','workGroup'],['project','projectGroup'],['education','educationGroup'],['other','otherGroup']]){
      const records=draft.records.map((r,i)=>({r,i})).filter(({r})=>r.type===type || p.raw.records.find(x=>x.source_id===r.source_id)?.type===type);
      body+=uiCard(records.map(({r,i})=>{
        const original=p.raw.records.find(x=>x.source_id===r.source_id);
        const fields=Object.entries(original?.fields || {}).map(([k,v])=>`${careerRecordFields[type][k]?CA.t(careerRecordFields[type][k]):k}: ${v}`).join('\n');
        return uiCard(careerInput(CA.t('title'),r.title,`CA.field(${i},'title',this.value)`)+
          careerInput(CA.t('description'),r.description,`CA.field(${i},'description',this.value)`,true)+
          careerInput(CA.t('skillsInput'),r.skills.join(', '),`CA.field(${i},'skills',this.value)`)+
          `<details><summary>${esc(CA.t('original'))}</summary><p class="career-source">${esc(fields)}\n${esc(original?.text)}</p></details>`,{title:esc(r.title)});
      }).join('') || `<p>${esc(CA.t('noRecords'))}</p>`,{title:esc(CA.t(title))});
    }
    body+=uiCard(`<p>${esc([...new Set(draft.records.flatMap(r=>r.skills))].join(', ') || CA.t('addSkills'))}</p>`,{title:esc(CA.t('skillsGroup'))});
    body+=`<p>${esc(CA.t('confirmHelp'))}</p>`;
  }
  return uiCard(`<fieldset ${CA.state.request.busy || CA.state.provider.busy?'disabled':''}>${body}</fieldset>`,{title:esc(CA.t(mode==='onboarding'?'rawHeading':'reviewHeading'))});
}
CA.jobList = jobs => jobs.map(job=>uiCard(
  CA.link(job.title || CA.t('savedFallback'),CA.jobURL(job.id))+' '+uiBadge(CA.t(job.status))+
  (job.outdated?uiBadge(CA.t('outdated'),'warn'):'')+
  `<p>${esc(CA.t('coverage'))}: ${esc(CA.coverage(job.coverage))}</p><p>${esc(CA.counts(job))}</p>`+careerDelete(job),{title:''})).join('') || `<p>${esc(CA.t('noJobs'))}</p>`;
CA.renderShell = () => {
  const s=CA.state,r=s.route,menu=document.getElementById('career-menu');
  document.documentElement.lang=CA.locale;
  document.getElementById('locale-label').textContent=CA.t('locale');
  document.getElementById('locale-select').value=CA.locale;
  document.getElementById('theme-toggle').textContent=CA.t('theme');
  menu.querySelector('summary').textContent=CA.t('menu');
  const links=[['overview','#overview'],['profile','#profile'],['settings','#settings']];
  document.getElementById('career-navigation').innerHTML=links.map(([key,url])=>`<a href="${url}" aria-current="${r.screen===key?'page':'false'}">${esc(CA.t(key))}</a>`).join('')+
    uiButton(CA.t('newJob'),{onclick:'CA.newJob()'})+`<h2>${esc(CA.t('recent'))}</h2>`+
    (s.snapshot?.jobs.slice(0,5).map(job=>`<a class="recent-job" href="${esc(CA.jobURL(job.id))}" aria-current="${['job','resume'].includes(r.screen) && r.id===job.id?'page':'false'}"><span>${esc(job.title || CA.t('savedFallback'))}</span><small>${esc(CA.t(job.status))} · ${esc(CA.coverage(job.coverage))}${job.outdated?' · '+esc(CA.t('outdated')):''}</small></a>`).join('') || `<p>${esc(CA.t('noJobs'))}</p>`)+
    `<a href="#jobs" aria-current="${r.screen==='jobs'?'page':'false'}">${esc(CA.t('allJobs'))}</a>`;
  document.getElementById('career-navigation').setAttribute('aria-label',CA.t('navigation'));
  CA.renderReadiness();
};
CA.render = () => {
  const s=CA.state,p=s.snapshot?.profile,r=s.route;
  const status=(s.request.error?uiNotice('failed',esc(CA.error(s.request.error,s.request.errorCode))):'')+
    (s.request.busy?uiNotice('note',esc(CA.t('working',{action:CA.t(s.request.action)}))):'');
  let body='';
  if(!s.snapshot)body=uiNotice('note',esc(CA.t('loading')))+uiButton(CA.t('retry'),{onclick:'CA.load()'});
  else if(r.screen==='overview')body=uiCard(
    `<p>${esc(CA.t(p?.confirmed?'confirmed':p?.normalized?'needsReview':'needsProfile'))}</p>`+
    `<p>${esc(p?.normalized?.basic?.Name || p?.raw?.basic?.Name || '')} · ${esc(CA.t('evidenceCount',{number:CA.number(s.snapshot.evidence.length)}))}</p>`+
    `<p>${esc((p?.normalized?.records || []).slice(0,3).map(record=>record.title).join(' · '))}</p>`+
    uiButton(CA.t(p?.confirmed?'editProfile':'setupProfile'),{onclick:`CA.edit('${p?.normalized?'review':'onboarding'}')`})+
    uiButton(CA.t('newJob'),{onclick:'CA.newJob()'}),{title:esc(CA.t('profile'))})+
    uiCard(CA.jobList(s.snapshot.jobs.slice(0,3)),{title:esc(CA.t('recent'))});
  else if(r.screen==='profile')body=uiButton(CA.t('editRaw'),{onclick:"CA.edit('onboarding')"})+
    (s.drafts.profile?uiButton(CA.t('review'),{onclick:"CA.edit('review')"}):'')+careerProfile();
  else if(r.screen==='jobs')body=uiCard(
    `<fieldset ${s.request.busy || s.provider.busy?'disabled':''}>`+
    careerActions(uiButton(CA.t(s.drafts.jobId?'reanalyze':'analyze'),{onclick:"CA.run('analyze_job')",attrs:!p?.confirmed?'disabled':''}))+
    `<p>${esc(CA.t('analysisHelp'))}</p>`+careerInput(CA.t('pasteJD'),s.drafts.jd,'CA.state.drafts.jd=this.value',true)+
    (s.drafts.jobId?uiButton(CA.t('asNew'),{level:'secondary',onclick:'CA.state.drafts.jobId=null;CA.render()'}):'')+'</fieldset>'+
    (!p?.confirmed?CA.link(CA.t('setupLink'),'#profile'):''),{title:esc(CA.t('analyzeHeading'))})+
    uiCard(CA.jobList(s.snapshot.jobs),{title:esc(CA.t('savedJobs'))});
  else if(['job','resume'].includes(r.screen)){
    const job=CA.job(r.id);
    body=!job?uiNotice('warn',esc(CA.t('missingJob')))+CA.link(CA.t('savedJobs'),'#jobs'):
      r.screen==='resume'?(job.resume?careerResume(job):uiNotice('warn',esc(CA.t('noResume')))+CA.link(CA.t('jobDetail'),CA.jobURL(job.id))):careerReport(job);
  }else if(r.screen==='settings')body=CA.settingsView();
  else body=uiNotice('warn',esc(CA.t('missingPage')))+CA.link(CA.t('overview'),'#overview');
  document.getElementById('view').innerHTML=status+body;
  CA.renderShell();
  CA.renderDelete();
  CA.updateActionSpacing();
};
