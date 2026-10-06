// No polling, general dashboard globals or AI work during navigation.
document.documentElement.dataset.theme=CA.theme();
CA.routeChanged();
CA.load().then(()=>{
  if(CA.state.snapshot?.profile?.normalized)CA.state.drafts.editor='review';
  CA.render();
});
CA.readiness();
