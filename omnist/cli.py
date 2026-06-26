"""The ``omnist`` command-line interface.

A thin wrapper over the public :mod:`omnist` API -- see
``docs/design/cli-spec.md`` for the full command surface. Each command maps
to one or two calls into the library; this module adds no new behavior of
its own beyond argument parsing, file/stdio plumbing, and exit codes.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import ParseError, SchemaError, WriteError, parse_schema, read_oml, to_dsl, write_oml


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_output(path: Optional[str], text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    if path is None or path == "-":
        sys.stdout.write(text)
    else:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)


def _cmd_format(args: argparse.Namespace) -> int:
    node = read_oml(_read_input(args.input))
    _write_output(args.output, write_oml(node))
    return 0


def _cmd_schema_format(args: argparse.Namespace) -> int:
    s = parse_schema(_read_input(args.schema_file))
    _write_output(args.output, to_dsl(s))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omnist")
    subparsers = parser.add_subparsers(dest="command", required=True)

    format_p = subparsers.add_parser(
        "format", help="canonicalize an OML document (the only format with no other tool for this)")
    format_p.add_argument("input", help="OML file, or - for stdin")
    format_p.add_argument("-o", "--output", help="output file; omit for stdout")
    format_p.set_defaults(func=_cmd_format)

    schema_p = subparsers.add_parser("schema", help="operate on a Schema (OSD)")
    schema_sub = schema_p.add_subparsers(dest="schema_command", required=True)

    schema_format_p = schema_sub.add_parser(
        "format", help="canonicalize an OSD schema file (safe reformat only, no structural change)")
    schema_format_p.add_argument("schema_file", help="OSD file, or - for stdin")
    schema_format_p.add_argument("-o", "--output", help="output file; omit for stdout")
    schema_format_p.set_defaults(func=_cmd_schema_format)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ParseError, SchemaError, WriteError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
