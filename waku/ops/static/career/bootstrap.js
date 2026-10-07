// No polling, general dashboard globals or AI work during navigation.
document.documentElement.dataset.theme=CA.theme();
window.addEventListener('resize',CA.updateActionSpacing);
const careerNarrow=window.matchMedia('(max-width:899px)');
careerNarrow.addEventListener('change',()=>{document.getElementById('career-menu').open=!careerNarrow.matches;});
document.getElementById('career-navigation').addEventListener('click',event=>{
  if(careerNarrow.matches && event.target.closest('a,button'))document.getElementById('career-menu').open=false;
});
CA.routeChanged();
CA.load().then(()=>{
  if(CA.state.snapshot?.profile?.normalized)CA.state.drafts.editor='review';
  CA.render();
});
CA.readiness();
