from rest_framework import serializers

from .models import UploadBatch, UploadType


class UploadBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadBatch
        fields = (
            "id",
            "original_filename",
            "upload_type",
            "status",
            "uploaded_at",
            "started_at",
            "completed_at",
            "total_rows",
            "inserted_rows",
            "updated_rows",
            "unchanged_rows",
            "rejected_rows",
            "snapshot_scope",
            "error_summary",
            "metadata",
        )
        read_only_fields = fields


class UploadCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    upload_type = serializers.ChoiceField(choices=UploadType.choices)
    snapshot_scope = serializers.CharField(required=False, allow_blank=True, max_length=150)
    field_map = serializers.JSONField(required=False)

    def validate_file(self, value):
        name = value.name.lower()
        if not name.endswith((".csv", ".xlsx", ".xlsm")):
            raise serializers.ValidationError("Upload a .csv, .xlsx or .xlsm file.")
        max_size = 20 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File exceeds the 20 MB upload limit.")
        return value

    def validate_field_map(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("field_map must be a JSON object.")
        return value

    def validate(self, attrs):
        if attrs["upload_type"] == UploadType.FULL and not attrs.get("snapshot_scope", "").strip():
            raise serializers.ValidationError({
                "snapshot_scope": "An explicit snapshot scope is required for full reports."
            })
        return attrs
