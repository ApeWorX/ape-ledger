from ape import plugins

from ape_ledger.accounts import AccountContainer, LedgerAccount


@plugins.register(plugins.AccountPlugin)
def account_types():
    return AccountContainer, LedgerAccount
