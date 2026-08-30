from __future__ import annotations
from pathlib import Path
import pytest
from g3_core.settings import TerminalSettings
from g3_launcher.discovery import GodotDiscoveryError,resolve_godot_executable
from g3_launcher.runtime import build_godot_command

def test_saved_godot_path_has_highest_priority(tmp_path):
    saved=tmp_path/"Godot_v4.7.2-stable_win64.exe"; env=tmp_path/"env.exe"; saved.write_bytes(b""); env.write_bytes(b""); settings=TerminalSettings.default(); settings.godot_executable=str(saved)
    assert resolve_godot_executable(settings,environment={"GODOT_EXE":str(env)},which=lambda _name:None,chooser=lambda:None)==saved.resolve()
def test_environment_path_is_used_and_persisted(tmp_path):
    exe=tmp_path/"Godot.exe"; exe.write_bytes(b""); settings=TerminalSettings.default(); result=resolve_godot_executable(settings,environment={"GODOT_EXE":str(exe)},which=lambda _name:None,chooser=lambda:None); assert result==exe.resolve(); assert settings.godot_executable==str(exe.resolve())
def test_path_lookup_is_used_before_chooser(tmp_path):
    exe=tmp_path/"godot.exe"; exe.write_bytes(b""); settings=TerminalSettings.default(); chooser_called=False
    def chooser():
        nonlocal chooser_called; chooser_called=True; return None
    result=resolve_godot_executable(settings,environment={},which=lambda name:str(exe) if name=="godot" else None,chooser=chooser); assert result==exe.resolve(); assert chooser_called is False
def test_chooser_is_last_resort_and_persisted(tmp_path):
    exe=tmp_path/"Godot.exe"; exe.write_bytes(b""); settings=TerminalSettings.default(); result=resolve_godot_executable(settings,environment={},which=lambda _name:None,chooser=lambda:str(exe)); assert result==exe.resolve(); assert settings.godot_executable==str(exe.resolve())
def test_missing_godot_raises_clear_error():
    settings=TerminalSettings.default()
    with pytest.raises(GodotDiscoveryError): resolve_godot_executable(settings,environment={},which=lambda _name:None,chooser=lambda:None)
def test_build_godot_command_runs_project_directly(tmp_path):
    exe=tmp_path/"Godot.exe"; project=tmp_path/"g3_frontend"; exe.write_bytes(b""); project.mkdir(); command=build_godot_command(exe,project); assert command==[str(exe.resolve()),"--path",str(project.resolve())]; assert "--editor" not in command
