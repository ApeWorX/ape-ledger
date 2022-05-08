import json
from pathlib import Path
from typing import Optional

import pytest
from ape import networks
from ape.api import TransactionAPI
from ape.api.networks import LOCAL_NETWORK_NAME
from ape_ethereum.ecosystem import DynamicFeeTransaction, StaticFeeTransaction
from eip712.messages import EIP712Message, EIP712Type
from eth_account.messages import SignableMessage

from ape_ledger.accounts import AccountContainer, LedgerAccount
from ape_ledger.exceptions import LedgerSigningError

from .conftest import TEST_ADDRESS, TEST_ALIAS, TEST_HD_PATH, assert_account


class Person(EIP712Type):
    name: "string"  # type: ignore # noqa: F821
    wallet: "address"  # type: ignore # noqa: F821


class Mail(EIP712Message):
    _chainId_: "uint256" = 1  # type: ignore # noqa: F821
    _name_: "string" = "Ether Mail"  # type: ignore # noqa: F821
    _verifyingContract_: "address" = "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC"  # type: ignore # noqa: F821 E501
    _version_: "string" = "1"  # type: ignore # noqa: F821

    sender: Person
    receiver: Person


# noinspection PyArgumentList
TEST_SENDER = Person("Cow", "0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826")  # type: ignore
# noinspection PyArgumentList
TEST_RECEIVER = Person("Bob", "0xB0B0b0b0b0b0B000000000000000000000000000")  # type: ignore
# noinspection PyArgumentList
TEST_TYPED_MESSAGE = Mail(sender=TEST_SENDER, receiver=TEST_RECEIVER)  # type: ignore
TEST_TXN_DATA = b"""`\x80`@R4\x80\x15a\x00\x10W`\x00\x80\xfd[P`\x00\x80T`\x01`\x01`\xa0\x1b\x03\x19\x163\x17\x90U`\x03\x80T`\xff\x19\x16`\x01\x17\x90Ua\x04\xa8\x80a\x00?`\x009`\x00\xf3\xfe`\x80`@R`\x046\x10a\x00pW`\x005`\xe0\x1c\x80c>G\xd6\xf3\x11a\x00NW\x80c>G\xd6\xf3\x14a\x00\xd4W\x80c\x8d\xa5\xcb[\x14a\x01\x19W\x80c\xb6\rB\x88\x14a\x01JW\x80c\xdc\r=\xff\x14a\x01RWa\x00pV[\x80c\x12)\xdc\x9e\x14a\x00uW\x80c#\x8d\xaf\xe0\x14a\x00\xa3W\x80c<\xcf\xd6\x0b\x14a\x00\xccW[`\x00\x80\xfd[4\x80\x15a\x00\x81W`\x00\x80\xfd[Pa\x00\xa1`\x04\x806\x03` \x81\x10\x15a\x00\x98W`\x00\x80\xfd[P5\x15\x15a\x01|V[\x00[4\x80\x15a\x00\xafW`\x00\x80\xfd[Pa\x00\xb8a\x01\xdcV[`@\x80Q\x91\x15\x15\x82RQ\x90\x81\x90\x03` \x01\x90\xf3[a\x00\xa1a\x01\xe5V[4\x80\x15a\x00\xe0W`\x00\x80\xfd[Pa\x01\x07`\x04\x806\x03` \x81\x10\x15a\x00\xf7W`\x00\x80\xfd[P5`\x01`\x01`\xa0\x1b\x03\x16a\x02\xddV[`@\x80Q\x91\x82RQ\x90\x81\x90\x03` \x01\x90\xf3[4\x80\x15a\x01%W`\x00\x80\xfd[Pa\x01.a\x02\xefV[`@\x80Q`\x01`\x01`\xa0\x1b\x03\x90\x92\x16\x82RQ\x90\x81\x90\x03` \x01\x90\xf3[a\x00\xa1a\x02\xfeV[4\x80\x15a\x01^W`\x00\x80\xfd[Pa\x01.`\x04\x806\x03` \x81\x10\x15a\x01uW`\x00\x80\xfd[P5a\x03\xa4V[`\x00T`\x01`\x01`\xa0\x1b\x03\x163\x14a\x01\xc9W`@\x80QbF\x1b\xcd`\xe5\x1b\x81R` `\x04\x82\x01R`\x0b`$\x82\x01Rj\x08X]]\x1a\x1b\xdc\x9a^\x99Y`\xaa\x1b`D\x82\x01R\x90Q\x90\x81\x90\x03`d\x01\x90\xfd[`\x03\x80T`\xff\x19\x16\x91\x15\x15\x91\x90\x91\x17\x90UV[`\x03T`\xff\x16\x81V[`\x00T`\x01`\x01`\xa0\x1b\x03\x163\x14a\x022W`@\x80QbF\x1b\xcd`\xe5\x1b\x81R` `\x04\x82\x01R`\x0b`$\x82\x01Rj\x08X]]\x1a\x1b\xdc\x9a^\x99Y`\xaa\x1b`D\x82\x01R\x90Q\x90\x81\x90\x03`d\x01\x90\xfd[`\x03T`\xff\x16a\x02AW`\x00\x80\xfd[`@Q3\x90G\x80\x15a\x08\xfc\x02\x91`\x00\x81\x81\x81\x85\x88\x88\xf1\x93PPPP\x15\x80\x15a\x02mW=`\x00\x80>=`\x00\xfd[P`\x00[`\x02T\x81\x10\x15a\x02\xbcW`\x00`\x02\x82\x81T\x81\x10a\x02\x8aW\xfe[`\x00\x91\x82R` \x80\x83 \x90\x91\x01T`\x01`\x01`\xa0\x1b\x03\x16\x82R`\x01\x90\x81\x90R`@\x82 \x91\x90\x91U\x91\x90\x91\x01\x90Pa\x02qV[P`@\x80Q`\x00\x81R` \x81\x01\x91\x82\x90RQa\x02\xda\x91`\x02\x91a\x03\xcbV[PV[`\x01` R`\x00\x90\x81R`@\x90 T\x81V[`\x00T`\x01`\x01`\xa0\x1b\x03\x16\x81V[`\x03T`\xff\x16a\x03\rW`\x00\x80\xfd[`\x004\x11a\x03LW`@QbF\x1b\xcd`\xe5\x1b\x81R`\x04\x01\x80\x80` \x01\x82\x81\x03\x82R`#\x81R` \x01\x80a\x04P`#\x919`@\x01\x91PP`@Q\x80\x91\x03\x90\xfd[3`\x00\x81\x81R`\x01` \x81\x90R`@\x82 \x80T4\x01\x90U`\x02\x80T\x91\x82\x01\x81U\x90\x91R\x7f@W\x87\xfa\x12\xa8#\xe0\xf2\xb7c\x1c\xc4\x1b;\xa8\x82\x8b3!\xca\x81\x11\x11\xfau\xcd:\xa3\xbbZ\xce\x01\x80T`\x01`\x01`\xa0\x1b\x03\x19\x16\x90\x91\x17\x90UV[`\x02\x81\x81T\x81\x10a\x03\xb1W\xfe[`\x00\x91\x82R` \x90\x91 \x01T`\x01`\x01`\xa0\x1b\x03\x16\x90P\x81V[\x82\x80T\x82\x82U\x90`\x00R` `\x00 \x90\x81\x01\x92\x82\x15a\x04 W\x91` \x02\x82\x01[\x82\x81\x11\x15a\x04 W\x82Q\x82T`\x01`\x01`\xa0\x1b\x03\x19\x16`\x01`\x01`\xa0\x1b\x03\x90\x91\x16\x17\x82U` \x90\x92\x01\x91`\x01\x90\x91\x01\x90a\x03\xebV[Pa\x04,\x92\x91Pa\x040V[P\x90V[[\x80\x82\x11\x15a\x04,W\x80T`\x01`\x01`\xa0\x1b\x03\x19\x16\x81U`\x01\x01a\x041V\xfeFund amount must be greater than 0.\xa2dipfsX"\x12 \\.\xe1\xb9\xbd\xde\x0b.`io)\xf2\xb6\xf1\xd5\xce\x1d\xd7_\x8b\xfd\xf6\xfbT\x14#\x1a\x12\xcf\xa7\xffdsolcC\x00\x06\x0c\x003"""  # noqa: E501


