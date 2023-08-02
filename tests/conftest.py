import json

import pytest
from ape.api.accounts import AccountContainerAPI
from click.testing import CliRunner
from eth_typing import HexAddress, HexStr

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
