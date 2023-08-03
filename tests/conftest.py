import json

import pytest
from ape import accounts, networks
from ape.api.accounts import AccountContainerAPI
from click.testing import CliRunner
from eth_account.messages import encode_defunct
from ethpm_types import HexBytes

from ape_ledger.client import LedgerDeviceClient

TEST_ALIAS = "TestAlias"
TEST_HD_PATH = "m/44'/60'/{x}'/0/0"


@pytest.fixture
def hd_path():
    return TEST_HD_PATH


@pytest.fixture
def alias():
    return TEST_ALIAS


@pytest.fixture
def test_accounts():
    return accounts.test_accounts


@pytest.fixture
def account_addresses(test_accounts):
    return [a.address for a in test_accounts]


@pytest.fixture
def account_0(test_accounts):
    return test_accounts[0]


@pytest.fixture
def account_1(test_accounts):
    return test_accounts[0]


@pytest.fixture
def address(account_addresses):
    return account_addresses[0]


@pytest.fixture(autouse=True)
def connection():
    with networks.ethereum.local.use_provider("test") as provider:
        yield provider


@pytest.fixture
def msg_signature(account_0):
    msg = encode_defunct(text="__TEST_MESSAGE__")
    sig = account_0.sign_message(msg)
    return (
        sig.v,
        int(HexBytes(sig.r).hex(), 16),
        int(HexBytes(sig.s).hex(), 16),
    )


@pytest.fixture
def receipt(account_0, account_1):
    return account_0.transfer(account_1, "1 gwei")


@pytest.fixture
def tx_signature(receipt):
    return (
        receipt.signature.v,
        int(HexBytes(receipt.signature.r).hex(), 16),
        int(HexBytes(receipt.signature.s).hex(), 16),
    )


@pytest.fixture(autouse=True)
def mock_device(mocker, hd_path, account_addresses, msg_signature, tx_signature):
    device = mocker.MagicMock(spec=LedgerDeviceClient)
    device._account = hd_path
    device.get_address.side_effect = (
        lambda *args, **kwargs: account_addresses[args[0]] if args else account_addresses[0]
    )
    device.sign_message.side_effect = lambda *args, **kwargs: msg_signature
    device.sign_typed_data.side_effect = lambda *args, **kwargs: msg_signature
    device.sign_transaction.side_effect = lambda *args, **kwargs: tx_signature
    return device


@pytest.fixture
def mock_container(mocker):
    return mocker.MagicMock(spec=AccountContainerAPI)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def assert_account(address):
    def fn(account_path, expected_address=None, expected_hdpath="m/44'/60'/0'/0/0"):
        expected_address = expected_address or address
        with open(account_path) as account_file:
            account_data = json.load(account_file)
            assert account_data["address"] == expected_address
            assert account_data["hdpath"] == expected_hdpath

    return fn


@pytest.fixture
def device_factory(mocker, mock_device):
    def fn(module):
        patch = mocker.patch(f"ape_ledger.{module}.get_device")
        patch.return_value = mock_device

    return fn