def _build_transaction(txn: TransactionAPI, receiver: Optional[str] = None) -> TransactionAPI:
    txn.chain_id = 579875
    txn.nonce = 0
    txn.gas_limit = 2
    txn.value = 10000000000
    txn.data = TEST_TXN_DATA

    if receiver:
        txn.receiver = receiver

    # Values not part of RLP
    txn.sender = TEST_SENDER.wallet

    return txn


def _create_static_fee_txn(receiver: Optional[str] = None) -> StaticFeeTransaction:
    txn = StaticFeeTransaction()
    txn = _build_transaction(txn, receiver=receiver)  # type: ignore
    txn.gas_price = 1
    return txn  # type: ignore


def _create_dynamic_fee_txn(receiver: Optional[str] = None) -> DynamicFeeTransaction:
    txn = DynamicFeeTransaction()
    txn = _build_transaction(txn, receiver=receiver)  # type: ignore
    txn.max_fee = 300000000
    txn.max_priority_fee = 10000000
    return txn  # type: ignore


TEST_STATIC_FEE_TXN = _create_static_fee_txn()
TEST_STATIC_FEE_TXN_WITH_RECEIVER = _create_static_fee_txn(receiver=TEST_RECEIVER.wallet)
TEST_DYNAMIC_FEE_TXN = _create_dynamic_fee_txn()
TEST_DYNAMIC_FEE_TXN_WITH_RECEIVER = _create_dynamic_fee_txn(receiver=TEST_RECEIVER.wallet)


