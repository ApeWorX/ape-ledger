import atexit
from functools import cached_property
from typing import Dict, Tuple

import hid  # type: ignore
from ape.logging import LogLevel, logger
from ledgerblue.comm import HIDDongleHIDAPI, getDongle  # type: ignore
from ledgereth.accounts import get_account_by_path
from ledgereth.messages import sign_message, sign_typed_data_draft
from ledgereth.transactions import SignedType2Transaction, create_transaction

from ape_ledger.hdpath import HDAccountPath


class DeviceFactory:
    device_map: Dict[str, "LedgerDeviceClient"] = {}

    def create_device(self, account: HDAccountPath):
        if account.path in self.device_map:
            return self.device_map[account.path]

        device = LedgerDeviceClient(account)
        self.device_map[account.path] = device
        return device


def get_dongle(debug: bool = False, reopen_on_fail: bool = True) -> HIDDongleHIDAPI:
    try:
        return getDongle(debug=debug)
    except (OSError, RuntimeError) as err:
        if str(err).lower().strip() in ("open failed", "already open") and reopen_on_fail:
            # Device was not closed properly.
            device = hid.device()
            device.close()
            return get_dongle(debug=debug, reopen_on_fail=False)

        raise  # the OSError


class LedgerDeviceClient:
    def __init__(self, account: HDAccountPath):
        self._account = account.path.lstrip("m/")

    @cached_property
    def dongle(self):
        debug = logger.level <= LogLevel.DEBUG
        device = get_dongle(debug=debug)

        def close():
            logger.info("Closing device.")
            device.close()

        atexit.register(close)
        return device

    def get_address(self) -> str:
        return get_account_by_path(self._account, dongle=self.dongle).address

    def sign_message(self, text: bytes) -> Tuple[int, int, int]:
        signed_msg = sign_message(text, sender_path=self._account, dongle=self.dongle)
        return signed_msg.v, signed_msg.r, signed_msg.s

    def sign_typed_data(self, domain_hash: bytes, message_hash: bytes) -> Tuple[int, int, int]:
        signed_msg = sign_typed_data_draft(
            domain_hash, message_hash, sender_path=self._account, dongle=self.dongle
        )
        return signed_msg.v, signed_msg.r, signed_msg.s

    def sign_transaction(self, txn: Dict) -> Tuple[int, int, int]:
        kwargs = {**txn, "sender_path": self._account, "dongle": self.dongle}
        signed_tx = create_transaction(**kwargs)
        if isinstance(signed_tx, SignedType2Transaction):
            return signed_tx.y_parity, signed_tx.sender_r, signed_tx.sender_s
        else:
            return signed_tx.v, signed_tx.r, signed_tx.s


_device_factory = DeviceFactory()


def get_device(account: HDAccountPath):
    return _device_factory.create_device(account)
