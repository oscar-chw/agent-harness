"""User profile and knowledge are persistent data, not removable package code."""
from agent_harness import installer


def test_uninstall_keeps_preexisting_and_new_profile_knowledge(tmp_path):
    hh = tmp_path / "hh"
    profile = hh / "profile"
    (profile / "knowledge").mkdir(parents=True)
    files = {profile / "profile.toml": b'name="my-laptop"\n',
             profile / "rules.md": b"My original operating rules.\n",
             profile / "knowledge/guide.md": b"Retain source conditions.\n"}
    for path, body in files.items():
        path.write_bytes(body)
    for sub in ("lib", "content"):
        (hh / sub).mkdir()
        (hh / sub / "generated").write_text("package code")
    installer.save_state(hh, {"entries": [], "roots": [str(tmp_path)]})
    installer.uninstall(hh)
    assert {path: path.read_bytes() for path in files} == files
    assert not (hh / "lib").exists()
    assert not (hh / "content").exists()
    assert not (hh / "installed.json").exists()
