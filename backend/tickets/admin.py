from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "incident_number", "title", "status", "category", "subcategory",
        "plant_code", "assignee", "created_at_source",
        "missing_from_latest_full_snapshot",
    )
    list_filter = ("status", "category", "channel", "missing_from_latest_full_snapshot")
    search_fields = ("incident_number", "title", "plant_code", "assignee")
    readonly_fields = ("created_on", "updated_on")
