#!/usr/bin/env python3
"""Build a schema in Python with the builder, compare it to the DSL, validate.

Run: python3 examples/build_schema.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataspec import (
    schema, obj, arr, mapping, enum, optional, nullable,
    string, integer, boolean, doc, parse_schema,
)


def main():
    # The builder produces the same object tree parse_schema would.
    s = schema(obj(
        id      = integer,
        name    = string,
        status  = enum("open", "shipped", "cancelled"),
        tags    = arr(string),
        note    = optional(string),
        deleted = nullable(boolean),
        scores  = mapping(integer),            # { [string]: integer }
    ))

    print("== built schema, printed as DSL ==")
    print(s.to_dsl())

    equivalent_dsl = parse_schema("""
        root {
            id:      integer,
            name:    string,
            status:  "open" | "shipped" | "cancelled",
            tags:    [string],
            note?:   string,
            deleted: boolean?,
            scores:  { [string]: integer },
        }
    """)
    print("builder == DSL:", s.equivalent(equivalent_dsl))

    print("\n== validate a document ==")
    d = doc({
        "id": 1, "name": "Ann", "status": "open",
        "tags": ["a"], "deleted": None, "scores": {"jan": 5},
    })
    print(s.validate(d))

    print("\n== navigate the schema with uniform getters ==")
    print("field 'status':", s.root.field("status"))
    print("children:", [name for name, _ in s.root.children()])


if __name__ == "__main__":
    main()
