from typing import Optional, Union

from eth_typing import HexStr
from eth_utils import add_0x_prefix, decode_hex
from rlp import Serializable  # type: ignore
from rlp.sedes import BigEndianInt, Binary, CountableList  # type: ignore
from rlp.sedes import List as ListSedes  # type: ignore
from rlp.sedes import big_endian_int, binary  # type: ignore

"""Inspired from https://github.com/mikeshultz/ledger-eth-lib"""


def _encode_hex(receiver: Optional[Union[str, bytes]] = None) -> bytes:
    if receiver is None:
        return b""

    if isinstance(receiver, str):
        add_0x_prefix(HexStr(receiver))
        # Note: We are encoding to bytes, nevermind the name of this method 'decode_hex'.
        return decode_hex(receiver)

    return receiver


# Define typed transaction common sedes.
# [[{20 bytes}, [{32 bytes}...]]...], where ... means “zero or more of the thing to the left”.
access_list_sede_type = CountableList(
    ListSedes(
        [
            Binary.fixed_length(20, allow_empty=False),
            CountableList(BigEndianInt(32)),
        ]
    ),
)


class StaticFeeTransaction(Serializable):
    fields = [
        ("nonce", big_endian_int),
        ("gas_sprice", big_endian_int),
        ("gas_limit", big_endian_int),
        ("receiver", Binary.fixed_length(20, allow_empty=True)),
        ("value", big_endian_int),
        ("data", binary),
        ("chain_id", big_endian_int),
        # Expected nine elements as part of EIP-155 transactions
        ("ignored_1", big_endian_int),
        ("ignored_2", big_endian_int),
    ]

    def __init__(
        self,
        nonce: int,
        gasPrice: int,
        gas: int,
        value: int,
        data: bytes,
        chainId: int,
        to: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            nonce,
            gasPrice,
            gas,
            _encode_hex(to),
            value,
            data,
            chainId,
            0,
            0,
        )


class DynamicFeeTransaction(Serializable):
    fields = [
        ("chain_id", big_endian_int),
        ("nonce", big_endian_int),
        ("max_priority_fee", big_endian_int),
        ("max_fee", big_endian_int),
        ("gas_limit", big_endian_int),
        ("receiver", Binary.fixed_length(20, allow_empty=True)),
        ("value", big_endian_int),
        ("data", binary),
        ("access_list", access_list_sede_type),
    ]

    def __init__(
        self,
        nonce: int,
        maxFeePerGas: int,
        maxPriorityFeePerGas: int,
        gas: int,
        value: int,
        data: bytes,
        chainId: int,
        to: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            chainId,
            nonce,
            maxPriorityFeePerGas,
            maxFeePerGas,
            gas,
            _encode_hex(to),
            value,
            data,
            [],
        )
