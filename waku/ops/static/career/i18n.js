// UI text only: stored profile keys, JD prose and generated documents stay unchanged.
CA.messages = {
  overview:['Overview','概览'], profile:['Career Profile','职业档案'], settings:['Settings','设置'],
  jobs:['Jobs','职位'], allJobs:['View All Jobs','查看全部职位'], recent:['Recent Jobs','最近职位'],
  newJob:['Analyze New Job','分析新职位'], navigation:['Career navigation','职业导航'],
  menu:['Navigation and Recent Jobs','导航与最近职位'], locale:['UI language','界面语言'],
  theme:['Change theme','切换主题'], retry:['Retry','重试'], loading:['Loading your Career workspace.','正在加载职业工作区。'],
  name:['Name','姓名'], phone:['Phone','电话'], email:['Email','邮箱'], location:['Current Location','现居地'],
  additional:['Additional Information','补充信息'], company:['Company','公司'], position:['Position','职位'],
  start:['Start Date','开始日期'], end:['End Date','结束日期'], school:['School','学校'], degree:['Degree','学位'],
  major:['Major','专业'], projectName:['Project Name','项目名称'],
  work:['work','工作'], project:['project','项目'], education:['education','教育'], other:['other','其他'],
  helpWork:['Include company, position and dates. What did you mainly work on? What responsibilities did you have? What problems did you solve? What happened as a result? What technologies did you use?','请填写公司、职位和时间。你主要做了什么？承担了哪些职责？解决了什么问题？结果如何？使用了哪些技术？'],
  helpProject:['What was this project about? What exactly did you do? What technologies did you use? What problems did you solve? What was the result?','这个项目做什么？你具体做了什么？使用了哪些技术？解决了什么问题？结果如何？'],
  helpEducation:['Include school, degree, major and dates. Anything else worth mentioning: research, thesis, courses, awards or academic projects?','请填写学校、学位、专业和时间。还可以补充研究、论文、课程、奖项或学术项目。'],
  helpOther:['Describe skills, languages, certifications, research, publications, awards or other useful facts.','请描述技能、语言、证书、研究、出版物、奖项或其他有用的事实。'],
  profileHelp:['You do not need to write like a resume. Describe what you actually did. AI organizes your wording; it must not invent facts or metrics.','不需要写成简历。请描述你实际做过的事情。AI 会整理表述，但不能编造事实或数据。'],
  recordType:['Record type','记录类型'], record:['Career record {number}','职业记录 {number}'], tell:['Tell your Career Agent','描述你的职业经历'],
  removeRecord:['Remove Record','移除记录'], addRecord:['Add Career Record','添加职业记录'], saveRaw:['Save Information','保存信息'],
  normalize:['Normalize Profile','整理档案'], normalizeHelp:['Normalize Profile saves your input first. You can also save and return later.','整理档案会先保存输入。你也可以只保存，稍后继续。'],
  workGroup:['Work Experience','工作经历'], projectGroup:['Projects','项目经历'], educationGroup:['Education','教育经历'], otherGroup:['Research / Certifications / Other Evidence','研究 / 证书 / 其他证据'],
  title:['Title','标题'], description:['Description','描述'], skillsInput:['Skills (comma separated)','技能（用英文逗号分隔）'],
  original:['Original information','原始信息'], noRecords:['No records in this group.','本组尚无记录。'], addSkills:['Add skills within your records.','请在经历记录中添加技能。'],
  skillsGroup:['Skills / Technologies','技能 / 技术'], saveProfile:['Save Profile Edits','保存档案修改'], confirm:['Confirm & Continue','确认并继续'],
  confirmHelp:['Confirm & Continue saves your edits and confirms your entire profile.','确认并继续会保存修改，并确认整个职业档案。'],
  rawHeading:['Original Career Information','原始职业信息'], reviewHeading:['Review Career Profile','审核职业档案'], editRaw:['Edit Original Information','编辑原始信息'], review:['Review Normalized Profile','审核整理后的档案'],
  confirmed:['Your profile is confirmed.','职业档案已确认。'], needsReview:['Review and confirm your profile.','请审核并确认职业档案。'], needsProfile:['Add your original career information to begin.','请先添加原始职业信息。'],
  evidenceCount:['{number} evidence records','{number} 条证据记录'], editProfile:['View / Edit Profile','查看 / 编辑档案'], setupProfile:['Set Up Career Profile','建立职业档案'],
  analysisHelp:['Confirm your Career Profile, analyze a job, inspect requirement coverage and evidence, then explicitly generate a tailored resume.','先确认职业档案，再分析职位、查看要求覆盖率及证据，最后手动生成定制简历。'],
  pasteJD:['Paste Job Description','粘贴职位描述'], analyze:['Analyze Job','分析职位'], reanalyze:['Re-run Job Analysis','重新分析职位'], asNew:['Use as New Job','作为新职位分析'], setupLink:['Set up and confirm your profile','建立并确认职业档案'], analyzeHeading:['Analyze a Job','分析职位'], savedJobs:['Saved Jobs','已保存职位'],
  savedFallback:['Saved Job Description','已保存的职位描述'], noJobs:['No saved analyses yet. Paste a job description to begin.','暂无已保存的分析。粘贴职位描述即可开始。'],
  coverage:['JD Requirement Coverage','职位要求覆盖率'], insufficient:['Insufficient information','信息不足'],
  pending:['Pending','待处理'], complete:['Complete','已完成'], failed:['Failed','失败'], outdated:['Outdated','已过期'],
  MATCH:['MATCH','匹配'], PARTIAL:['PARTIAL','部分匹配'], GAP:['GAP','缺口'], required:['required','必需'], preferred:['preferred','优先'],
  staleJob:['Your Career Profile or job description has changed. Re-run job analysis before generating a resume.','职业档案或职位描述已更改。请重新分析职位后再生成简历。'],
  incomplete:['The latest analysis did not complete. Any report below comes from an earlier successful analysis.','最近一次分析未完成。下方报告来自之前成功的分析。'],
  weights:['Based on {number} extracted requirements. Required requirements have weight 2; preferred requirements have weight 1. MATCH counts as full coverage, PARTIAL as half, and GAP as zero.','基于提取的 {number} 项要求。必需要求权重为 2，优先要求权重为 1。匹配计为完全覆盖，部分匹配计为一半，缺口计为零。'],
  coverageHelp:['This score shows how much of the extracted job requirements your confirmed Career Profile supports. It is not a hiring or interview probability.','该分数表示已确认职业档案对提取的职位要求的支持程度，并非录用或面试概率。'],
  report:['Job Match Report','职位匹配报告'], pastedJD:['Pasted Job Description','已粘贴的职位描述'], responsibilities:['Responsibilities','岗位职责'],
  assessmentMissing:['Assessment unavailable','暂无评估'], jdSource:['JD source','职位描述来源'], extracted:['Extracted Requirements','提取的要求'],
  viewEvidence:['View Evidence','查看证据'], requirement:['Requirement','要求'], evidenceId:['Evidence ID','证据编号'],
  corrections:['Original information and explicit corrections','原始信息与明确修正'], normalized:['Normalized information','整理后的信息'], skills:['Skills','技能'],
  noRequirements:['No requirements were extracted in this category.','此类别未提取到要求。'], requiredHeading:['Required Requirements','必需要求'], preferredHeading:['Preferred Requirements','优先要求'],
  strengths:['Strengths','优势'], gaps:['Gaps','缺口'], focus:['Recommended Resume Focus','建议简历重点'], noItems:['No items were identified.','未识别到项目。'],
  editCareer:['Edit Career Profile','编辑职业档案'], resumeLanguage:['Resume language','简历语言'], English:['English','英语'], Chinese:['Chinese','中文'], Japanese:['Japanese','日语'],
  generate:['Generate Tailored Resume','生成定制简历'], viewResume:['View Resume','查看简历'], activity:['Career Activity','职业活动'], noActivity:['No activity was recorded.','暂无活动记录。'],
  staleResume:['This draft uses an earlier confirmed profile or analysis. Confirm your profile and re-run analysis before generating a new draft.','该草稿使用了之前确认的档案或分析。请确认档案并重新分析后再生成新草稿。'],
  download:['Download Markdown','下载 Markdown'], print:['Print / Save as PDF','打印 / 保存为 PDF'], backReport:['Back to Match Report','返回匹配报告'],
  missingJob:['This job is unavailable. Open Saved Jobs to choose an existing analysis.','此职位不可用。请打开已保存职位，选择现有分析。'], noResume:['This job has no saved resume. Generate one explicitly from its analysis.','此职位尚无已保存简历。请从分析页面手动生成。'], jobDetail:['Job Detail','职位详情'], missingPage:['This page is unavailable.','此页面不可用。'],
  working:['Working on {action}. You can navigate while this completes.','正在{action}。处理期间仍可切换页面。'],
  save_onboarding:['saving information','保存信息'], save_profile:['saving profile edits','保存档案修改'], analyze_job:['analyzing the job','分析职位'], generate_resume:['generating the resume','生成简历'], delete_job:['deleting the job','删除职位'],
  providerLoading:['Loading provider settings.','正在加载模型服务设置。'], providerReady:['Provider access is configured. Readiness does not call the provider.','模型服务已配置。就绪检查不会调用模型服务。'],
  providerStatus:['{provider} · {model} (configured; no background probe)','{provider} · {model}（已配置；无后台探测）'], providerMissing:['Set a provider key in Settings.','请在设置中填写模型服务密钥。'], providerUnavailable:['Provider is unavailable. Choose a configured provider.','模型服务不可用。请选择已配置的服务。'],
  provider:['Provider','模型服务'], model:['Model','模型'], apiKey:['API key','API 密钥'], baseURL:['Base URL','服务地址'], keepKey:['Leave blank to keep the saved key','留空以保留已保存密钥'],
  providerHelp:['The key is saved to your local .env. Saving a changed key or endpoint may call the provider to validate it.','密钥保存在本机 .env 中。保存更改后的密钥或地址时，可能会调用模型服务进行验证。'], saving:['Saving…','正在保存…'], activate:['Save and activate','保存并启用'], providerHeading:['Career Provider Settings','职业模型服务设置'],
  about:['About Career Agent','关于 Career Agent'], attribution:['Career Agent adapts MIT code from Waku by Sean Chen (ShenSeanChen). This independent Career interface does not imply upstream endorsement.','Career Agent 改编自 Sean Chen（ShenSeanChen）的 Waku MIT 代码。此独立职业界面不代表上游认可。'],
  actions:['Contextual actions','当前页面操作'], delete:['Delete Job','删除职位'], cancel:['Cancel','取消'], deleteHeading:['Permanently delete this job?','永久删除此职位？'],
  deleteHelp:['Delete “{title}”? Its saved analysis and generated resume will be permanently removed. Your Career Profile and evidence will remain.','删除“{title}”？已保存的职位分析和生成的简历将永久移除。职业档案及证据会保留。'],
  invalid_job_id:['Provide a valid saved job ID.','请提供有效的已保存职位编号。'], job_not_found:['This saved job no longer exists.','此已保存职位已不存在。'],
  confirmFirst:['Confirm your Career Profile before analyzing a job.','请先确认职业档案，再分析职位。'], normalizeFirst:['Normalize and review your profile first.','请先整理并审核职业档案。'],
  invalidJD:['Paste a job description of at most 60000 characters.','请粘贴不超过 60000 个字符的职位描述。'], unknownJob:['Unknown Career job ID.','未知的职业职位编号。'],
  analysisFirst:['Complete job analysis before generating a resume.','请先完成职位分析，再生成简历。'], staleGate:['Your Career Profile has changed. Re-run job analysis before generating a resume.','职业档案已更改。请重新分析职位后再生成简历。'], usableFirst:['Usable job requirements are required before generating a resume.','生成简历前需要有效的职位要求。'], chooseLanguage:['Choose English, Chinese, or Japanese.','请选择英语、中文或日语。'],
  rawRequired:['Provide basic information and career records.','请提供基本信息和职业记录。'],
  basicText:['Basic information must contain text fields.','基本信息字段必须为文本。'],
  recordRequired:['Add at least one career record.','请至少添加一条职业记录。'],
  recordDescription:['Each career record needs a type and a description.','每条职业记录都需要类型和描述。'],
  fieldsText:['Career fields must contain text values.','职业信息字段必须为文本。'],
  saveFirst:['Save onboarding first.','请先保存原始职业信息。'],
  saveNormalize:['Save onboarding before normalizing.','请先保存原始信息，再整理档案。'],
  normalizationFailed:['Normalization did not produce a valid profile. Please retry.','整理未生成有效的职业档案。请重试。'],
  profileShape:['Profile must contain basic and records.','职业档案必须包含基本信息和经历记录。'],
  basicPreserved:['Basic information must preserve the supplied fields.','基本信息必须保留提供的字段。'],
  oneRecord:['Keep one normalized record per source record.','每条原始记录应对应一条整理后的记录。'],
  recordTitle:['Record title and description must be text.','记录标题和描述必须为文本。'],
  skillsText:['Skills must be a list of text values.','技能必须为文本列表。'],
  configureProvider:['Configure a provider in Settings.','请在设置中配置模型服务。'],
  requestFailed:['The request failed.','请求失败。']
};
CA.defaultLocale = () => {
  try{const saved=localStorage.getItem('career-locale');if(['en','zh-CN'].includes(saved))return saved;}catch(_){}
  return (navigator.languages || [navigator.language || 'en']).some(l=>/^zh-(CN|SG|Hans)(-|$)/i.test(l))?'zh-CN':'en';
};
CA.locale=CA.defaultLocale();
CA.t = (key,values={}) => {
  const pair=CA.messages[key];
  if(!pair)throw new Error(`Unknown UI translation: ${key}`);
  return pair[CA.locale==='zh-CN'?1:0].replace(/\{(\w+)\}/g,(_,name)=>String(values[name] ?? `{${name}}`));
};
CA.number = value => new Intl.NumberFormat(CA.locale,{maximumFractionDigits:1}).format(value);
CA.coverage = value => value===null?CA.t('insufficient'):new Intl.NumberFormat(CA.locale,{style:'percent',maximumFractionDigits:1}).format(value/100);
CA.error = (detail,code='') => {
  const known={
    'Confirm your Career Profile before analyzing a job.':'confirmFirst',
    'Confirm your Career Profile before continuing.':'confirmFirst',
    'Normalize and review your profile first.':'normalizeFirst',
    'Paste a job description of at most 60000 characters.':'invalidJD',
    'Unknown Career job ID.':'unknownJob',
    'Complete job analysis before generating a resume.':'analysisFirst',
    'Your Career Profile has changed. Re-run job analysis before generating a resume.':'staleGate',
    'Usable job requirements are required before generating a resume.':'usableFirst',
    'Choose English, Chinese, or Japanese.':'chooseLanguage'
  };
  for(const key of ['rawRequired','basicText','recordRequired','recordDescription','fieldsText',
    'saveFirst','saveNormalize','normalizationFailed','profileShape','basicPreserved','oneRecord',
    'recordTitle','skillsText','configureProvider','providerMissing'])known[CA.messages[key][0]]=key;
  const key=CA.messages[code]?code:known[detail];
  return key?CA.t(key):CA.locale==='en'?detail:`${CA.t('requestFailed')} ${detail}`;
};
CA.setLocale = locale => {
  if(!['en','zh-CN'].includes(locale))return;
  const active=document.activeElement,focusId=active?.id;
  const fields=[...document.querySelectorAll('#view input,#view textarea,#view select')];
  const index=fields.indexOf(active),start=active?.selectionStart,end=active?.selectionEnd;
  const x=window.scrollX,y=window.scrollY;
  CA.locale=locale;
  try{localStorage.setItem('career-locale',locale);}catch(_){}
  CA.render();
  const next=focusId?document.getElementById(focusId):[...document.querySelectorAll('#view input,#view textarea,#view select')][index];
  next?.focus({preventScroll:true});
  if(next?.setSelectionRange && start!==null && start!==undefined && next.type!=='number'){
    try{next.setSelectionRange(start,end);}catch(_){}
  }
  window.scrollTo(x,y);
};
