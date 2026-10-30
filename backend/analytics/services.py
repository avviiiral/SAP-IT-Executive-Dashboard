"""Dashboard calculations built on the canonical Ticket model.

The reporting window and legacy treatment follow the supplied executive-dashboard
reference: tickets created before 1 April 2026 are excluded from trend/KPI
calculations but remain visible in the open backlog.
"""
from calendar import monthrange
from datetime import date, datetime, timedelta
from statistics import median

from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from tickets.models import Ticket, TicketCategory, TicketChannel, TicketStatus

REPORTING_START_DATE = date(2026, 4, 1)
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500


def _parse_date(value, name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Use YYYY-MM-DD format."}) from None


def _parse_month(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except (TypeError, ValueError):
        raise ValidationError({"month": "Use YYYY-MM format."}) from None


def _normalize_choice(value, choices, field):
    if not value:
        return None
    raw = str(value).strip()
    key = raw.upper().replace("-", "_").replace(" ", "_")
    valid = {choice for choice, _label in choices}
    if key not in valid:
        labels = {label.casefold(): choice for choice, label in choices}
        key = labels.get(raw.casefold())
    if key not in valid:
        raise ValidationError({field: f"Unsupported value '{value}'."})
    return key


def filtered_tickets(params, *, ignore_month=False):
    """Apply dashboard filters. Date bounds are inclusive."""
    qs = Ticket.objects.all()
    month = None if ignore_month else _parse_month(params.get("month"))
    date_from = _parse_date(params.get("date_from"), "date_from")
    date_to = _parse_date(params.get("date_to"), "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValidationError({"date_to": "Must be on or after date_from."})
    if month:
        next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        qs = qs.filter(created_at_source__date__gte=month,
                       created_at_source__date__lt=next_month)
    if date_from:
        qs = qs.filter(created_at_source__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at_source__date__lte=date_to)

    simple_filters = {
        "plant": "plant_code",
        "subcategory": "subcategory",
        "assignee": "assignee",
    }
    for param, field in simple_filters.items():
        value = params.get(param)
        if value:
            qs = qs.filter(**{field: value.strip()})
    for param, field, choices in (
        ("status", "status", TicketStatus.choices),
        ("category", "category", TicketCategory.choices),
        ("channel", "channel", TicketChannel.choices),
    ):
        value = _normalize_choice(params.get(param), choices, param)
        if value:
            qs = qs.filter(**{field: value})
    return qs


def _is_legacy(ticket):
    return ticket.created_at_source is None or timezone.localtime(
        ticket.created_at_source
    ).date() < REPORTING_START_DATE


def _resolution_days(ticket):
    if ticket.resolution_days is not None:
        return float(ticket.resolution_days)
    if ticket.resolved_at and ticket.created_at_source:
        seconds = (ticket.resolved_at - ticket.created_at_source).total_seconds()
        return max(seconds / 86400, 0)
    return None


def _month_start(value):
    return date(value.year, value.month, 1)


def _previous_month(value):
    return (_month_start(value) - timedelta(days=1)).replace(day=1)


def _as_of_date(qs):
    latest = qs.aggregate(latest=Max("created_at_source"))["latest"]
    if latest:
        return timezone.localtime(latest).date()
    return timezone.localdate()


def _month_metrics(tickets):
    operational = [t for t in tickets if not _is_legacy(t)]
    resolved = [t for t in operational if t.status == TicketStatus.RESOLVED]
    return {
        "tickets": len(operational),
        "resolved": len(resolved),
        "resolution_rate": round(len(resolved) / len(operational), 6) if operational else 0,
    }


def _comparison_months(base_qs, as_of):
    """Compare the last two complete months available in the report."""
    today = timezone.localdate()
    latest_month = _month_start(as_of)
    current_month = _month_start(today)
    latest_complete = _previous_month(current_month) if latest_month >= current_month else latest_month
    previous = _previous_month(latest_complete)
    return latest_complete, previous


def dashboard_summary(params):
    qs = filtered_tickets(params)
    all_for_comparison = filtered_tickets(params, ignore_month=True)
    tickets = list(qs.select_related())
    operational = [t for t in tickets if not _is_legacy(t)]
    resolved = [t for t in operational if t.status == TicketStatus.RESOLVED]
    open_tickets = [t for t in tickets if t.status != TicketStatus.RESOLVED]
    durations = [d for t in resolved if (d := _resolution_days(t)) is not None]

    week_keys = {
        (timezone.localtime(t.created_at_source).isocalendar().year,
         timezone.localtime(t.created_at_source).isocalendar().week)
        for t in operational if t.created_at_source
    }
    as_of = _as_of_date(qs)
    oldest_age = max(
        ((as_of - timezone.localtime(t.created_at_source).date()).days
         for t in open_tickets if t.created_at_source),
        default=0,
    )

    latest_month, previous_month = _comparison_months(all_for_comparison, as_of)
    month_start = latest_month
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    prev_next = (previous_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    latest_rows = list(all_for_comparison.filter(
        created_at_source__date__gte=month_start,
        created_at_source__date__lt=next_month,
    ))
    previous_rows = list(all_for_comparison.filter(
        created_at_source__date__gte=previous_month,
        created_at_source__date__lt=prev_next,
    ))
    latest_metrics = _month_metrics(latest_rows)
    previous_metrics = _month_metrics(previous_rows)

    avg_days = sum(durations) / len(durations) if durations else 0
    # The reference dashboard selects the upper middle observation for even-sized sets.
    sorted_durations = sorted(durations)
    median_days = sorted_durations[len(sorted_durations) // 2] if sorted_durations else 0
    within_one_day = sum(d <= 1 for d in durations)

    return {
        "reporting_start_date": REPORTING_START_DATE.isoformat(),
        "as_of_date": as_of.isoformat(),
        "filters": {
            key: params.get(key) for key in
            ("month", "date_from", "date_to", "plant", "category",
             "subcategory", "assignee", "status", "channel") if params.get(key)
        },
        "total_tickets": len(operational),
        "resolved_tickets": len(resolved),
        "resolution_rate": round(len(resolved) / len(operational), 6) if operational else 0,
        "open_backlog": len(open_tickets),
        "oldest_open_age_days": oldest_age,
        "average_resolution_days": round(avg_days, 4),
        "median_resolution_days": round(median_days, 4),
        "resolved_within_one_day_rate": round(within_one_day / len(resolved), 6) if resolved else 0,
        "average_tickets_per_week": round(len(operational) / len(week_keys), 2) if week_keys else 0,
        "weeks_in_reporting_data": len(week_keys),
        "comparison": {
            "latest_complete_month": latest_month.strftime("%Y-%m"),
            "previous_complete_month": previous_month.strftime("%Y-%m"),
            "latest": latest_metrics,
            "previous": previous_metrics,
        },
    }


def _group_count(tickets, getter):
    groups = {}
    for ticket in tickets:
        key = getter(ticket) or "Unassigned/Unknown"
        groups[key] = groups.get(key, 0) + 1
    return [{"name": name, "tickets": count} for name, count in
            sorted(groups.items(), key=lambda item: (-item[1], item[0]))]


def dashboard_trends(params):
    qs = filtered_tickets(params)
    operational = qs.filter(created_at_source__date__gte=REPORTING_START_DATE)
    monthly_qs = filtered_tickets(params, ignore_month=True).filter(
        created_at_source__date__gte=REPORTING_START_DATE
    )
    month_counts = {}
    for ticket in monthly_qs.only("created_at_source", "status"):
        month = timezone.localtime(ticket.created_at_source).strftime("%Y-%m")
        entry = month_counts.setdefault(month, {"tickets": 0, "resolved": 0})
        entry["tickets"] += 1
        if ticket.status == TicketStatus.RESOLVED:
            entry["resolved"] += 1
    monthly = [
        {"month": month, **values,
         "resolution_rate": round(values["resolved"] / values["tickets"], 6) if values["tickets"] else 0}
        for month, values in sorted(month_counts.items())
    ]

    week_counts = {}
    for ticket in operational.only("created_at_source"):
        local_date = timezone.localtime(ticket.created_at_source).date()
        monday = local_date - timedelta(days=local_date.weekday())
        week_counts[monday] = week_counts.get(monday, 0) + 1
    weekly = [{"week_start": monday.isoformat(), "tickets": count}
              for monday, count in sorted(week_counts.items())]
    return {"monthly": monthly, "weekly": weekly}


def dashboard_breakdowns(params):
    tickets = list(filtered_tickets(params).filter(
        created_at_source__date__gte=REPORTING_START_DATE
    ))
    resolved = [t for t in tickets if t.status == TicketStatus.RESOLVED]
    by_subcategory = _group_count(tickets, lambda t: t.subcategory)
    by_plant = _group_count(tickets, lambda t: t.plant_code)[:10]
    by_channel = _group_count(tickets, lambda t: t.get_channel_display())
    by_assignee = _group_count(tickets, lambda t: t.assignee)[:9]

    resolution_groups = {}
    for ticket in resolved:
        duration = _resolution_days(ticket)
        if duration is None:
            continue
        key = ticket.subcategory or "Unassigned/Unknown"
        entry = resolution_groups.setdefault(key, {"resolved": 0, "total_days": 0})
        entry["resolved"] += 1
        entry["total_days"] += duration
    by_resolution = [
        {"name": name, "resolved": data["resolved"],
         "average_resolution_days": round(data["total_days"] / data["resolved"], 4)}
        for name, data in resolution_groups.items() if data["resolved"] >= 5
    ]
    by_resolution.sort(key=lambda item: item["average_resolution_days"], reverse=True)
    return {
        "by_subcategory": by_subcategory[:10],
        "by_plant": by_plant,
        "by_channel": by_channel,
        "by_assignee": by_assignee,
        "average_resolution_by_subcategory": by_resolution[:10],
    }


def dashboard_backlog(params, *, limit=100):
    qs = filtered_tickets(params).exclude(status=TicketStatus.RESOLVED).select_related()
    tickets = list(qs)
    as_of = _as_of_date(qs)
    tickets.sort(key=lambda t: t.created_at_source or timezone.make_aware(datetime.min), reverse=False)
    rows = []
    for ticket in tickets[:limit]:
        created = timezone.localtime(ticket.created_at_source).date() if ticket.created_at_source else None
        age = (as_of - created).days if created else None
        due = timezone.localtime(ticket.due_at).date() if ticket.due_at else None
        rows.append({
            "incident_number": ticket.incident_number,
            "title": ticket.title,
            "status": ticket.status,
            "status_label": ticket.get_status_display(),
            "category": ticket.category,
            "subcategory": ticket.subcategory or "Unassigned/Unknown",
            "plant": ticket.plant_code or "Unassigned/Unknown",
            "assignee": ticket.assignee or "Unassigned/Unknown",
            "created_date": created.isoformat() if created else None,
            "due_date": due.isoformat() if due else None,
            "age_days": age,
            "overdue": bool(due and due < as_of),
            "legacy": bool(created and created < REPORTING_START_DATE),
        })
    return {
        "as_of_date": as_of.isoformat(),
        "total_open": len(tickets),
        "older_than_30_days": sum(
            1 for t in tickets if t.created_at_source and (as_of - timezone.localtime(t.created_at_source).date()).days > 30
        ),
        "older_than_90_days": sum(
            1 for t in tickets if t.created_at_source and (as_of - timezone.localtime(t.created_at_source).date()).days > 90
        ),
        "overdue_count": sum(1 for t in tickets if t.due_at and timezone.localtime(t.due_at).date() < as_of),
        "results": rows,
        "limit": limit,
    }


def dashboard_ticket_list(params):
    qs = filtered_tickets(params)
    scope = params.get("scope", "all")
    if scope == "operational":
        qs = qs.filter(created_at_source__date__gte=REPORTING_START_DATE)
    elif scope == "resolved":
        qs = qs.filter(status=TicketStatus.RESOLVED)
    elif scope == "open":
        qs = qs.exclude(status=TicketStatus.RESOLVED)
    elif scope == "within_one_day":
        qs = qs.filter(status=TicketStatus.RESOLVED, resolution_days__lte=1)
    elif scope != "all":
        raise ValidationError({"scope": "Use all, operational, resolved, open or within_one_day."})

    try:
        page = max(int(params.get("page", 1)), 1)
        page_size = min(max(int(params.get("page_size", DEFAULT_PAGE_SIZE)), 1), MAX_PAGE_SIZE)
    except (TypeError, ValueError):
        raise ValidationError({"page": "page and page_size must be integers."}) from None
    total = qs.count()
    qs = qs.order_by("-created_at_source", "incident_number")
    start = (page - 1) * page_size
    records = qs[start:start + page_size]
    results = [{
        "incident_number": t.incident_number,
        "title": t.title,
        "status": t.status,
        "status_label": t.get_status_display(),
        "category": t.category,
        "subcategory": t.subcategory,
        "plant": t.plant_code,
        "channel": t.channel,
        "assignee": t.assignee,
        "created_at": t.created_at_source.isoformat() if t.created_at_source else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        "resolution_days": _resolution_days(t),
        "due_at": t.due_at.isoformat() if t.due_at else None,
    } for t in records]
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "results": results,
    }
