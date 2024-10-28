import pytest
from ape import accounts
from ape._cli import cli

from ape_ledger.hdpath import HDBasePath


def _get_container():
    return accounts.containers["ledger"]


@pytest.fixture
def alias():
    val = "__integration_test_alias__"
    container = _get_container()
    if val in [a.alias for a in container.accounts]:
        container.delete_account(val)

    return val


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


@pytest.fixture
def choices(mocker):
    def fn(addr, account_id):
        patch = mocker.patch("ape_ledger._cli._select_account")

        def se(hd_path):
            return addr, HDBasePath(hd_path).get_account_path(account_id)

        patch.side_effect = se

    return fn


def _clean_up(runner):
    runner.invoke(cli, ("ledger", "delete", alias), input="y")


def _get_account_path(alias=alias):
    container = _get_container()
    return container.data_folder.joinpath(f"{alias}.json")


@pytest.mark.parametrize("cmd", (["ledger", "list"], ["accounts", "list", "--all"]))
def test_list(runner, existing_account, cmd, address, alias):
    result = runner.invoke(cli, cmd)
    assert result.exit_code == 0, result.output
    assert alias in result.output
    assert address.lower() in result.output.lower()


def test_add(runner, assert_account, address, alias, choices, hd_path):
    container = _get_container()
    choices(address, 2)
    result = runner.invoke(cli, ("ledger", "add", alias), catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert f"Account '{address}' successfully added with alias '{alias}'." in result.output

    expected_path = container.data_folder.joinpath(f"{alias}.json")
    expected_hd_path = "m/44'/60'/2'/0/0"
    assert_account(expected_path, expected_hdpath=expected_hd_path)


def test_add_when_hd_path_specified(runner, alias, address, hd_path, assert_account, choices):
    test_hd_path = "m/44'/60'/0'"
    container = _get_container()
    choices(address, 2)
    result = runner.invoke(
        cli,
        ("ledger", "add", alias, "--hd-path", test_hd_path),
    )
    assert result.exit_code == 0, result.output
    assert f"Account '{address}' successfully added with alias '{alias}'." in result.output

    expected_path = container.data_folder.joinpath(f"{alias}.json")
    expected_hd_path = "m/44'/60'/0'/2"
    assert_account(expected_path, expected_hdpath=expected_hd_path)


def test_add_alias_already_exists(runner, existing_account, choices, address, alias):
    choices(address, 2)

    # Ensure exists
    runner.invoke(cli, ("ledger", "add", alias))

    result = runner.invoke(cli, ("ledger", "add", alias))
    assert result.exit_code == 1, result.output
    assert "ERROR:" in result.output
    assert "(AliasAlreadyInUseError)" in result.output
    assert f"Account with alias '{alias}' already in use." in result.output


def test_delete(runner, existing_account, alias):
    result = runner.invoke(cli, ("ledger", "delete", alias))
    assert result.exit_code == 0, result.output
    assert f"Account '{alias}' has been removed" in result.output


def test_delete_account_not_exists(runner, alias):
    not_alias = f"{alias}TYPO"
    result = runner.invoke(cli, ("ledger", "delete", not_alias))
    assert result.exit_code == 2
    assert f"'{not_alias}'" in result.output
