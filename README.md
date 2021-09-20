# ape-ledger

Ape Ledger is a plugin for Ape Framework which integrates with Ledger devices 
to load and create accounts, sign messages, and sign transactions.

## Dependencies

* [python3](https://www.python.org/downloads) version 3.7 or greater, python3-dev
* hidapi

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

You must have the ledge USB device connected, have it unlocked by entering the passcode, and open the Ethereum app.

## Development

This project is in early development and should be considered an alpha.
Things might not work, breaking changes are likely.
Comments, questions, criticisms and pull requests are welcomed.

## License

This project is licensed under the [Apache 2.0](LICENSE).
