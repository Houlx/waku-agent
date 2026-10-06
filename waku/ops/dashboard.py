"""Transitional old dashboard shell and debugging/provider facades for C2."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from waku.config import load_settings
from waku.integrations import (
    apply_integration,
    apply_provider,
    apply_provider_disabled,
    test_integration,
)
from waku.ops.catalog import list_models
from waku.ops.settings_api import apply_settings, pin_action, settings_info
from waku.ops.tracing import TraceEncodingError, iter_trace_lines

PORT = 7777


STATIC = Path(__file__).resolve().parent / "static"


def collect() -> dict:
    """Read retained trace diagnostics without starting the retired assistant."""
    settings = load_settings()
    trace_errors, events = [], []
    paths = sorted((settings.home / "traces").glob("*.jsonl"))
    for path in paths:
        try:
            for line in iter_trace_lines(path):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except TraceEncodingError as exc:
            trace_errors.append({"file": path.name, "error": str(exc)})
    return {"settings": settings_info(), "trace_errors": trace_errors,
            "trace_file": paths[-1].name if paths else None, "trace_tail": events[-18:][::-1]}


def career_state():
    from waku.runtime.career_runtime import current_runtime

    return current_runtime().state()


def career_action(payload):
    from waku.runtime.career_runtime import current_runtime

    return current_runtime().action(payload)


def _rel_to_home(path, home) -> str:
    """Path relative to WAKU_HOME if it lives there, else the repo-relative
    'skills/...' path — either way something reveal_path can open."""
    try:
        return str(path.resolve().relative_to(home.resolve()))
    except ValueError:
        return str(path)


def run_query(payload: dict) -> dict:
    """A tiny read-only SQL console (the Supabase-editor idea, scoped down).
    Opens state.db in read-only mode so a write can't slip through, and only
    accepts a single SELECT/WITH statement. Caps at 200 rows."""
    sql = (payload.get("sql") or "").strip().rstrip(";").strip()
    if not sql:
        return {"error": "Type a SELECT query."}
    low = sql.lower()
    if not (low.startswith(("select", "with"))):
        return {"error": "Only SELECT (or WITH … SELECT) queries are allowed."}
    if ";" in sql:
        return {"error": "One statement at a time (no semicolons)."}
    import sqlite3

    settings = load_settings()
    settings.ensure_home()
    db = (settings.home / "state.db").resolve()
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        cur = c.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        data = [[str(r[i]) if r[i] is not None else "" for i in range(len(cols))]
                for r in cur.fetchmany(200)]
        c.close()
        return {"columns": cols, "rows": data}
    except sqlite3.Error as exc:
        return {"error": str(exc)}


def _editor_cmd() -> list[str] | None:
    """The user's code editor CLI: $WAKU_EDITOR, then cursor, then code."""

    custom = os.getenv("WAKU_EDITOR")
    if custom and shutil.which(custom):
        return [custom]
    for cli in ("cursor", "code"):
        if shutil.which(cli):
            return [cli]
    return None


def reveal_path(rel: str) -> dict:
    """Open a file/folder under WAKU_HOME — in the user's code editor if one
    is on PATH (cursor/code/$WAKU_EDITOR), otherwise reveal in Finder.
    Restricted to paths inside WAKU_HOME."""
    import subprocess
    import sys

    settings = load_settings()
    settings.ensure_home()
    home = settings.home.resolve()
    target = (home / (rel or ".")).resolve()
    if target != home and home not in target.parents:
        return {"error": "path is outside the .waku home"}
    if not target.exists():
        return {"error": f"not found: {target}"}

    editor = _editor_cmd()
    if editor and target.is_file() and target.suffix != ".db":  # editors choke on sqlite
        subprocess.run([*editor, str(target)], check=False)
        return {"ok": True, "opened_in": editor[0], "path": str(target)}
    if sys.platform != "darwin":
        return {"error": f"no editor found and reveal is macOS-only — the path is {target}"}
    subprocess.run(
        ["open", "-R", str(target)] if target.is_file() else ["open", str(target)],
        check=False,
    )
    return {"ok": True, "revealed": str(target)}


def events_since(cursor):
    """Read new trace events past a line cursor in today's trace file.

    cursor=None returns the current tail without replaying stored events.
    """
    settings = load_settings()
    settings.ensure_home()
    path = settings.home / "traces" / (datetime.now().strftime("%Y-%m-%d") + ".jsonl")
    if not path.exists():
        return {"events": [], "cursor": 0}
    try:
        lines = list(iter_trace_lines(path))
    except TraceEncodingError as exc:
        return {"events": [], "cursor": 0, "error": str(exc)}
    if cursor is None or cursor < 0 or cursor > len(lines):
        return {"events": [], "cursor": len(lines)}
    out = []
    for ln in lines[cursor:]:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return {"events": out, "cursor": len(lines)}


