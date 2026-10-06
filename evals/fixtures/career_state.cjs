// Offline state/action behavior without a browser or external dependency.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const context=vm.createContext({console,window:{addEventListener(){}},location:{hash:'#jobs'},history:{},setTimeout});
for(const name of ['ui','state','router','actions'])vm.runInContext(fs.readFileSync(`waku/ops/static/career/${name}.js`,'utf8'),context);
vm.runInContext(`
(async()=>{
 CA.render=()=>{};
 CA.state.snapshot={profile:null,evidence:[],jobs:[]};CA.ensureDrafts();
 CA.state.drafts.raw.basic.Name='Unsaved';
 CA.ensureDrafts();
 if(CA.state.drafts.raw.basic.Name!=='Unsaved')throw Error('Draft was overwritten');
 CA.state.drafts.jd='Failed JD';
 let calls=[];
 CA.json=async(url,payload)=>{
   calls.push(payload);
   if(payload)throw Error('Scripted extraction failure');
   return {profile:null,evidence:[],jobs:[{id:'failed-job',raw_jd:'Failed JD',status:'failed'}]};
 };
 await CA.run('analyze_job');
 if(CA.state.drafts.jd!=='Failed JD' || CA.state.drafts.jobId!=='failed-job')throw Error('Failed input/target lost');
 if(!CA.state.request.error.includes('extraction failure'))throw Error('Failure was hidden');
 await CA.run('analyze_job');
 if(calls.filter(Boolean)[1].job_id!=='failed-job')throw Error('Retry created another job');
 if(CA.parseRoute('#jobs/a%2Fb/resume').id!=='a/b')throw Error('Stable ID was not decoded');
 if(CA.parseRoute('#jobs/x/unavailable').screen!=='missing')throw Error('Unknown route was accepted');
 if(esc('<script>"&')!=='&lt;script&gt;&quot;&amp;')throw Error('Untrusted text was not escaped');
})()
`,context).then(()=>console.log('Career offline draft/failure/routing checks passed.')).catch(error=>{console.error(error);process.exitCode=1;});
