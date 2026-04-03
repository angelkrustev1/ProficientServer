from django.urls import path

from .consumers import CourseChatConsumer

websocket_urlpatterns = [
    path("ws/courses/<int:course_id>/chat/", CourseChatConsumer.as_asgi()),
]
