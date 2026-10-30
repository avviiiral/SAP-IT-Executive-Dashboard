from django.urls import path

from .views import UploadBatchListView, UploadCreateView

urlpatterns = [
    path("", UploadBatchListView.as_view(), name="upload-batch-list"),
    path("import/", UploadCreateView.as_view(), name="upload-create"),
]
