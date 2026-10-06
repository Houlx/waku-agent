CA.load = async () => {
  try{CA.state.snapshot=await CA.json('/api/career');CA.ensureDrafts();CA.state.request.error='';}
  catch(e){CA.state.request.error=e.message;}
  CA.render();
};
CA.edit = mode => {CA.ensureDrafts();CA.state.drafts.editor=mode;CA.navigate('#profile');CA.render();};
CA.field = (i,key,value) => {
  const draft=CA.currentDraft();
  if(i===-1) draft.basic[key]=value;
  else draft.records[i][key]=key==='skills'?value.split(',').map(x=>x.trim()).filter(Boolean):value;
};
CA.detail = (i,key,value) => {const r=CA.currentDraft().records[i];(r.fields ||= {})[key]=value;};
CA.add = () => {CA.currentDraft().records.push({type:'project',text:''});CA.render();};
CA.remove = i => {CA.currentDraft().records.splice(i,1);CA.render();};
CA.reanalyze = id => {const j=CA.job(id);CA.state.drafts.jobId=id;CA.state.drafts.jd=j.raw_jd;CA.navigate('#jobs');};
CA.newJob = () => {CA.state.drafts.jobId=null;CA.navigate('#jobs');};
CA.run = async action => {
  const s=CA.state,d=s.drafts,q=s.request;
  if(q.busy || s.provider.busy) return;
  const navigation=s.navigation,editor=d.editor;
  const previousJobIds=new Set(s.snapshot.jobs.map(job=>job.id));
  const raw=CA.copy(d.raw),profile=CA.copy(d.profile),jd=d.jd;
  const target=action==='generate_resume'?s.route.id:d.jobId;
  const payload={action};
  if(action==='save_onboarding') payload.raw=raw;
  if(['save_profile','confirm'].includes(action)) payload.profile=profile;
  if(action==='analyze_job'){payload.jd=jd;if(target) payload.job_id=target;}
  if(action==='generate_resume'){payload.job_id=target;payload.language=CA.language(CA.job(target));}
  q.busy=true;q.error='';q.action=action;q.target=target;CA.render();
  try{
    if(action==='normalize' && editor==='onboarding'){
      s.snapshot=await CA.json('/api/career',{action:'save_onboarding',raw});
      d.raw=CA.copy(s.snapshot.profile.raw);
    }
    const result=await CA.json('/api/career',payload);s.snapshot=result;
    let route=null;
    if(action==='save_onboarding') d.raw=CA.copy(result.profile.raw);
    if(['normalize','save_profile'].includes(action)){
      d.profile=CA.copy(result.profile.normalized);
      if(s.navigation===navigation)d.editor='review';
      route='#profile';
    }
    if(action==='confirm'){d.profile=CA.copy(result.profile.normalized);route='#overview';}
    if(action==='analyze_job'){
      if(d.jd===jd)d.jobId=result.job_id;
      route=CA.jobURL(result.job_id);
    }
    if(action==='generate_resume')route=CA.jobURL(target,true);
    if(route && s.navigation===navigation)CA.navigate(route);
  }catch(e){
    q.error=e.message;
    // A failed stage may have persisted a job; retain its inputs and older artifacts.
    try{
      s.snapshot=await CA.json('/api/career');
      if(action==='analyze_job' && !target && d.jd===jd && d.jobId===target){
        const failed=s.snapshot.jobs.find(job=>!previousJobIds.has(job.id) && job.raw_jd===jd && job.status==='failed');
        if(failed)d.jobId=failed.id;
      }
    }catch(_){}
  }finally{q.busy=false;CA.render();}
};
CA.download = () => {
  const job=CA.job(CA.state.route.id);
  const url=URL.createObjectURL(new Blob([job.resume.markdown],{type:'text/markdown;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download='tailored-resume.md';link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
};
CA.print = () => {document.body.classList.add('career-print');try{window.print();}finally{document.body.classList.remove('career-print');}};
