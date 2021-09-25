import struct


class HDPath:
    """
    A class representing an HD path. This class is the base class
    for both account specific HD paths (:class:`~ape_ledger.hdpath.HDAccountPath`)
    as well as the derivation HD path class :class:`~ape_ledger.hdpath.HDBasePath`.
    """

    def __init__(self, path: str):
        path = path.rstrip("/")
        if not path.startswith("m/"):
            raise ValueError("HD path must begin with m/")

        self.path = path

    def __str__(self):
        return self.path


class HDAccountPath(HDPath):
    """
    An HD path where the account node is set.
    """

    def as_bytes(self):
        """
        Convert ``self.path`` to the Ledger bytes format.

        Ledger expect the following bytes input:
          1. Number of BIP 32 derivations to perform (max 10)
          2. First derivation index (big endian)
          3. Second derivation index (big endian)

        References:
        - https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
        - https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
        """
        if len(self.path) == 0:
            return b""

        result = b""
        elements = self.path.split("/")[1:]

        for path_element in elements:
            element = path_element.split("'")
            if len(element) == 1:
                result = result + struct.pack(">I", int(element[0]))
            else:
                result = result + struct.pack(">I", 0x80000000 | int(element[0]))

        return result


class HDBasePath(HDPath):
    """
    A derivation HD path useful for creating objects of type
    :class:`~ape_ledger.hdpath.HDAccountPath`.
    """

    DEFAULT = "m/44'/60'/{x}'/0/0"

    def __init__(self, base_path=DEFAULT):
        base_path = base_path or self.DEFAULT
        base_path = base_path.rstrip("/")
        base_path = base_path if "{x}" in base_path else f"{base_path}/{{x}}"
        super().__init__(base_path)

    def get_account_path(self, account_id) -> HDAccountPath:
        return HDAccountPath(self.path.format(x=str(account_id)))


__all__ = ["HDAccountPath", "HDBasePath"]
