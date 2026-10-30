"""Convert source values into the canonical ticket model vocabulary."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from tickets.models import TicketCategory, TicketChannel, TicketStatus


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_datetime(value: Any, field_label: str) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    else:
        text = clean_text(value)
        parsed = None
        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                parsed = datetime.fromisoformat(candidate)
                break
            except ValueError:
                continue
        if parsed is None:
            for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
        if parsed is None:
            raise ValueError(f"{field_label} must be a valid date/time.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def parse_decimal(value: Any, field_label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_label} must be numeric.") from None
    if number < 0:
        raise ValueError(f"{field_label} cannot be negative.")
    return number


def normalize_status(value: Any) -> tuple[str, str]:
    source = clean_text(value)
    key = source.casefold().replace("_", " ").replace("-", " ")
    if key in {"resolved", "closed", "complete", "completed"}:
        canonical = TicketStatus.RESOLVED
    elif key in {"in progress", "inprogress", "work in progress", "wip"}:
        canonical = TicketStatus.IN_PROGRESS
    elif key in {"on hold", "hold", "pending"}:
        canonical = TicketStatus.ON_HOLD
    elif key in {"open", "new", "assigned"}:
        canonical = TicketStatus.OPEN
    else:
        canonical = TicketStatus.UNKNOWN
    return canonical, source


def normalize_category(value: Any) -> tuple[str, str]:
    source = clean_text(value)
    key = source.casefold()
    if key == "it":
        canonical = TicketCategory.IT
    elif key == "sap":
        canonical = TicketCategory.SAP
    elif key in {"", "unassigned", "unknown", "nan", "none"}:
        canonical = TicketCategory.UNASSIGNED
    else:
        canonical = TicketCategory.OTHER
    return canonical, source


def normalize_channel(value: Any) -> tuple[str, str]:
    source = clean_text(value)
    key = source.casefold().replace(" ", "")
    if key in {"webapp", "web", "portal"}:
        canonical = TicketChannel.WEBAPP
    elif key in {"email", "e-mail", "mail"}:
        canonical = TicketChannel.EMAIL
    elif not key:
        canonical = TicketChannel.UNKNOWN
    else:
        canonical = TicketChannel.OTHER
    return canonical, source