def create_account(account_path, hd_path):
    with open(account_path, "w") as account_file:
        account_data = {"address": TEST_ADDRESS, "hdpath": hd_path}
        account_file.writelines(json.dumps(account_data))


@pytest.fixture
def account_connection(mocker, ledger_account):
    patch = mocker.patch("ape_ledger.accounts.connect_to_ethereum_account")
    patch.return_value = ledger_account
    return patch


@pytest.fixture(autouse=True)
def isolated_file_system(runner):
    with runner.isolated_filesystem():
        yield


@pytest.fixture
def account(mock_container):
    create_account("account.json", TEST_HD_PATH)
    with networks.parse_network_choice(f"ethereum:{LOCAL_NETWORK_NAME}:test"):
        yield LedgerAccount(container=mock_container, account_file_path=Path("account.json"))


@pytest.fixture
def sign_txn_spy(mocker):
    spy = mocker.spy(LedgerAccount, "_client")
    spy.sign_transaction.return_value = (0, b"r", b"s")
    return spy


class TestAccountContainer:
    def test_save_account(self, mock_container):
        container = AccountContainer(data_folder=Path("."), account_type=LedgerAccount)
        container.save_account(TEST_ALIAS, TEST_ADDRESS, TEST_HD_PATH)
        assert_account(f"{TEST_ALIAS}.json", expected_hdpath=TEST_HD_PATH)


