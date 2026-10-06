// Saved artifacts, editor drafts and request progress have separate owners.
CA.state = {snapshot:null, route:{screen:'overview'}, navigation:0,
  drafts:{raw:null,profile:null,editor:'onboarding',jd:'',jobId:null,languages:{}},
  request:{busy:false,action:null,target:null,error:''},
  provider:{status:null,draft:null,busy:false,error:''}};
CA.job = id => CA.state.snapshot?.jobs.find(j=>j.id===id);
CA.ensureDrafts = () => {
  const d=CA.state.drafts,p=CA.state.snapshot?.profile;
  if(!d.raw) d.raw=CA.copy(p?.raw || {basic:{},records:[{type:'work',text:''}]});
  if(!d.profile && p?.normalized) d.profile=CA.copy(p.normalized);
};
CA.currentDraft = () => CA.state.drafts.editor==='review'?CA.state.drafts.profile:CA.state.drafts.raw;
CA.language = job => CA.state.drafts.languages[job.id] || job.language;
CA.counts = job => ['MATCH','PARTIAL','GAP'].map(s=>`${s}: ${job.requirements.filter(r=>r.status===s).length}`).join(' · ');
