def test_cli_reaches_fixture(controller, pytestconfig):
    assert controller.address == pytestconfig.getoption("--controller-ip")
    assert controller.strict == (pytestconfig.getoption("--emulation-mode") == "strict")
