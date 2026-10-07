// Offline locale and deletion behavior through the actual frontend modules.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
function make({languages=['en'],saved=null,blocked=false}={}){
 let stored=saved;
 const document={activeElement:null,querySelectorAll:()=>[],getElementById:()=>null};
 const location={hash:'#jobs/a'},history={replaceState:(_,__,url)=>location.hash=url};
 const context=vm.createContext({console,Intl,navigator:{languages},document,location,history,
  localStorage:{getItem:()=>{if(blocked)throw Error('Blocked');return stored;},setItem:(_,v)=>{if(blocked)throw Error('Blocked');stored=v;}},
  window:{addEventListener(){},scrollX:0,scrollY:250,scrollTo(){}},setTimeout});
 for(const name of ['ui','i18n','state','router','actions'])vm.runInContext(fs.readFileSync(`waku/ops/static/career/${name}.js`,'utf8'),context);
 return context;
}
(async()=>{
 for(const [options,expected] of [
  [{languages:['zh-CN']},'zh-CN'],[{languages:['zh-Hans-SG']},'zh-CN'],[{languages:['zh-SG']},'zh-CN'],
  [{languages:['zh-TW']},'en'],[{languages:['ja']},'en'],[{languages:['zh-CN'],saved:'en'},'en'],
  [{languages:['en'],saved:'zh-CN'},'zh-CN'],[{languages:['en'],saved:'invalid'},'en'],
  [{languages:['zh-CN'],blocked:true},'zh-CN']]){
  assert.equal(vm.runInContext('CA.locale',make(options)),expected);
 }
 const same=make();
 vm.runInContext(`CA.render=()=>{CA.renders=(CA.renders || 0)+1;};
 location.hash='#jobs';CA.state.drafts.jobId='old';CA.state.drafts.jd='Keep pasted JD';CA.newJob();
 if(CA.state.drafts.jobId!==null || CA.state.drafts.jd!=='Keep pasted JD' || CA.state.route.screen!=='jobs' || CA.renders!==1 || CA.state.navigation!==1)throw Error('Same-route New Job did not refresh its target and view');`,same);
 const c=make({blocked:true});
 await vm.runInContext(`(async()=>{
 const check=(ok,message)=>{if(!ok)throw Error(message);};
 CA.render=()=>{};CA.routeChanged=()=>{CA.state.navigation++;CA.state.route=CA.parseRoute(location.hash);};
 CA.state.snapshot={profile:{confirmed:true},evidence:[],jobs:[{id:'a',raw_jd:'JD',language:'English',report:{summary:'Stored English artifact'}},{id:'b',language:'Chinese'}]};
 CA.ensureDrafts();CA.state.route={screen:'job',id:'a'};
 CA.state.drafts.jd='Unrelated unsaved JD';CA.state.drafts.jobId='b';CA.state.drafts.languages={a:'Japanese',b:'Chinese'};
 let calls=0;CA.json=async()=>{calls++;throw Error('Translation must never request data');};
 const before=JSON.stringify(CA.state);
 CA.setLocale('zh-CN');check(CA.t('overview')==='概览','Chinese text missing');
 check(CA.coverage(50)==='50%','Coverage value changed');
 CA.setLocale('en');check(CA.t('overview')==='Overview','English text missing');
 check(JSON.stringify(CA.state)===before && calls===0,'Locale mutated drafts/artifacts or made requests');
 for(const [key,pair] of Object.entries(CA.messages)){
  check(pair.length===2 && pair.every(v=>typeof v==='string' && v.length),'Incomplete translation '+key);
  check(JSON.stringify([...pair[0].matchAll(/\\{(\\w+)\\}/g)].map(m=>m[1]).sort())===JSON.stringify([...pair[1].matchAll(/\\{(\\w+)\\}/g)].map(m=>m[1]).sort()),'Interpolation mismatch '+key);
 }
 CA.locale='zh-CN';check(CA.error('safe detail','job_not_found')==='此已保存职位已不存在。','Stable error code missing');
 check(CA.error('diagnostic sentinel').includes('diagnostic sentinel'),'Safe fallback was hidden');
 CA.locale='en';
 const deleted={profile:{confirmed:true},evidence:[],jobs:[CA.state.snapshot.jobs[0]]};
 CA.json=async()=>{calls++;return deleted;};
 await CA.deleteJob('b');
 check(location.hash==='#jobs/a','Deleting another job moved the route');
 check(!CA.state.drafts.languages.b && CA.state.drafts.jobId===null && CA.state.drafts.jd==='Unrelated unsaved JD','Delete damaged draft state');
 // Duplicate deletion and navigation during a pending request.
 let release;const pending=new Promise(resolve=>release=resolve);let posts=0;
 CA.json=async(url,payload)=>{if(payload)posts++;return pending;};
 const first=CA.deleteJob('a');await CA.deleteJob('a');
 CA.state.navigation++;CA.state.route={screen:'profile'};location.hash='#profile';
 release({profile:null,evidence:[],jobs:[]});await first;
 check(posts===1 && location.hash==='#profile','Duplicate delete or late redirect');
 // Viewed Resume deletion replaces the current entry and retains unrelated JD.
 CA.state.snapshot={profile:null,evidence:[],jobs:[{id:'a'}]};CA.state.route={screen:'resume',id:'a'};location.hash='#jobs/a/resume';
 CA.json=async()=>({profile:null,evidence:[],jobs:[]});await CA.deleteJob('a');
 check(location.hash==='#jobs' && CA.state.drafts.jd==='Unrelated unsaved JD','Viewed resume delete did not navigate safely');
 // Failure keeps the route and artifacts; lost responses are reconciled without resubmission.
 const snapshot={profile:null,evidence:[],jobs:[{id:'a'}]};CA.state.snapshot=snapshot;CA.state.route={screen:'job',id:'a'};location.hash='#jobs/a';
 CA.json=async(url,payload)=>{if(payload)throw Error('Synthetic delete failure');return snapshot;};
 await CA.deleteJob('a');check(location.hash==='#jobs/a' && CA.state.snapshot.jobs[0].id==='a' && CA.state.request.error,'Delete failure lost the job');
 CA.json=async(url,payload)=>{if(payload)throw Error('Lost response');return {profile:null,evidence:[],jobs:[]};};
 await CA.deleteJob('a');check(location.hash==='#jobs' && !CA.state.request.error,'Committed delete was not reconciled');
})()`,c);
 console.log('Career locale and deletion state checks passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
