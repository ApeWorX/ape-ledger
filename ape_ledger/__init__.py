from importlib import import_module
from typing import Any

from ape import plugins


@plugins.register(plugins.AccountPlugin)
def account_types():
    from ape_ledger.accounts import AccountContainer, LedgerAccount

    return AccountContainer, LedgerAccount


def __getattr__(name: str) -> Any:
    if name in ("AccountContainer", "LedgerAccount"):
        return getattr(import_module("ape_ledger.accounts"), name)

    else:
        raise AttributeError(name)


__all__ = [
    "AccountContainer",
    "LedgerAccount",
]
