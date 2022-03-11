import pytest
from ape import accounts
from ape._cli import cli
from ape.managers.accounts import AccountManager

from ape_ledger import LedgerAccount
from ape_ledger.hdpath import HDBasePath

from .conftest import TEST_ADDRESS, TEST_HD_PATH, assert_account


def _get_container():
    return accounts.containers["ledger"]


TEST_ALIAS = "__integration_test_alias__"
TEST_ACCOUNT_PATH = _get_container().data_folder.joinpath(f"{TEST_ALIAS}.json")


@pytest.fixture
def mock_account_manager(mocker):
    return mocker.MagicMock(spec=AccountManager)


@pytest.fixture
def mock_account(mocker):
    return mocker.MagicMock(spec=LedgerAccount)


@pytest.fixture
def mock_device_connection(mocker, mock_ethereum_app):
    patch = mocker.patch("ape_ledger._cli.connect_to_ethereum_app")
    patch.return_value = mock_ethereum_app
    return patch


@pytest.fixture
def existing_account(runner):
    try:
        container = _get_container()
        container.save_account(TEST_ALIAS, TEST_ADDRESS, TEST_HD_PATH)
        yield
    finally:
        _clean_up(runner)


@pytest.fixture(autouse=True)
def clean_after(runner):
    try:
        yield
    finally:
        _clean_up(runner)


def _clean_up(runner):
    runner.invoke(cli, ["ledger", "delete", TEST_ALIAS], input="y")


def _get_account_path(alias=TEST_ALIAS):
    container = _get_container()
    return container.data_folder.joinpath(f"{alias}.json")


def test_list(runner, existing_account):
    result = runner.invoke(cli, ["ledger", "list"])
    assert result.exit_code == 0, result.output
    assert TEST_ALIAS in result.output
    assert TEST_ADDRESS.lower() in result.output.lower()


def test_add(runner, mock_device_connection):
    selected_account_id = 0
    result = runner.invoke(cli, ["ledger", "add", TEST_ALIAS], input=str(selected_account_id))
    assert result.exit_code == 0, result.output
    assert (
        f"SUCCESS: Account '{TEST_ADDRESS}' successfully added with alias '{TEST_ALIAS}'."
        in result.output
    )

    container = _get_container()
    expected_path = container.data_folder.joinpath(f"{TEST_ALIAS}.json")
    expected_hd_path = f"m/44'/60'/{selected_account_id}'/0/0"
    assert_account(expected_path, expected_hdpath=expected_hd_path)


def test_add_when_hd_path_specified(
    runner, mock_ethereum_app, mock_device_connection, mock_account
):
    test_hd_path = "m/44'/60'/0'"
    mock_ethereum_app.hd_root_path = HDBasePath(test_hd_path)

    selected_account_id = 0
    result = runner.invoke(
        cli,
        ["ledger", "add", TEST_ALIAS, "--hd-path", test_hd_path],
        input=str(selected_account_id),
    )
    assert result.exit_code == 0, result.output
    assert (
        f"SUCCESS: Account '{TEST_ADDRESS}' successfully added with alias '{TEST_ALIAS}'."
        in result.output
    )

    expected_path = TEST_ACCOUNT_PATH
    expected_hd_path = f"m/44'/60'/0'/{selected_account_id}"
    assert_account(expected_path, expected_hdpath=expected_hd_path)


def test_add_alias_already_exists(
    runner, mock_ethereum_app, mock_device_connection, existing_account
):
    result = runner.invoke(cli, ["ledger", "add", TEST_ALIAS], input="0")
    assert result.exit_code == 1, result.output
    assert (
        f"ERROR: (AliasAlreadyInUseError) Account with alias '{TEST_ALIAS}' already in use."
        in result.output
    )


def test_delete(runner, existing_account):
    result = runner.invoke(cli, ["ledger", "delete", TEST_ALIAS])
    assert result.exit_code == 0, result.output
    assert f"SUCCESS: Account '{TEST_ALIAS}' has been removed" in result.output


def test_delete_account_not_exists(runner):
    result = runner.invoke(cli, ["ledger", "delete", TEST_ALIAS])
    assert result.exit_code == 2
    assert f"'{TEST_ALIAS}' is not one of" in result.output
