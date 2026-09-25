import pytest

pytest.importorskip("xdist", reason="Install the plugins extra for worker fixtures")


@pytest.mark.parametrize("vlan_id", [10, 20, 30, 40])
def test_workers_have_isolated_state(controller, tmp_path, worker_id, vlan_id):
    assert controller.vlans == {}
    controller.create_vlan(vlan_id, ("eth1", "eth2"))
    capture = tmp_path / "worker.txt"
    capture.write_text(worker_id, encoding="utf-8")
    assert capture.read_text(encoding="utf-8") == worker_id
    assert set(controller.vlans) == {vlan_id}
