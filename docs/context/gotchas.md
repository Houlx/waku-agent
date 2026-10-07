# Gotchas

Traps someone already stepped on. This is the only append-only file in the
rulebook. Each entry is one line: a date, a title, the trap and the right
move, and the condition that retires it. The file holds 40 entries at most,
and anyone deletes an entry that no longer holds, in the PR that makes it
false. A gotcha that can become a test should become one.

- **[2026-09-13] Changing only the URL hash does not reload the dashboard's CSS or JS** — switching views with `#view` keeps the old stylesheets, so a CSS edit looks like it failed. Hard-reload, or change the query string. _Retire when: the dashboard serves assets with a content hash._
- **[2026-09-14] python-dotenv's `set_key` replaces a symlinked `.env` with a real file** — saving a setting from the dashboard inside a worktree detaches the linked `.env`. Check that `.env` is still a symlink before deleting a worktree. _Retire when: settings stop being written through `set_key`._

- **[2026-10-06] Same-route hash navigation emits no hashchange** — Analyze New Job can clear its reanalysis target while staying at `#jobs`. Call the route renderer for explicit same-route navigation so labels and navigation guards update. _Retire when: Career no longer uses hashchange routing._
