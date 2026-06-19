"""Executable check of the snippets shown in README/docs (run via pytest)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tomllib

import pytest

import dataspec as ds
from dataspec import INTEGER, STRING, Field, ObjectType, ScalarType, Schema


def test_readme_at_a_glance():
    data = ds.read_json('{"name": "Ann", "age": 30, "tags": ["x", "y"]}')
    assert ds.infer([data]).to_dsl().strip() == \
        "root { name: string, age: integer, tags: [string] }"


def test_readme_compatibility():
    v1 = ds.parse_schema("root { host: string, port: integer }")
    v2 = ds.parse_schema("root { host: string, port: integer, tls?: boolean }")
    assert v1.compatible_with(v2)
    assert not v2.compatible_with(v1)


def test_usage_programmatic_schema():
    s = Schema(ObjectType({
        "name": Field(ScalarType({STRING}), True),
        "age": Field(ScalarType({INTEGER}), False),
    }))
    assert s.validate(ds.doc({"name": "A"})).ok
    assert not s.validate(ds.doc({"age": 1})).ok


def test_formats_null_option_c():
    assert tomllib.loads(ds.write_toml({"a": 1, "b": None})) == {"a": 1}


def test_getting_started_map_and_any():
    # snippets shown in docs/schema.md
    assert ds.parse_schema("root { [string]: integer }").accepts(ds.doc({"jan": 1, "feb": 2}))
    assert ds.parse_schema("root { name: string, meta: any }").accepts(
        ds.doc({"name": "A", "meta": {"x": [1, 2]}}))


EXAMPLES = [
    "quickstart.py", "validate_api_payload.py", "convert_formats.py",
    "infer_and_refine.py", "version_check.py",
    "build_document.py", "build_schema.py",
]


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_runs(name):
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, os.path.join(root, "examples", name)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
