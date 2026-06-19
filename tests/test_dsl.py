"""DSL parse + serialize round-trip."""
import re

import pytest

from dataspec import SchemaError, parse_schema, to_dsl

CASES = [
    "root string",
    "root string?",
    "root integer | string",
    'root "a" | "b" | "c"',
    "root { name: string, age?: integer }",
    "root { a: integer, ... }",
    "root { [string]: integer }",
    "root { id: string, [string]: number }",
    "root { meta: any }",
    "root { cache: { [string]: [integer] } }",
    "root [string]",
    "root [integer]+",
    "root [integer]{2,5}",
    "root [integer]{3}",
    "root { user: { name: string }? }",
    "root { tags: [string], scores: [number]+ }",
    "root { when: datetime, day: date, at: time }",
    "type Point = { x: number, y: number }\nroot { a: Point, b: Point }",
    "type Tree = { value: integer, kids: [Tree] }\nroot Tree",
]


@pytest.mark.parametrize("text", CASES)
def test_round_trip_equivalent(text):
    s = parse_schema(text)
    s2 = parse_schema(to_dsl(s))
    assert s.equivalent(s2), f"\noriginal: {text}\nserialized: {to_dsl(s)}"


def test_to_dsl_readable():
    dsl = to_dsl(parse_schema("root { name: string, age?: integer, tags: [string]+ }"))
    assert "name: string" in dsl
    assert "age?: integer" in dsl
    assert "[string]+" in dsl


def test_reject_excessive_nesting():
    # Deeply/adversarially nested DSL text must raise a clean SchemaError,
    # not crash the process with an uncatchable RecursionError.
    text = "root " + "[" * 10_000 + "string" + "]" * 10_000
    with pytest.raises(SchemaError, match="maximum depth"):
        parse_schema(text)


# Malformed DSL text, one case per error the hand-written parser can raise.
# A parser's error path is as much its contract as its happy path, so each
# of these pins both that SchemaError (not some other exception) is raised
# and that the message stays recognizable if the parser is ever refactored.
BAD_CASES = [
    ("unterminated string", 'root "abc', "unterminated string"),
    ("unexpected character", "root @", "unexpected character"),
    ("missing closing brace", "root { name: string", "expected '}'"),
    ("missing type name", "type = string\nroot string", "expected type name"),
    ("duplicate type", "type Point = string\ntype Point = integer\nroot Point",
     "duplicate type"),
    ("multiple root declarations", "root string\nroot integer",
     "multiple 'root'"),
    ("bad top-level keyword", "foo string", "expected 'type' or 'root'"),
    ("no root declaration", "type Point = string", "no 'root'"),
    ("unexpected token", "root ?", "unexpected token"),
    ("map key must be string", "root { [integer]: string }",
     "map key type must be 'string'"),
    ("missing field name", "root { : string }", "expected field name"),
    ("empty arity", "root [string]{}", "empty arity"),
    ("union of structural types", "root { a: string } | { b: integer }",
     "union of structural types is not supported"),
    ("unknown type reference", "root Undefined", "unknown type"),
]


@pytest.mark.parametrize("text,expected", [(c[1], c[2]) for c in BAD_CASES],
                        ids=[c[0] for c in BAD_CASES])
def test_malformed_dsl_raises_schema_error(text, expected):
    with pytest.raises(SchemaError, match=re.escape(expected)):
        parse_schema(text)
