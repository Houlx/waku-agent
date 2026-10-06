// Transitional launch: reuse the Career workspace without general dashboard polling.
let careerProviderStatus = null;
async function careerReadiness(){
  const r = await fetch('/api/provider-status');
  careerProviderStatus = await r.json();
  const s = careerProviderStatus;
  document.getElementById('provider-status').textContent = s.error || `${s.provider} · ${s.model} (configured; no background probe)`;
}
async function careerProviderSetup(){
  try { await careerReadiness(); }
  catch(e){ careerError = e.message; careerPaint(); return; }
  const s = careerProviderStatus;
  openDialog(`<h2>Provider setup</h2><form id="career-provider-form" onsubmit="careerSaveProvider(event)">
    <label class="career-field">Provider<select name="provider" onchange="careerProviderFields(this.value)">
    ${s.providers.map(p=>`<option value="${esc(p.key)}" ${p.key===s.provider?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label>
    <label class="career-field">Model<input name="model" value="${esc(s.model)}"></label>
    <label class="career-field">API key<input type="password" name="key" autocomplete="off" placeholder="Leave blank to keep the saved key"></label>
    <label class="career-field">Base URL<input name="base_url" value="${esc(s.endpoint)}" placeholder="Leave blank for the provider default" list="career-endpoints"></label>
    <datalist id="career-endpoints"></datalist>
    <p>The key is saved to your local .env. A changed key or endpoint may be tested when you save.</p>
    <p id="career-provider-error" role="alert"></p>
    <button class="btn btn-primary" type="submit">Save and activate</button>
    <button class="btn btn-secondary" type="button" onclick="closeDialog()">Cancel</button>
    </form>`, {label:'Provider setup'});
}
function careerProviderFields(name){
  const p = careerProviderStatus.providers.find(p=>p.key===name);
  const form = document.getElementById('career-provider-form');
  form.elements.model.value = p.model;
  form.elements.key.value = '';
  form.elements.base_url.value = p.base_url;
  document.getElementById('career-endpoints').innerHTML = p.endpoints.map(e=>`<option value="${esc(e.base_url)}">${esc(e.label)}</option>`).join('');
}
async function careerSaveProvider(event){
  event.preventDefault();
  const form = event.target;
  const submit = form.querySelector('button[type="submit"]');
  if(submit.disabled) return;
  submit.disabled = true;
  const payload = Object.fromEntries(new FormData(form));
  if(!payload.key) delete payload.key;
  try {
    const result = await postJSON('/api/providers', payload);
    if(!result.ok) throw new Error(result.error || 'Provider configuration failed.');
    closeDialog();
    await careerReadiness();
  } catch(e){ document.getElementById('career-provider-error').textContent = e.message; }
  finally { submit.disabled = false; }
}
if(location.hash !== '#career') location.hash = '#career';
window.addEventListener('hashchange', ()=>{ if(location.hash !== '#career') location.hash = '#career'; careerPaint(); });
applyTheme(currentTheme());
watchSlots();
careerLoad();
careerReadiness().catch(e=>{ document.getElementById('provider-status').textContent = e.message; });
