CA.readiness = async () => {
  try{
    const p=CA.state.provider;p.status=await CA.json('/api/provider-status',undefined,true);
    if(!p.draft)p.draft={provider:p.status.provider,model:p.status.model,key:'',base_url:p.status.endpoint};
    document.getElementById('provider-status').textContent=p.status.error || `${p.status.provider} · ${p.status.model} (configured; no background probe)`;
  }catch(e){CA.state.provider.error=e.message;}
  if(CA.state.route.screen==='settings')CA.render();
};
CA.providerField = (key,value) => {CA.state.provider.draft[key]=value;};
CA.changeProvider = name => {
  const p=CA.state.provider,provider=p.status.providers.find(v=>v.key===name);
  p.draft={provider:name,model:provider.model,key:'',base_url:provider.base_url};CA.render();
};
CA.settingsView = () => {
  const p=CA.state.provider,d=p.draft;
  if(!d)return uiNotice('note','Loading provider settings.')+uiButton('Retry',{onclick:'CA.readiness()'});
  const provider=p.status.providers.find(v=>v.key===d.provider);
  return uiCard(`<p>${esc(p.status.error || 'Provider access is configured. Readiness does not call the provider.')}</p>`+
    `<form onsubmit="CA.saveProvider(event)"><fieldset ${p.busy?'disabled':''}>
    <label>Provider<select onchange="CA.changeProvider(this.value)">${p.status.providers.map(v=>`<option value="${esc(v.key)}" ${v.key===d.provider?'selected':''}>${esc(v.name)}</option>`).join('')}</select></label>
    <label>Model<input value="${esc(d.model)}" oninput="CA.providerField('model',this.value)"></label>
    <label>API key<input type="password" autocomplete="off" value="${esc(d.key)}" oninput="CA.providerField('key',this.value)" placeholder="Leave blank to keep the saved key"></label>
    <label>Base URL<input value="${esc(d.base_url)}" oninput="CA.providerField('base_url',this.value)" list="career-endpoints"></label>
    <datalist id="career-endpoints">${provider.endpoints.map(v=>`<option value="${esc(v.base_url)}">${esc(v.label)}</option>`).join('')}</datalist>
    <p>The key is saved to your local .env. Saving a changed key or endpoint may call the provider to validate it.</p>
    <button type="submit" ${CA.state.request.busy?'disabled':''}>${p.busy?'Saving…':'Save and activate'}</button></fieldset></form>`+
    (p.error?uiNotice('failed',esc(p.error)):''),{title:'Career Provider Settings'})+
    uiCard('<p>Career Agent adapts MIT code from Waku by Sean Chen (ShenSeanChen). This independent Career interface does not imply upstream endorsement.</p>',{title:'About Career Agent'});
};
CA.saveProvider = async event => {
  event.preventDefault();const p=CA.state.provider;
  if(p.busy || CA.state.request.busy)return;
  const payload={...p.draft};if(!payload.key)delete payload.key;
  p.busy=true;p.error='';CA.render();
  try{await CA.json('/api/providers',payload);p.draft.key='';await CA.readiness();}
  catch(e){p.error=e.message;}
  finally{p.busy=false;CA.render();}
};
