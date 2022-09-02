import json
from pathlib import Path
from typing import Iterator, Optional, Union

import click
import rlp  # type: ignore
from ape.api import AccountAPI, AccountContainerAPI, TransactionAPI
from ape.types import AddressType, MessageSignature, TransactionSignature
from ape_ethereum.transactions import TransactionType
from eth_account.messages import SignableMessage
from hexbytes import HexBytes

from ape_ledger.client import LedgerEthereumAccountClient, connect_to_ethereum_account
from ape_ledger.exceptions import LedgerSigningError
from ape_ledger.hdpath import HDAccountPath
from ape_ledger.objects import DynamicFeeTransaction, StaticFeeTransaction


class AccountContainer(AccountContainerAPI):
    @property
    def accounts(self) -> Iterator[AccountAPI]:
        for account_file in self._account_files:
            yield LedgerAccount(container=self, account_file_path=account_file)  # type: ignore

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

    # Optional because it's lazily loaded
    account_client: Optional[LedgerEthereumAccountClient] = None

    @property
    def alias(self) -> str:
        return self.account_file_path.stem

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

    @property
    def _client(self) -> LedgerEthereumAccountClient:
        if self.account_client is None:
            self.account_client = connect_to_ethereum_account(self.address, self.hdpath)
        return self.account_client

    def sign_message(self, msg: SignableMessage) -> Optional[MessageSignature]:
        version = msg.version
        if version == b"E":
            _echo_object_to_sign(msg)
            signed_msg = self._client.sign_personal_message(msg.body)
        elif version == b"\x01":
            _echo_object_to_sign(msg)
            signed_msg = self._client.sign_typed_data(msg.header, msg.body)
        else:
            raise LedgerSigningError(
                f"Unsupported message-signing specification, (version={version!r})."
            )

        v, r, s = signed_msg
        return MessageSignature(v, r, s)  # type: ignore

    def sign_transaction(self, txn: TransactionAPI) -> Optional[TransactionSignature]:
        txn_type = TransactionType(txn.type)  # In case it is not enum
        if txn_type == TransactionType.STATIC:
            serializable_txn = StaticFeeTransaction(**txn.dict())
            txn_bytes = rlp.encode(serializable_txn, StaticFeeTransaction)
        else:
            serializable_txn = DynamicFeeTransaction(**txn.dict())
            version_byte = bytes(HexBytes(TransactionType.DYNAMIC.value))
            txn_bytes = version_byte + rlp.encode(serializable_txn, DynamicFeeTransaction)

        _echo_object_to_sign(txn)
        v, r, s = self._client.sign_transaction(txn_bytes)

        chain_id = txn.chain_id
        # NOTE: EIP-1559 transactions don't pack 'chain_id' with 'v'.
        if txn_type != TransactionType.DYNAMIC and (chain_id * 2 + 35) + 1 > 255:
            ecc_parity = v - ((chain_id * 2 + 35) % 256)
            v = (chain_id * 2 + 35) + ecc_parity

        return TransactionSignature(v, r, s)  # type: ignore
