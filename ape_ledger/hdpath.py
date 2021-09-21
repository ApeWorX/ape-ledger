import struct


class HDPath:
    def __init__(self, path):
        path = path.rstrip("/")
        if not path.startswith("m/"):
            raise ValueError("Derivation path must begin with m/")

        self.path = path

    def __str__(self):
        return self.path


class HDAccountPath(HDPath):
    def as_bytes(self):
        """
        Convert ``self.path`` to the Ledger bytes format.

        References:
        - https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
        - https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
        """
        elements = self.path.split("/")[1:]
        depth = len(elements)
        num_of_derivations_to_do = bytes([depth])

        for derivation_index in elements:
            is_hardened = "'" in derivation_index
            index = int(derivation_index.strip("'"))

            if is_hardened:
                # See bip32 spec for hardened derivation spec
                index = 0x80000000 | index

            # Append index to result as a big-endian (>) unsigned int (I)
            num_of_derivations_to_do += struct.pack(">I", index)

        return num_of_derivations_to_do


class HDBasePath(HDPath):
    DEFAULT = "m/44'/60'/{x}'/0/0"

    def __init__(self, base_path=DEFAULT):
        base_path = base_path or self.DEFAULT
        base_path = base_path.rstrip("/")
        base_path = base_path if "{x}" in base_path else f"{base_path}/{{x}}"
        super().__init__(base_path)

    def get_account_path(self, account_id) -> HDAccountPath:
        return HDAccountPath(self.path.format(x=str(account_id)))


__all__ = ["HDAccountPath", "HDBasePath"]
