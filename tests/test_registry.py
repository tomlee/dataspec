"""The format registry: built-ins plus registering a new format as a plugin."""
import pytest

from dataspec import (
    Doc, doc, Format, register_format, get_format, formats, WriteReport,
)


class TestRegistry:
    def test_builtins_registered(self):
        assert set(formats()) >= {"json", "yaml", "toml", "xml"}

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get_format("does-not-exist")

    def test_get_returns_format(self):
        fmt = get_format("json")
        assert fmt.name == "json" and ".json" in fmt.extensions


class TestPluginFormat:
    def test_register_and_use_a_new_format(self):
        # a trivial "lines" format: one scalar per line, objects/arrays unsupported
        def read(text):
            return [int(x) for x in text.split() if x]

        def write(data, *, strict=False, report=None, **opts):
            return " ".join(str(x) for x in data)

        def check(data, **opts):
            return WriteReport()

        register_format(Format("lines", read, write, check, (".lines",)))

        assert "lines" in formats()
        d = Doc.from_format("lines", "1 2 3")
        assert d.to_data() == [1, 2, 3]
        assert d.to_format("lines") == "1 2 3"

    def test_doc_dispatches_through_registry(self):
        # to_format on an unknown name surfaces the registry error
        with pytest.raises(KeyError):
            doc({"a": 1}).to_format("nope")
