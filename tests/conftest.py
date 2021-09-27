import json

import pytest
from ape.api.accounts import AccountContainerAPI
from click.testing import CliRunner
from eth_typing import ChecksumAddress, HexAddress, HexStr

from ape_ledger.client import (
    LedgerEthereumAccountClient,
    LedgerEthereumAppClient,
    LedgerUsbDeviceClient,
)
from ape_ledger.hdpath import HDAccountPath, HDBasePath

TEST_ADDRESSES = [
    HexAddress(HexStr("0x0A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x1A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x2A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x3A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x4A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x5A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x6A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x7A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x8A78AAAAA2122100000b9046f0A085AB2E111113")),
    HexAddress(HexStr("0x9A78AAAAA2122100000b9046f0A085AB2E111113")),
]
TEST_ADDRESS = TEST_ADDRESSES[0]
TEST_ALIAS = "TestAlias"
TEST_HD_PATH = "m/44'/60'/0'/0/0"


@pytest.fixture
def mock_apdu(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_device(mocker):
    return mocker.MagicMock(spec=LedgerUsbDeviceClient)


def create_test_account(mock_device, address=TEST_ADDRESS):
    address = ChecksumAddress(address)
    path = HDAccountPath(TEST_HD_PATH)
    return LedgerEthereumAccountClient(mock_device, address, path)


@pytest.fixture
def ledger_account(mock_device):
    return create_test_account(mock_device)


@pytest.fixture
def mock_ethereum_app(mocker, mock_device):
    mock = mocker.MagicMock(spec=LedgerEthereumAppClient)
    mock.hd_root_path = HDBasePath()

    def _get_address(account_id: int):
        if len(TEST_ADDRESSES) > account_id >= 0:
            address = TEST_ADDRESSES[account_id]
            return create_test_account(mock_device, address=address)

    mock.load_account.side_effect = _get_address
    return mock


@pytest.fixture
def mock_container(mocker):
    return mocker.MagicMock(spec=AccountContainerAPI)


@pytest.fixture
def runner():
    return CliRunner()


def assert_account(account_path, expected_address=TEST_ADDRESS, expected_hdpath="m/44'/60'/0'/0/0"):
    with open(account_path) as account_file:
        account_data = json.load(account_file)
        assert account_data["address"] == expected_address
        assert account_data["hdpath"] == expected_hdpath
