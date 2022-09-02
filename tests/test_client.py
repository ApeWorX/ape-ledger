import ape_ledger.client as client_module


def test_device_connects_once():
    device_0 = client_module.device_manager.device
    device_1 = client_module.device_manager.device
    assert device_0 == device_1
