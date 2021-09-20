from ape.exceptions import AccountsError


class AliasNotExistsError(AccountsError):
    """
    An error raised when an account with the given alias does not exist.
    """

    def __init__(self, alias):
        super().__init__(f"The account with alias '{alias}' does not exist")


class LedgerUsbException(AccountsError):
    def __init__(self, message, status=0):
        self.status = status
        super().__init__(message)
