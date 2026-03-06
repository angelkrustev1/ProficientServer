from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course
from .models import Message, MessageLike
from .permissions import IsCourseMemberOrCreator, IsMessageAuthorOrAdmin
from .serializers import MessageSerializer, MessageCreateSerializer


class CourseMessageListView(generics.ListAPIView):
    """
    Returns all messages for a given course as an array of objects.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsCourseMemberOrCreator]

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs["course_id"])

    def get_queryset(self):
        course = self.get_course()
        return (
            Message.objects
            .filter(course=course)
            .select_related("author", "course")
            .prefetch_related("likes")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class MessageCreateView(generics.CreateAPIView):
    """
    Create a message in a given course.
    """
    serializer_class = MessageCreateSerializer
    permission_classes = [IsAuthenticated, IsCourseMemberOrCreator]

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs["course_id"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["course"] = self.get_course()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()

        output_serializer = MessageSerializer(
            message,
            context={"request": request},
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class MessageDeleteView(generics.DestroyAPIView):
    """
    Delete a message from a course.
    Only the author/admin can delete it.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsCourseMemberOrCreator, IsMessageAuthorOrAdmin]

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs["course_id"])

    def get_queryset(self):
        course = self.get_course()
        return Message.objects.filter(course=course).select_related("author", "course")


class MessageLikeView(APIView):
    """
    Like a message.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(
            Message.objects.select_related("course", "author"),
            pk=message_id,
        )

        user = request.user
        course = message.course

        if not (course.creator_id == user.id or course.members.filter(id=user.id).exists()):
            return Response(
                {"detail": "You do not have access to this course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        like_exists = MessageLike.objects.filter(message=message, user=user).exists()
        if like_exists:
            return Response(
                {
                    "detail": "You have already liked this message.",
                    "likes_count": message.likes.count(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        MessageLike.objects.create(message=message, user=user)

        return Response(
            {
                "detail": "Message liked successfully.",
                "likes_count": message.likes.count(),
            },
            status=status.HTTP_201_CREATED,
        )


class MessageUnlikeView(APIView):
    """
    Unlike a message.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, message_id):
        message = get_object_or_404(
            Message.objects.select_related("course", "author"),
            pk=message_id,
        )

        user = request.user
        course = message.course

        if not (course.creator_id == user.id or course.members.filter(id=user.id).exists()):
            return Response(
                {"detail": "You do not have access to this course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        like = MessageLike.objects.filter(message=message, user=user).first()

        if not like:
            return Response(
                {
                    "detail": "You have not liked this message.",
                    "likes_count": message.likes.count(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        like.delete()

        return Response(
            {
                "detail": "Message unliked successfully.",
                "likes_count": message.likes.count(),
            },
            status=status.HTTP_200_OK,
        )
