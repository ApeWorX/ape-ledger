import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import rich
from ape.api import AccountAPI, AccountContainerAPI, TransactionAPI
from ape.types import AddressType, MessageSignature, TransactionSignature
from ape_ethereum.transactions import DynamicFeeTransaction, StaticFeeTransaction
from eip712 import EIP712Message
from eth_account.messages import SignableMessage, encode_defunct
from eth_pydantic_types import HexBytes
from eth_utils import is_0x_prefixed, to_bytes
from ledgereth.exceptions import LedgerError

from ape_ledger.client import LedgerDeviceClient, get_device
from ape_ledger.exceptions import LedgerSigningError
from ape_ledger.hdpath import HDAccountPath


def _to_bytes(val) -> bytes:
    if val is None:
        return b""
    elif isinstance(val, str) and is_0x_prefixed(val):
        return to_bytes(hexstr=val)
    elif isinstance(val, str):
        return to_bytes(text=val)
    elif isinstance(val, HexBytes):
        return bytes(val)
    else:
        return to_bytes(val)


class AccountContainer(AccountContainerAPI):
    name: str = "ledger"

    @property
    def accounts(self) -> Iterator[AccountAPI]:
        for account_file in self._account_files:
            yield LedgerAccount(container=self, account_file_path=account_file)

    def __setitem__(self, address: AddressType, account: AccountAPI):
        raise NotImplementedError()

    def __delitem__(self, address: AddressType):
        raise NotImplementedError()

    @property
    def _account_files(self) -> Iterator[Path]:
        return self.data_folder.glob("*.json")

    @property
    def aliases(self) -> Iterator[str]:
        for p in self._account_files:
            yield p.stem

    def __len__(self) -> int:
        return len([*self._account_files])

    def save_account(self, alias: str, address: str, hd_path: str):
        """
        Save a new Ledger account to your ape configuration.
        """
        account_data = {"address": address, "hdpath": hd_path}
        path = self.data_folder.joinpath(f"{alias}.json")
        path.write_text(json.dumps(account_data))

    def delete_account(self, alias: str):
        path = self.data_folder.joinpath(f"{alias}.json")
        path.unlink(missing_ok=True)


def _echo_object_to_sign(obj: Any):

    if isinstance(obj, EIP712Message):
        # NOTE: pydantic models actually have very nice `rich.print` support
        rich.print(obj)

        # NOTE: Ledger Nano devices only show domain hash and message hash for EIP712
        _, domain_hash, message_hash = obj.signable_message
        rich.print(f"Domain Hash: 0x{domain_hash.hex().upper()}")
        rich.print(f"Message Hash: 0x{message_hash.hex().upper()}")

    else:  # NOTE: Do this to capture our native handling of TransactionAPI
        rich.print(str(obj))

    rich.print("\nPlease follow the prompts on your device.\n")


class LedgerAccount(AccountAPI):
    account_file_path: Path

    @property
    def alias(self) -> str:
        return self.account_file_path.stem

    @property
    def _client(self) -> LedgerDeviceClient:
        return get_device(self.hdpath)

    @property
    def address(self) -> AddressType:
        ecosystem = self.network_manager.get_ecosystem("ethereum")
        return ecosystem.decode_address(self.account_file["address"])

    @property
    def hdpath(self) -> HDAccountPath:
        raw_path = self.account_file["hdpath"]
        return HDAccountPath(raw_path)

    @property
    def account_file(self) -> dict:
        return json.loads(self.account_file_path.read_text())

    def sign_message(self, msg: Any, **signer_options) -> MessageSignature | None:
        use_eip712_package = isinstance(msg, EIP712Message)
        use_eip712 = use_eip712_package
        if isinstance(msg, str):
            msg_to_sign = encode_defunct(text=msg)
        elif isinstance(msg, int):
            msg_to_sign = encode_defunct(hexstr=HexBytes(msg).hex())
        elif isinstance(msg, bytes):
            msg_to_sign = encode_defunct(primitive=msg)
        elif use_eip712_package:
            # Using eip712 package.
            msg_to_sign = msg.signable_message
        elif isinstance(msg, SignableMessage):
            if msg.version == b"\x01":
                # Using EIP-712 without eip712 package.
                use_eip712 = True
            elif msg.version != b"E":
                try:
                    version_str = msg.version.decode("utf8")
                except Exception:
                    try:
                        version_str = HexBytes(msg.version).hex()
                    except Exception:
                        version_str = "<UnknownVersion>"

                raise LedgerSigningError(
                    f"Unsupported message-signing specification, (version={version_str})."
                )

            msg_to_sign = msg
        else:
            type_name = getattr(type(msg), "__name__", None)
            if not type_name:
                try:
                    type_name = str(type(msg))
                except Exception:
                    type_name = "<UnknownType>"

            raise LedgerSigningError(f"Cannot sign messages of type '{type_name}'.")

        # Echo original message.
        _echo_object_to_sign(msg)

        if use_eip712:
            header = HexBytes(msg_to_sign.header)
            body = HexBytes(msg_to_sign.body)
            try:
                signed_msg = self._client.sign_typed_data(header, body)

            except LedgerError:
                return None

        else:
            try:
                signed_msg = self._client.sign_message(msg_to_sign.body)

            except LedgerError:
                return None

        v, r, s = signed_msg
        return MessageSignature(v=v, r=HexBytes(r), s=HexBytes(s))

    def sign_transaction(self, txn: TransactionAPI, **kwargs) -> TransactionAPI | None:
        txn.chain_id = 1
        txn_dict: dict = {
            "nonce": txn.nonce,
            "gas": txn.gas_limit,
            "amount": txn.value,
            "data": _to_bytes(txn.data.hex()),
            "destination": _to_bytes(txn.receiver),
            "chain_id": txn.chain_id,
        }
        if isinstance(txn, StaticFeeTransaction):
            txn_dict["gas_price"] = txn.gas_price

        elif isinstance(txn, DynamicFeeTransaction):
            txn_dict["max_fee_per_gas"] = txn.max_fee
            txn_dict["max_priority_fee_per_gas"] = txn.max_priority_fee
            if txn.access_list:
                txn_dict["access_list"] = [[ls.address, ls.storage_keys] for ls in txn.access_list]

        else:
            raise TypeError(type(txn))

        _echo_object_to_sign(txn)
        v, r, s = self._client.sign_transaction(txn_dict)
        txn.signature = TransactionSignature(
            v=v,
            r=HexBytes(r),
            s=HexBytes(s),
        )
        return txn
