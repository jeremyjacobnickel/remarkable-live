import subprocess

import server


def completed(returncode, stdout=b"", stderr=b""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_deploys_grabber_when_missing_on_tablet(monkeypatch):
    results = [completed(server.COMMAND_NOT_FOUND), completed(0, b"png")]
    deployed = []
    monkeypatch.setattr(server, "_run_grabber", lambda: results.pop(0))
    monkeypatch.setattr(server, "_deploy_grabber", lambda: deployed.append(True))
    monkeypatch.setattr(server.subprocess, "run", lambda *a, **k: completed(0))

    assert server.grab_png() == b"png"
    assert deployed == [True]


def test_reports_ssh_failure(monkeypatch):
    monkeypatch.setattr(server, "_run_grabber", lambda: completed(255, stderr=b"No route"))
    try:
        server.grab_png()
    except RuntimeError as error:
        assert "No route" in str(error)
    else:
        raise AssertionError("RuntimeError erwartet")
