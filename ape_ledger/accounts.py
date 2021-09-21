import json
from pathlib import Path
from typing import Iterator, Optional

from ape.api.accounts import AccountAPI, AccountContainerAPI, TransactionAPI
from ape.convert import to_address
from ape.types import AddressType, MessageSignature, TransactionSignature
from eth_account.messages import SignableMessage

from ape_ledger.client import EthereumAccountClient, connect_to_ethereum_account


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

    def __delitem__(self, address: AddressType):
        pass

    def __setitem__(self, address: AddressType, account: AccountAPI):
        pass

    def save_account(self, alias: str, address: str, hd_path: str):
        """
        Save a new Ledger account to your ape configuration.
        """
        account_data = {"address": address, "hdpath": hd_path}
        path = self.data_folder.joinpath(f"{alias}.json")
        path.write_text(json.dumps(account_data))


class LedgerAccount(AccountAPI):
    _account_file_path: Path
    _account_client = None

    @property
    def alias(self) -> str:
        return self._account_file_path.stem

    @property
    def address(self) -> AddressType:
        return to_address(self.account_file["address"])

    @property
    def hdpath(self):
        return self.account_file["hdpath"]

    @property
    def account_file(self) -> dict:
        return json.loads(self._account_file_path.read_text())

    @property
    def _client(self) -> EthereumAccountClient:
        if self._account_client is None:
            self._account_client = connect_to_ethereum_account(self.address, self.hdpath)
        return self._account_client

    def sign_message(self, msg: SignableMessage) -> Optional[MessageSignature]:
        # TODO
        #        if msg.version == ""

        vrs = self._client.sign_message(text=str(msg.body))
        return MessageSignature(*vrs)  # type: ignore

    def sign_transaction(self, txn: TransactionAPI) -> Optional[TransactionSignature]:
        vrs = self._client.sign_transaction(txn.as_dict())
        return TransactionSignature(*vrs)  # type: ignore
