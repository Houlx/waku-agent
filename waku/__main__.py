"""Career Agent commands:

  waku                       Career Agent → localhost:7777/#overview (default)
  waku career                explicit Career Agent launch
  waku --help                show these commands

General Waku product commands have been retired from this fork.
"""

from __future__ import annotations

import sys


def _tolerant_stdio() -> None:
    """Windows consoles default to a legacy codepage (cp1252) that cannot
    encode the arrows and middots in our output — printing the dashboard
    banner would crash with UnicodeEncodeError before the server even
    started. Keep the console's encoding but replace what it can't show."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass  # not a real console stream (tests, pipes) — leave it alone


def main() -> None:
    _tolerant_stdio()
    args = sys.argv[1:]
    if not args or args == ["career"]:
        from waku.ops.career_dashboard import main as career_main

        career_main()
    elif args in (["--help"], ["-h"], ["career", "--help"], ["career", "-h"]):
        print(__doc__)
    else:
        print("Unsupported command or arguments. Use 'waku --help' for Career Agent commands.",
              file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
