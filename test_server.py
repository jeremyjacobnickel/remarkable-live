import subprocess

import pytest

import server

REAL_SHRINK = server.shrink_png


def completed(returncode, stdout=b"", stderr=b""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


@pytest.fixture(autouse=True)
def no_resize(monkeypatch):
    monkeypatch.setattr(server, "shrink_png", lambda png: png)
    monkeypatch.setattr(server, "_working_host", None)


def test_deploys_grabber_when_missing_on_tablet(monkeypatch):
    results = [completed(server.COMMAND_NOT_FOUND), completed(0, b"png")]
    deployed = []
    monkeypatch.setattr(server, "HOSTS", ["usb"])
    monkeypatch.setattr(server, "_run_grabber", lambda host: results.pop(0))
    monkeypatch.setattr(server, "_deploy_grabber", deployed.append)

    assert server.grab_png() == b"png"
    assert deployed == ["usb"]


def test_falls_back_to_wlan_and_remembers_it(monkeypatch):
    calls = []

    def run(host):
        calls.append(host)
        return completed(0, b"png") if host == "wlan" else completed(255, stderr=b"timeout")

    monkeypatch.setattr(server, "HOSTS", ["usb", "wlan"])
    monkeypatch.setattr(server, "_run_grabber", run)

    assert server.grab_png() == b"png"
    assert server.grab_png() == b"png"
    assert calls == ["usb", "wlan", "wlan"]


def test_reports_errors_of_all_hosts(monkeypatch):
    monkeypatch.setattr(server, "HOSTS", ["usb", "wlan"])
    monkeypatch.setattr(server, "_run_grabber", lambda host: completed(255, stderr=b"No route"))

    with pytest.raises(RuntimeError, match="usb: No route; wlan: No route"):
        server.grab_png()


def test_shrink_png_keeps_aspect_ratio():
    import io

    from PIL import Image

    out = io.BytesIO()
    Image.new("L", (1620, 2160), 255).save(out, format="PNG")
    small = Image.open(io.BytesIO(REAL_SHRINK(out.getvalue())))
    assert small.size == (1200, 1600)


def test_deploy_streams_binary_over_ssh(monkeypatch, tmp_path):
    binary = tmp_path / "rmgrab"
    binary.write_bytes(b"ELF")
    calls = []
    monkeypatch.setattr(server, "LOCAL_BINARY", binary)
    monkeypatch.setattr(server.subprocess, "run", lambda cmd, **k: calls.append((cmd, k)))
    server._deploy_grabber("usb")
    (cmd, kwargs), = calls
    assert cmd[0] == "ssh" and "scp" not in cmd and kwargs["input"] == b"ELF"
