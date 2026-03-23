from importlib import util
from pathlib import Path


def test_project_root_contains_run_once_script():
    assert Path("run_once.py").exists()


def test_main_returns_zero():
    spec = util.spec_from_file_location(
        "run_once",
        Path("run_once.py"),
    )
    assert spec is not None
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    assert module.main() == 0
