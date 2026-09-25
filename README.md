# pytest-power

A runnable teaching repository showing pytest features independently and together, using a small SDN lab that exists entirely in memory. No hardware, Docker daemon, SSH credentials, external services, or network requests are needed to execute the tests. Installing dependencies requires package index access.

`FakeController` is a **stateful fake**: it validates ports and VLANs, records changes, and supports rollback. `Mock`, `create_autospec`, and `AsyncMock` are **interaction mocks**: they supply controlled responses and verify calls. Tests use both so you can see when each is useful.

## Get started

Requires Python 3.11 or newer. From this directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pytest
```

On macOS/Linux, activate with `source .venv/bin/activate`. Activation is optional: on Windows you can use `.venv\Scripts\python.exe` in place of `python`.

The default installation needs only pytest. Optional plugin modules skip with an installation hint. A few skips and one strict expected failure are deliberate teaching examples; an unexpected pass of the QinQ example fails the suite.

Install all plugin examples into the same environment:

```console
python -m pip install -e ".[plugins]"
python -m pytest
```

The rerun lesson deliberately produces one `RERUN` before succeeding. Its first attempt also generates a diagnostic JSON file. Dependency version ranges are declared in `pyproject.toml`; these are compatible ranges, not a frozen lockfile.

## Learning map

Every Python test below can run by file or node ID, for example `python -m pytest tests/mocking/test_interactions.py -vv`. The ordered plugin workflow is the one intentional exception: run its whole module because its steps depend on one another.

| Topic | Examples | What to inspect |
| --- | --- | --- |
| All five fixture scopes | `tests/conftest.py`, `tests/fixtures/` | Function controller; class ports; module config; package inventory; session bridge/container |
| Yield, composition, autouse | `tests/fixtures/test_lifecycle.py` | Bridge → container → controller → VLAN; environment reset without a signature argument |
| Dynamic fixture lookup | `tests/fixtures/test_dynamic.py` | CLI default or `backend` marker selects a fixture through `request.getfixturevalue` |
| Data-driven testing | `tests/parametrization/test_matrix.py` | Cartesian products, indirect fixture parameters, fixture `params`, ID functions, per-case markers |
| Markers | `tests/markers/test_selection.py` | Smoke/regression/slow/hardware selection; skip, skipif, strict xfail |
| Assertions and diagnostics | `tests/assertions/test_diagnostics.py` | Dataclasses, dicts, sets, raises, warns, approx, opt-in assertion failure |
| Built-in fixtures | `tests/builtins/test_standard_fixtures.py` | monkeypatch, tmp_path, tmp_path_factory, caplog, capsys, request |
| Standard-library mocking | `tests/mocking/test_interactions.py` | Autospec, call order, side effects, rollback, AsyncMock |
| CLI and lifecycle hooks | `src/pytest_power/pytest_plugin.py` | addoption, collection ordering/filtering, setup, teardown, makereport |
| Custom file collection | `tests/hooks/test_cases.topology.json` | JSON cases become independent pytest items |
| Tests of pytest itself | `tests/hooks/test_plugin_contract.py` | pytester subprocesses verify failure phases, cleanup, gating, collection errors |
| Combined workflow | `tests/integration/` | CLI-generated links + indirect VLAN fixture + markers + probe mock + rollback + captured logs/output + JSON artifact |
| Ecosystem plugins | `tests/plugins/` | Focused examples plus combinations; see below |

## Explore core features

```console
python -m pytest tests/fixtures --setup-show -v
python -m pytest tests/parametrization --collect-only -q
python -m pytest -m "sdn and not slow" -v
python -m pytest -k "rollback or verification" -v
python -m pytest tests/hooks/test_cases.topology.json -v
python -m pytest tests/integration --topo=spine-leaf --emulation-mode=strict -vv
python -m pytest tests/fixtures/test_dynamic.py --emulation-mode=strict -vv
python -m pytest tests/hooks/test_cli.py --controller-ip=192.0.2.10
python -m pytest tests/markers --run-hardware -v
python -m pytest --fixtures tests/fixtures
```

`--controller-ip` is metadata only. `--run-hardware` enables a **simulated** hardware test. `--emulation-mode=strict` still uses a fake; it requires at least two ports per VLAN. `--topo` controls generated link cases in `tests/integration`. The JSON collector always runs the cases explicitly listed in its file.

The collection hook stably moves smoke tests first. The setup hook enforces opt-in markers; the teardown hook records lifecycle events. The report wrapper observes failed setup/call/teardown reports and writes diagnostics. The integration `conftest.py` also demonstrates `pytest_generate_tests` and a local fixture override.

## Follow the combined example

Read `tests/integration/conftest.py`, then `test_workflow.py`:

1. `--topo` generates one or two link cases during collection.
2. Indirect parametrization passes VLAN IDs into the `deployed_vlan` fixture.
3. That yield fixture provisions and verifies a VLAN before the test starts.
4. The test patches the reachability probe to simulate a failure on a second deployment.
5. The service rolls back that failed deployment, preserving the original VLAN.
6. Assertions check mock calls, state, logs, stdout, an optical tolerance, and a temporary JSON snapshot.
7. Fixture finalizers delete the original VLAN and close the controller.

The failure-report hook also works on this test: temporarily break an assertion to inspect the controller's state before fixture teardown.

## See a real failure report

This command **intentionally exits with code 1**:

```console
python -m pytest tests/assertions/test_diagnostics.py::test_intentional_failure --run-diagnostics -vv --showlocals --tb=short
```

Open the JSON path printed under `mock lab diagnostics`. Files live under `artifacts/run-*/`; each contains node ID, failure phase, traceback, lifecycle events, and the controller snapshot when that fixture is available. Each run/worker gets its own directory, and filenames include the test hash, phase and retry attempt. Use `--artifacts-dir=reports/failures` to change the base directory.

The default run skips this deliberate failure. Tests in `test_plugin_contract.py` run failing child suites on purpose and assert their outcomes; the parent tests pass. Normal passing tests do not create diagnostic files.

## Plugin recipes

Install `.[plugins]` first. Plugins are optional so the core lessons remain independently runnable.

| Plugin | Example / command |
| --- | --- |
| pytest-xdist | `python -m pytest -n 2` and `tests/plugins/test_parallel.py` |
| pytest-rerunfailures | `python -m pytest tests/plugins/test_reruns.py -vv`; deterministic timeout followed by success, only timeout errors retried |
| pytest-timeout | `tests/plugins/test_timeout.py`; `@pytest.mark.timeout(5)` on a quick mock probe |
| pytest-order + pytest-dependency | `python -m pytest tests/plugins/test_ordered_lifecycle.py -vv`; create → verify → remove despite definition order |
| pytest-mock | `tests/plugins/test_mocker.py`; spy on real fake behavior and replace a method |
| pytest-httpx | `tests/plugins/test_httpx.py`; HTTP success and 503 without a socket connection |
| responses | `tests/plugins/test_responses.py`; intercept the requests library (responses is a mocking library, not a pytest plugin) |
| pytest-asyncio | `tests/plugins/test_asyncio.py`; async fixture, AsyncMock, awaited call assertions |
| asyncio + HTTPX | `tests/plugins/test_async_httpx.py`; await an intercepted HTTP call |
| pytest-cov | `python -m pytest --cov=pytest_power --cov-report=term-missing --cov-report=html:reports/coverage` |
| pytest-html | `python -m pytest --html=reports/report.html --self-contained-html` |
| allure-pytest | `python -m pytest --alluredir=reports/allure-results`; `test_reporting.py` attaches JSON and named steps |

Allure's Python plugin writes result files. Viewing them as an HTML report requires a separately installed Allure CLI: `allure serve reports/allure-results`. pytest-html directly produces an HTML file. Core pytest also supports `python -m pytest --junitxml=reports/junit.xml`.

Combine parallel execution, coverage and an HTML report:

```console
python -m pytest -n 2 --cov=pytest_power --cov-report=term-missing --html=reports/parallel.html --self-contained-html
python -m pytest tests/plugins/test_ordered_lifecycle.py -vv
```

The local plugin deselects `serial` tests when xdist is active. Ordered dependencies need the same process and compatible ordering; they are demonstrated separately. Selecting only a dependent step causes it to skip because its prerequisite did not run. Prefer isolated tests and fixture composition for normal suites.

## Lifecycle details that matter

- Session scope means once **per pytest process**, so xdist creates one session fixture per worker. It does not provide a single global controller across workers.
- Package scope needs a package boundary; `tests/fixtures/__init__.py` supplies one here. Fixtures in that directory's `conftest.py` apply only to its subtree.
- A broad-scoped fixture cannot depend on a narrower-scoped fixture. The session container depends on a session bridge; function controllers depend on that container.
- Cleanup after a reached `yield` runs after an assertion failure or ordinary exception. If setup raises before reaching `yield`, that fixture's post-yield code does not run; already established dependencies still finalize. Keep each resource acquisition small. Process termination or a timeout that kills the process cannot guarantee Python finalizers.
- `pytest.raises(SomeError)` accepts subclasses and `match` is a regular expression. The assertion lesson checks `type(error.value)` when exact type matters.
- `skip` is unconditional; `skipif` supplies a condition. Strict `xfail` flags unexpected passes and the example limits expected failures to `NotImplementedError`.
- Retries are deliberately narrow here. A deterministic assertion regression should remain visible.
- The standalone JSON `pytest.Item` manages its own resources; it does not get normal function-fixture injection. Use `pytest_generate_tests` when you want data-driven Python tests with fixtures.

## Repository checks

The GitHub Actions workflow runs a pytest-only suite on Python 3.11 and 3.13, then an optional-plugin suite both serially and with xdist. Hook contract tests verify actual subprocess outcomes rather than merely inspecting hook implementation details.

The project intentionally makes no coverage-percentage claim. Coverage reports are a lesson and a way to find unexercised behavior.
