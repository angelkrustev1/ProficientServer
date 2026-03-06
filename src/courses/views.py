from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Course
from .serializers import (
    CourseListSerializer,
    CourseDetailSerializer,
    CourseCreateSerializer,
    CourseUpdateSerializer,
    CourseJoinSerializer,
)
from .permissions import IsCourseCreatorOrReadOnly


class CourseListView(generics.ListAPIView):
    """
    GET /courses/ -> all courses
    """
    queryset = Course.objects.select_related("creator").all().order_by("-created_at")
    serializer_class = CourseListSerializer
    permission_classes = (permissions.IsAuthenticated,)


class CourseDetailView(generics.RetrieveAPIView):
    """
    GET /courses/<id>/ -> course by id + members list
    """
    queryset = Course.objects.select_related("creator").prefetch_related("members").all()
    serializer_class = CourseDetailSerializer
    permission_classes = (permissions.IsAuthenticated,)


class CourseCreateView(generics.CreateAPIView):
    """
    POST /courses/create/ -> create course (creator = request.user)
    """
    queryset = Course.objects.all()
    serializer_class = CourseCreateSerializer
    permission_classes = (permissions.IsAuthenticated,)


class CourseUpdateView(generics.UpdateAPIView):
    """
    PUT/PATCH /courses/<id>/edit/ -> edit (creator only)
    """
    queryset = Course.objects.all()
    serializer_class = CourseUpdateSerializer
    permission_classes = (permissions.IsAuthenticated, IsCourseCreatorOrReadOnly)


class CourseDeleteView(generics.DestroyAPIView):
    """
    DELETE /courses/<id>/delete/ -> delete (creator only)
    """
    queryset = Course.objects.all()
    permission_classes = (permissions.IsAuthenticated, IsCourseCreatorOrReadOnly)


class CourseJoinView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CourseJoinSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]

        try:
            course = Course.objects.get(join_code=code)
        except Course.DoesNotExist:
            return Response(
                {"detail": "Invalid join code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            course.members.add(request.user)

        return Response(
            {"detail": "Joined course successfully."},
            status=status.HTTP_200_OK,
        )

class CourseLeaveView(APIView):
    """
    POST /courses/<id>/leave/
    Removes the authenticated user from course.members
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk: int):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response(
                {"detail": "Course not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent creator from leaving their own course
        if course.creator_id == request.user.id:
            return Response(
                {"detail": "The creator cannot leave their own course."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove user from members
        course.members.remove(request.user)

        return Response(
            {"detail": "Left course successfully."},
            status=status.HTTP_200_OK,
        )
