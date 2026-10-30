import json

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UploadBatch, UploadType
from .serializers import UploadBatchSerializer, UploadCreateSerializer
from .services.importer import ImportExecutionError, process_upload


class UploadCreateView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (IsAdminUser,)

    def post(self, request):
        serializer = UploadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        field_map = payload.get("field_map")
        if isinstance(field_map, str):
            try:
                field_map = json.loads(field_map)
            except json.JSONDecodeError:
                return Response(
                    {"field_map": "Must be a valid JSON object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if field_map is not None and not isinstance(field_map, dict):
            return Response(
                {"field_map": "Must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = payload["file"]
        batch = UploadBatch.objects.create(
            original_filename=uploaded_file.name[:255],
            upload_type=payload["upload_type"],
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        try:
            process_upload(
                batch=batch,
                file_obj=uploaded_file,
                field_map=field_map,
                snapshot_scope=payload.get("snapshot_scope", ""),
            )
        except ImportExecutionError as exc:
            batch.refresh_from_db()
            return Response(
                {
                    "error": str(exc),
                    "batch": UploadBatchSerializer(batch).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch.refresh_from_db()
        return Response(
            UploadBatchSerializer(batch).data,
            status=(
                status.HTTP_207_MULTI_STATUS
                if batch.rejected_rows
                else status.HTTP_201_CREATED
            ),
        )


class UploadBatchListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        batches = UploadBatch.objects.all()[:100]
        return Response(UploadBatchSerializer(batches, many=True).data)
