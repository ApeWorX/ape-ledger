from typing import Tuple

import click
from ape import accounts
from ape.exceptions import AliasAlreadyInUseError
from ape.utils import Abort, notify

from ape_ledger.accounts import LedgerAccount
from ape_ledger.choices import AddressPromptChoice
from ape_ledger.client import connect_to_ethereum_app
from ape_ledger.exceptions import AliasNotExistsError
from ape_ledger.hdpath import HDAccountPath, HDBasePath


def _get_container():
    return accounts.containers.get("ledger")


@click.group(short_help="Manage Ledger accounts")
def cli():
    """
    Command-line helper for managing Ledger hardware device accounts.
    You can add accounts using the add method.
    """


def _require_non_existing_alias(arg):
    if arg in accounts.aliases:
        raise AliasAlreadyInUseError(arg)
    return arg


def _require_existing_alias(arg):
    if arg not in accounts.aliases:
        raise AliasNotExistsError(arg)
    return arg


existing_alias_argument = click.argument(
    "alias", callback=lambda ctx, param, arg: _require_existing_alias(arg)
)
non_existing_alias_argument = click.argument(
    "alias", callback=lambda ctx, param, arg: _require_non_existing_alias(arg)
)


@cli.command("list")
def _list():
    """List the Ledger accounts in your ape configuration"""

    ledger_accounts = [a for a in accounts if isinstance(a, LedgerAccount)]
    for ledger_account in ledger_accounts:
        click.echo(f"{ledger_account.alias}:")
        click.echo(f"\taddress: {ledger_account.address.lower()}")


def _handle_hd_path(arg: str) -> Tuple[str, HDAccountPath]:
    path = HDBasePath(arg or HDBasePath.DEFAULT)
    app = connect_to_ethereum_app(path)
    choices = AddressPromptChoice(app)
    return choices.get_user_selected_account()


@cli.command()
@non_existing_alias_argument
@click.option(
    "--hdpath",
    "account_choice",
    help=(
        f"The Ethereum account derivation path prefix. "
        f"Defaults to {HDBasePath.DEFAULT} where {{x}} is the account ID. "
        "Exclude {{x}} to append the account ID to the end of the base path."
    ),
    callback=lambda ctx, param, arg: _handle_hd_path(arg),
)
def add(alias, account_choice):
    """Add a account from your Ledger hardware wallet"""

    address, account_hd_path = account_choice
    container = _get_container()
    container.save_account(alias, address, str(account_hd_path))
    notify("SUCCESS", f"Account '{address}' successfully added with alias '{alias}'.")


@cli.command()
@existing_alias_argument
@click.option(
    "-y",
    "--yes",
    "skip_confirmation",
    default=False,
    is_flag=True,
    help="Don't ask for confirmation when removing the account",
)
def remove(alias, skip_confirmation):
    """Remove a Ledger account from your ape configuration.
    (The account will not be deleted from the Ledger hardware device)"""

    if not _user_agrees_to_remove(skip_confirmation, alias):
        notify("INFO", f"'{alias}' was not removed")
        return

    container = _get_container()
    path = container.data_folder.joinpath(f"{alias}.json")

    try:
        path.unlink()
        notify("SUCCESS", f"Account '{alias}' has been removed")
    except Exception as err:
        raise Abort(f"File does not exist: {path}") from err


def _user_agrees_to_remove(skip_confirmation, alias):
    return skip_confirmation or click.confirm(f"Remove account '{alias}' from ape?")
