# camt053 examples

Runnable, self-contained examples for the camt053 library. Run any of them from
the repository root:

```sh
python examples/<name>.py
```

| Example | Demonstrates |
|---------|--------------|
| [`reverse_ac04.py`](reverse_ac04.py) | The headline workflow — read a statement, find the AC04 (Closed Account) entries, and generate a validated reversing entry |
| [`parse_statement.py`](parse_statement.py) | Parsing a camt.053 statement into the typed model (account, balances, entries, return reasons) |
| [`services_facade.py`](services_facade.py) | The shared `camt053.services` facade — message types, return reasons, required fields, identifier validation |
| [`validate_identifiers.py`](validate_identifiers.py) | IBAN / BIC / LEI validation (ISO 13616 / 9362 / 17442) |
| [`rest_api_client.py`](rest_api_client.py) | Driving the FastAPI REST API in-process (parse, entries, reverse) |

Install the package first:

```sh
pip install camt053   # Python 3.10+
```
