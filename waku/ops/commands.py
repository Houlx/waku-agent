"""Retired workflow command facade retained until Batch C2."""


def discover() -> dict[str, str]:
    return {}


def describe() -> str:
    return "General graph workflows are retired."


def parse(message: str) -> tuple[str, str] | None:
    """('graphs', '') / ('gather', 'rest of line') / None if not a command.

    A leading slash only counts at the very start and with no space after it,
    so a message that merely mentions a path is still a message.
    """
    text = (message or "").strip()
    if not text.startswith("/") or text.startswith("/ "):
        return None
    head, _, rest = text[1:].partition(" ")
    return head.strip().lower(), rest.strip()


def run(name: str, emit, arg: str = "") -> dict | None:
    return None


def unknown_reply(name: str) -> str:
    return "General graph workflows are retired."
