import pytest


@pytest.fixture(scope="package")
def package_inventory():
    """Immutable shared data is safe to reuse across modules in this package."""
    return ("leaf-1", "leaf-2")


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Scoped to this directory: automatic setup and automatic restoration."""
    monkeypatch.setenv("LAB_ENV", "test")
