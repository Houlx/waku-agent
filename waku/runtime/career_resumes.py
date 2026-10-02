"""One cited resume per job, generated only by an explicit Career action."""
from __future__ import annotations

import json
import re
import uuid

from waku.runtime.career_jobs import (
    TEXT,
    TEXTS,
    object_schema,
    require_keys,
    require_text,
    run_stage,
)
from waku.tools.career import confirmed_profile, get_evidence, make_evidence_tool

LANGUAGES = ('English', 'Chinese', 'Japanese')
CLAIM = object_schema({'text': TEXT, 'evidence_ids': TEXTS})
RESUME_SCHEMA = object_schema({
    'summary': {'type': 'array', 'items': CLAIM},
    'skills': {'type': 'array', 'items': CLAIM},
    'records': {'type': 'array', 'items': object_schema({
        'evidence_id': TEXT, 'bullets': {'type': 'array', 'items': CLAIM}})}})


def saved_resume(conn, job_id):
    row = conn.execute('SELECT * FROM resumes WHERE job_id=?', (job_id,)).fetchone()
    if not row:
        return None
    resume = dict(row)
    resume['outdated'] = bool(resume['outdated'])
    resume['content'] = json.loads(resume.pop('content_json'))
    resume['activity'] = json.loads(resume.pop('activity_json'))
    resume['markdown'] = markdown(resume['content'], resume['language'])
    return resume


def validate_resume(value, conn, collected):
    require_keys(value, RESUME_SCHEMA['properties'], 'Resume')

    def claims(items, owner=None):
        if not isinstance(items, list) or len(items) > 100:
            raise ValueError('Resume claims must be a bounded list.')
        for claim in items:
            require_keys(claim, ('text', 'evidence_ids'), 'Resume claim')
            require_text(claim['text'], 'Resume claim')
            ids = claim['evidence_ids']
            if (not isinstance(ids, list) or not ids or len(ids) > 20
                    or not all(isinstance(eid, str) for eid in ids) or len(set(ids)) != len(ids)):
                raise ValueError('Every substantive claim needs unique evidence references.')
            if owner and owner not in ids:
                raise ValueError('Record bullets must cite their own evidence.')
            records = [get_evidence(conn, eid) for eid in ids]
            if any(eid not in collected for eid in ids):
                raise ValueError('Inspect every resume citation before submitting.')
            # Numbers, including dates and metrics, must occur in the cited factual input.
            numbers = set(re.findall(r'\d+(?:[.,]\d+)*%?', claim['text']))
            supplied = set(re.findall(r'\d+(?:[.,]\d+)*%?', '\n'.join(r['raw_text'] for r in records)))
            if not numbers <= supplied:
                raise ValueError('Resume dates and metrics must preserve supplied numbers.')

    claims(value['summary'])
    claims(value['skills'])
    if not isinstance(value['records'], list) or not 1 <= len(value['records']) <= 100:
        raise ValueError('Select at least one supported career record.')
    seen = set()
    for record in value['records']:
        require_keys(record, ('evidence_id', 'bullets'), 'Resume record')
        eid = record['evidence_id']
        evidence = get_evidence(conn, eid)
        if eid not in collected or eid in seen:
            raise ValueError('Select unique inspected career records.')
        seen.add(eid)
        claims(record['bullets'], eid)
        # Canonical headings are application-owned: the model cannot alter protected fields.
        record['source_type'] = evidence['source_type']
        record['title'] = evidence['normalized']['title']
    return value


def generate_resume(conn, job_id, language, settings, client):
    confirmed_profile(conn)
    job = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not job or job['status'] != 'complete':
        raise ValueError('Complete job analysis before generating a resume.')
    if job['outdated']:
        raise ValueError('Your Career Profile has changed. Re-run job analysis before generating a resume.')
    requirements = [dict(r) for r in conn.execute('SELECT * FROM job_requirements WHERE job_id=?', (job_id,))]
    if not requirements or job['coverage'] is None:
        raise ValueError('Usable job requirements are required before generating a resume.')
    if language not in LANGUAGES:
        raise ValueError('Choose English, Chinese, or Japanese.')
    profile_row = conn.execute('SELECT * FROM career_profile WHERE id=1').fetchone()
    profile = json.loads(profile_row['normalized_json'])
    raw = json.loads(profile_row['raw_input_json'])
    edits = json.loads(profile_row['user_edits_json'])
    collected, activity = {}, []

    def validate(value):
        value = validate_resume(value, conn, collected)
        sources = {r['source_id']: r for r in raw['records']}
        for record in value['records']:
            evidence = collected[record['evidence_id']]
            record['fields'] = sources[evidence['source_id']].get('fields', {})
        return value

    content = run_stage(settings, client, 'resume generation',
                        'Write a truthful tailored resume in the selected language. Select relevant records and '
                        'inspect each with get_evidence. Cite every summary, skill and bullet. A GAP remains '
                        'unsupported; never add qualifications requested by the JD. Never invent employers, '
                        'positions, projects, responsibilities, technologies, education, research, certifications, '
                        'achievements, dates, metrics or years of experience. Preserve canonical names, titles, '
                        'dates and metrics verbatim, even when translating prose. Do not put employer names, '
                        'job titles or dates in generated bullets; the application renders factual headings. '
                        'Return only summary, skills and records; each record selects an evidence_id and bullets.',
                        {'job_id': job_id, 'language': language, 'career_profile': profile, 'raw_profile': raw, 'explicit_edits': edits,
                         'job_description': job['raw_jd'], 'job_analysis': requirements,
                         'match_report': json.loads(job['report_json']),
                         'available_evidence_ids': [r[0] for r in conn.execute(
                             'SELECT evidence_id FROM career_evidence WHERE active=1')]},
                        RESUME_SCHEMA, validate, (make_evidence_tool(conn, collected),), activity=activity)
    activity.append({'stage': 'resume evidence selection', 'status': 'complete',
                     'result': f"Selected {len(content['records'])} career records with inspected citations."})
    content['basic'] = profile['basic']
    content['evidence'] = collected
    with conn:
        conn.execute('INSERT INTO resumes(id,job_id,language,content_json,activity_json) VALUES(?,?,?,?,?) '
                     'ON CONFLICT(job_id) DO UPDATE SET language=excluded.language,content_json=excluded.content_json,'
                     'activity_json=excluded.activity_json,outdated=0,updated_at=CURRENT_TIMESTAMP',
                     (uuid.uuid4().hex, job_id, language, json.dumps(content, ensure_ascii=False), json.dumps(activity)))


def markdown(content, language):
    labels = {'English': ('Professional Summary', 'Skills'), 'Chinese': ('职业概述', '技能'),
              'Japanese': ('職務要約', 'スキル')}[language]
    # Escape Markdown syntax so user facts remain text in downloaded files.
    def literal(text):
        return re.sub(r'([\\`*_{}\[\]<>#!|])', r'\\\1', text).replace('\n', ' ')

    lines = [literal(v) for v in content['basic'].values() if v]
    for key, label in zip(('summary', 'skills'), labels, strict=True):
        if content[key]:
            lines += ['', '## ' + label] + ['- ' + literal(c['text']) for c in content[key]]
    for record in content['records']:
        lines += ['', '## ' + literal(record['title'])]
        lines += [literal(v) for v in record['fields'].values() if v]
        lines += ['- ' + literal(c['text']) for c in record['bullets']]
    return '\n'.join(lines) + '\n'
