CA.renderReadiness = () => {
  const p=CA.state.provider,status=p.status;
  const text=status?(status.error?(status.configured?CA.t('providerUnavailable'):CA.t('providerMissing')):CA.t('providerStatus',{provider:status.provider,model:status.model})):p.error?CA.error(p.error,p.errorCode):'';
  document.getElementById('provider-status').textContent=text;
};
CA.readiness = async () => {
  try{
    const p=CA.state.provider;p.status=await CA.json('/api/provider-status',undefined,true);p.error='';
    if(!p.draft)p.draft={provider:p.status.provider,model:p.status.model,key:'',base_url:p.status.endpoint};
  }catch(e){CA.state.provider.error=e.message;CA.state.provider.errorCode=e.code;}
  CA.render();
};
CA.providerField = (key,value) => {CA.state.provider.draft[key]=value;};
CA.changeProvider = name => {
  const p=CA.state.provider,provider=p.status.providers.find(v=>v.key===name);
  p.draft={provider:name,model:provider.model,key:'',base_url:provider.base_url};CA.render();
};
CA.settingsView = () => {
  const p=CA.state.provider,d=p.draft;
  if(!d)return uiNotice('note',esc(CA.t('providerLoading')))+uiButton(CA.t('retry'),{onclick:'CA.readiness()'});
  const provider=p.status.providers.find(v=>v.key===d.provider);
  return uiCard(`<p>${esc(p.status.error?(p.status.configured?CA.t('providerUnavailable'):CA.t('providerMissing')):CA.t('providerReady'))}</p>`+
    `<form onsubmit="CA.saveProvider(event)"><fieldset ${p.busy || CA.state.request.busy?'disabled':''}>
    <label>${esc(CA.t('provider'))}<select onchange="CA.changeProvider(this.value)">${p.status.providers.map(v=>`<option value="${esc(v.key)}" ${v.key===d.provider?'selected':''}>${esc(v.name)}</option>`).join('')}</select></label>
    <label>${esc(CA.t('model'))}<input value="${esc(d.model)}" oninput="CA.providerField('model',this.value)"></label>
    <label>${esc(CA.t('apiKey'))}<input type="password" autocomplete="off" value="${esc(d.key)}" oninput="CA.providerField('key',this.value)" placeholder="${esc(CA.t('keepKey'))}"></label>
    <label>${esc(CA.t('baseURL'))}<input value="${esc(d.base_url)}" oninput="CA.providerField('base_url',this.value)" list="career-endpoints"></label>
    <datalist id="career-endpoints">${provider.endpoints.map(v=>`<option value="${esc(v.base_url)}">${esc(v.label)}</option>`).join('')}</datalist>
    <p>${esc(CA.t('providerHelp'))}</p><button type="submit">${esc(CA.t(p.busy?'saving':'activate'))}</button></fieldset></form>`+
    (p.error?uiNotice('failed',esc(CA.error(p.error,p.errorCode))):''),{title:esc(CA.t('providerHeading'))})+
    uiCard(`<p>${esc(CA.t('attribution'))}</p>`,{title:esc(CA.t('about'))});
};
CA.saveProvider = async event => {
  event.preventDefault();const p=CA.state.provider;
  if(p.busy || CA.state.request.busy)return;
  const payload={...p.draft};if(!payload.key)delete payload.key;
  p.busy=true;p.error='';p.errorCode='';CA.render();
  try{await CA.json('/api/providers',payload);p.draft.key='';await CA.readiness();}
  catch(e){p.error=e.message;p.errorCode=e.code;}
  finally{p.busy=false;CA.render();}
};
