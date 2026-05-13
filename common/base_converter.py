"""
Abstract base class for CSV-based bookmark converters.

This module defines :class:`BaseConverter`, the shared contract for all CSV
exporting bookmark importers (Pocket, Evernote, Firefox, Chrome). It
standardizes the constructor signature ``(input_file, output_file, logger=None)``
and — more importantly — centralizes the ``csv.DictWriter`` configuration so
every converter produces consistently quoted CSV (``csv.QUOTE_ALL`` with
``delimiter=","``, ``lineterminator="\n"``, ``quotechar='"'``).

The format-specific work (reading the source, walking the tree/HTML/XML and
extracting bookmark rows) is left to subclasses via two abstract methods:
``read_input`` and ``extract_bookmarks``.
"""

from __future__ import annotations

import argparse
import csv
import logging
from abc import ABC, abstractmethod
from typing import IO, Any

from common.logging import get_logger

# Single source of truth for csv.DictWriter kwargs across all converters.
# Subclasses MUST construct csv.DictWriter via ``new_csv_writer`` (or splat
# ``CSV_WRITER_KWARGS``) so that all CSV output is quoted consistently — see
# the QUOTE_ALL regression tests in tests/<plugin>/test_*.py.
CSV_WRITER_KWARGS: dict[str, Any] = {
    "delimiter": ",",
    "lineterminator": "\n",
    "quotechar": '"',
    "quoting": csv.QUOTE_ALL,
}


class BaseConverter(ABC):
    """Abstract base for CSV-based bookmark converters.

    Subclasses implement ``read_input`` (returns format-specific parsed data)
    and ``extract_bookmarks`` (returns a list of dict-like bookmark rows or
    typed bookmark records the subclass knows how to write).

    The base class supplies:

    * a normalized constructor: ``(input_file, output_file, logger=None)``
    * ``new_csv_writer``: builds a ``csv.DictWriter`` with the standardized
      QUOTE_ALL kwargs so every converter's CSV output is uniformly quoted.
    * ``configure_input_file_arg``: a public hook to replace the
      ``parser._option_string_actions['--input-file']`` private-API access
      pattern used by individual ``main()`` helpers.
    """

    def __init__(
        self,
        input_file: str,
        output_file: str,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the converter.

        Parameters
        ----------
        input_file:
            Path to the source file (HTML/JSON/ENEX/etc.).
        output_file:
            Path to write the CSV output to.
        logger:
            Optional logger; if omitted, ``get_logger()`` is used.
        """
        self.input_file = input_file
        self.output_file = output_file
        self.logger = logger or get_logger()

    @abstractmethod
    def read_input(self) -> Any:
        """Read and parse the input file. Implementation-specific return type."""

    @abstractmethod
    def extract_bookmarks(self, data: Any) -> list[Any]:
        """Extract bookmark records from the parsed input data."""

    @staticmethod
    def new_csv_writer(file_obj: IO[str], fieldnames: list[str]) -> csv.DictWriter:
        """Build a ``csv.DictWriter`` with the standardized QUOTE_ALL kwargs.

        All subclasses MUST construct writers via this helper so the
        ``QUOTE_ALL`` / delimiter / lineterminator / quotechar settings stay in
        one place. This is the single fix for the firefox + evernote
        inconsistent-quoting bugs tracked by the cycle 3c xfail markers.
        """
        return csv.DictWriter(file_obj, fieldnames=fieldnames, **CSV_WRITER_KWARGS)

    @staticmethod
    def configure_input_file_arg(
        parser: argparse.ArgumentParser, metavar: str, help_text: str
    ) -> None:
        """Update the ``--input-file`` argument's metavar and help text.

        Wraps the ``parser._option_string_actions["--input-file"]`` private
        argparse access pattern in a single public helper. Plugins and ``main``
        helpers should use this rather than reaching into argparse internals.
        """
        action = parser._option_string_actions["--input-file"]
        action.metavar = metavar
        action.help = help_text
