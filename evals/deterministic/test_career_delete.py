"""Permanent deletion stays transactional, scoped and independent of AI."""
import json
import sqlite3
import threading

import pytest

from evals.career import run_scenario
from evals.deterministic.test_career_acceptance import JOBS, RAW, AcceptanceClient
from evals.deterministic.test_career_http import request
from waku.config import Settings
from waku.db import connect_career
from waku.ops.career_dashboard import CareerServer
from waku.runtime.career_jobs import JobDeletionError, delete_job
from waku.runtime.career_runtime import CareerRuntime


@pytest.fixture
def saved(tmp_path):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path, check_same_thread=False)
    run_scenario(conn, settings, AcceptanceClient(JOBS[0]), RAW, JOBS[0], 'Chinese')
    with conn:
        conn.execute("INSERT INTO jobs(id,raw_jd,status) VALUES('other','Other JD','failed')")
    yield conn, settings
    conn.close()


def rows(conn, tables):
    return {table: [tuple(row) for row in conn.execute(f'SELECT * FROM {table}')]
            for table in tables}


def test_delete_removes_owned_rows_preserves_profile_evidence_files_and_other_job(saved):
    conn, settings = saved
    job_id = conn.execute("SELECT id FROM jobs WHERE id!='other'").fetchone()[0]
    shared = ['career_profile', 'career_evidence', 'career_evidence_fts']
    before = rows(conn, shared)
    other = tuple(conn.execute("SELECT * FROM jobs WHERE id='other'").fetchone())
    usage = settings.home / 'usage.jsonl'
    usage.write_text('Usage sentinel\n')
    files = {p: p.read_bytes() for p in settings.home.rglob('*')
             if p.is_file() and p.name != 'state.db'}
    # The explicit order also works when foreign-key enforcement is enabled.
    conn.execute('PRAGMA foreign_keys=ON')
    with CareerRuntimeForTest(conn, settings) as runtime:
        result = runtime.action({'action': 'delete_job', 'job_id': job_id})
        assert runtime.client is None
    assert [job['id'] for job in result['jobs']] == ['other']
    assert rows(conn, shared) == before
    assert tuple(conn.execute("SELECT * FROM jobs WHERE id='other'").fetchone()) == other
    for table in ('job_matches', 'job_requirements', 'resumes'):
        assert conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    assert all(path.read_bytes() == data for path, data in files.items())
    reopened = connect_career(settings.home)
    assert reopened.execute('SELECT count(*) FROM jobs').fetchone()[0] == 1
    reopened.close()


class CareerRuntimeForTest:
    """An injected connection remains available for post-shutdown assertions."""
    def __init__(self, conn, settings):
        self.runtime = CareerRuntime(settings, conn=conn,
                                     client_factory=lambda _: pytest.fail('Deletion created AI client'))

    def __enter__(self):
        return self.runtime

    def __exit__(self, *args):
        self.runtime.close()


@pytest.mark.parametrize('table', ['job_matches', 'job_requirements', 'resumes', 'jobs'])
def test_every_delete_step_rolls_back_on_failure(saved, table):
    conn, _ = saved
    tables = ['jobs', 'job_requirements', 'job_matches', 'resumes',
              'career_profile', 'career_evidence', 'career_evidence_fts']
    before = rows(conn, tables)
    job_id = conn.execute("SELECT id FROM jobs WHERE id!='other'").fetchone()[0]
    conn.execute(f"CREATE TEMP TRIGGER fail_delete BEFORE DELETE ON {table} "
                 "BEGIN SELECT RAISE(ABORT,'Synthetic deletion failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match='Synthetic deletion failure'):
        delete_job(conn, job_id)
    assert rows(conn, tables) == before


@pytest.mark.parametrize('job_id', [None, '', ' ', ' other ', [], {}, 42, 'x' * 201, 'bad\x00id'])
def test_malformed_delete_id_is_stable_and_does_not_mutate(saved, job_id):
    conn, _ = saved
    before = rows(conn, ['jobs', 'job_requirements', 'job_matches', 'resumes'])
    with pytest.raises(JobDeletionError) as error:
        delete_job(conn, job_id)
    assert error.value.code == 'invalid_job_id'
    assert rows(conn, list(before)) == before


def test_missing_id_is_stable(saved):
    with pytest.raises(JobDeletionError) as error:
        delete_job(saved[0], 'missing')
    assert error.value.code == 'job_not_found'


def test_http_deletion_uses_action_api_without_ai(saved, monkeypatch):
    conn, settings = saved
    with CareerRuntimeForTest(conn, settings) as runtime:
        server = CareerServer(('127.0.0.1', 0), runtime)
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        try:
            for payload, code in [({'action': 'delete_job'}, 'invalid_job_id'),
                                  ({'action': 'delete_job', 'job_id': 'missing'}, 'job_not_found')]:
                _, _, body = request(server, '/api/career', payload)
                assert json.loads(body)['error_code'] == code
            _, _, body = request(server, '/api/career', {'action': 'delete_job', 'job_id': 'other'})
            assert all(job['id'] != 'other' for job in json.loads(body)['jobs'])
            assert runtime.client is None
            # Only application-owned identifiers may bypass redacted error details.
            class DiagnosticError(ValueError):
                code = 'Private provider metadata sentinel'

            def fail(payload):
                raise DiagnosticError('Safe fallback detail')

            monkeypatch.setattr(runtime, 'action', fail)
            _, _, body = request(server, '/api/career', {'action': 'delete_job', 'job_id': 'other'})
            failure = json.loads(body)
            assert failure == {'error': 'Safe fallback detail', 'error_code': ''}
        finally:
            server.shutdown()
            server.server_close()
            worker.join(5)


def test_delete_waits_for_runtime_serialization(saved):
    conn, settings = saved
    started, done = threading.Event(), threading.Event()
    with CareerRuntimeForTest(conn, settings) as runtime:
        def remove():
            started.set()
            runtime.action({'action': 'delete_job', 'job_id': 'other'})
            done.set()

        with runtime.lock:
            worker = threading.Thread(target=remove)
            worker.start()
            assert started.wait(2)
            assert not done.wait(.05)
            assert conn.execute("SELECT 1 FROM jobs WHERE id='other'").fetchone()
        worker.join(5)
        assert done.is_set()


def test_delete_does_not_call_an_existing_client(saved):
    conn, settings = saved
    class Client:
        def __getattr__(self, name):
            pytest.fail('Deletion accessed the configured provider client')

    client = Client()
    runtime = CareerRuntime(settings, conn=conn, client=client)
    try:
        runtime.action({'action': 'delete_job', 'job_id': 'other'})
        assert runtime.client is client
    finally:
        runtime.close()
