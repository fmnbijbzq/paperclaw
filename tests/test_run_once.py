from pathlib import Path


def test_project_root_contains_run_once_script():
    assert Path("run_once.py").exists()
