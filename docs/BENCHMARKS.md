<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Benchmarks

`benches/bench_statement_pipeline.py` measures how the cost of a statement
grows with its size: parsing, listing entries buffered against streaming, and
the first XSD validation in a process against later ones. CI runs it with
`--quick` as a smoke test. Nothing asserts a threshold: wall-clock depends on
hardware, Python and dependency versions, and no hardware-independent claim
is made.

```sh
poetry install
python benches/bench_statement_pipeline.py           # full run
python benches/bench_statement_pipeline.py --quick   # what CI runs
python benches/bench_statement_pipeline.py --json
```

## Results, 2026-10-20

Apple A18 Pro (arm64), macOS, Python 3.12.15, xmlschema 4.3.2, lxml 6.1.3,
full run. The machine was shared with other work, and wall-clock figures
moved by up to 4x between three back-to-back runs, so they are given as the
range of those runs. Peak memory was identical in all three.

### `parse_statement`

| Entries | Size | Time | Per entry |
| ---: | ---: | ---: | ---: |
| 50 | 13.8 KiB | 1.5 ms | 30 µs |
| 500 | 132.8 KiB | 17.7 ms | 35 µs |
| 2,000 | 530.8 KiB | 69 to 167 ms | 35 to 84 µs |
| 10,000 | 2,655.8 KiB | 558 to 1,053 ms | 56 to 105 µs |

The single-run rows at 50 and 500 entries are from the first run.

### `list_entries`, buffered against streaming, 10,000 entries

| Mode | Time | Per entry | Peak memory |
| :--- | ---: | ---: | ---: |
| buffered | 389 to 497 ms | 39 to 50 µs | 32,935 KiB |
| streaming | 572 to 2,227 ms | 57 to 223 µs | 22,926 KiB |

Streaming holds peak memory down by about 30% at this size. Its per-entry
time exceeded buffered in all three runs at 10,000 entries, which the
benchmark flags as worth investigating; on this shared machine the spread is
too wide to say whether that is the generator or the load, and it is not
claimed either way.

### `validate_statement`, cold against warm

| Call | Time |
| :--- | ---: |
| First call in a fresh interpreter | 353 to 3,039 ms |
| Second call | 28 to 273 ms |

The XSD compiles once per process and is cached. A service validating one
document per invocation pays the first-call cost every time; a long-lived one
pays it once.
