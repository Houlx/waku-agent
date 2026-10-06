"""Career Day 1 behavior, exercised with the real loop and offline model."""
import json

import pytest

from evals.helpers import ScriptedClient, response, text_block, tool_block
from waku.config import Settings
from waku.db import connect_career as connect
from waku.runtime.career import action, state


@pytest.fixture
def world(tmp_path):
    settings = Settings(home=tmp_path, model='offline', max_iterations=3)
    settings.ensure_home()
    conn = connect(tmp_path)
    raw = {'basic': {'Name': 'Alex'}, 'records': [
        {'source_id': 'project-one', 'type': 'project',
         'text': 'I migrated React 16 to React 18 and fixed compatibility problems.'}]}
    action(conn, {'action': 'save_onboarding', 'raw': raw})
    return conn, settings, raw


def proposal():
    return {'basic': {'Name': 'Alex'}, 'records': [
        {'source_id': 'project-one', 'title': 'React migration',
         'description': 'Migrated React 16 to React 18 and resolved compatibility problems.',
         'skills': ['React']}]}


def normalize(world, profile=None):
    conn, settings, _ = world
    client = ScriptedClient([
        response([tool_block('submit_stage_result', {'profile': profile or proposal()})], 'tool_use'),
        response([text_block('Profile ready for review.')])])
    return action(conn, {'action': 'normalize'}, settings, client)


def test_journey_persists_raw_and_coarse_evidence(world):
    conn, settings, raw = world
    result = normalize(world)
    assert result['profile']['raw'] == raw
    assert not result['profile']['confirmed']
    assert len(result['evidence']) == 1
    evidence = result['evidence'][0]
    assert evidence['evidence_id'] == 'career-project-one'
    assert evidence['raw_text'] == raw['records'][0]['text']
    assert conn.execute("SELECT count(*) FROM career_evidence_fts WHERE career_evidence_fts MATCH 'React'").fetchone()[0] == 1
    action(conn, {'action': 'confirm'})
    reopened = connect(settings.home)
    assert state(reopened)['profile']['confirmed']
    tables = {row[0] for row in reopened.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not {'facts', 'chat_log', 'episodes'} & tables
    trace = ''.join(p.read_text() for p in (settings.home / 'traces').glob('*.jsonl'))
    assert json.loads(trace.splitlines()[0])['type'] == 'turn_start'
    assert (settings.home / 'usage.jsonl').exists()
    reopened.close()


def test_confirmation_saves_user_edits_and_retains_original(world):
    conn, _, raw = world
    normalize(world)
    edited = proposal()
    edited['basic']['Name'] = 'Alex Chen'
    edited['records'][0]['description'] = 'I coordinated the React migration.'
    result = action(conn, {'action': 'confirm', 'profile': edited})
    assert result['profile']['confirmed']
    assert result['profile']['normalized'] == edited
    assert result['profile']['raw'] == raw
    assert 'Explicit user edit' in result['evidence'][0]['raw_text']
    assert result['evidence'][0]['evidence_id'] == 'career-project-one'
    edits = json.loads(conn.execute('SELECT user_edits_json FROM career_profile').fetchone()[0])
    assert edits['basic'] == edited['basic']
    assert edits['records']['project-one'] == edited['records'][0]
    action(conn, {'action': 'save_profile', 'profile': edited})
    assert not state(conn)['profile']['confirmed']


@pytest.mark.parametrize('change', ['source', 'metric', 'duplicate'])
def test_invalid_normalization_never_publishes(world, change):
    candidate = proposal()
    if change == 'source':
        candidate['records'][0]['source_id'] = 'imaginary'
    elif change == 'metric':
        candidate['records'][0]['description'] += ' Improved performance by 70%.'
    else:
        candidate['records'].append(candidate['records'][0])
    with pytest.raises(ValueError, match='valid profile'):
        normalize(world, candidate)
    result = state(world[0])
    assert result['profile']['normalized'] is None
    assert result['evidence'] == []


def test_missing_profile_and_unknown_actions(world):
    with pytest.raises(ValueError, match='review'):
        action(world[0], {'action': 'confirm'})
    with pytest.raises(ValueError, match='Unknown Career'):
        action(world[0], {'action': 'unknown_action'})


def test_provider_failure_preserves_saved_input(world):
    with pytest.raises(IndexError):
        action(world[0], {'action': 'normalize'}, world[1], ScriptedClient([]))
    assert state(world[0])['profile']['raw'] == world[2]
    assert state(world[0])['profile']['normalized'] is None


def test_onboarding_replaces_current_profile_and_deactivates_evidence(world):
    normalize(world)
    raw = world[2]
    raw['records'] = [{'type': 'education', 'text': 'Studied computer science.'}]
    result = action(world[0], {'action': 'save_onboarding', 'raw': raw})
    assert not result['profile']['confirmed']
    assert result['profile']['normalized'] is None
    assert result['evidence'] == []
    assert result['profile']['raw']['records'][0]['source_id']


def test_first_visit(tmp_path):
    assert state(connect(tmp_path)) == {'profile': None, 'evidence': [], 'jobs': []}


def test_dashboard_handlers_use_the_existing_model_and_keep_chat_empty(world, monkeypatch):
    from waku.ops import dashboard
    from waku.runtime import career_runtime

    conn, settings, _ = world
    monkeypatch.setattr(dashboard, 'load_settings', lambda: settings)
    client = ScriptedClient([
        response([tool_block('submit_stage_result', {'profile': proposal()})], 'tool_use'),
        response([text_block('Done.')])])
    runtime = career_runtime.CareerRuntime(conn=conn, settings=settings, client=client)
    monkeypatch.setattr(career_runtime, '_runtime', runtime)
    assert dashboard.career_state()['profile']['normalized'] is None
    assert dashboard.career_action({'action': 'normalize'})['profile']['normalized'] == proposal()
    assert dashboard.career_action({'action': 'confirm'})['profile']['confirmed']
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not {'facts', 'chat_log', 'episodes'} & tables


def test_iteration_limit_does_not_publish_partial_stage(world):
    conn, settings, _ = world
    settings.max_iterations = 1
    client = ScriptedClient([
        response([tool_block('submit_stage_result', {'profile': proposal()})], 'tool_use')])
    with pytest.raises(ValueError, match='valid profile'):
        action(conn, {'action': 'normalize'}, settings, client)
    assert state(conn)['profile']['normalized'] is None


def test_structured_fields_are_preserved_in_provenance(world):
    conn, _, raw = world
    raw['records'][0]['fields'] = {'Project Name': 'UI Upgrade', 'Start Date': '2024'}
    action(conn, {'action': 'save_onboarding', 'raw': raw})
    result = normalize(world)
    assert result['profile']['raw'] == raw
    assert 'UI Upgrade' in result['evidence'][0]['raw_text']
    assert '2024' in result['evidence'][0]['raw_text']


def test_confirmation_without_changes_does_not_fabricate_user_edits(world):
    result = normalize(world)
    confirmed = action(world[0], {'action': 'confirm', 'profile': result['profile']['normalized']})
    assert 'Explicit user edit' not in confirmed['evidence'][0]['raw_text']
    assert json.loads(world[0].execute('SELECT user_edits_json FROM career_profile').fetchone()[0]) == {}
