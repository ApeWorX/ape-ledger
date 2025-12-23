import json
from typing import TYPE_CHECKING, cast

import pytest
from ape import networks
from ape.utils import create_tempdir
from ape_ethereum.ecosystem import DynamicFeeTransaction, StaticFeeTransaction
from eip712.messages import EIP712Domain, EIP712Message
from eth_account.messages import SignableMessage
from eth_pydantic_types import HexBytes, abi
from pydantic import BaseModel

from ape_ledger.accounts import AccountContainer, LedgerAccount
from ape_ledger.exceptions import LedgerSigningError

if TYPE_CHECKING:
    from ape.api import TransactionAPI
    from ape.types import AddressType


@pytest.fixture(autouse=True)
def patch_device(device_factory):
    return device_factory("accounts")


class Person(BaseModel):
    name: abi.string
    wallet: abi.address


class Mail(EIP712Message):
    eip712_domain = EIP712Domain(
        chainId=1,
        name="Ether Mail",
        verifyingContract="0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC",
        version="1",
    )

    sender: Person
    receiver: Person


ALICE_ADDRESS = "0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826"
TEST_SENDER = Person(name="Alice", wallet=ALICE_ADDRESS)  # type: ignore
BOB_ADDRESS = "0xB0B0b0b0b0b0B000000000000000000000000000"
TEST_RECEIVER = Person(name="Bob", wallet=BOB_ADDRESS)  # type: ignore
TEST_TYPED_MESSAGE = Mail(sender=TEST_SENDER, receiver=TEST_RECEIVER)  # type: ignore
TEST_TXN_DATA = b"""`\x80`@R4\x80\x15a\x00\x10W`\x00\x80\xfd[P`\x00\x80T`\x01`\x01`\xa0\x1b\x03\x19\x163\x17\x90U`\x03\x80T`\xff\x19\x16`\x01\x17\x90Ua\x04\xa8\x80a\x00?`\x009`\x00\xf3\xfe`\x80`@R`\x046\x10a\x00pW`\x005`\xe0\x1c\x80c>G\xd6\xf3\x11a\x00NW\x80c>G\xd6\xf3\x14a\x00\xd4W\x80c\x8d\xa5\xcb[\x14a\x01\x19W\x80c\xb6\rB\x88\x14a\x01JW\x80c\xdc\r=\xff\x14a\x01RWa\x00pV[\x80c\x12)\xdc\x9e\x14a\x00uW\x80c#\x8d\xaf\xe0\x14a\x00\xa3W\x80c<\xcf\xd6\x0b\x14a\x00\xccW[`\x00\x80\xfd[4\x80\x15a\x00\x81W`\x00\x80\xfd[Pa\x00\xa1`\x04\x806\x03` \x81\x10\x15a\x00\x98W`\x00\x80\xfd[P5\x15\x15a\x01|V[\x00[4\x80\x15a\x00\xafW`\x00\x80\xfd[Pa\x00\xb8a\x01\xdcV[`@\x80Q\x91\x15\x15\x82RQ\x90\x81\x90\x03` \x01\x90\xf3[a\x00\xa1a\x01\xe5V[4\x80\x15a\x00\xe0W`\x00\x80\xfd[Pa\x01\x07`\x04\x806\x03` \x81\x10\x15a\x00\xf7W`\x00\x80\xfd[P5`\x01`\x01`\xa0\x1b\x03\x16a\x02\xddV[`@\x80Q\x91\x82RQ\x90\x81\x90\x03` \x01\x90\xf3[4\x80\x15a\x01%W`\x00\x80\xfd[Pa\x01.a\x02\xefV[`@\x80Q`\x01`\x01`\xa0\x1b\x03\x90\x92\x16\x82RQ\x90\x81\x90\x03` \x01\x90\xf3[a\x00\xa1a\x02\xfeV[4\x80\x15a\x01^W`\x00\x80\xfd[Pa\x01.`\x04\x806\x03` \x81\x10\x15a\x01uW`\x00\x80\xfd[P5a\x03\xa4V[`\x00T`\x01`\x01`\xa0\x1b\x03\x163\x14a\x01\xc9W`@\x80QbF\x1b\xcd`\xe5\x1b\x81R` `\x04\x82\x01R`\x0b`$\x82\x01Rj\x08X]]\x1a\x1b\xdc\x9a^\x99Y`\xaa\x1b`D\x82\x01R\x90Q\x90\x81\x90\x03`d\x01\x90\xfd[`\x03\x80T`\xff\x19\x16\x91\x15\x15\x91\x90\x91\x17\x90UV[`\x03T`\xff\x16\x81V[`\x00T`\x01`\x01`\xa0\x1b\x03\x163\x14a\x022W`@\x80QbF\x1b\xcd`\xe5\x1b\x81R` `\x04\x82\x01R`\x0b`$\x82\x01Rj\x08X]]\x1a\x1b\xdc\x9a^\x99Y`\xaa\x1b`D\x82\x01R\x90Q\x90\x81\x90\x03`d\x01\x90\xfd[`\x03T`\xff\x16a\x02AW`\x00\x80\xfd[`@Q3\x90G\x80\x15a\x08\xfc\x02\x91`\x00\x81\x81\x81\x85\x88\x88\xf1\x93PPPP\x15\x80\x15a\x02mW=`\x00\x80>=`\x00\xfd[P`\x00[`\x02T\x81\x10\x15a\x02\xbcW`\x00`\x02\x82\x81T\x81\x10a\x02\x8aW\xfe[`\x00\x91\x82R` \x80\x83 \x90\x91\x01T`\x01`\x01`\xa0\x1b\x03\x16\x82R`\x01\x90\x81\x90R`@\x82 \x91\x90\x91U\x91\x90\x91\x01\x90Pa\x02qV[P`@\x80Q`\x00\x81R` \x81\x01\x91\x82\x90RQa\x02\xda\x91`\x02\x91a\x03\xcbV[PV[`\x01` R`\x00\x90\x81R`@\x90 T\x81V[`\x00T`\x01`\x01`\xa0\x1b\x03\x16\x81V[`\x03T`\xff\x16a\x03\rW`\x00\x80\xfd[`\x004\x11a\x03LW`@QbF\x1b\xcd`\xe5\x1b\x81R`\x04\x01\x80\x80` \x01\x82\x81\x03\x82R`#\x81R` \x01\x80a\x04P`#\x919`@\x01\x91PP`@Q\x80\x91\x03\x90\xfd[3`\x00\x81\x81R`\x01` \x81\x90R`@\x82 \x80T4\x01\x90U`\x02\x80T\x91\x82\x01\x81U\x90\x91R\x7f@W\x87\xfa\x12\xa8#\xe0\xf2\xb7c\x1c\xc4\x1b;\xa8\x82\x8b3!\xca\x81\x11\x11\xfau\xcd:\xa3\xbbZ\xce\x01\x80T`\x01`\x01`\xa0\x1b\x03\x19\x16\x90\x91\x17\x90UV[`\x02\x81\x81T\x81\x10a\x03\xb1W\xfe[`\x00\x91\x82R` \x90\x91 \x01T`\x01`\x01`\xa0\x1b\x03\x16\x90P\x81V[\x82\x80T\x82\x82U\x90`\x00R` `\x00 \x90\x81\x01\x92\x82\x15a\x04 W\x91` \x02\x82\x01[\x82\x81\x11\x15a\x04 W\x82Q\x82T`\x01`\x01`\xa0\x1b\x03\x19\x16`\x01`\x01`\xa0\x1b\x03\x90\x91\x16\x17\x82U` \x90\x92\x01\x91`\x01\x90\x91\x01\x90a\x03\xebV[Pa\x04,\x92\x91Pa\x040V[P\x90V[[\x80\x82\x11\x15a\x04,W\x80T`\x01`\x01`\xa0\x1b\x03\x19\x16\x81U`\x01\x01a\x041V\xfeFund amount must be greater than 0.\xa2dipfsX"\x12 \\.\xe1\xb9\xbd\xde\x0b.`io)\xf2\xb6\xf1\xd5\xce\x1d\xd7_\x8b\xfd\xf6\xfbT\x14#\x1a\x12\xcf\xa7\xffdsolcC\x00\x06\x0c\x003"""  # noqa: E501


