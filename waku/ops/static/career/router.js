CA.jobURL = (id,resume=false) => `#jobs/${encodeURIComponent(id)}${resume?'/resume':''}`;
CA.parseRoute = hash => {
  const parts=hash.replace(/^#/,'').split('/');
  if(parts[0]==='jobs' && parts.length>=2){
    try{if(parts.length===2 || (parts.length===3 && parts[2]==='resume')) return {screen:parts[2]==='resume'?'resume':'job',id:decodeURIComponent(parts[1])};}catch(_){}
  }
  return parts.length===1 && ['overview','profile','jobs','settings'].includes(parts[0])?{screen:parts[0]}:{screen:'missing'};
};
CA.navigate = route => {
  if(location.hash===route)CA.routeChanged();
  else location.hash=route;
};
CA.routeChanged = () => {
  if(!location.hash || location.hash==='#career') history.replaceState(null,'','#overview');
  CA.state.route=CA.parseRoute(location.hash);
  CA.state.navigation++;
  const menu=document.getElementById('career-menu');
  if(menu && window.matchMedia('(max-width:899px)').matches)menu.open=false;
  CA.render();
};
window.addEventListener('hashchange',CA.routeChanged);
