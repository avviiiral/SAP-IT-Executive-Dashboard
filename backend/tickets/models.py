from django.db import models
from django.db.models import Q


class TicketStatus(models.TextChoices):
    RESOLVED = "RESOLVED", "Resolved"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    ON_HOLD = "ON_HOLD", "On Hold"
    OPEN = "OPEN", "Open"
    UNKNOWN = "UNKNOWN", "Unknown"


class TicketCategory(models.TextChoices):
    IT = "IT", "IT"
    SAP = "SAP", "SAP"
    UNASSIGNED = "UNASSIGNED", "Unassigned / Unknown"
    OTHER = "OTHER", "Other"


class TicketChannel(models.TextChoices):
    WEBAPP = "WEBAPP", "WebApp"
    EMAIL = "EMAIL", "Email"
    OTHER = "OTHER", "Other"
    UNKNOWN = "UNKNOWN", "Unknown"


class Ticket(models.Model):
    """Canonical incident record, keyed by its stable external incident number."""

    incident_number = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.UNKNOWN, db_index=True)
    source_status = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=20, choices=TicketCategory.choices, default=TicketCategory.UNASSIGNED, db_index=True)
    source_category = models.CharField(max_length=100, blank=True)
    subcategory = models.CharField(max_length=150, blank=True, db_index=True)
    plant_code = models.CharField(max_length=50, blank=True, db_index=True)
    channel = models.CharField(max_length=20, choices=TicketChannel.choices, default=TicketChannel.UNKNOWN, db_index=True)
    source_channel = models.CharField(max_length=100, blank=True)
    assignee = models.CharField(max_length=150, blank=True, db_index=True)

    created_at_source = models.DateTimeField(null=True, blank=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolution_days = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)

    # Snapshot membership is independent of ticket status. Absence is not resolution.
    last_seen_in_full_snapshot_at = models.DateTimeField(null=True, blank=True)
    missing_from_latest_full_snapshot = models.BooleanField(default=False, db_index=True)

    source_updated_at = models.DateTimeField(null=True, blank=True)
    raw_source_data = models.JSONField(default=dict, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at_source", "incident_number")
        indexes = [
            models.Index(fields=("status", "created_at_source"), name="ticket_status_created_idx"),
            models.Index(fields=("plant_code", "status"), name="ticket_plant_status_idx"),
            models.Index(fields=("category", "subcategory"), name="ticket_category_subcat_idx"),
            models.Index(fields=("assignee", "status"), name="ticket_assignee_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(resolution_days__isnull=True) | Q(resolution_days__gte=0),
                name="ticket_resolution_days_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.incident_number} — {self.title[:80]}"
