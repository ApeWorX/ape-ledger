from typing import Dict, Tuple

from ledgereth.accounts import get_account_by_path  # type: ignore
from ledgereth.messages import sign_message
from ledgereth.transactions import SignedType2Transaction, create_transaction  # type: ignore

from ape_ledger.hdpath import HDAccountPath


class DeviceFactory:
    device_map: Dict[str, "Device"] = {}

    def create_device(self, account: HDAccountPath):
        if account.path in self.device_map:
            return self.device_map[account.path]

        device = Device(account)
        self.device_map[account.path] = device
        return device


class Device:
    def __init__(self, account: HDAccountPath):
        self._account = account.path.lstrip("m/")

    def get_address(self) -> str:
        return get_account_by_path(self._account)

    def sign_message(self, text: str) -> Tuple[int, int, int]:
        signed_msg = sign_message(text, sender_path=self._account)
        return signed_msg.v, signed_msg.r, signed_msg.s

    def sign_transaction(self, txn: Dict) -> Tuple[int, int, int]:
        kwargs = {**txn, "sender_path": self._account}
        signed_tx = create_transaction(**kwargs)
        if isinstance(signed_tx, SignedType2Transaction):
            return 1, signed_tx.sender_r, signed_tx.sender_s
        else:
            return signed_tx.v, signed_tx.r, signed_tx.s


_device_factory = DeviceFactory()


def get_device(account: HDAccountPath):
    return _device_factory.create_device(account)
