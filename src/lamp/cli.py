"""Command line interface for LAMP audits."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click

from .audit import run_audit


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main() -> None:
    """Run executable LAMP failure-mode audits."""


@main.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to LAMP YAML config.",
)
@click.option(
    "--data",
    "--input",
    "data_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to CSV score table.",
)
@click.option(
    "--output",
    "--out",
    "output_dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Directory where audit_summary.json and audit_report.md are written.",
)
@click.option(
    "--print-json",
    is_flag=True,
    help="Print the audit summary JSON to stdout.",
)
@click.option(
    "--log-level",
    default="WARNING",
    show_default=True,
    help="Python logging level.",
)
def audit(
    config_path: Path,
    data_path: Path,
    output_dir: Path,
    print_json: bool,
    log_level: str,
) -> None:
    """Audit a prediction table using a YAML configuration."""
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.WARNING))
    result = run_audit(
        config_path=config_path,
        input_path=data_path,
        out_dir=output_dir,
    )
    if print_json:
        click.echo(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
