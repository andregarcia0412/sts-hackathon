"""Which process runs an analysis, so a server start only fails the analyses whose process is really gone.

A CLI benchmark runs analyses in its own process; starting (or reloading) the server must not mark them."""

import os
import socket
import uuid
from datetime import UTC, datetime
from pathlib import Path

_FALLBACK_BOOT = uuid.uuid4().hex  # no /proc: a process-scoped id (a reboot then looks like a new machine)


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return _FALLBACK_BOOT


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{boot_id()}"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # exists, owned by someone else
        return True
    return True


def is_orphan(worker: str | None, heartbeat_at: datetime | None, stale_after_s: float,
              now: datetime | None = None) -> bool:
    """True when the analysis can no longer finish: no worker recorded (old data), a dead process of this host
    (or of a previous boot), or a silent worker of another host for longer than `stale_after_s`."""
    if not worker:
        return True
    host, _, rest = worker.partition(":")
    pid_text, _, boot = rest.partition(":")
    if host == socket.gethostname():
        if boot != boot_id():
            return True
        try:
            pid = int(pid_text)
        except ValueError:
            return True
        return not pid_alive(pid)
    if heartbeat_at is None:
        return True
    moment = heartbeat_at if heartbeat_at.tzinfo else heartbeat_at.replace(tzinfo=UTC)
    return ((now or datetime.now(UTC)) - moment).total_seconds() > stale_after_s
