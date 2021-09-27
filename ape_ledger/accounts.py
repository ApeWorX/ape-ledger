import json
from pathlib import Path
from typing import Iterator, Optional

from ape.api.accounts import AccountAPI, AccountContainerAPI, TransactionAPI
from ape.convert import to_address
from ape.types import AddressType, MessageSignature, TransactionSignature
from eth_account.messages import SignableMessage
from hexbytes import HexBytes

from ape_ledger.client import LedgerEthereumAccountClient, connect_to_ethereum_account
from ape_ledger.exceptions import LedgerSigningError
from ape_ledger.hdpath import HDAccountPath


def _extract_version(msg: SignableMessage) -> bytes:
    if isinstance(msg.version, HexBytes):
        return msg.version.hex().encode()

    return msg.version


class AccountContainer(AccountContainerAPI):
    _usb_device = None

    @property
    def _account_files(self) -> Iterator[Path]:
        return self.data_folder.glob("*.json")

    @property
    def aliases(self) -> Iterator[str]:
        for p in self._account_files:
            yield p.stem

    def __len__(self) -> int:
        return len([*self._account_files])

    def __iter__(self) -> Iterator[AccountAPI]:
        for account_file in self._account_files:
            yield LedgerAccount(self, account_file)  # type: ignore

    def save_account(self, alias: str, address: str, hd_path: str):
        """
        Save a new Ledger account to your ape configuration.
        """
        account_data = {"address": address, "hdpath": hd_path}
        path = self.data_folder.joinpath(f"{alias}.json")
        path.write_text(json.dumps(account_data))

    def delete_account(self, alias: str):
        path = self.data_folder.joinpath(f"{alias}.json")

        try:
            path.unlink()
        except FileNotFoundError:
            # It is ok file is missing.
            # NOTE: we are unable to use ``missing_ok`` parameter in `unlink()`
            # because of python 3.7 compatibility
            return


class LedgerAccount(AccountAPI):
    _account_file_path: Path

    # Optional because it's lazily loaded
    _account_client: Optional[LedgerEthereumAccountClient] = None

    @property
    def alias(self) -> str:
        return self._account_file_path.stem

    @property
    def address(self) -> AddressType:
        return to_address(self.account_file["address"])

    @property
    def hdpath(self) -> HDAccountPath:
        raw_path = self.account_file["hdpath"]
        return HDAccountPath(raw_path)

    @property
    def account_file(self) -> dict:
        return json.loads(self._account_file_path.read_text())

    @property
    def _client(self) -> LedgerEthereumAccountClient:
        if self._account_client is None:
            self._account_client = connect_to_ethereum_account(self.address, self.hdpath)
        return self._account_client

    def sign_message(self, msg: SignableMessage) -> Optional[MessageSignature]:
        version = _extract_version(msg)

        if version == b"E":
            vrs = self._client.sign_personal_message(msg.body)
        elif version == b"0x01":
            vrs = self._client.sign_typed_data(msg.header, msg.body)
        else:
            raise LedgerSigningError(
                f"Unsupported message-signing specification, (version={version!r})"
            )

        return MessageSignature(*vrs)  # type: ignore

    def sign_transaction(self, txn: TransactionAPI) -> Optional[TransactionSignature]:
        vrs = self._client.sign_transaction(txn.as_dict())
        return TransactionSignature(*vrs)  # type: ignore
