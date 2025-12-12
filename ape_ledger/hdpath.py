import struct


class HDPath:
    """
    A class representing an HD path. This class is the base class
    for both account specific HD paths (:class:`~ape_ledger.hdpath.HDAccountPath`)
    as well as the derivation HD path class :class:`~ape_ledger.hdpath.HDBasePath`.
    """

    def __init__(self, path: "HDBasePath | str"):
        if not isinstance(path, str) and hasattr(path, "path"):
            # NOTE: Using getattr for mypy
            path_str = getattr(path, "path")
        else:
            path_str = path

        path_str = path_str.rstrip("/")
        if not path_str.startswith("m/"):
            raise ValueError("HD path must begin with m/")

        self.path = path_str

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
        elements = self.path.split("/")[1:]
        depth = len(elements)

        # Number of BIP 32 derivations to perform (max 10)
        result = bytes([depth])

        for derivation_index in elements:
            # For each derivation index in the path check if it is hardened
            hardened = "'" in derivation_index
            index = int(derivation_index.strip("'"))

            if hardened:
                # See bip32 spec for hardened derivation spec
                index = 0x80000000 | index

            # Append index to result as a big-endian (>) unsigned int (I)
            result += struct.pack(">I", index)

        return result


class HDBasePath(HDPath):
    """
    A derivation HD path useful for creating objects of type
    :class:`~ape_ledger.hdpath.HDAccountPath`.
    """

    def __init__(self, base_path: "HDBasePath | str | None" = None):
        base_path = base_path or "m/44'/60'/{x}'/0/0"
        if not isinstance(base_path, str) and hasattr(base_path, "path"):
            base_path_str = base_path.path
        else:
            base_path_str = base_path

        base_path_str = base_path_str.rstrip("/")
        base_path_str = base_path_str if "{x}" in base_path_str else f"{base_path_str}/{{x}}"
        super().__init__(base_path_str)

    def get_account_path(self, account_id) -> HDAccountPath:
        return HDAccountPath(self.path.format(x=str(account_id)))


__all__ = ["HDAccountPath", "HDBasePath"]
