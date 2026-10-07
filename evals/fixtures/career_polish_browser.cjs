// Additional acceptance checks use the same temporary server and scripted clients.
const assert=require('node:assert/strict');
module.exports=async(page,id)=>{
 const main=page.locator('main'),locale=page.locator('#locale-select');
 const wait=()=>page.waitForFunction(()=>CA.state.snapshot && !CA.state.request.busy && !CA.state.provider.busy);
 const go=async hash=>{await page.evaluate(hash=>CA.navigate(hash),hash);await page.waitForURL('**/'+hash);};
 const click=async name=>main.getByRole('button',{name,exact:true}).click();
 const confirmDelete=async()=>{await page.locator('#delete-dialog').getByRole('button',{name:'Delete Job',exact:true}).click();await wait();};
 const jobURL='#jobs/'+encodeURIComponent(id);
 let requests=0,deletePosts=0;
 page.on('request',r=>{requests++;if(r.method()==='POST' && new URL(r.url()).pathname==='/api/career' && r.postDataJSON().action==='delete_job')deletePosts++;});
 await page.waitForFunction(()=>CA.state.provider.status);
 await go('#jobs');
 await page.getByLabel('Paste Job Description',{exact:true}).fill('Unsaved JD 中文草稿');
 await page.evaluate(id=>{CA.state.drafts.jobId=id;CA.render();},id);
 await page.getByRole('navigation').getByRole('button',{name:'Analyze New Job',exact:true}).click();
 await main.getByRole('button',{name:'Analyze Job',exact:true}).waitFor();
 assert.equal(await page.getByLabel('Paste Job Description',{exact:true}).inputValue(),'Unsaved JD 中文草稿');
 await go('#profile');await page.getByLabel('Name',{exact:true}).fill('Unsaved Profile 中文');
 await go('#settings');await page.getByLabel('Model',{exact:true}).fill('Unsaved model draft');
 await go(jobURL);await page.getByLabel('Resume language',{exact:true}).selectOption('Japanese');
 const before=await page.evaluate(()=>JSON.stringify({snapshot:CA.state.snapshot,drafts:CA.state.drafts,provider:CA.state.provider.draft,route:CA.state.route,navigation:CA.state.navigation}));
 const requestCount=requests;
 await locale.selectOption('zh-CN');
 assert.equal(await page.locator('html').getAttribute('lang'),'zh-CN');
 await main.getByRole('button',{name:'生成定制简历',exact:true}).waitFor();
 assert.equal(await page.getByLabel('简历语言',{exact:true}).inputValue(),'Japanese');
 assert(await page.getByRole('navigation').getByRole('link',{name:'概览',exact:true}).isVisible());
 assert.equal(await page.locator('.recent-job[aria-current=page]').count(),1);
 await locale.selectOption('en');
 assert.equal(requests,requestCount,'Locale switching made requests');
 assert.equal(await page.evaluate(()=>JSON.stringify({snapshot:CA.state.snapshot,drafts:CA.state.drafts,provider:CA.state.provider.draft,route:CA.state.route,navigation:CA.state.navigation})),before);
 await go('#jobs');assert.equal(await page.getByLabel('Paste Job Description',{exact:true}).inputValue(),'Unsaved JD 中文草稿');
 await go('#profile');assert.equal(await page.getByLabel('Name',{exact:true}).inputValue(),'Unsaved Profile 中文');
 await go('#settings');assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'Unsaved model draft');
 // All direct routes load in both languages. Reload retains artifacts, not unsaved drafts.
 for(const language of ['zh-CN','en']){
  await locale.selectOption(language);
  for(const hash of ['#overview','#profile','#jobs',jobURL,jobURL+'/resume','#settings','#jobs/missing']){
   await page.goto(process.env.CAREER_BROWSER_URL+'/'+hash);await wait();
   assert.equal(await page.locator('html').getAttribute('lang'),language);
   assert.equal(new URL(page.url()).hash,hash);
   if(hash.includes(id))assert.equal(await page.locator('.recent-job[aria-current=page]').count(),1);
  }
 }
 // Default locale and unavailable storage use isolated browser contexts.
 for(const options of [{locale:'zh-CN',expected:'zh-CN'},{locale:'zh-TW',expected:'en'},{locale:'en-US',expected:'en',blocked:true}]){
  const context=await page.context().browser().newContext({locale:options.locale});
  if(options.blocked)await context.addInitScript(()=>{Object.defineProperty(window,'localStorage',{get(){throw Error('Storage unavailable');}});});
  const other=await context.newPage();await other.goto(process.env.CAREER_BROWSER_URL+'/#overview');
  await other.waitForFunction(()=>CA.state.snapshot);
  assert.equal(await other.locator('html').getAttribute('lang'),options.expected);
  if(options.blocked){await other.locator('#locale-select').selectOption('zh-CN');assert.equal(await other.locator('html').getAttribute('lang'),'zh-CN');}
  await context.close();
 }
 // Gating remains present on sticky controls after profile edits from the original journey.
 await go(jobURL);assert(await main.getByRole('button',{name:'Generate Tailored Resume',exact:true}).isDisabled());
 // Long fixtures exercise actual document scrolling and sticky bounding rectangles.
 const sticky=async()=>{
  await page.locator('.career-actions').scrollIntoViewIfNeeded();
  await page.locator('.career-actions').evaluate(el=>window.scrollTo(0,window.scrollY+el.getBoundingClientRect().top+250));
  const box=await page.locator('.career-actions').boundingBox();
  assert(box && box.y>=-1 && box.y<5 && box.y+box.height<=await page.evaluate(()=>innerHeight),'Actions did not stick within the viewport: '+JSON.stringify(box));
 };
 await go('#profile');await sticky();
 await click('Edit Original Information');await sticky();
 await go('#jobs');await page.getByLabel('Paste Job Description',{exact:true}).evaluate(el=>el.style.height='1800px');await sticky();
 await go(jobURL);await sticky();
 await go(jobURL+'/resume');
 await page.locator('.career-resume').evaluate(el=>el.style.minHeight='1800px');await sticky();
 // Print controls are absent for both native printing and the explicit application print class.
 for(const explicit of [false,true]){
  await page.evaluate(explicit=>document.body.classList.toggle('career-print',explicit),explicit);
  await page.emulateMedia({media:'print'});
  for(const selector of ['header','.career-sidebar','.career-actions','#provider-status','#delete-dialog'])assert.equal(await page.locator(selector).isVisible(),false);
  assert(await page.locator('.career-resume').isVisible());
  assert.equal(await page.locator('.career-debug').first().isVisible(),false);
  await page.emulateMedia({media:'screen'});
 }
 await page.evaluate(()=>document.body.classList.remove('career-print'));
 // Responsive disclosure preserves drafts; long titles and labels fit a narrow viewport.
 await go('#jobs');await page.getByLabel('Paste Job Description',{exact:true}).fill('Responsive draft');
 await locale.selectOption('zh-CN');await page.setViewportSize({width:390,height:844});
 await page.waitForFunction(()=>!document.getElementById('career-menu').open);
 assert.equal(await page.locator('#career-menu').getAttribute('open'),null);
 await page.locator('#career-menu summary').click();
 await page.getByRole('navigation').getByRole('link',{name:'职业档案',exact:true}).click();
 assert.equal(await page.locator('#career-menu').getAttribute('open'),null);
 await page.locator('#career-menu summary').click();await page.getByRole('navigation').getByRole('link',{name:'查看全部职位',exact:true}).click();
 assert.equal(await page.getByLabel('粘贴职位描述',{exact:true}).inputValue(),'Responsive draft');
 await page.evaluate(()=>{CA.state.snapshot.jobs[0].title='这是一个非常长的中文职位标题'.repeat(20);CA.render();});
 await page.locator('#career-menu summary').click();
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.setViewportSize({width:640,height:450});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Layout overflows at a desktop-equivalent 200% zoom viewport');
 // Wrapped action heights determine focus clearance at narrow widths.
 await locale.selectOption('en');await go('#profile');
 const input=page.getByLabel('Name',{exact:true});
 await input.evaluate(el=>el.scrollIntoView({block:'start'}));await input.focus();
 const fieldBox=await input.boundingBox(),barBox=await page.locator('.career-actions').boundingBox();
 assert(fieldBox.y>=barBox.y+barBox.height,'Sticky actions obscure the focused field');
 await go(jobURL);await locale.selectOption('zh-CN');
 await page.setViewportSize({width:1280,height:900});
 await main.getByRole('button',{name:'删除职位',exact:true}).first().click();
 await page.locator('#delete-dialog').getByText('永久删除此职位？',{exact:true}).waitFor();
 assert((await page.locator('#delete-description').textContent()).includes('职业档案及证据会保留'));
 await page.locator('#delete-dialog').getByRole('button',{name:'取消',exact:true}).click();
 await locale.selectOption('en');
 await page.evaluate(()=>CA.load());await wait();
 // Confirm saved profile edits and create enough jobs to test the five-entry sidebar cap.
 await page.evaluate(()=>CA.run('confirm'));await wait();
 const others=await page.evaluate(async()=>{
  const jd=CA.state.snapshot.jobs[0].raw_jd,ids=[];
  for(let i=0;i<6;i++){const result=await CA.json('/api/career',{action:'analyze_job',jd});CA.state.snapshot=result;ids.push(result.job_id);}
  CA.render();return ids;
 });
 assert.equal(await page.locator('.recent-job').count(),5);
 const recentFirst=await page.evaluate(()=>CA.state.snapshot.jobs[0].id);
 await page.locator(`.recent-job[href="#jobs/${recentFirst}"]`).click();assert.equal(new URL(page.url()).hash,'#jobs/'+recentFirst);
 // Deleting a different job from history retains route and unrelated draft.
 await go('#jobs');await page.getByLabel('Paste Job Description',{exact:true}).fill('Keep this JD draft');
 const panel=main.locator('.panel').filter({has:page.locator(`a[href="#jobs/${others[0]}"]`)}).last();
 await panel.getByRole('button',{name:'Delete Job',exact:true}).click();
 await page.locator('#delete-dialog').getByRole('button',{name:'Cancel',exact:true}).click();
 assert.equal(deletePosts,0);assert(await page.evaluate(id=>!!CA.job(id),others[0]));
 await panel.getByRole('button',{name:'Delete Job',exact:true}).click();await confirmDelete();
 assert.equal(new URL(page.url()).hash,'#jobs');assert.equal(await page.getByLabel('Paste Job Description',{exact:true}).inputValue(),'Keep this JD draft');
 // A backend failure keeps the viewed job and shows the safe fallback detail.
 await go('#jobs/'+others[1]);
 await page.route('**/api/career',route=>route.request().method()==='POST' && route.request().postDataJSON().action==='delete_job'?route.fulfill({json:{error:'Synthetic delete failure'}}):route.continue());
 await click('Delete Job');await confirmDelete();
 await page.getByRole('alert').filter({hasText:'Synthetic delete failure'}).waitFor();assert.equal(new URL(page.url()).hash,'#jobs/'+others[1]);
 assert(await page.evaluate(id=>!!CA.job(id),others[1]));await page.unroute('**/api/career');
 // Navigation while pending wins; duplicate invocation sends one POST.
 let release;const pending=new Promise(resolve=>release=resolve);let posts=0;
 await page.route('**/api/career',async route=>{if(route.request().method()==='POST' && route.request().postDataJSON().action==='delete_job'){posts++;await pending;}await route.continue();});
 await click('Delete Job');await page.locator('#delete-dialog').getByRole('button',{name:'Delete Job',exact:true}).click();
 await page.waitForFunction(()=>CA.state.request.busy);await page.evaluate(id=>CA.deleteJob(id),others[1]);
 await page.getByRole('navigation').getByRole('link',{name:'Overview',exact:true}).click();release();await wait();
 assert.equal(posts,1);assert.equal(new URL(page.url()).hash,'#overview');await page.unroute('**/api/career');
 // Delete viewed job replaces the current entry. Earlier history entries show missing state.
 await go('#jobs/'+others[2]);await go('#overview');await go('#jobs/'+others[2]);
 await click('Delete Job');await confirmDelete();assert.equal(new URL(page.url()).hash,'#jobs');
 await page.goBack();assert.equal(new URL(page.url()).hash,'#overview');await page.goBack();
 await page.getByText('This job is unavailable.',{exact:false}).waitFor();await page.goForward();await page.goForward();
 assert.equal(new URL(page.url()).hash,'#jobs');
 // Delete saved resume context and remove its remembered language/reanalysis target only.
 await go(jobURL+'/resume');
 await page.evaluate(id=>{CA.state.drafts.jobId=id;CA.state.drafts.languages[id]='Japanese';},id);
 await click('Delete Job');await confirmDelete();assert.equal(new URL(page.url()).hash,'#jobs');
 assert.equal(await page.evaluate(id=>CA.state.drafts.languages[id] || null,id),null);
 assert.equal(await page.evaluate(()=>CA.state.drafts.jobId),null);
 assert.equal(await page.getByLabel('Paste Job Description',{exact:true}).inputValue(),'Keep this JD draft');
 await page.reload();await wait();assert.equal(await page.evaluate(id=>CA.job(id) || null,id),null);
 console.log('Career UI polish passed: locales, sidebar, responsive/sticky/print controls, deletion and history.');
};
