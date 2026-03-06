from django.db import transaction
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers

from .models import Material, MaterialFile
from .permissions import IsCreatorOrStaffOrReadOnly
from .serializers import MaterialReadSerializer, MaterialWriteSerializer


class MaterialListView(generics.ListAPIView):
    """
    GET /materials/
    """
    queryset = Material.objects.select_related("course", "creator").prefetch_related("files")
    serializer_class = MaterialReadSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]


class MaterialDetailView(generics.RetrieveAPIView):
    """
    GET /materials/<id>/
    """
    queryset = Material.objects.select_related("course", "creator").prefetch_related("files")
    serializer_class = MaterialReadSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]


@extend_schema(
    request=inline_serializer(
        name="MaterialCreateMultipart",
        fields={
            "course_id": drf_serializers.IntegerField(),
            "title": drf_serializers.CharField(),
            "description": drf_serializers.CharField(required=False, allow_blank=True),
            # IMPORTANT: this makes Swagger show "Choose File" inputs
            "files": drf_serializers.ListField(
                child=drf_serializers.FileField(),
                required=False,
                allow_empty=True,
            ),
        },
    ),
    responses=MaterialReadSerializer,
)
class MaterialCreateView(generics.CreateAPIView):
    """
    POST /materials/create/
    multipart/form-data:
      - course_id
      - title
      - description
      - files (repeatable)
    """
    queryset = Material.objects.all()
    serializer_class = MaterialWriteSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # 1) Create the material (no files in serializer)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        material = serializer.save(creator=request.user)

        # 2) Attach files uploaded under key "files"
        uploaded_files = request.FILES.getlist("files")
        if uploaded_files:
            MaterialFile.objects.bulk_create(
                [MaterialFile(material=material, file=f) for f in uploaded_files]
            )

        # 3) Return full data including nested files
        material = (
            Material.objects.select_related("course", "creator")
            .prefetch_related("files")
            .get(pk=material.pk)
        )
        out = MaterialReadSerializer(material, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)


@extend_schema(
    request=inline_serializer(
        name="MaterialUpdateMultipart",
        fields={
            "course_id": drf_serializers.IntegerField(required=False),
            "title": drf_serializers.CharField(required=False),
            "description": drf_serializers.CharField(required=False, allow_blank=True),
            # Optional: allow adding new files when editing (appends, does not remove old)
            "files": drf_serializers.ListField(
                child=drf_serializers.FileField(),
                required=False,
                allow_empty=True,
            ),
        },
    ),
    responses=MaterialReadSerializer,
)
class MaterialUpdateView(generics.UpdateAPIView):
    """
    PUT/PATCH /materials/<id>/edit/
    Can also append new files via files[].
    """
    queryset = Material.objects.select_related("course", "creator").prefetch_related("files")
    serializer_class = MaterialWriteSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        material = self.get_object()

        serializer = self.get_serializer(material, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        material = serializer.save()

        uploaded_files = request.FILES.getlist("files")
        if uploaded_files:
            MaterialFile.objects.bulk_create(
                [MaterialFile(material=material, file=f) for f in uploaded_files]
            )

        material = (
            Material.objects.select_related("course", "creator")
            .prefetch_related("files")
            .get(pk=material.pk)
        )
        out = MaterialReadSerializer(material, context={"request": request}).data
        return Response(out, status=status.HTTP_200_OK)


class MaterialDeleteView(generics.DestroyAPIView):
    """
    DELETE /materials/<id>/delete/
    """
    queryset = Material.objects.all()
    permission_classes = [IsCreatorOrStaffOrReadOnly]
