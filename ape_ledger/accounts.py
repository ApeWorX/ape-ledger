import json
from pathlib import Path
from typing import Dict, Iterator, Optional, Union

import click
from ape.api import AccountAPI, AccountContainerAPI, TransactionAPI
from ape.types import AddressType, MessageSignature, TransactionSignature
from ape_ethereum.transactions import DynamicFeeTransaction, StaticFeeTransaction
from eth_account.messages import SignableMessage
from eth_utils import is_0x_prefixed, to_bytes
from hexbytes import HexBytes

from ape_ledger.client import LedgerDeviceClient, get_device
from ape_ledger.exceptions import LedgerSigningError
from ape_ledger.hdpath import HDAccountPath


def _to_bytes(val):
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

        if path.exists():
            path.unlink()


def _echo_object_to_sign(obj: Union[TransactionAPI, SignableMessage]):
    click.echo(f"{obj}\nPlease follow the prompts on your device.")


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

    def sign_message(self, msg: SignableMessage) -> Optional[MessageSignature]:
        version = msg.version
        if version == b"E":
            _echo_object_to_sign(msg)
            signed_msg = self._client.sign_message(msg.body)
        elif version == b"\x01":
            _echo_object_to_sign(msg)
            header = _to_bytes(msg.header)
            body = _to_bytes(msg.body)
            signed_msg = self._client.sign_typed_data(header, body)
        else:
            raise LedgerSigningError(
                f"Unsupported message-signing specification, (version={version!r})."
            )

        v, r, s = signed_msg
        return MessageSignature(v=v, r=HexBytes(r), s=HexBytes(s))

    def sign_transaction(self, txn: TransactionAPI, **kwargs) -> Optional[TransactionAPI]:
        txn.chain_id = 1
        txn_dict: Dict = {
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
