import json
from pathlib import Path

import pytest
from eip712.messages import EIP712Message, EIP712Type
from eth_account.messages import SignableMessage

from ape_ethereum.ecosystem import StaticFeeTransaction
from ape_ledger.accounts import AccountContainer, LedgerAccount
from ape_ledger.exceptions import LedgerSigningError
from conftest import TEST_ADDRESS, TEST_ALIAS, TEST_HD_PATH, assert_account


class Person(EIP712Type):
    name: "string"  # type: ignore # noqa: F821
    wallet: "address"  # type: ignore # noqa: F821


class Mail(EIP712Message):
    _chainId_: "uint256" = 1  # type: ignore # noqa: F821
    _name_: "string" = "Ether Mail"  # type: ignore # noqa: F821
    _verifyingContract_: "address" = "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC"  # type: ignore # noqa: F821 E501
    _version_: "string" = "1"  # type: ignore # noqa: F821

    sender: Person
    receiver: Person


# noinspection PyArgumentList
TEST_SENDER = Person("Cow", "0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826")  # type: ignore
# noinspection PyArgumentList
TEST_RECEIVER = Person("Bob", "0xB0B0b0b0b0b0B000000000000000000000000000")  # type: ignore
# noinspection PyArgumentList
TEST_TYPED_MESSAGE = Mail(sender=TEST_SENDER, receiver=TEST_RECEIVER)  # type: ignore


def create_account(account_path, hd_path):
    with open(account_path, "w") as account_file:
        account_data = {"address": TEST_ADDRESS, "hdpath": hd_path}
        account_file.writelines(json.dumps(account_data))


@pytest.fixture
def account_connection(mocker, ledger_account):
    patch = mocker.patch("ape_ledger.accounts.connect_to_ethereum_account")
    patch.return_value = ledger_account
    return patch


@pytest.fixture
def mock_config_manager(mocker):
    return mocker.MagicMock()


@pytest.fixture(autouse=True)
def isolated_file_system(runner):
    with runner.isolated_filesystem():
        yield


@pytest.fixture
def account(mock_container):
    create_account("account.json", TEST_HD_PATH)
    return LedgerAccount(mock_container, Path("account.json"))


class TestAccountContainer:
    def test_save_account(self, mock_container, mock_config_manager):
        container = AccountContainer(Path("."), LedgerAccount, mock_config_manager)
        container.save_account(TEST_ALIAS, TEST_ADDRESS, TEST_HD_PATH)
        assert_account(f"{TEST_ALIAS}.json", expected_hdpath=TEST_HD_PATH)


class TestLedgerAccount:
    def test_address_returns_address_from_file(self, account):
        assert account.address.lower() == TEST_ADDRESS.lower()

    def test_hdpath_returns_address_from_file(self, account):
        assert account.hdpath.path == TEST_HD_PATH

    def test_sign_message_personal(self, mocker, account, account_connection):
        spy = mocker.spy(LedgerAccount, "_client")
        spy.sign_personal_message.return_value = (b"v", b"r", b"s")

        message = SignableMessage(
            version=b"E", header=b"thereum Signed Message:\n6", body=b"I\xe2\x99\xa5SF"
        )
        actual_v, actual_r, actual_s = account.sign_message(message)

        assert actual_v == b"v"
        assert actual_r == b"r"
        assert actual_s == b"s"
        spy.sign_personal_message.assert_called_once_with(message.body)

    def test_sign_message_typed(self, mocker, account, account_connection):
        spy = mocker.spy(LedgerAccount, "_client")
        spy.sign_typed_data.return_value = (b"v", b"r", b"s")

        message = TEST_TYPED_MESSAGE.signable_message
        actual_v, actual_r, actual_s = account.sign_message(message)

        assert actual_v == b"v"
        assert actual_r == b"r"
        assert actual_s == b"s"
        spy.sign_typed_data.assert_called_once_with(message.header, message.body)

    def test_sign_message_unsupported(self, account, account_connection):
        unsupported_version = b"X"
        message = SignableMessage(
            version=unsupported_version,
            header=b"thereum Signed Message:\n6",
            body=b"I\xe2\x99\xa5SF",
        )
        with pytest.raises(LedgerSigningError) as err:
            account.sign_message(message)

        actual = str(err.value)
        expected = (
            f"Unsupported message-signing specification, (version={unsupported_version})."
        )
        assert actual == expected

    def test_sign_transaction(self, mocker, account, account_connection):
        txn = StaticFeeTransaction()
        spy = mocker.spy(LedgerAccount, "_client")
        spy.sign_transaction.return_value = (b"v", b"r", b"s")

        # Values part of RLP
        txn.chain_id = 579875
        txn.nonce = 0
        txn.gas_price = 1
        txn.gas_limit = 2
        txn.receiver = TEST_RECEIVER.wallet
        txn.data = b"\x132235235235235"

        # Values not part of RLP
        txn.sender = TEST_SENDER.wallet
        txn.value = 100

        account.sign_transaction(txn)

        expected_txn_data = {
            "chainId": 579875,
            "nonce": 0,
            "gasPrice": 1,
            "gas": 2,
            "to": TEST_RECEIVER.wallet,
            "data": b"\x132235235235235",
        }
        spy.sign_transaction.assert_called_once_with(expected_txn_data)
