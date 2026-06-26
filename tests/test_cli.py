"""Tests for the omnist CLI (omnist/cli.py).

Each command is invoked in-process via ``main(argv)`` with stdin/stdout/
stderr captured -- no subprocess, consistent with this repo's fast test
suite. See docs/design/cli-spec.md for the full command surface; this
file's coverage grows alongside the CLI's own implementation PRs.
"""
from __future__ import annotations

import pytest

from omnist.cli import main


def run(argv, stdin=None, capsys=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(stdin))
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


class TestFormat:
    def test_reformats_oml_from_file_to_stdout(self, tmp_path, capsys):
        p = tmp_path / "in.oml"
        p.write_text('a: 1\nb: "x"\n')
        code, out, err = run(["format", str(p)], capsys=capsys, monkeypatch=None)
        assert code == 0
        assert err == ""
        assert out == 'a: 1\nb: "x"\n'

    def test_writes_to_output_file(self, tmp_path, capsys):
        src = tmp_path / "in.oml"
        src.write_text('a: 1\n')
        dst = tmp_path / "out.oml"
        code, out, err = run(["format", str(src), "-o", str(dst)], capsys=capsys, monkeypatch=None)
        assert code == 0
        assert out == ""
        assert dst.read_text() == 'a: 1\n'

    def test_reads_from_stdin(self, capsys, monkeypatch):
        code, out, err = run(
            ["format", "-"], stdin='a: 1\n', capsys=capsys, monkeypatch=monkeypatch)
        assert code == 0
        assert out == 'a: 1\n'

    def test_round_trips_canonically_even_if_messy(self, tmp_path, capsys):
        p = tmp_path / "in.oml"
        p.write_text('a:   1\nb:"x"\n')
        code, out, err = run(["format", str(p)], capsys=capsys, monkeypatch=None)
        assert code == 0
        assert out == 'a: 1\nb: "x"\n'

    def test_invalid_oml_is_a_clean_error_not_a_traceback(self, tmp_path, capsys):
        p = tmp_path / "bad.oml"
        p.write_text('a: [1, 2]\n')   # OML has no JSON-style array literal
        code, out, err = run(["format", str(p)], capsys=capsys, monkeypatch=None)
        assert code == 2
        assert out == ""
        assert err.startswith("error: ")

    def test_missing_file_is_a_clean_error(self, tmp_path, capsys):
        missing = tmp_path / "nope.oml"
        code, out, err = run(["format", str(missing)], capsys=capsys, monkeypatch=None)
        assert code == 2
        assert err.startswith("error: ")

    def test_missing_input_argument_is_argparse_usage_error(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["format"])
        assert exc.value.code == 2


class TestSchemaFormat:
    def test_reformats_osd_from_file_to_stdout(self, tmp_path, capsys):
        p = tmp_path / "in.osd"
        p.write_text('record R { "a": integer }\nroot R\n')
        code, out, err = run(["schema", "format", str(p)], capsys=capsys, monkeypatch=None)
        assert code == 0
        assert err == ""
        assert out == 'record R {\n    "a": integer,\n}\nroot R\n'

    def test_writes_to_output_file(self, tmp_path, capsys):
        src = tmp_path / "in.osd"
        src.write_text('record R { "a": integer }\nroot R\n')
        dst = tmp_path / "out.osd"
        code, out, err = run(
            ["schema", "format", str(src), "-o", str(dst)], capsys=capsys, monkeypatch=None)
        assert code == 0
        assert out == ""
        assert dst.read_text() == 'record R {\n    "a": integer,\n}\nroot R\n'

    def test_reads_from_stdin(self, capsys, monkeypatch):
        code, out, err = run(
            ["schema", "format", "-"],
            stdin='record R { "a": integer }\nroot R\n',
            capsys=capsys, monkeypatch=monkeypatch)
        assert code == 0
        assert out == 'record R {\n    "a": integer,\n}\nroot R\n'

    def test_invalid_osd_is_a_clean_error_not_a_traceback(self, tmp_path, capsys):
        p = tmp_path / "bad.osd"
        p.write_text('record R { "a": integer }\n')   # no root
        code, out, err = run(["schema", "format", str(p)], capsys=capsys, monkeypatch=None)
        assert code == 2
        assert out == ""
        assert err.startswith("error: ")

    def test_missing_schema_file_argument_is_argparse_usage_error(self):
        with pytest.raises(SystemExit) as exc:
            main(["schema", "format"])
        assert exc.value.code == 2

    def test_missing_schema_subcommand_is_argparse_usage_error(self):
        with pytest.raises(SystemExit) as exc:
            main(["schema"])
        assert exc.value.code == 2


class TestTopLevel:
    def test_missing_command_is_argparse_usage_error(self):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 2

    def test_unknown_command_is_argparse_usage_error(self):
        with pytest.raises(SystemExit) as exc:
            main(["bogus"])
        assert exc.value.code == 2
