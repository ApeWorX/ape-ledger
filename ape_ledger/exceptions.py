from ape.exceptions import AccountsError


class LedgerAccountException(AccountsError):
    """
    An error that occurs in the ape Ledger plugin.
    """


class LedgerSigningError(LedgerAccountException):
    """
    An error that occurs when signing a message or transaction
    using the Ledger plugin.
    """
