import json
from pathlib import Path

from conftest import TEST_ADDRESS, TEST_ALIAS, TEST_HD_PATH, assert_account

from ape_ledger.accounts import AccountContainer, LedgerAccount


def create_account(account_path, hd_path):
    with open(account_path, "w") as account_file:
        account_data = {"address": TEST_ADDRESS, "hdpath": hd_path}
        account_file.writelines(json.dumps(account_data))


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
