# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line interface for Camt053.

Reads incoming ISO 20022 cash-management statements and generates reversing
entries. Every command is a thin wrapper over :mod:`camt053.services`, so the
CLI behaves identically to the REST API, MCP server, and LSP server.
"""

import sys

import click
from rich import box
from rich.console import Console
from rich.table import Table

from camt053 import services
from camt053.constants import VERSION
from camt053.exceptions import Camt053Error

console = Console()


def _read_input(input_file: str) -> str:
    """Read statement XML from a file path or ``-`` for stdin."""
    if input_file == "-":
        return sys.stdin.read()
    with open(input_file, encoding="utf-8") as handle:
        return handle.read()


@click.group(
    help=(
        "Read ISO 20022 camt Bank-to-Customer Statements (camt.053) and "
        "Reports (camt.052 / camt.054), extract entries by return reason "
        "code, and generate validated reversing entries.\n\n"
        "EXAMPLES:\n\n"
        "  Generate a reversing entry for every AC04 (Closed Account) entry:\n"
        "    camt053 reverse -i statement.xml -r AC04 -o reversal.xml\n\n"
        "  List the entries on a statement:\n"
        "    camt053 entries -i statement.xml\n\n"
        "  Inspect the parsed statement as JSON:\n"
        "    camt053 parse -i statement.xml\n"
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(VERSION, "-V", "--version", prog_name="Camt053")
def main() -> None:
    """Camt053 command group."""


@main.command("message-types")
def message_types() -> None:
    """List the supported cash-management message types."""
    table = Table(box=box.SIMPLE, title="Supported message types")
    table.add_column("Message type", style="cyan")
    table.add_column("Name")
    for row in services.list_message_types():
        table.add_row(row["message_type"], row["name"])
    console.print(table)


@main.command("reasons")
def reasons() -> None:
    """List the known ISO external return reason codes."""
    table = Table(box=box.SIMPLE, title="Return reason codes")
    table.add_column("Code", style="cyan")
    table.add_column("Name")
    for row in services.list_return_reasons():
        table.add_row(row["code"], row["name"])
    console.print(table)


@main.command("parse")
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    help="Path to the statement XML file ('-' for stdin).",
)
def parse(input_file: str) -> None:
    """Parse a statement and print it as JSON."""
    import json

    try:
        document = services.parse_statement(_read_input(input_file))
    except (OSError, Camt053Error) as exc:
        console.print(f"[bold red]✗ Parse failed:[/bold red] {exc}")
        sys.exit(1)
    console.print_json(json.dumps(document))


@main.command("validate")
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    help="Path to the statement XML file ('-' for stdin).",
)
def validate(input_file: str) -> None:
    """Validate a statement against its official ISO camt XSD."""
    try:
        report = services.validate_statement(_read_input(input_file))
    except (OSError, Camt053Error) as exc:
        console.print(f"[bold red]✗ Validation failed:[/bold red] {exc}")
        sys.exit(1)

    message_type = report["message_type"]
    if report["valid"]:
        console.print(f"[bold green]✓ Valid {message_type}[/bold green]")
        return

    console.print(
        f"[bold red]✗ Invalid {message_type}[/bold red] "
        f"({len(report['errors'])} error(s))"
    )
    for error in report["errors"]:
        console.print(f"  [red]•[/red] {error}")
    sys.exit(1)


@main.command("entries")
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    help="Path to the statement XML file ('-' for stdin).",
)
@click.option(
    "-r",
    "--reason",
    "reason_code",
    default=None,
    help="Only show entries carrying this return reason code (e.g. AC04).",
)
def entries(input_file: str, reason_code: str | None) -> None:
    """List the entries on a statement (optionally filtered by reason)."""
    try:
        xml = _read_input(input_file)
        rows = (
            services.filter_entries(xml, reason_code)
            if reason_code
            else services.list_entries(xml)
        )
    except (OSError, Camt053Error) as exc:
        console.print(f"[bold red]✗ Failed:[/bold red] {exc}")
        sys.exit(1)

    table = Table(box=box.SIMPLE, title="Statement entries")
    table.add_column("Reference", style="cyan")
    table.add_column("Amount", justify="right")
    table.add_column("Ccy")
    table.add_column("Cr/Dr")
    table.add_column("Reason")
    for entry in rows:
        table.add_row(
            entry.get("reference") or "",
            entry.get("amount") or "",
            entry.get("currency") or "",
            entry.get("credit_debit_indicator") or "",
            entry.get("reason_code") or "",
        )
    console.print(table)
    console.print(f"[cyan]{len(rows)} entr{'y' if len(rows) == 1 else 'ies'}.")


@main.command("reverse")
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    help="Path to the incoming statement XML file ('-' for stdin).",
)
@click.option(
    "-r",
    "--reason",
    "reason_code",
    default="AC04",
    show_default=True,
    help="Return reason code whose entries are reversed.",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    default=None,
    help="Write the reversing entry here (default: stdout).",
)
def reverse(
    input_file: str, reason_code: str, output_file: str | None
) -> None:
    """Generate a reversing entry for matching statement entries."""
    try:
        xml = _read_input(input_file)
        reversal = services.generate_reversal(xml, reason_code)
    except (OSError, Camt053Error) as exc:
        console.print(f"[bold red]✗ Reversal failed:[/bold red] {exc}")
        sys.exit(1)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as handle:
            handle.write(reversal)
        console.print(
            f"[bold green]✓ Reversing entry written to[/bold green] "
            f"{output_file}"
        )
    else:
        click.echo(reversal)


@main.command("validate-id")
@click.option(
    "-k",
    "--kind",
    type=click.Choice(["iban", "bic", "lei"], case_sensitive=False),
    required=True,
    help="Identifier kind.",
)
@click.option("-v", "--value", required=True, help="Identifier value.")
def validate_id(kind: str, value: str) -> None:
    """Validate an IBAN, BIC, or LEI."""
    result = services.validate_identifier(kind, value)
    if result["valid"]:
        console.print(f"[bold green]✓ Valid {kind.upper()}[/bold green]")
    else:
        console.print(f"[bold red]✗ Invalid {kind.upper()}[/bold red]")
        sys.exit(1)
