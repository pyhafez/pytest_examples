import json

import pytest

allure = pytest.importorskip("allure", reason="Install the plugins extra for Allure attachments")


@allure.feature("VLAN provisioning")
@allure.story("Attach a mock controller snapshot")
def test_report_with_attachment(controller):
    with allure.step("Provision VLAN 100"):
        controller.create_vlan(100, ("eth1", "eth2"))
    allure.attach(json.dumps(controller.snapshot(), indent=2), name="controller snapshot", attachment_type=allure.attachment_type.JSON)
    with allure.step("Check reachability"):
        assert controller.reachable(100)