class TestLedgerAccount:
    def test_address_returns_address_from_file(self, account):
        assert account.address.lower() == TEST_ADDRESS.lower()

    def test_hdpath_returns_address_from_file(self, account):
        assert account.hdpath.path == TEST_HD_PATH

    def test_sign_message_personal(self, mocker, account, account_connection, capsys):
        spy = mocker.spy(LedgerAccount, "_client")
        spy.sign_personal_message.return_value = (0, b"r", b"s")

        message = SignableMessage(
            version=b"E", header=b"thereum Signed Message:\n6", body=b"I\xe2\x99\xa5SF"
        )
        actual_v, actual_r, actual_s = account.sign_message(message)

        assert actual_v == 1
        assert actual_r == b"r"
        assert actual_s == b"s"
        spy.sign_personal_message.assert_called_once_with(message.body)

        output = capsys.readouterr()
        assert str(message) in output.out
        assert "Please follow the prompts on your device." in output.out

    def test_sign_message_typed(self, mocker, account, account_connection, capsys):
        spy = mocker.spy(LedgerAccount, "_client")
        spy.sign_typed_data.return_value = (0, b"r", b"s")

        message = TEST_TYPED_MESSAGE.signable_message
        actual_v, actual_r, actual_s = account.sign_message(message)

        assert actual_v == 1
        assert actual_r == b"r"
        assert actual_s == b"s"
        spy.sign_typed_data.assert_called_once_with(message.header, message.body)

        output = capsys.readouterr()
        assert str(message) in output.out
        assert "Please follow the prompts on your device." in output.out

    def test_sign_message_unsupported(self, account, account_connection, capsys):
        unsupported_version = b"X"
        message = SignableMessage(
            version=unsupported_version,
            header=b"thereum Signed Message:\n6",
            body=b"I\xe2\x99\xa5SF",
        )
        with pytest.raises(LedgerSigningError) as err:
            account.sign_message(message)

        actual = str(err.value)
        expected = f"Unsupported message-signing specification, (version={unsupported_version})."
        assert actual == expected

        # Should NOT print out faulty message
        assert not capsys.readouterr().out

    @pytest.mark.parametrize(
        "txn,expected",
        (
            (
                TEST_STATIC_FEE_TXN,
                "f904fa800102808502540be400b904e7608060405234801561001057600080fd5b50600080546001600160a01b031916331790556003805460ff191660011790556104a88061003f6000396000f3fe6080604052600436106100705760003560e01c80633e47d6f31161004e5780633e47d6f3146100d45780638da5cb5b14610119578063b60d42881461014a578063dc0d3dff1461015257610070565b80631229dc9e14610075578063238dafe0146100a35780633ccfd60b146100cc575b600080fd5b34801561008157600080fd5b506100a16004803603602081101561009857600080fd5b5035151561017c565b005b3480156100af57600080fd5b506100b86101dc565b604080519115158252519081900360200190f35b6100a16101e5565b3480156100e057600080fd5b50610107600480360360208110156100f757600080fd5b50356001600160a01b03166102dd565b60408051918252519081900360200190f35b34801561012557600080fd5b5061012e6102ef565b604080516001600160a01b039092168252519081900360200190f35b6100a16102fe565b34801561015e57600080fd5b5061012e6004803603602081101561017557600080fd5b50356103a4565b6000546001600160a01b031633146101c9576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b6003805460ff1916911515919091179055565b60035460ff1681565b6000546001600160a01b03163314610232576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b60035460ff1661024157600080fd5b60405133904780156108fc02916000818181858888f1935050505015801561026d573d6000803e3d6000fd5b5060005b6002548110156102bc5760006002828154811061028a57fe5b60009182526020808320909101546001600160a01b031682526001908190526040822091909155919091019050610271565b5060408051600081526020810191829052516102da916002916103cb565b50565b60016020526000908152604090205481565b6000546001600160a01b031681565b60035460ff1661030d57600080fd5b6000341161034c5760405162461bcd60e51b81526004018080602001828103825260238152602001806104506023913960400191505060405180910390fd5b33600081815260016020819052604082208054340190556002805491820181559091527f405787fa12a823e0f2b7631cc41b3ba8828b3321ca811111fa75cd3aa3bb5ace0180546001600160a01b0319169091179055565b600281815481106103b157fe5b6000918252602090912001546001600160a01b0316905081565b828054828255906000526020600020908101928215610420579160200282015b8281111561042057825182546001600160a01b0319166001600160a01b039091161782556020909201916001909101906103eb565b5061042c929150610430565b5090565b5b8082111561042c5780546001600160a01b031916815560010161043156fe46756e6420616d6f756e74206d7573742062652067726561746572207468616e20302ea26469706673582212205c2ee1b9bdde0b2e60696f29f2b6f1d5ce1dd75f8bfdf6fb5414231a12cfa7ff64736f6c634300060c00338308d9238080",  # noqa: E501
            ),
            (
                TEST_STATIC_FEE_TXN_WITH_RECEIVER,
                "f9050e80010294b0b0b0b0b0b0b0000000000000000000000000008502540be400b904e7608060405234801561001057600080fd5b50600080546001600160a01b031916331790556003805460ff191660011790556104a88061003f6000396000f3fe6080604052600436106100705760003560e01c80633e47d6f31161004e5780633e47d6f3146100d45780638da5cb5b14610119578063b60d42881461014a578063dc0d3dff1461015257610070565b80631229dc9e14610075578063238dafe0146100a35780633ccfd60b146100cc575b600080fd5b34801561008157600080fd5b506100a16004803603602081101561009857600080fd5b5035151561017c565b005b3480156100af57600080fd5b506100b86101dc565b604080519115158252519081900360200190f35b6100a16101e5565b3480156100e057600080fd5b50610107600480360360208110156100f757600080fd5b50356001600160a01b03166102dd565b60408051918252519081900360200190f35b34801561012557600080fd5b5061012e6102ef565b604080516001600160a01b039092168252519081900360200190f35b6100a16102fe565b34801561015e57600080fd5b5061012e6004803603602081101561017557600080fd5b50356103a4565b6000546001600160a01b031633146101c9576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b6003805460ff1916911515919091179055565b60035460ff1681565b6000546001600160a01b03163314610232576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b60035460ff1661024157600080fd5b60405133904780156108fc02916000818181858888f1935050505015801561026d573d6000803e3d6000fd5b5060005b6002548110156102bc5760006002828154811061028a57fe5b60009182526020808320909101546001600160a01b031682526001908190526040822091909155919091019050610271565b5060408051600081526020810191829052516102da916002916103cb565b50565b60016020526000908152604090205481565b6000546001600160a01b031681565b60035460ff1661030d57600080fd5b6000341161034c5760405162461bcd60e51b81526004018080602001828103825260238152602001806104506023913960400191505060405180910390fd5b33600081815260016020819052604082208054340190556002805491820181559091527f405787fa12a823e0f2b7631cc41b3ba8828b3321ca811111fa75cd3aa3bb5ace0180546001600160a01b0319169091179055565b600281815481106103b157fe5b6000918252602090912001546001600160a01b0316905081565b828054828255906000526020600020908101928215610420579160200282015b8281111561042057825182546001600160a01b0319166001600160a01b039091161782556020909201916001909101906103eb565b5061042c929150610430565b5090565b5b8082111561042c5780546001600160a01b031916815560010161043156fe46756e6420616d6f756e74206d7573742062652067726561746572207468616e20302ea26469706673582212205c2ee1b9bdde0b2e60696f29f2b6f1d5ce1dd75f8bfdf6fb5414231a12cfa7ff64736f6c634300060c00338308d9238080",  # noqa: E501
            ),
            (
                TEST_DYNAMIC_FEE_TXN,
                "02f905018308d92380839896808411e1a30002808502540be400b904e7608060405234801561001057600080fd5b50600080546001600160a01b031916331790556003805460ff191660011790556104a88061003f6000396000f3fe6080604052600436106100705760003560e01c80633e47d6f31161004e5780633e47d6f3146100d45780638da5cb5b14610119578063b60d42881461014a578063dc0d3dff1461015257610070565b80631229dc9e14610075578063238dafe0146100a35780633ccfd60b146100cc575b600080fd5b34801561008157600080fd5b506100a16004803603602081101561009857600080fd5b5035151561017c565b005b3480156100af57600080fd5b506100b86101dc565b604080519115158252519081900360200190f35b6100a16101e5565b3480156100e057600080fd5b50610107600480360360208110156100f757600080fd5b50356001600160a01b03166102dd565b60408051918252519081900360200190f35b34801561012557600080fd5b5061012e6102ef565b604080516001600160a01b039092168252519081900360200190f35b6100a16102fe565b34801561015e57600080fd5b5061012e6004803603602081101561017557600080fd5b50356103a4565b6000546001600160a01b031633146101c9576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b6003805460ff1916911515919091179055565b60035460ff1681565b6000546001600160a01b03163314610232576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b60035460ff1661024157600080fd5b60405133904780156108fc02916000818181858888f1935050505015801561026d573d6000803e3d6000fd5b5060005b6002548110156102bc5760006002828154811061028a57fe5b60009182526020808320909101546001600160a01b031682526001908190526040822091909155919091019050610271565b5060408051600081526020810191829052516102da916002916103cb565b50565b60016020526000908152604090205481565b6000546001600160a01b031681565b60035460ff1661030d57600080fd5b6000341161034c5760405162461bcd60e51b81526004018080602001828103825260238152602001806104506023913960400191505060405180910390fd5b33600081815260016020819052604082208054340190556002805491820181559091527f405787fa12a823e0f2b7631cc41b3ba8828b3321ca811111fa75cd3aa3bb5ace0180546001600160a01b0319169091179055565b600281815481106103b157fe5b6000918252602090912001546001600160a01b0316905081565b828054828255906000526020600020908101928215610420579160200282015b8281111561042057825182546001600160a01b0319166001600160a01b039091161782556020909201916001909101906103eb565b5061042c929150610430565b5090565b5b8082111561042c5780546001600160a01b031916815560010161043156fe46756e6420616d6f756e74206d7573742062652067726561746572207468616e20302ea26469706673582212205c2ee1b9bdde0b2e60696f29f2b6f1d5ce1dd75f8bfdf6fb5414231a12cfa7ff64736f6c634300060c0033c0",  # noqa: E501
            ),
            (
                TEST_DYNAMIC_FEE_TXN_WITH_RECEIVER,
                "02f905158308d92380839896808411e1a3000294b0b0b0b0b0b0b0000000000000000000000000008502540be400b904e7608060405234801561001057600080fd5b50600080546001600160a01b031916331790556003805460ff191660011790556104a88061003f6000396000f3fe6080604052600436106100705760003560e01c80633e47d6f31161004e5780633e47d6f3146100d45780638da5cb5b14610119578063b60d42881461014a578063dc0d3dff1461015257610070565b80631229dc9e14610075578063238dafe0146100a35780633ccfd60b146100cc575b600080fd5b34801561008157600080fd5b506100a16004803603602081101561009857600080fd5b5035151561017c565b005b3480156100af57600080fd5b506100b86101dc565b604080519115158252519081900360200190f35b6100a16101e5565b3480156100e057600080fd5b50610107600480360360208110156100f757600080fd5b50356001600160a01b03166102dd565b60408051918252519081900360200190f35b34801561012557600080fd5b5061012e6102ef565b604080516001600160a01b039092168252519081900360200190f35b6100a16102fe565b34801561015e57600080fd5b5061012e6004803603602081101561017557600080fd5b50356103a4565b6000546001600160a01b031633146101c9576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b6003805460ff1916911515919091179055565b60035460ff1681565b6000546001600160a01b03163314610232576040805162461bcd60e51b815260206004820152600b60248201526a08585d5d1a1bdc9a5e995960aa1b604482015290519081900360640190fd5b60035460ff1661024157600080fd5b60405133904780156108fc02916000818181858888f1935050505015801561026d573d6000803e3d6000fd5b5060005b6002548110156102bc5760006002828154811061028a57fe5b60009182526020808320909101546001600160a01b031682526001908190526040822091909155919091019050610271565b5060408051600081526020810191829052516102da916002916103cb565b50565b60016020526000908152604090205481565b6000546001600160a01b031681565b60035460ff1661030d57600080fd5b6000341161034c5760405162461bcd60e51b81526004018080602001828103825260238152602001806104506023913960400191505060405180910390fd5b33600081815260016020819052604082208054340190556002805491820181559091527f405787fa12a823e0f2b7631cc41b3ba8828b3321ca811111fa75cd3aa3bb5ace0180546001600160a01b0319169091179055565b600281815481106103b157fe5b6000918252602090912001546001600160a01b0316905081565b828054828255906000526020600020908101928215610420579160200282015b8281111561042057825182546001600160a01b0319166001600160a01b039091161782556020909201916001909101906103eb565b5061042c929150610430565b5090565b5b8082111561042c5780546001600160a01b031916815560010161043156fe46756e6420616d6f756e74206d7573742062652067726561746572207468616e20302ea26469706673582212205c2ee1b9bdde0b2e60696f29f2b6f1d5ce1dd75f8bfdf6fb5414231a12cfa7ff64736f6c634300060c0033c0",  # noqa: E501
            ),
        ),
    )
    def test_sign_transaction(
        self, txn, expected, sign_txn_spy, account, account_connection, capsys
    ):
        account.sign_transaction(txn)
        actual = sign_txn_spy.sign_transaction.call_args[0][0].hex()
        assert actual == expected

        output = capsys.readouterr()
        assert str(txn) in output.out
        assert "Please follow the prompts on your device." in output.out
