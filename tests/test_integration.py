import pytest
from ape import accounts
from ape._cli import cli

from ape_ledger.hdpath import HDBasePath


def _get_container():
    return accounts.containers["ledger"]


@pytest.fixture
def alias():
    return "__integration_test_alias__"


@pytest.fixture
def test_account_path(alias):
    return _get_container().data_folder.joinpath(f"{alias}.json")


@pytest.fixture
def existing_account(runner, alias, address, hd_path):
    try:
        container = _get_container()
        container.save_account(alias, address, hd_path)
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
    runner.invoke(cli, ["ledger", "delete", alias], input="y")


def _get_account_path(alias=alias):
    container = _get_container()
    return container.data_folder.joinpath(f"{alias}.json")


@pytest.mark.parametrize("cmd", (["ledger", "list"], ["accounts", "list", "--all"]))
def test_list(runner, existing_account, cmd, address):
    result = runner.invoke(cli, cmd)
    assert result.exit_code == 0, result.output
    assert alias in result.output
    assert address.lower() in result.output.lower()


def test_add(runner, mock_device_connection, assert_account, address, alias):
    selected_account_id = 0
    result = runner.invoke(cli, ["ledger", "add", alias], input=str(selected_account_id))
    assert result.exit_code == 0, result.output
    assert f"SUCCESS: Account '{address}' successfully added with alias '{alias}'." in result.output

    container = _get_container()
    expected_path = container.data_folder.joinpath(f"{alias}.json")
    expected_hd_path = f"m/44'/60'/{selected_account_id}'/0/0"
    assert_account(expected_path, expected_hdpath=expected_hd_path)


def test_add_when_hd_path_specified(
    runner, mock_ethereum_app, mock_device_connection, alias, address, hd_path, assert_account
):
    test_hd_path = "m/44'/60'/0'"
    mock_ethereum_app.hd_root_path = HDBasePath(test_hd_path)

    selected_account_id = 0
    result = runner.invoke(
        cli,
        ["ledger", "add", alias, "--hd-path", test_hd_path],
        input=str(selected_account_id),
    )
    assert result.exit_code == 0, result.output
    assert f"SUCCESS: Account '{address}' successfully added with alias '{alias}'." in result.output

    expected_path = hd_path
    expected_hd_path = f"m/44'/60'/0'/{selected_account_id}"
    assert_account(expected_path, expected_hdpath=expected_hd_path)


def test_add_alias_already_exists(runner, mock_device_connection, existing_account):
    result = runner.invoke(cli, ["ledger", "add", alias], input="0")
    assert result.exit_code == 1, result.output
    assert (
        f"ERROR: (AliasAlreadyInUseError) Account with alias '{alias}' already in use."
        in result.output
    )


def test_delete(runner, existing_account, alias):
    result = runner.invoke(cli, ["ledger", "delete", alias])
    assert result.exit_code == 0, result.output
    assert f"SUCCESS: Account '{alias}' has been removed" in result.output


def test_delete_account_not_exists(runner, alias):
    result = runner.invoke(cli, ["ledger", "delete", alias])
    assert result.exit_code == 2
    assert f"'{alias}' is not one of" in result.output
