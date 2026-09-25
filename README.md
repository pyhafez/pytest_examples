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

## How to observe pytest features in this project

Run these commands from the repository root after completing the installation above. Follow each command with a look at the linked source: some features appear in terminal output, while others are demonstrated by assertions inside a passing test.

Start with `python -m pytest -vv -ra`. `-vv` shows individual test names and parameter IDs; `-ra` explains non-passing outcomes. `PASSED` means the assertions succeeded, `SKIPPED` means the example was not executed, and `XFAIL` means the documented unsupported feature failed as expected. Optional-plugin skips are normal with the core installation. The pytester tests create failing child runs as part of their checks; their parent tests should still pass.

### 1. Watch fixture injection, scopes and cleanup

```console
python -m pytest tests/fixtures --setup-show -v
python -m pytest --fixtures tests/fixtures
```

Read [the shared fixtures](tests/conftest.py), [the package fixtures](tests/fixtures/conftest.py), and [the lifecycle tests](tests/fixtures/test_lifecycle.py).

In `--setup-show` output, find `SETUP` and `TEARDOWN` entries with these scope letters:

| Scope | Fixture to find | What to observe |
| --- | --- | --- |
| `S`: session | `network_bridge`, `docker_service` | One setup per process, reused by dependent tests |
| `P`: package | `package_inventory` | Shared by the class fixture and the test in another module of `tests/fixtures` |
| `M`: module | `module_config` | Reused within `test_lifecycle.py` |
| `C`: class | `class_ports` | One setup for the two methods of `TestScopeHierarchy` |
| `F`: function | `controller`, `provisioned_vlan` | Fresh setup for each requesting test and cleanup afterward |

For `test_yield_fixture_composes_resources`, follow `network_bridge` -> `docker_service` -> `controller` -> `provisioned_vlan`. Pytest supplies each object through matching argument names. The VLAN finalizes before its controller; the session resources remain available until their scope ends. Extra entries from built-in or installed-plugin fixtures are normal.

Find `isolated_environment` in the output even though tests do not request it in their signatures: that is `autouse=True` in action.

To observe cleanup after a failure:

```console
python -m pytest tests/hooks/test_plugin_contract.py -k "cleanup" -vv
```

Read the cleanup tests in [the hook contracts](tests/hooks/test_plugin_contract.py). They check files written by finalizers in failing child suites. One verifies reverse teardown order; the other verifies that a fixture failing before `yield` does not run its post-yield code, while its established dependency still cleans up.

### 2. See runtime fixture selection

```console
python -m pytest tests/fixtures/test_dynamic.py --emulation-mode=memory -vv
python -m pytest tests/fixtures/test_dynamic.py --emulation-mode=strict -vv
```

Both runs should pass. In [test_dynamic.py](tests/fixtures/test_dynamic.py), follow `selected_controller` to `request.getfixturevalue(...)`. The unmarked test follows the CLI setting; the `backend` markers override it. The strict example asserts rejection of a single-port VLAN, while the memory example accepts one. The distinction is in the objects and assertions, even though both runs show green results.

### 3. See one test expand into many cases

```console
python -m pytest tests/parametrization/test_matrix.py::test_protocol_vlan_matrix --collect-only -q
python -m pytest tests/parametrization/test_matrix.py -vv
```

The first command lists **six cases** without running their test bodies: three VLAN IDs multiplied by two OpenFlow versions. Look for readable `VLAN-100` and `OpenFlow-1.5` labels in the node IDs.

In [test_matrix.py](tests/parametrization/test_matrix.py), compare three mechanisms: stacked `parametrize` decorators create the matrix; `indirect=["topology"]` sends port data into a fixture through `request.param`; and `@pytest.fixture(params=...)` repeats every test that requests that fixture. The named optical case also demonstrates a custom ID and a marker attached to one parameter set.

### 4. See markers control selection and outcomes

```console
python -m pytest tests/markers -vv -ra
python -m pytest tests/markers -m "sdn and not slow" -vv
python -m pytest tests/markers --run-hardware -vv -ra
```

Compare the results with [test_selection.py](tests/markers/test_selection.py):

- The `-m` expression selects the SDN smoke test and reports other cases as deselected.
- `test_retired_protocol` always skips; `test_linux_only` skips on non-Linux systems.
- `test_opt_in_simulated_hardware` changes from skipped to passed with `--run-hardware`.
- `test_known_unsupported_feature` reports `XFAIL` because the fake lacks QinQ. Its strict marker makes an unexpected pass a suite failure.

To select by test name instead of marker, try `python -m pytest tests/mocking -k "verification" -vv`.

### 5. See hooks extend collection and execution

```console
python -m pytest tests/markers --collect-only -q
python -m pytest tests/hooks/test_cases.topology.json -vv
python -m pytest tests/hooks/test_cli.py --controller-ip=192.0.2.10 -vv
```

The collection listing places the smoke test first. The JSON command runs two named cases, `access-pair` and `spine-leaf`, although the input is not a Python test file. The CLI test verifies that the supplied address reaches the controller fixture.

Read [pytest_plugin.py](src/pytest_power/pytest_plugin.py) alongside [the JSON cases](tests/hooks/test_cases.topology.json). Match those observations to `pytest_collection_modifyitems`, `pytest_collect_file`, and `pytest_addoption`. The marker opt-in checks above exercise `pytest_runtest_setup`; the failure demonstration below exercises `pytest_runtest_makereport`. The plugin also records teardown events, checked by the hook contract tests.

