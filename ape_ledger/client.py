"""
Implementation inspired from
https://github.com/vegaswap/ledgertools/blob/master/ledger_usb.py
"""
import struct
import time
from typing import List, Optional, Tuple

import hid  # type: ignore
from eth_typing.evm import ChecksumAddress
from eth_utils import to_checksum_address

from ape_ledger.exceptions import LedgerTimeoutError, LedgerUsbError
from ape_ledger.hdpath import HDAccountPath, HDBasePath

_CHANNEL_ID = 0x0101


class _CmdTag:
    APDU = 0x05
    PING = 0x02


class _PacketData:
    # Packet HEADER is defined at
    # 1. Communication channel ID (big endian) value is always CHANNEL_ID
    # 2. Command tag (TAG_APDU or TAG_PING)
    # 3. Packet sequence index (big endian) starting at 0x00

    HEADER = struct.pack(">HBH", _CHANNEL_ID, _CmdTag.APDU, 0x00)
    SIZE = 64  # in bytes
    FREE = SIZE - len(HEADER)


class APDUStatus:
    """Device-returned status words.

    Source:
        https://github.com/LedgerHQ/app-ethereum/blob/master/doc/ethapp.asc#status-words
    """

    TX_TYPE_UNSUPPORTED = 0x6501
    OUTPUT_BUFFER_TOO_SMALL = 0x6502
    PLUGIN_ERROR = 0x6503
    INT_CONVERSION_ERROR = 0x6504
    INCORRECT_LENGTH = 0x6700
    CANCELED_BY_USER = 0x6982
    DECLINED = 0x6985
    INVALID_DATA = 0x6A80
    INCORRECT_PARAMETER = 0x6A80
    APP_SLEEP = 0x6804
    APP_NOT_STARTED = 0x6D00
    DEVICE_LOCKED = 0x6B0C
    OK = 0x9000

    @classmethod
    def to_status_message(cls, status: int) -> str:
        """
        Convert a byte word to the English equivalent.
        """

        internal_error = "Internal error"
        if 0x6F00 <= status <= 0x6FFF:
            return internal_error

        mapping = {
            cls.TX_TYPE_UNSUPPORTED: "TransactionType not supported",
            cls.OUTPUT_BUFFER_TOO_SMALL: "Output buffer too small for chainId conversion",
            cls.PLUGIN_ERROR: "Plugin error",
            cls.INT_CONVERSION_ERROR: "Failed to convert from int256",
            cls.INCORRECT_LENGTH: "Incorrect length",
            cls.CANCELED_BY_USER: "Security status not satisfied. Canceled by user.",
            cls.DECLINED: "User declined on device",
            cls.INVALID_DATA: "Invalid data",
            cls.INCORRECT_PARAMETER: "Incorrect parameter P1 or P2",
            cls.APP_SLEEP: "Ethereum app not ready on device",
            cls.APP_NOT_STARTED: "Ethereum app not started on device",
            cls.DEVICE_LOCKED: "The device is locked",
            cls.OK: "OK",
        }

        return mapping.get(status, internal_error)


class _Code:
    """Device command codes."""

    CLA = 0xE0
    INS_GET_PUBLIC_KEY = 0x02
    INS_SIGN_TX = 0x04
    INS_GET_APP_CONFIGURATION = 0x06
    INS_SIGN_PERSONAL_MESSAGE = 0x08
    INS_SIGN_EIP_712 = 0x0C
    P1_CONFIRM = 0x01
    P1_NON_CONFIRM = 0x00
    P2_NO_CHAINCODE = 0x00
    P2_CHAINCODE = 0x01
    P1_FIRST = 0x00
    P1_MORE = 0x80


_LEDGER_VENDOR_ID = 0x2C97
_LEDGER_USAGE_PAGE_ID = 0xFFA0


class APDUBuilder:
    def __init__(self, ins: int, p1: int = _Code.P1_FIRST, p2: int = _Code.P2_NO_CHAINCODE):
        self.apdu = struct.pack(">BBBB", _Code.CLA, ins, p1, p2)

    def append(self, path: bytes, payload: bytes):
        length = len(payload) + len(path)
        self.apdu += struct.pack(">B", length)
        self.apdu += path + payload


def _wrap_apdu(command: bytes) -> List[bytes]:
    """Return a list of packet to be sent to the device"""

    packets = []
    header = struct.pack(">H", len(command))
    command = header + command
    chunks = [command[i : i + _PacketData.FREE] for i in range(0, len(command), _PacketData.FREE)]

    # Create a packet for each command chunk
    for packet_id in range(len(chunks)):
        header = struct.pack(">HBH", _CHANNEL_ID, _CmdTag.APDU, packet_id)
        packet = header + chunks[packet_id]
        packet.ljust(_PacketData.SIZE, bytes([0x0]))
        packets.append(packet)

    return packets


