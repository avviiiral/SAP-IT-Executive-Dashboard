"""Read tabular ticket exports without assuming source-system column names."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


class FileReadError(ValueError):
    """Raised when an uploaded file cannot be read as a supported table."""


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}


def _clean_header(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def read_tabular_file(file_obj, filename: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (headers, rows), with source row numbers starting at 2."""
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise FileReadError("Unsupported file type. Upload .csv, .xlsx or .xlsm.")

    try:
        if extension == ".csv":
            raw = file_obj.read()
            if isinstance(raw, bytes):
                text = raw.decode("utf-8-sig")
            else:
                text = raw
            sample = text[:8192]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(text.splitlines(), dialect)
            matrix = list(reader)
        else:
            workbook = load_workbook(file_obj, read_only=True, data_only=True)
            worksheet = workbook.active
            matrix = list(worksheet.iter_rows(values_only=True))
            workbook.close()
    except (UnicodeDecodeError, OSError, csv.Error, ValueError) as exc:
        raise FileReadError(f"Unable to read uploaded file: {exc}") from exc

    if not matrix:
        raise FileReadError("The uploaded file is empty.")

    headers = [_clean_header(value) for value in matrix[0]]
    if not any(headers):
        raise FileReadError("The first row must contain column headers.")
    if len([h.casefold() for h in headers if h]) != len(set(h.casefold() for h in headers if h)):
        raise FileReadError("The file contains duplicate column headers.")

    rows: list[dict[str, Any]] = []
    for row_number, values in enumerate(matrix[1:], start=2):
        values = list(values)
        if not any(value not in (None, "") for value in values):
            continue
        padded = values + [None] * max(0, len(headers) - len(values))
        rows.append({
            "__row_number__": row_number,
            **{header: padded[index] for index, header in enumerate(headers) if header},
        })
    return headers, rows
