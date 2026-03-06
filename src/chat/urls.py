from django.urls import path

from .views import (
    CourseMessageListView,
    MessageCreateView,
    MessageDeleteView,
    MessageLikeView,
    MessageUnlikeView,
)

urlpatterns = [
    path(
        "<int:course_id>/messages/",
        CourseMessageListView.as_view(),
        name="course-message-list",
    ),
    path(
        "<int:course_id>/messages/create/",
        MessageCreateView.as_view(),
        name="message-create",
    ),
    path(
        "<int:course_id>/messages/<int:pk>/delete/",
        MessageDeleteView.as_view(),
        name="message-delete",
    ),
    path(
        "messages/<int:message_id>/like/",
        MessageLikeView.as_view(),
        name="message-like",
    ),
    path(
        "messages/<int:message_id>/unlike/",
        MessageUnlikeView.as_view(),
        name="message-unlike",
    ),
]
