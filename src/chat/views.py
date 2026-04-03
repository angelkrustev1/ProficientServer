from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course
from .models import Message, MessageLike
from .permissions import IsCourseMemberOrCreator, IsMessageAuthorOrAdmin
from .serializers import (
    MessageSerializer,
    MessageCreateSerializer,
    serialize_message_for_socket,
)


def broadcast_course_chat_event(course_id, payload):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"course_chat_{course_id}",
        {
            "type": "chat.event",
            "payload": payload,
        },
    )


class CourseMessageListView(generics.ListAPIView):
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

        broadcast_course_chat_event(
            message.course_id,
            {
                "type": "message_created",
                "message": serialize_message_for_socket(message),
            },
        )

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class MessageDeleteView(generics.DestroyAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsCourseMemberOrCreator, IsMessageAuthorOrAdmin]

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs["course_id"])

    def get_queryset(self):
        course = self.get_course()
        return Message.objects.filter(course=course).select_related("author", "course")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        course_id = instance.course_id
        message_id = instance.id

        self.perform_destroy(instance)

        broadcast_course_chat_event(
            course_id,
            {
                "type": "message_deleted",
                "message_id": message_id,
            },
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(
            Message.objects.select_related("course", "author"),
            pk=message_id,
        )

        user = request.user
        course = message.course

        if not (
            user.is_staff
            or user.has_perm("accounts.can_administer_profiles")
            or course.creator_id == user.id
            or course.members.filter(id=user.id).exists()
        ):
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
        likes_count = message.likes.count()

        broadcast_course_chat_event(
            message.course_id,
            {
                "type": "message_reaction_updated",
                "message_id": message.id,
                "likes_count": likes_count,
                "acted_by_email": user.email,
                "liked": True,
            },
        )

        return Response(
            {
                "detail": "Message liked successfully.",
                "likes_count": likes_count,
            },
            status=status.HTTP_201_CREATED,
        )


class MessageUnlikeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, message_id):
        message = get_object_or_404(
            Message.objects.select_related("course", "author"),
            pk=message_id,
        )

        user = request.user
        course = message.course

        if not (
            user.is_staff
            or user.has_perm("accounts.can_administer_profiles")
            or course.creator_id == user.id
            or course.members.filter(id=user.id).exists()
        ):
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
        likes_count = message.likes.count()

        broadcast_course_chat_event(
            message.course_id,
            {
                "type": "message_reaction_updated",
                "message_id": message.id,
                "likes_count": likes_count,
                "acted_by_email": user.email,
                "liked": False,
            },
        )

        return Response(
            {
                "detail": "Message unliked successfully.",
                "likes_count": likes_count,
            },
            status=status.HTTP_200_OK,
        )
