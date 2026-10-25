"""Classic CLI storage maintenance keeps ticking while the prompt is idle."""

from types import SimpleNamespace


def test_cli_storage_loop_keeps_checking_its_captured_home(tmp_path, monkeypatch):
    from hermes_cli.cli_auto_maintenance import _storage_maintenance_loop
    import hermes_constants_scratch_policy as policy
    import tools.checkpoint_maintenance as checkpoint

    seen = []
    stop = SimpleNamespace(ticks=0)
    stop.is_set = lambda: stop.ticks >= 2

    def wait(timeout=None):
        stop.ticks += 1
        return stop.is_set()

    stop.wait = wait
    monkeypatch.setattr(checkpoint, "auto_prune_from_config", lambda: None)
    monkeypatch.setattr(policy, "maybe_prune_scratch", lambda root: seen.append(root))
    _storage_maintenance_loop(tmp_path, stop)
    assert seen == [tmp_path / "cache" / "scratch"] * 2


def test_doctor_reports_configured_retention_and_budget(tmp_path, monkeypatch):
    from hermes_cli import doctor_state

    home = tmp_path / "home"
    home.mkdir()
    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: 48\n  max_size_gb: 10\n")
    seen = []
    monkeypatch.setattr(doctor_state, "check_ok", seen.append)
    monkeypatch.setattr(doctor_state, "check_warn", seen.append)
    doctor_state._check_scratch_dir(home, "test-home")
    assert any("48h idle" in message and "10 GB" in message for message in seen)
