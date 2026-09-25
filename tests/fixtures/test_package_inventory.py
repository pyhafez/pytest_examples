def test_same_package_fixture_available_in_another_module(package_inventory):
    assert "leaf-1" in package_inventory