def _unwrap_apdu(
    packet: bytes,
) -> Tuple[Optional[int], Optional[bytes], Optional[int], Optional[int], Optional[bytes]]:
    """
    Given a packet from the device, extract and return relevant info
    """
    if not packet:
        return None, None, None, None, None

    (channel, tag, packet_id, reply_size) = struct.unpack(">HBHH", packet[:7])

    if packet_id == 0:
        return channel, tag, packet_id, reply_size, packet[7:]

    return channel, tag, packet_id, None, packet[5:]


def _get_hid_device_path() -> Optional[str]:
    hid_info = {}
    for hid_info in hid.enumerate(0, 0):
        if hid_info.get("vendor_id") != _LEDGER_VENDOR_ID:
            continue

        interface_number = hid_info.get("interface_number")
        usage_page = hid_info.get("usage_page")
        if interface_number == 0 or usage_page == _LEDGER_USAGE_PAGE_ID:
            # Found
            break

    return hid_info.get("path")


def _get_device(hid_path: str) -> hid.device:
    device = hid.device()

    try:
        device.open_path(hid_path)
    except OSError as err:
        message = (
            "Unable to open HID path. "
            "Make sure you have your device unlocked via the passcode "
            "and have the Ethereum app open."
        )
        raise LedgerUsbError(message) from err

    device.set_nonblocking(True)
    return device


def _handle_reply_status(reply: bytes):
    (status,) = struct.unpack(">H", reply[-2:])

    if status == APDUStatus.OK:
        return reply[:-2]

    message = APDUStatus.to_status_message(status)
    raise LedgerUsbError(message, status=status)


def _verify_channel_and_tag(channel: Optional[int], tag: Optional[bytes]):
    if channel != _CHANNEL_ID:
        raise LedgerUsbError(f"Invalid channel '{channel}'. Expecting '{_CHANNEL_ID}'.")
    elif tag != _CmdTag.APDU:
        raise LedgerUsbError(f"Invalid tag '{tag!r}'. Expecting '{_CmdTag.APDU!r}'.")


class LedgerUsbDeviceClient:
    """
    This class is a APDU client for the Ledger device.
    It abstracts away communication with the device via it's
    :meth:`~ape_ledger.ledger.LedgerUsbDevice.exchange()` method.

    References:
    - https://github.com/ethereum/go-ethereum/blob/master/accounts/usbwallet/ledger.go
    """

    _exchange_timeout = 60

    def __init__(self, hid_device):
        self._device = hid_device

    def exchange(self, apdu: bytes) -> bytes:
        packets = _wrap_apdu(apdu)
        for packet in packets:
            self._device.write(packet)

        reply = self._receive_reply()
        return _handle_reply_status(reply)

    def _receive_reply(self) -> bytes:
        """
        Receive reply, size of reply is contained in first packet.
        """
        reply: bytes = b""
        reply_min_size = 2
        reply_start = time.time()
        while True:
            packet = bytes(self._device.read(64))
            (channel, tag, index, size, data) = _unwrap_apdu(packet)

            channel = self._wait_for_channel(channel, reply_start)
            if not channel:
                continue

            _verify_channel_and_tag(channel, tag)

            # Size is not None only on first reply
            reply_min_size = size or reply_min_size
            if data:
                reply += data

            # Check if we have received all the reply from device
            if len(reply) > reply_min_size:
                reply = bytes(reply[:reply_min_size])
                break

        return reply

    def _wait_for_channel(self, channel, reply_start):
        if channel:
            return channel

        if reply_start + self._exchange_timeout < time.time():
            raise LedgerTimeoutError(self._exchange_timeout)

        time.sleep(0.01)


def _to_vrs(reply: bytes) -> Tuple[int, bytes, bytes]:
    """
    Breaks a byte message into 3 chunks vrs,
    where `v` is 1 byte, `r` is 32 bytes, and `s` is 32 bytes.
    """
    if not reply:
        raise LedgerUsbError("No data in reply.")

    v = reply[0]  # 1 byte
    r = reply[1:33]  # 32 bytes
    s = reply[33:65]  # 32 bytes
    return v, r, s


