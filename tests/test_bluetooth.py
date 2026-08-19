"""Bluetooth autoconnect tests."""
import asyncio
import json
import subprocess

from app.services.bluetooth import manager as bluetooth_module


def test_connect_trusts_and_remembers_device(tmp_path, monkeypatch):
    autoconnect_path = tmp_path / "bluetooth_autoconnect.json"
    monkeypatch.setattr(bluetooth_module, "AUTOCONNECT_PATH", autoconnect_path)

    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "Connection successful", "")

    monkeypatch.setattr(bluetooth_module.subprocess, "run", fake_run)

    connected = asyncio.run(bluetooth_module.BluetoothManager().connect("A8:E6:E8:E4:DF:97"))

    assert connected is True
    assert commands == [
        ["bluetoothctl", "connect", "A8:E6:E8:E4:DF:97"],
        ["bluetoothctl", "trust", "A8:E6:E8:E4:DF:97"],
    ]
    assert json.loads(autoconnect_path.read_text(encoding="utf-8")) == ["A8:E6:E8:E4:DF:97"]


def test_remove_forgets_device(tmp_path, monkeypatch):
    autoconnect_path = tmp_path / "bluetooth_autoconnect.json"
    autoconnect_path.write_text(json.dumps(["A8:E6:E8:E4:DF:97"]), encoding="utf-8")
    monkeypatch.setattr(bluetooth_module, "AUTOCONNECT_PATH", autoconnect_path)
    monkeypatch.setattr(
        bluetooth_module.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "", ""),
    )

    removed = asyncio.run(bluetooth_module.BluetoothManager().remove("A8:E6:E8:E4:DF:97"))

    assert removed is True
    assert not autoconnect_path.exists()