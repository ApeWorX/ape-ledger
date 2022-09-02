import ape_ledger.client as client_module


def test_device_connects_once(mock_device):
    client_module.device_manager._device = mock_device
    assert client_module.device_manager.device == mock_device
