"""Load the teaching plugin and keep generated test data in the repository."""

import os

import pytest

pytest_plugins = ["pytest_power.pytest_plugin", "pytester"]


def pytest_configure(config):
    """Avoid shared system-temp permissions while honoring explicit overrides."""
    if config.option.basetemp is not None or "PYTEST_DEBUG_TEMPROOT" in os.environ:
        return

    temp_root = config.rootpath / "artifacts" / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    patch = pytest.MonkeyPatch()
    patch.setenv("PYTEST_DEBUG_TEMPROOT", str(temp_root))
    config.add_cleanup(patch.undo)
