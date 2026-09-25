"""Small local plugin demonstrating collection, CLI, lifecycle and report hooks."""

import hashlib
import json
from pathlib import Path
import tempfile
import warnings

import pytest

from pytest_power.network import FakeController

EVENTS = pytest.StashKey[list[str]]()
ARTIFACT_DIRECTORY = pytest.StashKey[Path]()


def pytest_addoption(parser):
    group = parser.getgroup("mock SDN lab")
    group.addoption("--controller-ip", default="controller.test", help="Fake address metadata")
    group.addoption("--topo", choices=["pair", "spine-leaf"], default="pair")
    group.addoption("--emulation-mode", choices=["memory", "strict"], default="memory")
    group.addoption("--run-hardware", action="store_true", help="Enable simulated device checks")
    group.addoption("--run-diagnostics", action="store_true", help="Enable deliberately failing lessons")
    group.addoption("--artifacts-dir", default="artifacts", help="Failure JSON directory")


def pytest_configure(config):
    # Also register when this plugin is loaded in a pytester sandbox.
    for marker in (
        "smoke: run early",
        "sdn: simulated network tests",
        "regression: behavioral checks",
        "hardware: opt-in simulated device checks",
        "diagnostic_demo: opt-in intentional failures",
        "serial: stateful tests requiring a single process",
    ):
        config.addinivalue_line("markers", marker)


def pytest_collection_modifyitems(config, items):
    # Stable ordering preserves relative order within both groups.
    items.sort(key=lambda item: item.get_closest_marker("smoke") is None)
    parallel = bool(getattr(config.option, "numprocesses", 0)) or hasattr(config, "workerinput")
    if parallel:
        selected = [item for item in items if item.get_closest_marker("serial") is None]
        deselected = [item for item in items if item.get_closest_marker("serial") is not None]
        items[:] = selected
        config.hook.pytest_deselected(items=deselected)


def pytest_runtest_setup(item):
    item.stash[EVENTS] = ["setup"]
    for marker, option in (("hardware", "--run-hardware"), ("diagnostic_demo", "--run-diagnostics")):
        if item.get_closest_marker(marker) and not item.config.getoption(option):
            pytest.skip(f"Opt in with {option}")


def pytest_runtest_teardown(item):
    item.stash.setdefault(EVENTS, []).append("teardown")


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # Other hooks construct/annotate the report before we inspect it.
    report = yield
    if report.failed:
        controller = getattr(item, "funcargs", {}).get("controller")
        payload = {
            "nodeid": item.nodeid,
            "phase": report.when,
            "outcome": report.outcome,
            "lifecycle": list(item.stash.get(EVENTS, [])),
            "controller": controller.snapshot() if isinstance(controller, FakeController) else None,
            "failure": str(report.longrepr),
        }
        try:
            directory = item.config.stash.get(ARTIFACT_DIRECTORY, None)
            if directory is None:
                base = Path(item.config.getoption("--artifacts-dir"))
                if not base.is_absolute():
                    base = item.config.rootpath / base
                base.mkdir(parents=True, exist_ok=True)
                directory = Path(tempfile.mkdtemp(prefix="run-", dir=base))
                item.config.stash[ARTIFACT_DIRECTORY] = directory
            worker = getattr(item.config, "workerinput", {}).get("workerid", "main")
            digest = hashlib.sha256(item.nodeid.encode()).hexdigest()[:16]
            attempt = getattr(item, "execution_count", 1)
            path = directory / f"{worker}-{digest}-{report.when}-{attempt}.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            report.sections.append(("mock lab diagnostics", str(path)))
        except OSError as exc:
            # A reporting problem must not replace the test's original failure.
            warnings.warn(pytest.PytestWarning(f"Cannot write failure diagnostics: {exc}"), stacklevel=2)
    return report


def pytest_collect_file(file_path, parent):
    if file_path.name.startswith("test_") and file_path.name.endswith(".topology.json"):
        return TopologyFile.from_parent(parent, path=file_path)


class TopologyFile(pytest.File):
    def collect(self):
        try:
            cases = json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise self.CollectError(f"Invalid topology JSON: {exc}") from exc
        if not isinstance(cases, list) or not cases:
            raise self.CollectError("Topology JSON must be a nonempty list of cases")
        names = set()
        for case in cases:
            required = {"name", "ports", "vlan_id", "expected_ports"}
            if not isinstance(case, dict) or not required <= case.keys():
                raise self.CollectError(f"Each case requires: {', '.join(sorted(required))}")
            name = case["name"]
            if not isinstance(name, str) or not name or name in names:
                raise self.CollectError("Case names must be unique nonempty strings")
            for field in ("ports", "expected_ports"):
                if not isinstance(case[field], list) or not all(isinstance(p, str) for p in case[field]):
                    raise self.CollectError(f"{name}: {field} must be a list of port names")
            if type(case["vlan_id"]) is not int:
                raise self.CollectError(f"{name}: vlan_id must be an integer")
            names.add(name)
            yield TopologyItem.from_parent(self, name=name, spec=case)


class TopologyItem(pytest.Item):
    def __init__(self, *, spec, **kwargs):
        super().__init__(**kwargs)
        self.spec = spec
        self.add_marker("sdn")
        self.add_marker("regression")

    def runtest(self):
        # Custom Items do not receive Python-function fixtures automatically.
        controller = FakeController(self.spec["ports"])
        try:
            vlan = controller.create_vlan(self.spec["vlan_id"], self.spec["ports"])
            if list(vlan.ports) != self.spec["expected_ports"]:
                raise AssertionError(
                    f"{self.name}: ports {list(vlan.ports)!r} != {self.spec['expected_ports']!r}"
                )
        finally:
            controller.close()

    def reportinfo(self):
        return self.path, 0, f"topology: {self.name}"
