"""Scratch cleanup for long-lived legacy serve backends, including hosted profiles."""

from pathlib import Path


def cleanup_served_scratch() -> None:
    from hermes_constants import get_process_hermes_home
    from hermes_constants_scratch_policy import maybe_prune_scratch
    from tui_gateway import server

    homes = {get_process_hermes_home()}
    for session in server._reaper_session_snapshot():
        if session.get("profile_home"):
            homes.add(Path(session["profile_home"]))
    for home in homes:
        root = home / "cache" / "scratch"
        if root.is_dir():
            maybe_prune_scratch(root)
