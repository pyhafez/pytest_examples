"""Check repository defaults and user overrides in actual child pytest runs."""

from pathlib import Path
import json
import sys
import tomllib

import pytest


@pytest.mark.parametrize("override", ["default", "environment", "cli", "both"])
def test_repository_temp_paths_and_overrides(pytester, monkeypatch, override):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("PYTHONPATH", str(root / "src"))
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    pytester.makeconftest((root / "conftest.py").read_text(encoding="utf-8"))
    settings = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    cache_dir = settings["tool"]["pytest"]["ini_options"]["cache_dir"]
    pytester.makeini(f"[pytest]\ncache_dir = {cache_dir}\n")

    custom_root = pytester.path / "custom-temp-root"
    if override in {"environment", "both"}:
        custom_root.mkdir()
        monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(custom_root))
    args = ["-q"]
    explicit_base = pytester.path / "explicit-base"
    if override in {"cli", "both"}:
        args.append(f"--basetemp={explicit_base}")

    # This file would be lost if the default silently used a fixed --basetemp.
    sentinel = pytester.path / "artifacts" / "tmp" / "keep.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("preserve existing outputs", encoding="utf-8")
    pytester.makepyfile("""
        from pathlib import Path
        import json

        def test_paths(tmp_path, pytestconfig):
            pytestconfig.cache.set("demo/value", "cached")
            Path("observed.json").write_text(
                json.dumps({"temp": str(tmp_path)}), encoding="utf-8"
            )
    """)

    # runpytest_subprocess injects --basetemp, masking the default we need to check.
    pytester.run(sys.executable, "-m", "pytest", *args).assert_outcomes(passed=1)
    observed = json.loads((pytester.path / "observed.json").read_text(encoding="utf-8"))
    temp = Path(observed["temp"])
    expected_root = (
        explicit_base if override in {"cli", "both"}
        else custom_root if override == "environment"
        else pytester.path / "artifacts" / "tmp"
    )
    assert temp.is_relative_to(expected_root)
    assert (pytester.path / cache_dir / "v" / "demo" / "value").is_file()
    assert not (pytester.path / ".pytest_cache").exists()
    assert sentinel.read_text(encoding="utf-8") == "preserve existing outputs"
