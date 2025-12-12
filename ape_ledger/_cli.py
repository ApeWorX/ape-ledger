from typing import TYPE_CHECKING

import click
from ape.cli.arguments import existing_alias_argument, non_existing_alias_argument
from ape.cli.options import ape_cli_context, network_option, skip_confirmation_option

if TYPE_CHECKING:
    # NOTE: Type-checking only imports so CLI help loads faster.
    from ape.api import AccountAPI
    from ape_ledger.accounts import LedgerAccount
    from ape_ledger.hdpath import HDAccountPath, HDBasePath

from ape_ledger.exceptions import LedgerSigningError


def _select_account(hd_path: "HDBasePath | str") -> tuple[str, "HDAccountPath"]:
    # NOTE: Lazy import so CLI help loads faster.
    from ape_ledger.choices import AddressPromptChoice

    choices = AddressPromptChoice(hd_path)
    return choices.get_user_selected_account()


@click.group(short_help="Manage Ledger accounts")
def cli():
    """
    Manage Ledger hardware device accounts.
    """


@cli.command("list")
@ape_cli_context()
def _list(cli_ctx):
    """List your Ledger accounts in ape"""

    ledger_accounts = _get_ledger_accounts()

    if len(ledger_accounts) == 0:
        cli_ctx.logger.warning("No accounts found.")
        return

    num_accounts = len(ledger_accounts)
    header = f"Found {num_accounts} account"
    header += "s:" if num_accounts > 1 else ":"
    click.echo(header)

    for account in ledger_accounts:
        alias_display = f" (alias: '{account.alias}')" if account.alias else ""
        hd_path_display = f" (hd-path: '{account.hdpath}')" if account.hdpath else ""
        click.echo(f"  {account.address}{alias_display}{hd_path_display}")


def _get_ledger_accounts() -> list["LedgerAccount"]:
    from ape.utils.basemodel import ManagerAccessMixin

    from ape_ledger.accounts import LedgerAccount

    return [a for a in ManagerAccessMixin.account_manager if isinstance(a, LedgerAccount)]


def _hdpath_callback(ctx, param, val) -> "HDBasePath":
    from ape_ledger.hdpath import HDBasePath

    return HDBasePath(val)


@cli.command()
@ape_cli_context()
@non_existing_alias_argument()
@click.option(
    "--hd-path",
    help=(
        "The Ethereum account derivation path prefix. "
        "Defaults to m/44'/60'/{x}'/0/0 where {{x}} is the account ID. "
        "Exclude {x} to append the account ID to the end of the base path."
    ),
    callback=_hdpath_callback,
)
def add(cli_ctx, alias, hd_path):
    """Add an account from your Ledger hardware wallet"""

    address, account_hd_path = _select_account(hd_path)
    container = cli_ctx.account_manager.containers["ledger"]
    container.save_account(alias, address, str(account_hd_path))
    cli_ctx.logger.success(f"Account '{address}' successfully added with alias '{alias}'.")


def _filter_accounts(acct: "AccountAPI") -> bool:
    from ape_ledger.accounts import LedgerAccount

    return isinstance(acct, LedgerAccount)


@cli.command()
@ape_cli_context()
@existing_alias_argument(account_type=_filter_accounts)
def delete(cli_ctx, alias):
    """Remove a Ledger account from ape"""

    container = cli_ctx.account_manager.containers["ledger"]
    container.delete_account(alias)
    cli_ctx.logger.success(f"Account '{alias}' has been removed.")


@cli.command()
@ape_cli_context()
@skip_confirmation_option("Don't ask for confirmation when removing all accounts")
def delete_all(cli_ctx, skip_confirmation):
    """Remove all Ledger accounts from ape"""

    container = cli_ctx.account_manager.containers["ledger"]
    ledger_accounts = _get_ledger_accounts()
    if len(ledger_accounts) == 0:
        cli_ctx.logger.warning("No accounts found.")
        return

    user_agrees = skip_confirmation or click.confirm("Remove all Ledger accounts from ape?")
    if not user_agrees:
        cli_ctx.logger.info("No account were removed.")
        return

    for account in ledger_accounts:
        container.delete_account(account.alias)
        cli_ctx.logger.success(f"Account '{account.alias}' has been removed.")


@cli.command(short_help="Sign a message with your Ledger device")
@ape_cli_context()
@click.argument("alias")
@click.argument("message", default="Hello World!")
@network_option()
def sign_message(cli_ctx, alias, message, network):
    """Sign a message using a Ledger account"""

    ctx = None
    if network:
        ctx = cli_ctx.network_manager.parse_network_choice(network)
        ctx.__enter__()

    try:
        _sign_message(cli_ctx, alias, message)
    finally:
        if network and ctx and ctx._provider and ctx._provider.is_connected:
            ctx.__exit__()


def _sign_message(cli_ctx, alias, message):
    from eth_account.account import Account
    from eth_account.messages import encode_defunct

    if alias not in cli_ctx.account_manager.aliases:
        cli_ctx.abort(f"Account with alias '{alias}' does not exist.")

    eip191message = encode_defunct(text=message)
    account = cli_ctx.account_manager.load(alias)
    signature = account.sign_message(eip191message)

    if not signature:
        cli_ctx.abort("Failed to sign message.")

    signature_bytes = signature.encode_rsv()

    # Verify signature
    signer = Account.recover_message(eip191message, signature=signature_bytes)
    if signer != account.address:
        cli_ctx.abort(f"Signer resolves incorrectly, got {signer}, expected {account.address}.")

    # Message signed successfully, return signature
    click.echo(signature_bytes.hex())


@cli.command(short_help="Verify a message with your Trezor device")
@ape_cli_context()
@click.argument("message")
@click.argument("signature")
def verify_message(cli_ctx, message, signature):
    from eth_account.account import Account
    from eth_account.messages import encode_defunct

    eip191message = encode_defunct(text=message)

    try:
        signer_address = Account.recover_message(eip191message, signature=signature)
    except ValueError as exc:
        message = "Message cannot be verified. Check the signature and try again."
        raise LedgerSigningError(message) from exc

    alias = (
        cli_ctx.account_manager[signer_address].alias
        if signer_address in cli_ctx.account_manager
        else ""
    )
    click.echo(f"Signer: {signer_address}  {alias}")
