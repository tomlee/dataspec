"""Adjustment reports for serialization.

Writing a Document to a format that can't hold every value (TOML/XML have no
``null``; JSON has no dates) means the writer has to *adjust* the data.  Instead
of silently losing information, each adjustment is recorded as an
:class:`Adjustment` and collected into a :class:`WriteReport`.

The same report drives all three behaviours:

* **lenient** (default) — adjust and move on; ignore the report if you like.
* **inspect** — pass ``report=`` to a writer, or call ``check_*``, to see what
  changed without stopping.
* **strict** — ``strict=True`` raises a ``WriteError`` (carrying the report) if
  the report is non-empty, guaranteeing a lossless round-trip.

Each adjustment has a ``severity``:

* ``"warning"`` — conventional / recoverable (a null object field omitted, a
  date written as a string).
* ``"error"`` — likely to surprise or corrupt meaning (a null array item
  dropped, which shifts positions; ``NaN`` in JSON).

``severity`` is advice for a human; ``strict`` ignores it and raises on anything.
"""

from __future__ import annotations

from typing import NamedTuple, Optional

from .errors import WriteError


class Adjustment(NamedTuple):
    """A single change the writer made to fit the data into a format."""

    path: str        # e.g. "$.items[3]" — same path style as validation
    code: str        # stable, machine-checkable, e.g. "null.item.dropped"
    message: str     # human-readable sentence
    severity: str    # "warning" | "error"


class WriteReport:
    """Everything a writer adjusted, mirroring ``ValidationResult``.

    Truthiness follows the safety question: a report is **True** when it has no
    error-severity entries (warnings are fine), so ``if check_toml(doc): ...``
    reads as "safe to write".
    """

    def __init__(self) -> None:
        self.adjustments: list[Adjustment] = []

    def add(self, path: str, code: str, message: str, severity: str) -> None:
        self.adjustments.append(Adjustment(path, code, message, severity))

    def extend(self, other: "WriteReport") -> None:
        self.adjustments.extend(other.adjustments)

    @property
    def warnings(self) -> list[Adjustment]:
        return [a for a in self.adjustments if a.severity == "warning"]

    @property
    def errors(self) -> list[Adjustment]:
        return [a for a in self.adjustments if a.severity == "error"]

    def __bool__(self) -> bool:
        return not self.errors

    def __iter__(self):
        return iter(self.adjustments)

    def __len__(self) -> int:
        return len(self.adjustments)

    def __str__(self) -> str:
        if not self.adjustments:
            return "no adjustments"
        return "\n".join(f"{a.severity}: {a.path}: {a.message}"
                         for a in self.adjustments)


def finish_write(text: str, rep: WriteReport, *, strict: bool = False,
                 report: Optional[WriteReport] = None) -> str:
    """Apply the standard ``strict``/``report`` handling to a writer's result.

    Every ``write_*`` follows the same shape: serialize, collect adjustments
    into a :class:`WriteReport`, then decide what to do with them. Call this
    at the end of your own ``write`` function instead of repeating that
    decision yourself::

        def write_csv(data, *, strict=False, report=None, **opts):
            text, rep = _serialize_csv(data, **opts)
            return finish_write(text, rep, strict=strict, report=report)

    If ``report`` is given, ``rep``'s adjustments are merged into it. If
    ``strict`` is true and ``rep`` has any adjustments (regardless of
    severity), raises :class:`~dataspec.errors.WriteError` carrying ``rep``.
    Otherwise returns ``text`` unchanged.
    """
    if report is not None:
        report.extend(rep)
    if strict and rep.adjustments:
        raise WriteError(str(rep), report=rep)
    return text