class LedgerEthereumAccountClient:
    """
    This class represents an account on the Ledger device when you know the full
    account HD path.
    """

    def __init__(
        self,
        client: LedgerUsbDeviceClient,
        address: ChecksumAddress,
        account_hd_path: HDAccountPath,
    ):
        self._client = client
        self._address = address
        self._account_hd_path = account_hd_path
        self._path_bytes = b""  # cached calculation

    def __str__(self):
        return self._address

    @property
    def address(self) -> str:
        return self._address

    @property
    def path_bytes(self) -> bytes:
        if self._path_bytes == b"":
            self._path_bytes = self._account_hd_path.as_bytes()

        return self._path_bytes

    def sign_personal_message(self, message_bytes: bytes) -> Tuple[int, bytes, bytes]:
        """
        Sign an Ethereum message only following the EIP 191 specification and using
        your Ledger device. You will need to follow the prompts on the device
        to validate the message data.

        APDU breakdown:
          Number of BIP 32 derivations to perform (max 10) - 1 byte
          First derivation index (big endian)              - 4 bytes
          ...                                              - 4 bytes
          Last derivation index (big endian)               - 4 bytes
          Message length                                   - 4 bytes
          Message chunk                                    - variable
        """

        encoded_message = struct.pack(">I", len(message_bytes))
        encoded_message += message_bytes
        builder = APDUBuilder(_Code.INS_SIGN_PERSONAL_MESSAGE)
        builder.append(self.path_bytes, encoded_message)
        reply = self._client.exchange(builder.apdu)
        return _to_vrs(reply)

    def sign_typed_data(self, domain_hash: bytes, message_hash: bytes) -> Tuple[int, bytes, bytes]:
        """
        Sign an Ethereum message following the EIP 712 specification.

        APDU breakdown:
          Number of BIP 32 derivations to perform (max 10) - 1 byte
          First derivation index (big endian)              - 4 bytes
          ...                                              - 4 bytes
          Last derivation index (big endian)               - 4 bytes
          domain hash                                      - 32 bytes
          message hash                                     - 32 bytes
        """

        encoded_message = domain_hash + message_hash
        builder = APDUBuilder(_Code.INS_SIGN_EIP_712)
        builder.append(self.path_bytes, encoded_message)
        reply = self._client.exchange(builder.apdu)
        return _to_vrs(reply)

    def sign_transaction(self, txn: bytes) -> Tuple[int, bytes, bytes]:
        """
        Sign a transaction using your Ledger device. You will need to follow
        the prompts on the device to validate the transaction data.

        APDU breakdown:
          Number of BIP 32 derivations to perform (max 10) - 1 byte
          First derivation index (big endian)              - 4 bytes
          ...                                              - 4 bytes
          Last derivation index (big endian)               - 4 bytes
          RLP transaction chunk                            - arbitrary
        """

        payload = self.path_bytes + txn
        chunks = [payload[i : i + 255] for i in range(0, len(payload), 255)]  # noqa: E203
        apdu_param1 = _Code.P1_FIRST
        reply = None

        for chunk in chunks:
            builder = APDUBuilder(_Code.INS_SIGN_TX, p1=apdu_param1)
            builder.append(b"", chunk)
            reply = self._client.exchange(builder.apdu)
            apdu_param1 = _Code.P1_MORE

        if not reply:
            raise LedgerUsbError("Signing transaction failed - received 0 bytes in reply.")

        return _to_vrs(reply)


class LedgerEthereumAppClient:
    """
    This class is able to get accounts from your Ethereum wallet.
    """

    def __init__(self, client: LedgerUsbDeviceClient, hd_path: HDBasePath):
        self._client = client
        self.hd_root_path = hd_path

    def load_account(self, account_id: int) -> LedgerEthereumAccountClient:
        path_bytes = self.hd_root_path.get_account_path(account_id).as_bytes()
        builder = APDUBuilder(_Code.INS_GET_PUBLIC_KEY, p1=_Code.P1_NON_CONFIRM)
        builder.append(path_bytes, b"")
        account_data = self._client.exchange(builder.apdu)
        offset = 1 + account_data[0]
        address = account_data[offset + 1 : offset + 1 + account_data[offset]]
        address_checksum = to_checksum_address(address.decode())
        return LedgerEthereumAccountClient(self._client, address_checksum, path_bytes)


def connect_to_ethereum_account(
    address: ChecksumAddress, hd_account_path: HDAccountPath
) -> LedgerEthereumAccountClient:
    """
    Create an account client using an active device connection.
    """

    return LedgerEthereumAccountClient(device_manager.device, address, hd_account_path)


def connect_to_ethereum_app(hd_path: HDBasePath) -> LedgerEthereumAppClient:
    """
    Create a client that is able to create account clients,
    using an active device connection.
    """

    return LedgerEthereumAppClient(device_manager.device, hd_path)


class DeviceManager:
    _device: Optional[LedgerUsbDeviceClient] = None
    _client_cls = LedgerUsbDeviceClient

    @property
    def device(self) -> LedgerUsbDeviceClient:
        """
        Create a Ledger device client and connect to it.
        """

        if self._device:
            return self._device

        hid_path = _get_hid_device_path()
        if hid_path is None:
            raise LedgerUsbError("No Ledger USB device found.")

        device = _get_device(hid_path)
        self._device = self._client_cls(device)
        return self._device


device_manager = DeviceManager()


__all__ = [
    "connect_to_ethereum_account",
    "connect_to_ethereum_app",
    "device_manager",
    "LedgerEthereumAccountClient",
    "LedgerEthereumAppClient",
    "LedgerUsbDeviceClient",
]
