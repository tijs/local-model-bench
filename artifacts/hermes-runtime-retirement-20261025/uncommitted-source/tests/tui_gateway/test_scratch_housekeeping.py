"""Serve housekeeping targets the explicit launch and session homes off-turn."""


def test_serve_reaper_checks_launch_and_hosted_profile_scratch(tmp_path, monkeypatch):
    from hermes_constants import get_scratch_dir
    import hermes_constants
    import hermes_constants_scratch_policy as policy
    from tui_gateway import server
    from tui_gateway.scratch_housekeeping import cleanup_served_scratch

    launch, hosted = tmp_path / "launch", tmp_path / "hosted"
    roots = {get_scratch_dir(h, prune=False) for h in (launch, hosted)}
    monkeypatch.setattr(hermes_constants, "get_process_hermes_home", lambda: launch)
    monkeypatch.setattr(server, "_reaper_session_snapshot",
                        lambda: [{"profile_home": str(hosted)}, {"profile_home": str(hosted)}])
    seen = []
    monkeypatch.setattr(policy, "maybe_prune_scratch", lambda root: seen.append(root))
    cleanup_served_scratch()
    assert set(seen) == roots and len(seen) == len(roots)
