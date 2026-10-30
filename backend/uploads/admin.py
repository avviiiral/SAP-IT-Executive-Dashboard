from django.contrib import admin

from .models import ImportRow, UploadBatch


class ImportRowInline(admin.TabularInline):
    model = ImportRow
    extra = 0
    fields = ("row_number", "incident_number", "status", "error_message", "ticket")
    readonly_fields = fields
    can_delete = False


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename", "upload_type", "status", "uploaded_at",
        "total_rows", "inserted_rows", "updated_rows", "rejected_rows",
    )
    list_filter = ("upload_type", "status", "uploaded_at")
    search_fields = ("original_filename", "file_sha256")
    readonly_fields = (
        "uploaded_at", "started_at", "completed_at", "total_rows",
        "inserted_rows", "updated_rows", "unchanged_rows", "rejected_rows",
    )
    inlines = (ImportRowInline,)


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ("batch", "row_number", "incident_number", "status", "processed_at")
    list_filter = ("status",)
    search_fields = ("incident_number", "error_message")
