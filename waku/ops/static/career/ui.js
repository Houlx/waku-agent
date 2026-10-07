// MIT helper behavior adapted from Waku; appearance belongs to Career Agent.
const CA = {};
CA.copy = value => JSON.parse(JSON.stringify(value));
function esc(value){return String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function uiCard(body,{title=''}={}){return `<section class="panel">${title?`<h2>${title}</h2>`:''}${body}</section>`;}
function uiNotice(level,body){return `<p class="message ${esc(level)}" role="${level==='failed'?'alert':'status'}">${body}</p>`;}
function uiBadge(text,variant=''){return `<span class="status ${esc(variant)}">${esc(text)}</span>`;}
function uiButton(label,{onclick='',attrs='',level='primary'}={}){return `<button class="${esc(level)}" onclick="${esc(onclick)}" ${attrs}>${esc(label)}</button>`;}
CA.link = (text,route) => `<a href="${esc(route)}">${esc(text)}</a>`;
CA.json = async (url,payload,allowError=false) => {
  const r=await fetch(url,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const result=await r.json();
  if(!r.ok || (result.error && !allowError) || result.ok===false){
    const error=new Error(result.error || `Request failed (${r.status}).`);
    error.code=result.error_code || '';throw error;
  }
  return result;
};
CA.theme = () => {try{return localStorage.getItem('career-theme')==='dark'?'dark':'light';}catch(_){return 'light';}};
CA.toggleTheme = () => {
  const t=document.documentElement.dataset.theme==='dark'?'light':'dark';
  document.documentElement.dataset.theme=t;
  try{localStorage.setItem('career-theme',t);}catch(_){}
};
CA.updateActionSpacing = () => {
  const bar=document.querySelector('.career-actions');
  // Wrapped bars need more room when fields or evidence controls receive focus.
  document.documentElement.style.setProperty('--career-action-offset',`${bar?bar.offsetHeight+16:16}px`);
};