STATIC_TYPES = {".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
                ".html": "text/html; charset=utf-8", ".woff2": "font/woff2"}


LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, *, no_cache: bool = False) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # The frontend files (app.js/style.css) change as we develop; without
        # this the browser serves a stale cached copy and edits look "missing".
        if no_cache:
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import parse_qs, urlsplit

        parsed = urlsplit(self.path)
        if parsed.path == "/api/career":
            self._send(json.dumps(career_state()).encode(), "application/json")
        elif parsed.path == "/api/data":
            self._send(json.dumps(collect(), default=str).encode(), "application/json")
        elif parsed.path == "/api/models":
            provider = parse_qs(parsed.query).get("provider", [None])[0]
            self._send(json.dumps(list_models(provider)).encode(), "application/json")
        elif parsed.path == "/api/events":
            raw = parse_qs(parsed.query).get("cursor", [None])[0]
            cursor = int(raw) if raw and raw.lstrip("-").isdigit() else None
            self._send(json.dumps(events_since(cursor)).encode(), "application/json")
        elif parsed.path == "/api/reveal":
            rel = parse_qs(parsed.query).get("path", [""])[0]
            self._send(json.dumps(reveal_path(rel)).encode(), "application/json")
        elif self.path.startswith("/static/"):
            self._serve_static(self.path)
        elif parsed.path == "/":
            self._send((STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def _serve_static(self, path: str) -> None:  # the frontend files
        name = path.split("/static/", 1)[1].split("?")[0]
        target = (STATIC / name).resolve()
        if STATIC.resolve() not in target.parents or not target.is_file():
            self.send_response(404)
            self.end_headers()
            return
        ctype = STATIC_TYPES.get(target.suffix, "application/octet-stream")
        self._send(target.read_bytes(), ctype, no_cache=True)

    def do_POST(self):
        routes = {"/api/career": career_action, "/api/settings": apply_settings,
                  "/api/query": run_query, "/api/pin": pin_action}
        if self.path not in routes and self.path not in (
                "/api/connections", "/api/connections/test", "/api/providers"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or "{}")
        try:
            if self.path == "/api/connections":
                out = asdict(apply_integration(payload.get("key", ""), payload.get("values") or {},
                                             tuple(payload.get("clear") or ()),
                                             force=bool(payload.get("force"))))
            elif self.path == "/api/connections/test":
                out = asdict(test_integration(payload.get("key", "")))
            elif self.path == "/api/providers":
                if "disabled" in payload and set(payload) <= {"provider", "disabled"}:
                    out = asdict(apply_provider_disabled(payload.get("provider", ""),
                                                         disabled=bool(payload["disabled"])))
                else:
                    out = asdict(apply_provider(**payload))
            else:
                out = routes[self.path](payload)
        except Exception as exc:
            out = {"error": f"{type(exc).__name__}: {exc}"}
        self._send(json.dumps(out, default=str).encode(), "application/json")

    def log_message(self, *args):  # keep the terminal quiet
        pass

def bind_host() -> str:
    """Where the dashboard listens. Loopback unless told otherwise.

    A container has to answer on its own address, so this is configurable —
    but the dashboard has no authentication and its SQL console runs
    arbitrary SQL, so leaving loopback prints a warning to the terminal that
    chose it.
    """
    host = os.getenv("WAKU_DASHBOARD_HOST", "127.0.0.1").strip() or "127.0.0.1"
    if host not in LOOPBACK:
        print(f"warning: WAKU_DASHBOARD_HOST={host} — the dashboard has no "
              f"authentication and its SQL console runs arbitrary SQL. "
              f"Only do this behind something that authenticates.")
    return host


def main() -> None:
    # Port precedence: WAKU_DASHBOARD_PORT, then the conventional PORT (used by
    # deploy platforms and IDE preview panes), then 7777. If it's taken, walk on.
    base = int(os.getenv("WAKU_DASHBOARD_PORT") or os.getenv("PORT") or PORT)
    # Resolved once, above the walk: the environment cannot change between
    # iterations, and bind_host() prints the off-loopback security warning. Ten
    # busy ports used to print it ten times, which teaches people to skip it.
    host = bind_host()
    from waku.config import home_notice
    if notice := home_notice():
        print(notice)
    for port in range(base, base + 10):  # walk past a busy port instead of crashing
        try:
            server = ThreadingHTTPServer((host, port), Handler)
        except OSError:
            print(f"port {port} busy, trying {port + 1}…")
            continue
        print(f"Waku dashboard → http://localhost:{port}  (Ctrl-C to stop)")
        try:
            server.serve_forever()
        finally:
            from waku.runtime.career_runtime import close_runtime

            close_runtime()
            server.server_close()
        return
    raise SystemExit(f"no free port in {base}–{base + 9}")


if __name__ == "__main__":
    main()
