// Canonical report clauses remain visible without invented match statuses.
const assert=require('node:assert/strict');
const {chromium}=require(process.env.CAREER_PLAYWRIGHT || 'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CAREER_CHROMIUM || undefined,args:['--no-sandbox']});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.CAREER_BROWSER_URL+'/#jobs/'+process.env.CAREER_GROUP_JOB);
 await page.getByRole('heading',{name:'Test Software Engineer',exact:true}).waitFor();
 assert((await page.locator('#view').innerText()).includes('Based on 6 scored requirement groups.'));
 const excluded=page.locator('.panel').filter({has:page.getByRole('heading',{name:'身体健康，吃苦耐劳，爱岗敬业',exact:true})}).last();
 assert((await excluded.innerText()).includes('excluded from Coverage'));
 assert.equal(await excluded.locator('.status').count(),0);
 await page.getByRole('heading',{name:'Needs confirmation',exact:true}).waitFor();
 await page.getByRole('heading',{name:'Not scoreable',exact:true}).waitFor();
 await page.getByLabel('UI language').selectOption('zh-CN');
 await page.getByRole('heading',{name:'需要确认',exact:true}).waitFor();
 await page.getByRole('heading',{name:'不参与评分',exact:true}).waitFor();
 assert((await page.locator('#view').innerText()).includes('不计入覆盖率'));
 await page.goto(process.env.CAREER_BROWSER_URL+'/#jobs/'+process.env.CAREER_EXCLUDED_JOB);
 await page.getByRole('heading',{name:'Test Software Engineer',exact:true}).waitFor();
 assert((await page.locator('#view').innerText()).includes('可评分信息不足'));
 assert(await page.getByRole('button',{name:'生成定制简历',exact:true}).isDisabled());
 await page.getByLabel('界面语言').selectOption('en');
 assert((await page.locator('#view').innerText()).includes('Insufficient scoreable information'));
 assert(await page.getByRole('button',{name:'Generate Tailored Resume',exact:true}).isDisabled());
 assert.deepEqual(errors,[]);await browser.close();
 console.log('Canonical report scoring/exclusion/confirmation and zero-score gates passed in both locales.');
})().catch(e=>{console.error(e);process.exitCode=1;});
