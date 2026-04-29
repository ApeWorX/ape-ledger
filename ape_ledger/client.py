import atexit
from typing import TYPE_CHECKING

import hid  # type: ignore
from ape.logging import LogLevel, logger
from ledgerblue.comm import HIDDongleHIDAPI, getDongle  # type: ignore
from ledgerblue.commException import CommException  # type: ignore
from ledgereth.accounts import get_account_by_path
from ledgereth.exceptions import LedgerError
from ledgereth.messages import sign_message, sign_typed_data_draft
from ledgereth.transactions import SignedType2Transaction, create_transaction

from ape_ledger.exceptions import LedgerAccountException

if TYPE_CHECKING:
    from ape_ledger.hdpath import HDAccountPath


LEDGER_VENDOR_ID = 0x2C97


class DeviceFactory:
    device_map: dict[str, "LedgerDeviceClient"] = {}

    def create_device(self, account: "HDAccountPath"):
        if account.path in self.device_map:
            return self.device_map[account.path]

        device = LedgerDeviceClient(account)
        self.device_map[account.path] = device
        return device


def _ledger_is_connected() -> bool:
    try:
        return any(d.get("vendor_id") == LEDGER_VENDOR_ID for d in hid.enumerate(0, 0))
    except OSError:
        # Some platforms raise on enumeration when permissions are missing.
        return False


def _open_failed_message() -> str:
    if _ledger_is_connected():
        return (
            "Detected a Ledger device but could not open it. Common causes:\n"
            "  - Ledger Live (or another app) is connected to the device. Quit it and retry.\n"
            "  - The device is locked. Unlock it with your PIN.\n"
            "  - The Ethereum app is not open on the device. Open it and retry.\n"
        )
    return (
        "No Ledger device detected. Plug in the device, unlock it, "
        "and open the Ethereum app, then retry."
    )


_dongle_cache: HIDDongleHIDAPI | None = None


def _close_cached_dongle() -> None:
    global _dongle_cache
    if _dongle_cache is not None:
        logger.info("Closing device.")
        try:
            _dongle_cache.close()
        except Exception:
            pass
        _dongle_cache = None


def get_dongle(debug: bool = False) -> HIDDongleHIDAPI:
    # The HID handle must be shared across all LedgerDeviceClient instances:
    # hidapi only allows one open handle per device, so opening a second
    # dongle while the first is still alive raises "open failed".
    global _dongle_cache
    if _dongle_cache is not None:
        return _dongle_cache

    try:
        _dongle_cache = getDongle(debug=debug)
    except (OSError, RuntimeError) as err:
        raise LedgerAccountException(_open_failed_message()) from err
    except CommException as err:
        # ledgerblue raises CommException("No dongle found") when enumeration
        # finds nothing — surface the same actionable message.
        if "no dongle" in (err.message or "").lower():
            raise LedgerAccountException(_open_failed_message()) from err
        raise LedgerAccountException(f"Failed to communicate with Ledger: {err.message}") from err
    except LedgerError as err:
        raise LedgerAccountException(f"Failed to communicate with Ledger: {err}") from err

    atexit.register(_close_cached_dongle)
    return _dongle_cache


class LedgerDeviceClient:
    def __init__(self, account: "HDAccountPath"):
        self._account = account.path.lstrip("m/")

    @property
    def dongle(self) -> HIDDongleHIDAPI:
        return get_dongle(debug=logger.level <= LogLevel.DEBUG)

    def get_address(self) -> str:
        return get_account_by_path(self._account, dongle=self.dongle).address

    def sign_message(self, text: bytes) -> tuple[int, int, int]:
        signed_msg = sign_message(text, sender_path=self._account, dongle=self.dongle)
        return signed_msg.v, signed_msg.r, signed_msg.s

    def sign_typed_data(self, domain_hash: bytes, message_hash: bytes) -> tuple[int, int, int]:
        signed_msg = sign_typed_data_draft(
            domain_hash, message_hash, sender_path=self._account, dongle=self.dongle
        )
        return signed_msg.v, signed_msg.r, signed_msg.s

    def sign_transaction(self, txn: dict) -> tuple[int, int, int]:
        kwargs = {**txn, "sender_path": self._account, "dongle": self.dongle}
        signed_tx = create_transaction(**kwargs)
        return (
            (signed_tx.y_parity, signed_tx.sender_r, signed_tx.sender_s)
            if isinstance(signed_tx, SignedType2Transaction)
            else (signed_tx.v, signed_tx.r, signed_tx.s)
        )


_device_factory = DeviceFactory()


def get_device(account: "HDAccountPath") -> LedgerDeviceClient:
    return _device_factory.create_device(account)
