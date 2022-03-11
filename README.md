# ape-ledger

Ape Ledger is a plugin for Ape Framework which integrates with Ledger devices 
to load and create accounts, sign messages, and sign transactions.

## Dependencies

* [python3](https://www.python.org/downloads) version 3.7 or greater, python3-dev

## Installation

### via `pip`

You can install the latest release via [`pip`](https://pypi.org/project/pip/):

```bash
pip install ape-ledger
```

### via `setuptools`

You can clone the repository and use [`setuptools`](https://github.com/pypa/setuptools) for the most up-to-date version:

```bash
git clone https://github.com/ApeWorX/ape-ledger.git
cd ape-ledger
python3 setup.py install
```

## Quick Usage

You must:

* have the Ledger USB device connected
* have the Ledger USB device unlocked (by entering the passcode)
* and have the Ethereum app open.

Then, add accounts:

```bash
ape ledger add <alias>
```

Ledger accounts have the following capabilities in `ape`:

1. Can sign transactions
2. Can sign messages using the default EIP-191 specification
3. Can sign messages using the EIP-712 specification

### Adjust HD Path

If you need to adjust your HD path, use the `--hd-path` flag when adding the account.

```bash
ape ledger add <alias> --hd-path "m/44'/60'/0'/0/{x}"
```

`{x}` indicates the account node. Note that excluding `{x}` assumes the account node is at the end
of the path.

The default HD path for the Ledger plugin is `m/44'/60'/{x}'/0/0`.
See https://github.com/MyCryptoHQ/MyCrypto/issues/2070 for more information.

## List accounts

To list just your Ledger accounts in `ape`, do:

```bash
ape ledger list
```

## Remove accounts

You can also remove accounts:

```bash
ape ledger delete <alias>
```

## Development

Please see the [contributing guide](CONTRIBUTING.md) to learn more how to contribute to this project.
Comments, questions, criticisms and pull requests are welcomed.

## License

This project is licensed under the [Apache 2.0](LICENSE).