def build_transaction(
    txn: "TransactionAPI", receiver: "AddressType | None" = None
) -> "TransactionAPI":
    txn.chain_id = 579875
    txn.nonce = 0
    txn.gas_limit = 2
    txn.value = 10000000000
    txn.data = HexBytes(TEST_TXN_DATA)

    if receiver:
        txn.receiver = receiver

    # Values not part of RLP
    txn.sender = TEST_SENDER.wallet

    return txn


def create_static_fee_txn(
    receiver: "AddressType | None" = None,
) -> StaticFeeTransaction:
    txn = StaticFeeTransaction()
    txn = cast(StaticFeeTransaction, build_transaction(txn, receiver=receiver))
    txn.gas_price = 1
    return txn


def create_dynamic_fee_txn(
    receiver: "AddressType | None" = None,
) -> DynamicFeeTransaction:
    txn = DynamicFeeTransaction()
    txn = cast(DynamicFeeTransaction, build_transaction(txn, receiver=receiver))
    txn.max_fee = 300000000
    txn.max_priority_fee = 10000000
    return txn


TEST_STATIC_FEE_TXN = create_static_fee_txn()
TEST_STATIC_FEE_TXN_WITH_RECEIVER = create_static_fee_txn(receiver=TEST_RECEIVER.wallet)
TEST_DYNAMIC_FEE_TXN = create_dynamic_fee_txn()
TEST_DYNAMIC_FEE_TXN_WITH_RECEIVER = create_dynamic_fee_txn(receiver=TEST_RECEIVER.wallet)


