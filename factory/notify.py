"""Effect: tell the operator something happened, on the desktop. Best effort; never raises."""
from factory import proc

TIME_LIMIT = 10.0


def send(title, body) -> bool:
    """Show a desktop notification. True if the notification command reported success."""
    try:
        exit_code, _, _ = proc.capture(["notify-send", title, body], cwd="/", timeout=TIME_LIMIT)
    except (OSError, TimeoutError):
        return False
    return exit_code == 0
