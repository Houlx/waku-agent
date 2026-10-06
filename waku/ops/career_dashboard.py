"""Explicit Career launch path, retaining the old dashboard for rollback."""
from __future__ import annotations

import json
import os
from errno import EADDRINUSE
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from waku.ops.provider_services import redact_error
from waku.runtime.career_runtime import CareerRuntime

STATIC = Path(__file__).resolve().parent / 'static'
STATIC_TYPES = {'.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml',
                '.html': 'text/html; charset=utf-8', '.woff2': 'font/woff2'}


class CareerServer(ThreadingHTTPServer):
    """The server owns the runtime it creates; injected runtimes belong to callers."""

    def __init__(self, address, runtime=None):
        self.runtime = runtime
        self._owns_runtime = runtime is None
        try:
            super().__init__(address, Handler)
            if self.runtime is None:
                self.runtime = CareerRuntime()
        except BaseException:
            self.server_close()
            raise

    def server_close(self):
        try:
            if hasattr(self, 'socket'):
                super().server_close()
        finally:
            if self._owns_runtime and self.runtime is not None:
                self.runtime.close()


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype='application/json', status=200):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(body)

    def _json(self, value, status=200):
        self._send(json.dumps(value, ensure_ascii=False).encode('utf-8'), status=status)

    def _file(self, target):
        self._send(target.read_bytes(), STATIC_TYPES.get(target.suffix, 'application/octet-stream'))

    def do_GET(self):
        url = urlsplit(self.path)
        runtime = self.server.runtime
        try:
            if url.path == '/api/career':
                self._json(runtime.state())
            elif url.path == '/api/provider-status':
                self._json(runtime.provider_status())
            elif url.path == '/api/models':
                provider = parse_qs(url.query).get('provider', [None])[0]
                self._json(runtime.models(provider))
            elif url.path == '/':
                self._file(STATIC / 'career.html')
            elif url.path.startswith('/static/'):
                target = (STATIC / unquote(url.path[len('/static/'):])).resolve()
                if STATIC.resolve() not in target.parents or not target.is_file():
                    self._json({'error': 'Static file not found.'}, 404)
                else:
                    self._file(target)
            else:
                self._json({'error': 'Unknown Career route.'}, 404)
        except Exception as exc:
            self._json({'error': redact_error(exc)})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in {'/api/career', '/api/providers'}:
            self._json({'error': 'Unknown Career route.'}, 404)
            return
        payload = {}
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 2_000_000:
                raise ValueError('Request is too large.')
            payload = json.loads(self.rfile.read(length) or '{}')
            if not isinstance(payload, dict):
                raise TypeError('Request must be a JSON object.')
            runtime = self.server.runtime
            result = (runtime.action(payload) if path == '/api/career'
                      else runtime.configure_provider(payload))
            self._json(result)
        except Exception as exc:
            secrets = [payload.get(k) for k in ('key', 'custom_key')] if isinstance(payload, dict) else []
            self._json({'error': redact_error(exc, secrets)})

    def log_message(self, *args):
        pass


def bind_host():
    host = os.getenv('WAKU_DASHBOARD_HOST', '127.0.0.1').strip() or '127.0.0.1'
    if host not in {'127.0.0.1', '::1', 'localhost'}:
        print(f'warning: WAKU_DASHBOARD_HOST={host} — Career has no authentication. '
              'Only use this behind something that authenticates.')
    return host


def main():
    base = int(os.getenv('WAKU_DASHBOARD_PORT') or os.getenv('PORT') or '7777')
    host = bind_host()
    for port in range(base, base + 10):
        try:
            server = CareerServer((host, port))
        except OSError as exc:
            if exc.errno == EADDRINUSE:
                continue
            raise
        print(f'Career Agent → http://localhost:{server.server_port}/#career  (Ctrl-C to stop)')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    raise SystemExit(f'no free port in {base}–{base + 9}')


if __name__ == '__main__':
    main()
