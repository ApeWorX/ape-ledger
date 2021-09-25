from typing import List

import click
from ape import accounts
from ape.exceptions import AliasAlreadyInUseError
from ape.utils import Abort, notify
from eth_account import Account
from eth_account.messages import encode_defunct

from ape_ledger.accounts import LedgerAccount
from ape_ledger.choices import AddressPromptChoice
from ape_ledger.client import connect_to_ethereum_app
from ape_ledger.exceptions import AliasNotExistsError
from ape_ledger.hdpath import HDBasePath


@click.group(short_help="Manage Ledger accounts")
def cli():
    """
    Command-line helper for managing Ledger hardware device accounts.
    You can add accounts using the `add` command.
    """


skip_confirmation_option = click.option(
    "-y",
    "--yes",
    "skip_confirmation",
    default=False,
    is_flag=True,
    help="Don't ask for confirmation when removing the account",
)


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

    ledger_accounts = _get_ledger_accounts()

    if len(ledger_accounts) == 0:
        notify("WARNING", "No accounts found.")
        return

    num_accounts = len(accounts)
    header = f"Found {num_accounts} account"
    header += "s:" if num_accounts > 1 else ":"
    click.echo(header)

    for account in ledger_accounts:
        alias_display = f" (alias: '{account.alias}')" if account.alias else ""
        hd_path_display = f" (hd-path: '{account.hdpath}')" if account.hdpath else ""
        click.echo(f"  {account.address}{alias_display}{hd_path_display}")


def _get_ledger_accounts() -> List[LedgerAccount]:
    return [a for a in accounts if isinstance(a, LedgerAccount)]


@cli.command()
@non_existing_alias_argument
@click.option(
    "--hd-path",
    help=(
        f"The Ethereum account derivation path prefix. "
        f"Defaults to {HDBasePath.DEFAULT} where {{x}} is the account ID. "
        "Exclude {x} to append the account ID to the end of the base path."
    ),
    callback=lambda ctx, param, arg: HDBasePath(arg),
)
def add(alias, hd_path):
    """Add a account from your Ledger hardware wallet"""

    app = connect_to_ethereum_app(hd_path)
    choices = AddressPromptChoice(app)
    address, account_hd_path = choices.get_user_selected_account()
    container = accounts.containers.get("ledger")
    container.save_account(alias, address, str(account_hd_path))
    notify("SUCCESS", f"Account '{address}' successfully added with alias '{alias}'.")


@cli.command()
@existing_alias_argument
def delete(alias):
    """Remove a Ledger account from your ape configuration"""

    container = accounts.containers.get("ledger")
    container.delete_account(alias)
    notify("SUCCESS", f"Account '{alias}' has been removed")


@cli.command()
@skip_confirmation_option
def delete_all(skip_confirmation):
    """Remove all Ledger accounts from your ape configuration"""

    container = accounts.containers.get("ledger")
    ledger_accounts = _get_ledger_accounts()
    if len(ledger_accounts) == 0:
        notify("WARNING", "No accounts found.")
        return

    user_agrees = skip_confirmation or click.confirm("Remove all Ledger accounts from ape?")
    if not user_agrees:
        notify("INFO", "No account were removed.")
        return

    for account in ledger_accounts:
        container.delete_account(account.alias)
        notify("SUCCESS", f"Account '{account.alias}' has been removed")


@cli.command(short_help="Sign a message with your Ledger device")
@click.argument("alias")
@click.argument("message", default="Hello World!")
def sign_message(alias, message):
    if alias not in accounts.aliases:
        notify("ERROR", f"Account with alias '{alias}' does not exist")
        return

    eip191message = encode_defunct(text=message)
    account = accounts.load(alias)
    signature = account.sign_message(eip191message)
    signature_bytes = signature.encode_rsv()

    # Verify signature
    signer = Account.recover_message(eip191message, signature=signature_bytes)
    if signer != account.address:
        raise Abort(f"Signer resolves incorrectly, got {signer}, expected {account.address}.")

    # Message signed successfully
    output_signature = signature.encode_vrs().hex()
    click.echo(output_signature)
