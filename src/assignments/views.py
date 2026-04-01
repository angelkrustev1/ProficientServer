from django.db import transaction
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers

from .models import Assignment, AssignmentFile, Submission, SubmissionFile
from .serializers import (
    AssignmentReadSerializer,
    AssignmentWriteSerializer,
    SubmissionReadSerializer,
)
from .permissions import IsCreatorOrStaffOrReadOnly


class AssignmentListView(generics.ListAPIView):
    serializer_class = AssignmentReadSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]

    def get_queryset(self):
        queryset = Assignment.objects.select_related("course", "creator").prefetch_related("files")

        course_id = self.request.query_params.get("course_id")
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset.order_by("-created_at")


class AssignmentDetailView(generics.RetrieveAPIView):
    queryset = Assignment.objects.select_related("course", "creator").prefetch_related("files")
    serializer_class = AssignmentReadSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]


@extend_schema(
    request=inline_serializer(
        name="AssignmentCreateMultipart",
        fields={
            "course_id": drf_serializers.IntegerField(),
            "title": drf_serializers.CharField(),
            "description": drf_serializers.CharField(required=False, allow_blank=True),
            "files": drf_serializers.ListField(
                child=drf_serializers.FileField(),
                required=False,
                allow_empty=True,
            ),
        },
    )
)
class AssignmentCreateView(generics.CreateAPIView):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentWriteSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(creator=request.user)

        uploaded_files = request.FILES.getlist("files")
        if uploaded_files:
            AssignmentFile.objects.bulk_create(
                [AssignmentFile(assignment=assignment, file=f) for f in uploaded_files]
            )

        assignment = (
            Assignment.objects.select_related("course", "creator")
            .prefetch_related("files")
            .get(pk=assignment.pk)
        )

        return Response(
            AssignmentReadSerializer(assignment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AssignmentUpdateView(generics.UpdateAPIView):
    queryset = Assignment.objects.select_related("course", "creator").prefetch_related("files")
    serializer_class = AssignmentWriteSerializer
    permission_classes = [IsCreatorOrStaffOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        assignment = self.get_object()

        serializer = self.get_serializer(
            assignment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()

        uploaded_files = request.FILES.getlist("files")
        if uploaded_files:
            AssignmentFile.objects.bulk_create(
                [AssignmentFile(assignment=assignment, file=f) for f in uploaded_files]
            )

        assignment = (
            Assignment.objects.select_related("course", "creator")
            .prefetch_related("files")
            .get(pk=assignment.pk)
        )

        return Response(
            AssignmentReadSerializer(assignment, context={"request": request}).data
        )


class AssignmentDeleteView(generics.DestroyAPIView):
    queryset = Assignment.objects.all()
    permission_classes = [IsCreatorOrStaffOrReadOnly]


@extend_schema(
    request=inline_serializer(
        name="SubmitAssignmentMultipart",
        fields={
            "files": drf_serializers.ListField(
                child=drf_serializers.FileField(),
                required=True,
            )
        },
    )
)
class SubmitAssignmentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        assignment = get_object_or_404(Assignment, pk=kwargs["assignment_id"])

        submission, created = Submission.objects.get_or_create(
            assignment=assignment,
            user=request.user,
        )

        if submission.is_submitted:
            return Response(
                {"detail": "You already submitted this assignment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"detail": "Please attach at least one file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        SubmissionFile.objects.bulk_create(
            [SubmissionFile(submission=submission, file=f) for f in files]
        )

        submission.mark_submitted()

        submission = Submission.objects.prefetch_related("files").get(pk=submission.pk)

        return Response(
            SubmissionReadSerializer(submission, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
