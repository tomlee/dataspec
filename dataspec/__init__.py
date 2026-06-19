"""dataspec — one data model, many formats.

A **Document** is a tree of objects, arrays, and scalars, held by a :class:`Doc`.
A **Schema** describes the shape a Document should have. Read a format into a
Doc, validate it against a Schema, and write it back out to any format.

    from dataspec import Doc, obj, arr, schema, t

    d = Doc.from_json('{"name": "Ann", "tags": ["x", "y"]}')
    d.to_toml()                                   # transcode JSON -> TOML

    s = schema(obj(name=t.string, tags=arr(t.string)))
    s.validate(d).ok                              # True

The low-level functional codecs (``read_json`` / ``write_toml`` / …) operate on
plain Python and are still available; ``Doc`` is the object layer over them.
"""

from .errors import (
    DataspecError, SchemaError, ParseError, WriteError, DocumentError,
    DetachedNode,
)
from .report import WriteReport, Adjustment
from .schema import (
    Schema, ValidationResult, Error,
    Type, AnyType, ScalarType, ArrayType, ObjectType, Field, RefType,
    STRING, INTEGER, NUMBER, BOOLEAN, DATE, TIME, DATETIME,
)
from .document import Doc, doc
from .builder import (
    obj, arr, mapping, ref, enum, optional, nullable, schema, t,
)
from .dsl import parse_schema, to_dsl
from .infer import infer
from .formats import (
    read_json, write_json, check_json,
    read_yaml, write_yaml, check_yaml,
    read_toml, write_toml, check_toml,
    read_xml, write_xml, check_xml,
    Format, register_format, get_format, formats,
)

__all__ = [
    # errors
    "DataspecError", "SchemaError", "ParseError", "WriteError", "DocumentError",
    "DetachedNode",
    # serialization reports
    "WriteReport", "Adjustment",
    # document (data DOM)
    "Doc", "doc",
    # schema model
    "Schema", "ValidationResult", "Error",
    "Type", "AnyType", "ScalarType", "ArrayType", "ObjectType", "Field", "RefType",
    "STRING", "INTEGER", "NUMBER", "BOOLEAN", "DATE", "TIME", "DATETIME",
    # schema builder
    "obj", "arr", "mapping", "ref", "enum", "optional", "nullable", "schema", "t",
    # dsl
    "parse_schema", "to_dsl",
    # operations
    "infer",
    # format registry
    "Format", "register_format", "get_format", "formats",
    # functional codecs
    "read_json", "write_json", "check_json",
    "read_yaml", "write_yaml", "check_yaml",
    "read_toml", "write_toml", "check_toml",
    "read_xml", "write_xml", "check_xml",
]

__version__ = "0.1.0a1"
