import json
from pathlib import Path

import pytest
from conftest import TEST_ADDRESS, TEST_ALIAS, TEST_HD_PATH, assert_account
from eth_account.messages import SignableMessage

from ape_ledger.accounts import AccountContainer, LedgerAccount


def create_account(account_path, hd_path):
    with open(account_path, "w") as account_file:
        account_data = {"address": TEST_ADDRESS, "hdpath": hd_path}
        account_file.writelines(json.dumps(account_data))


@pytest.fixture
def account_connection(mocker, ledger_account):
    patch = mocker.patch("ape_ledger.accounts.connect_to_ethereum_account")
    patch.return_value = ledger_account
    return patch


class TestAccountContainer:
    def test_save_account(self, runner, mock_container):
        with runner.isolated_filesystem():
            # noinspection PyArgumentList
            container = AccountContainer(Path("."), LedgerAccount)
            container.save_account(TEST_ALIAS, TEST_ADDRESS, TEST_HD_PATH)

            assert_account(f"{TEST_ALIAS}.json", expected_hdpath=TEST_HD_PATH)


class TestLedgerAccount:
    def test_address_returns_address_from_file(self, runner, mock_container):
        with runner.isolated_filesystem():
            create_account("account.json", TEST_HD_PATH)
            # noinspection PyArgumentList
            account = LedgerAccount(mock_container, Path("account.json"))
            assert account.address.lower() == TEST_ADDRESS.lower()

    def test_hdpath_returns_address_from_file(self, runner, mock_container):
        with runner.isolated_filesystem():
            create_account("account.json", TEST_HD_PATH)
            # noinspection PyArgumentList
            account = LedgerAccount(mock_container, Path("account.json"))
            assert account.hdpath == TEST_HD_PATH

    def test_sign_message_when_defunct_message_type(
        self, mocker, runner, mock_container, account_connection
    ):
        with runner.isolated_filesystem():
            create_account("account.json", TEST_HD_PATH)
            # noinspection PyArgumentList
            account = LedgerAccount(mock_container, Path("account.json"))
            spy = mocker.spy(LedgerAccount, "_client")
            spy.sign_raw_message.return_value = (b"v", b"r", b"s")

            message = SignableMessage(
                version=b"E", header=b"thereum Signed Message:\n6", body=b"I\xe2\x99\xa5SF"
            )
            actual = account.sign_message(message)

            spy.sign_raw_message.assert_called_once_with(message)
            assert actual.v == b"v"
            assert actual.r == b"r"
            assert actual.s == b"s"