@pytest.fixture
def create_account(address):
    def fn(account_path, hd_path):
        with open(account_path, "w") as account_file:
            account_data = {"address": address, "hdpath": hd_path}
            account_file.writelines(json.dumps(account_data))

    return fn


@pytest.fixture(autouse=True)
def isolated_file_system(runner):
    with runner.isolated_filesystem():
        yield


@pytest.fixture
def account(mock_container, create_account, hd_path):
    with create_tempdir() as temp_dir:
        path = temp_dir / "account.json"
        create_account(path, hd_path)
        with networks.ethereum.local.use_provider("test"):
            yield LedgerAccount(name=mock_container, account_file_path=path)


class TestAccountContainer:
    def test_save_account(self, mock_container, alias, address, hd_path, assert_account):
        container = AccountContainer(account_type=LedgerAccount)
        container.save_account(alias, address, hd_path)
        temp_dir = container.config_manager.DATA_FOLDER
        account_path = temp_dir / "ledger" / f"{alias}.json"
        assert_account(account_path, expected_hdpath=hd_path)


class TestLedgerAccount:
    def test_address_returns_address_from_file(self, account, address):
        assert account.address.lower() == address.lower()

    def test_hdpath_returns_address_from_file(self, account, hd_path):
        assert account.hdpath.path == hd_path

    def test_sign_message_personal(self, account, capsys, mock_device, msg_signature):
        message = SignableMessage(
            version=b"E", header=b"thereum Signed Message:\n6", body=b"I\xe2\x99\xa5SF"
        )
        v, r, s = account.sign_message(message)
        assert (v, int(r.hex(), 16), int(s.hex(), 16)) == msg_signature
        mock_device.sign_message.assert_called_once_with(message.body)
        output = capsys.readouterr()
        assert str(message) in output.out
        assert "Please follow the prompts on your device." in output.out

    def test_sign_message_typed(self, account, capsys, msg_signature):
        message = TEST_TYPED_MESSAGE.signable_message
        v, r, s = account.sign_message(message)
        assert (v, int(r.hex(), 16), int(s.hex(), 16)) == msg_signature
        output = capsys.readouterr()
        assert repr(message).replace("\n", "") in output.out.replace("\n", "")
        assert "Please follow the prompts on your device." in output.out

    def test_sign_message_unsupported(self, account, capsys):
        unsupported_version = b"X"
        message = SignableMessage(
            version=unsupported_version,
            header=b"thereum Signed Message:\n6",
            body=b"I\xe2\x99\xa5SF",
        )
        version_str = unsupported_version.decode("utf8")
        expected = rf"Unsupported message-signing specification, \(version={version_str}\)\."
        with pytest.raises(LedgerSigningError, match=expected):
            account.sign_message(message)

        output = capsys.readouterr()
        assert str(message) not in output.out
        assert "Please follow the prompts on your device." not in output.out

    @pytest.mark.parametrize(
        "txn",
        (
            TEST_STATIC_FEE_TXN,
            TEST_STATIC_FEE_TXN_WITH_RECEIVER,
            TEST_DYNAMIC_FEE_TXN,
            TEST_DYNAMIC_FEE_TXN_WITH_RECEIVER,
        ),
    )
    def test_sign_transaction(self, txn, mock_device, account, capsys, tx_signature):
        actual = account.sign_transaction(txn)
        v, r, s = actual.signature
        assert (v, int(r.hex(), 16), int(s.hex(), 16)) == tx_signature
        output = capsys.readouterr()
        # NOTE: `\t` shows up this way
        assert str(txn).replace("\t", "        ") in output.out
        assert "Please follow the prompts on your device." in output.out