`--controller-ip` is metadata only. `--run-hardware` enables a **simulated** hardware test. `--emulation-mode=strict` still uses a fake; it requires at least two ports per VLAN. `--topo` controls generated link cases in `tests/integration`. The JSON collector always runs the cases explicitly listed in its file.

### 6. Inspect assertions and built-in fixtures

```console
python -m pytest tests/assertions/test_diagnostics.py -vv
python -m pytest tests/builtins/test_standard_fixtures.py -vv --log-cli-level=INFO
```

Read [the assertion examples](tests/assertions/test_diagnostics.py): `raises` validates the error and message, `warns` validates a deprecation warning, and `approx` checks the optical result within a tolerance. These expected exceptions and warnings produce **passing tests**. Use the [intentional failure demonstration](#see-a-real-failure-report) below to see a rewritten dictionary assertion and local variables in an actual traceback.

In [the built-in fixture examples](tests/builtins/test_standard_fixtures.py), inspect `monkeypatch` changing an environment variable, dictionary and method; `capsys` checking exact stdout; `caplog` checking a log record; and `request` inspecting the current test. Captured stdout is asserted inside the test, so an ordinary passing run does not print `VLAN 100 ready`. The live-log option makes the controller's INFO messages visible.

To inspect the files created by `tmp_path` and `tmp_path_factory`, supply a **new, disposable directory**:

```console
python -m pytest tests/builtins/test_standard_fixtures.py --basetemp=artifacts/builtins-demo -vv
```

Afterward, look under `artifacts/builtins-demo` for `ports.json` in the shared topology directory and `switch.json` in the test's own directory. Pytest clears a supplied `--basetemp` directory before using it; use this dedicated demo path only for disposable output.

### 7. Inspect what mock objects prove

```console
python -m pytest tests/mocking/test_interactions.py -vv
```

In [test_interactions.py](tests/mocking/test_interactions.py), follow `create_autospec`, `return_value`, `side_effect`, `mock_calls`, and `assert_called_once_with`. The tests prove that a successful deployment calls its collaborators correctly, failed verification triggers rollback, and failed creation does not delete existing state. Autospec also catches a misspelled method and missing required arguments.

The final test uses `AsyncMock` and `assert_awaited_once_with` through `asyncio.run`, so it works with the core installation. The optional asyncio plugin examples show how to use an `async def` test and async fixture directly. Mock interactions are checked by assertions; they are not automatically printed as a call trace.


## Follow the combined example

After exploring the independent examples, compare these runs:

```console
python -m pytest tests/integration --topo=pair -vv --setup-show
python -m pytest tests/integration --topo=spine-leaf --emulation-mode=strict -vv --setup-show --log-cli-level=INFO
```

Expect **two cases** for the pair topology and **four cases** for spine-leaf: each generated link is tested with VLAN IDs 100 and 200. The names identify both the link and VLAN. Setup output shows the yield fixtures, and live logs show the attempted VLAN 300 deployment and its rollback.

Read [the integration fixtures](tests/integration/conftest.py), then [test_workflow.py](tests/integration/test_workflow.py):

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

| Plugin | Run it | What to observe |
| --- | --- | --- |
| pytest-xdist | `python -m pytest tests/plugins/test_parallel.py -n 2 -vv` | Worker labels such as `gw0` and `gw1`; four cases verify isolated controller state and temporary files |
| pytest-rerunfailures | `python -m pytest tests/plugins/test_reruns.py -vv` | One `RERUN` followed by a pass; a scripted timeout is retried once |
| pytest-timeout | `python -m pytest tests/plugins/test_timeout.py -vv` | A passing probe with a five-second deadline; this example does not deliberately hang or demonstrate timeout termination |
| pytest-order + pytest-dependency | `python -m pytest tests/plugins/test_ordered_lifecycle.py -vv` | Execution order is create, verify, remove despite a different definition order |
| pytest-mock | `python -m pytest tests/plugins/test_mocker.py -vv` | Read the spy's call/return assertions and the patched probe's rollback assertions |
| pytest-httpx | `python -m pytest tests/plugins/test_httpx.py -vv` | Both the HTTP success and expected 503-error tests pass using intercepted requests |
| responses | `python -m pytest tests/plugins/test_responses.py -vv` | The test checks an intercepted requests response and call count; responses is a mocking library, not a pytest plugin |
| pytest-asyncio | `python -m pytest tests/plugins/test_asyncio.py -vv` | Async test bodies and an async yield fixture run; awaited-call assertions verify the mock |
| asyncio + HTTPX | `python -m pytest tests/plugins/test_async_httpx.py -vv` | An async HTTP call returns the registered mock payload |
| pytest-cov | `python -m pytest --cov=pytest_power --cov-report=term-missing --cov-report=html:reports/coverage` | A terminal coverage table and browsable source coverage at `reports/coverage/index.html` |
| pytest-html | `python -m pytest --html=reports/report.html --self-contained-html` | Open `reports/report.html` to inspect test outcomes in a browser |
| allure-pytest | `python -m pytest tests/plugins/test_reporting.py --alluredir=reports/allure-results -vv` | Result and attachment files; the rendered report shows provisioning steps and the controller JSON snapshot |


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
