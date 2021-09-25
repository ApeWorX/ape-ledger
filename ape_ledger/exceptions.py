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


class AliasNotExistsError(LedgerAccountException):
    """
    An error raised when an account with the given alias does not exist.
    """

    def __init__(self, alias):
        super().__init__(f"The account with alias '{alias}' does not exist")


class LedgerUsbError(LedgerAccountException):
    def __init__(self, message, status=0):
        self.status = status
        super().__init__(message)


class LedgerTimeoutError(LedgerUsbError):
    """
    Raised when the Ledger client times-out waiting for a response from the device.
    """

    def __init__(self, timeout):
        message = (
            f"Timeout waiting device response (timeout={timeout}).\n"
            f"Make sure the Ledger device is not busy with another task."
        )
        super().__init__(message)
