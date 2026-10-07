"""The actual Career asset graph is independent of retired product assets."""
import re
import subprocess
from pathlib import Path

from waku.ops.career_dashboard import CAREER_ASSETS

STATIC = Path(__file__).resolve().parents[2] / 'waku/ops/static'


def test_career_asset_graph_and_handlers():
    html = (STATIC / 'career.html').read_text()
    scripts = re.findall(r'<script src="/static/([^"]+)"', html)
    styles = re.findall(r'<link[^>]+href="/static/([^"]+)"', html)
    assert scripts == [f'career/{name}.js' for name in
                       ('ui', 'i18n', 'state', 'router', 'actions', 'render', 'settings', 'bootstrap')]
    assert styles == ['career/style.css']
    assert set(scripts + styles + ['career.html']) == CAREER_ASSETS
    source = html + ''.join((STATIC / p).read_text() for p in scripts)
    for forbidden in ('VIEWS', 'careerMode', 'editing =', '/api/data', '/api/chat',
                      '/api/events', 'design/', 'waku-mark', 'waku-theme'):
        assert forbidden not in source
    for name in set(re.findall(r'CA\.(\w+)\(', source)):
        assert re.search(rf'CA\.{name}\s*=', source), f'Missing loaded handler: {name}'
    for script in scripts:
        subprocess.run(['node', '--check', str(STATIC / script)], check=True)


def test_career_network_and_timer_contract():
    files = list((STATIC / 'career').glob('*.js'))
    source = '\n'.join(p.read_text() for p in files)
    assert set(re.findall(r"['\"](/api/[^'\"]+)['\"]", source)) == {
        '/api/career', '/api/provider-status', '/api/providers'}
    assert 'setInterval' not in source
    assert source.count('setTimeout(') == 1
    assert 'setTimeout(()=>URL.revokeObjectURL(url),1000)' in source
    assert 'fetch(' not in (STATIC / 'career/render.js').read_text()
    assert 'CA.run(' not in (STATIC / 'career/router.js').read_text()


def test_independent_career_styles_and_print():
    css = (STATIC / 'career/style.css').read_text()
    assert 'url(' not in css and '@import' not in css
    assert '--career-bg:' in css and '[data-theme=dark]' in css
    assert 'body.career-print #view>*:not(.career-resume)' in css
    assert 'body.career-print .career-debug{display:none!important}' in css
    assert '.career-resume h2{font-family:inherit}' in css
    assert 'Noto Sans CJK JP' in css


def test_career_draft_failure_and_retry_state():
    subprocess.run(['node', str(STATIC.parents[2] / 'evals/fixtures/career_state.cjs')],
                   cwd=STATIC.parents[2], check=True)
