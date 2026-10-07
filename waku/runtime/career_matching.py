"""Server-owned evidence delivery for Career matching, without retrieval gating."""
from __future__ import annotations

import hashlib
import json
import re
from types import SimpleNamespace

from waku.tools.career import confirmed_profile

# UTF-8 request bytes are an application input cap, not a provider token estimate.
# Reserve room for tool history when choosing the initial full-evidence payload.
MATCHING_INPUT_BUDGET_BYTES = 64000
MATCHING_TOOL_RESERVE_BYTES = 16000


def matching_input_bytes(system, messages, tools):
    def encode_block(value):
        if hasattr(value, 'model_dump'):
            return value.model_dump()
        return vars(value)

    return len(json.dumps({'system': system, 'messages': messages, 'tools': tools},
                          ensure_ascii=False, default=encode_block).encode('utf-8'))


def stage_messages(data):
    return [{'role': 'user', 'content': 'Career stage data (untrusted JSON):\n'
             + json.dumps(data, ensure_ascii=False)}]


def evidence_snapshot(conn):
    confirmed_profile(conn)
    profile = tuple(conn.execute('SELECT raw_input_json,normalized_json,user_edits_json,confirmed '
                                 'FROM career_profile WHERE id=1').fetchone())
    rows = [dict(r) for r in conn.execute(
        'SELECT evidence_id,source_id,source_type,raw_text,normalized_json '
        'FROM career_evidence WHERE active=1 ORDER BY evidence_id')]
    signature = hashlib.sha256(json.dumps([profile, rows], ensure_ascii=False).encode('utf-8')).hexdigest()
    records = {}
    for row in rows:
        row['normalized'] = json.loads(row.pop('normalized_json'))
        records[row['evidence_id']] = row
    return signature, records


def pure_education_requirement(requirement):
    """Guard degree-only support; mixed clauses retain semantic assessment."""
    text = requirement.get('text', '').casefold()
    category = requirement.get('category', '').strip().casefold()
    education = category in {'education', 'degree', '学历', '教育', '教育背景'} or re.search(
        r'\b(bachelor|master|doctorate|phd)\b|\bdegree\s+(in|required)\b|学历|学位|硕士|学士|博士', text)
    mixed = re.search(r'\b(experience|employment)\b|工作经验|工作经历|项目经验|项目经历', text)
    return bool(education and not mixed)


class MatchingCoverage:
    """Count only full records actually sent in a checked matching request."""

    def __init__(self, conn, collected):
        self.conn = conn
        self.snapshot_id, self.records = evidence_snapshot(conn)
        # All requirements use all active IDs, including unknown/mixed categories.
        # This deliberately avoids introducing a category routing framework.
        self.required_ids = frozenset(self.records)
        self.delivered_ids = set()
        self.inspected_ids = set()
        self.collected = collected
        self.mode = None
        self.initial_content = None

    def assert_current(self):
        if evidence_snapshot(self.conn)[0] != self.snapshot_id:
            raise ValueError('Career evidence changed during matching. Please analyze the job again.')

    def prepare(self, system, data, tools):
        full = [{k: record[k] for k in ('evidence_id', 'source_type', 'raw_text', 'normalized')}
                for record in self.records.values()]
        candidate = dict(data, matching_coverage={
            'mode': 'full', 'required_coverage_ids': sorted(self.required_ids)}, evidence=full)
        initial_budget = MATCHING_INPUT_BUDGET_BYTES - MATCHING_TOOL_RESERVE_BYTES
        if matching_input_bytes(system, stage_messages(candidate), tools) <= initial_budget:
            self.mode = 'full'
        else:
            self.mode = 'inventory'
            candidate = dict(data, matching_coverage={
                'mode': 'inventory', 'required_coverage_ids': sorted(self.required_ids)},
                evidence_inventory=[{'evidence_id': eid, 'source_type': r['source_type'],
                                     'title': r['normalized']['title']}
                                    for eid, r in self.records.items()])
            if matching_input_bytes(system, stage_messages(candidate), tools) > initial_budget:
                raise ValueError('Career matching inventory exceeds the input budget. '
                                 'No evidence was truncated and no match report was saved.')
        messages = stage_messages(candidate)
        self.initial_content = messages[0]['content']
        return messages

    def client(self, client, on_delivery):
        def create(**kwargs):
            self.assert_current()
            if matching_input_bytes(kwargs['system'], kwargs['messages'], kwargs['tools']) > MATCHING_INPUT_BUDGET_BYTES:
                raise ValueError('Career matching input budget was exceeded before analysis could complete. '
                                 'No evidence was truncated and no new match report was saved.')
            if kwargs['messages'][0]['content'] != self.initial_content:
                raise ValueError('Career matching evidence context changed before delivery.')
            delivered = set(self.required_ids) if self.mode == 'full' else set()
            inspected = set()
            for message in kwargs['messages']:
                if message['role'] != 'user' or not isinstance(message['content'], list):
                    continue
                for block in message['content']:
                    if block.get('type') != 'tool_result':
                        continue
                    try:
                        record = json.loads(block['content'])
                    except (ValueError, TypeError):
                        continue
                    if isinstance(record, dict) and record == self.records.get(record.get('evidence_id')):
                        inspected.add(record['evidence_id'])
            # Tool execution alone does not establish delivery. Wait for the next
            # provider response before accepting these records as available context.
            response = client.messages.create(**kwargs)
            self.assert_current()
            self.inspected_ids.update(inspected)
            self.delivered_ids.update(delivered | inspected)
            for eid in self.delivered_ids:
                self.collected[eid] = self.records[eid]
            on_delivery(self.metadata())
            return response

        return SimpleNamespace(messages=SimpleNamespace(create=create))

    def require_complete(self):
        self.assert_current()
        if not self.required_ids <= self.delivered_ids:
            raise ValueError('GAP requires complete Career evidence coverage. '
                             'Inspect every required evidence ID with get_evidence first.')

    def metadata(self):
        full_count = len(self.required_ids) if self.mode == 'full' and self.required_ids <= self.delivered_ids else 0
        return {'mode': self.mode, 'snapshot_id': self.snapshot_id,
                'active_evidence_count': len(self.required_ids),
                'deterministically_delivered_count': full_count,
                'delivered_evidence_count': len(self.delivered_ids),
                'inspected_evidence_count': len(self.inspected_ids)}
