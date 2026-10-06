// Test-only Playwright dependency; no frontend build or live model.
const {chromium} = require(process.env.CAREER_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const raw = JSON.parse(fs.readFileSync('evals/fixtures/career_profile.json','utf8'));
(async()=>{
 console.log('Launching Chromium');
 const browser=await chromium.launch({headless:true,executablePath:process.env.CAREER_CHROMIUM || undefined,args:['--no-sandbox']});
 try{
 const page=await browser.newPage(),errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>requests.push(new URL(r.url()).pathname));
 if(process.env.CAREER_BROWSER_MUTATION==='navigation')await page.route('**/static/career/actions.js',async route=>{const response=await route.fetch();await route.fulfill({response,body:(await response.text()).replace('if(route && s.navigation===navigation)','if(route)')});});
 const button=name=>page.getByRole('button',{name,exact:true});
 const nav=name=>page.getByRole('navigation').getByRole('link',{name,exact:true});
 const wait=()=>page.waitForFunction(()=>CA.state.snapshot && !CA.state.request.busy);
 await page.route('**/api/provider-status',async route=>{const response=await route.fetch();const status=await response.json();await route.fulfill({json:{...status,configured:false,error:'Set a provider key in Settings.'}});});
 await page.goto(process.env.CAREER_BROWSER_URL+'/#career');await wait();
 assert.equal(new URL(page.url()).hash,'#overview');
 await nav('Settings').click();await page.getByLabel('Model',{exact:true}).waitFor();
 await page.getByText('Set a provider key in Settings.',{exact:true}).first().waitFor();
 await page.unroute('**/api/provider-status');
 // Explicit configuration fails without losing inputs, then recovers through the real provider service.
 await page.getByLabel('Model',{exact:true}).fill('offline');
 await page.route('**/api/providers',route=>route.fulfill({json:{ok:false,error:'Synthetic configuration failure'}}));
 await button('Save and activate').click();await page.getByRole('alert').filter({hasText:'Synthetic configuration failure'}).waitFor();
 assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'offline');
 await page.unroute('**/api/providers');
 await button('Save and activate').click();await page.waitForFunction(()=>!CA.state.provider.busy);
 assert.equal(await page.evaluate(()=>CA.state.provider.error),'');
 console.log('Provider setup passed');
 await nav('Overview').click();await button('Set Up Career Profile').click();
 await button('Add Career Record').click();await button('Remove Record').last().click();
 // Populate every fixture record through real form input handlers.
 await page.getByLabel('Name',{exact:true}).fill(raw.basic.Name);
 for(let i=1;i<raw.records.length;i++)await button('Add Career Record').click();
 for(let i=0;i<raw.records.length;i++){
  await page.getByLabel('Record type',{exact:true}).nth(i).selectOption(raw.records[i].type);
  const panel=page.locator('.panel').filter({has:page.getByRole('heading',{name:`Career record ${i+1}`,exact:true})}).last();
  for(const [key,value] of Object.entries(raw.records[i].fields || {}))await panel.getByLabel(key,{exact:true}).fill(value);
  await page.getByLabel('Tell your Career Agent',{exact:true}).nth(i).fill(raw.records[i].text);
 }
 // Stable source IDs are supplied by this fixture to exercise inspected evidence references.
 await page.evaluate(records=>records.forEach((r,i)=>CA.state.drafts.raw.records[i].source_id=r.source_id),raw.records);
 await nav('Jobs').click();await nav('Career Profile').click();
 assert.equal(await page.getByLabel('Name',{exact:true}).inputValue(),raw.basic.Name);
 // Missing-provider error stays actionable and input survives.
 await page.route('**/api/career',route=>route.request().method()==='POST' && route.request().postDataJSON().action==='normalize'?route.fulfill({json:{error:'Configure a provider in Settings.'}}):route.continue());
 await button('Normalize Profile').click();await page.getByRole('alert').filter({hasText:'Configure a provider'}).waitFor();
 await page.unroute('**/api/career');await button('Normalize Profile').click();await wait();
 await page.getByRole('heading',{name:'Skills / Technologies',exact:true}).waitFor();
 await page.getByLabel('Name',{exact:true}).fill('Edited Candidate');
 await nav('Overview').click();await nav('Career Profile').click();
 assert.equal(await page.getByLabel('Name',{exact:true}).inputValue(),'Edited Candidate');
 console.log('Profile editing passed');
 await button('Confirm & Continue').click();await wait();await page.waitForURL('**/#overview');
 await button('Analyze New Job').click();await page.getByLabel('Paste Job Description',{exact:true}).fill('AI Engineer. Required: Build retrieval augmented generation applications. Required: Production PyTorch training. Preferred: Python.');
 await nav('Career Profile').click();await nav('Jobs').click();
 assert.equal(await page.getByLabel('Paste Job Description',{exact:true}).inputValue(),'AI Engineer. Required: Build retrieval augmented generation applications. Required: Production PyTorch training. Preferred: Python.');
 console.log('Draft retention passed');
 let posts=0,release;const delayed=new Promise(resolve=>release=resolve);
 await page.route('**/api/career',async route=>{
  if(route.request().method()==='POST' && route.request().postDataJSON().action==='analyze_job'){posts++;await delayed;}
  await route.continue();
 });
 await button('Analyze Job').click();await page.waitForFunction(()=>CA.state.request.busy);
 await page.evaluate(()=>CA.run('analyze_job'));await nav('Overview').click();release();await wait();
 assert.equal(posts,1);assert.equal(new URL(page.url()).hash,'#overview');
 await page.unroute('**/api/career');
 console.log('Delayed request passed');
 assert.equal(await page.evaluate(()=>CA.state.request.error),'');
 const id=await page.evaluate(()=>CA.state.snapshot.jobs[0].id),jobURL='#jobs/'+encodeURIComponent(id);
 await nav('Jobs').click();await page.getByRole('link',{name:'AI Engineer',exact:true}).click();
 assert.equal(new URL(page.url()).hash,jobURL);
 for(const status of ['MATCH','PARTIAL','GAP'])await page.getByText(status,{exact:true}).first().waitFor();
 assert(await page.getByText('50%',{exact:true}).count()>0);
 await page.getByText('View Evidence:',{exact:false}).first().click();
 assert(await page.getByText('Evidence ID:',{exact:false}).first().isVisible());
 await page.goBack();assert.equal(new URL(page.url()).hash,'#jobs');await page.goForward();
 await page.reload();await wait();assert.equal(new URL(page.url()).hash,jobURL);
 assert.equal(await page.evaluate(()=>CA.state.snapshot.jobs[0].resume),null);
 await button('Re-run Job Analysis').click();
 const originalJD=await page.getByLabel('Paste Job Description',{exact:true}).inputValue();
 await page.getByLabel('Paste Job Description',{exact:true}).fill(originalJD+' Synthetic failure');
 await button('Re-run Job Analysis').click();await wait();
 await page.getByRole('alert').filter({hasText:'Synthetic extraction failure'}).waitFor();
 assert.equal(await page.getByLabel('Paste Job Description',{exact:true}).inputValue(),originalJD+' Synthetic failure');
 assert.equal(await page.evaluate(()=>CA.state.snapshot.jobs[0].status),'failed');
 assert.equal(await page.evaluate(()=>CA.state.snapshot.jobs[0].coverage),50);
 await page.getByRole('link',{name:'AI Engineer',exact:true}).click();
 await page.getByText('The latest analysis did not complete.',{exact:false}).waitFor();
 assert(await button('Generate Tailored Resume').isDisabled());
 await button('Re-run Job Analysis').click();await page.getByLabel('Paste Job Description',{exact:true}).fill(originalJD);
 await button('Re-run Job Analysis').click();await wait();await page.getByText('MATCH',{exact:true}).first().waitFor();
 await page.getByLabel('Resume language',{exact:true}).selectOption('Japanese');
 await nav('Overview').click();await page.goto(process.env.CAREER_BROWSER_URL+'/#jobs/missing');await wait();
 await page.getByText('This job is unavailable.',{exact:false}).waitFor();
 await page.goto(process.env.CAREER_BROWSER_URL+'/'+jobURL+'/resume');await wait();
 await page.getByText('This job has no saved resume.',{exact:false}).waitFor();
 await page.getByRole('link',{name:'Job Detail',exact:true}).click();
 await page.getByLabel('Resume language',{exact:true}).selectOption('Japanese');
 console.log('Job routing passed');
 await button('Generate Tailored Resume').click();await wait();await page.locator('.career-resume').waitFor();
 assert.equal(new URL(page.url()).hash,jobURL+'/resume');assert.equal(await page.locator('.career-resume').getAttribute('lang'),'ja');
 const download=page.waitForEvent('download');await button('Download Markdown').click();assert.equal((await download).suggestedFilename(),'tailored-resume.md');
 await button('Change theme').click();assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 await page.reload();await wait();assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 await button('Change theme').click();
 await page.evaluate(()=>window.print=()=>{window.printWasCalled=document.body.classList.contains('career-print');});
 await button('Print / Save as PDF').click();assert.equal(await page.evaluate(()=>window.printWasCalled),true);
 await page.evaluate(()=>document.body.classList.add('career-print'));await page.emulateMedia({media:'print'});
 assert.equal(await page.locator('header').isVisible(),false);assert.equal(await page.locator('.career-debug').first().isVisible(),false);assert(await page.locator('.career-resume').isVisible());
 assert.equal(await page.locator('.career-resume h2').first().evaluate(el=>getComputedStyle(el).fontFamily===getComputedStyle(el.parentElement).fontFamily),true);
 await page.emulateMedia({media:'screen'});await page.evaluate(()=>document.body.classList.remove('career-print'));
 for(const language of ['Chinese','English']){
  await button('Back to Match Report').click();await page.getByLabel('Resume language',{exact:true}).selectOption(language);
  assert.equal(await page.evaluate(()=>CA.state.snapshot.jobs[0].resume.language),language==='Chinese'?'Japanese':'Chinese');
  await button('Generate Tailored Resume').click();await wait();await page.locator('.career-resume').waitFor();
  assert.equal(await page.locator('.career-resume').getAttribute('lang'),language==='Chinese'?'zh':'en');
 }
 // Editing confirmed facts invalidates analysis and retains the saved resume.
 await nav('Career Profile').click();await page.getByLabel('Name',{exact:true}).fill('Changed Candidate');await button('Save Profile Edits').click();await wait();
 await page.goto(process.env.CAREER_BROWSER_URL+'/'+jobURL);await wait();assert(await button('Generate Tailored Resume').isDisabled());
 await button('View Resume').click();await page.getByText('This draft uses an earlier confirmed profile',{exact:false}).waitFor();
 assert.deepEqual(errors,[]);
 assert(requests.every(p=>!p.startsWith('/api/') || ['/api/career','/api/provider-status','/api/providers','/api/models'].includes(p)));
 assert(requests.filter(p=>p.startsWith('/static/')).every(p=>p.startsWith('/static/career/')));
 console.log('Career Chromium journey passed: routes, drafts, actions, evidence, resume, settings, print and reload.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
