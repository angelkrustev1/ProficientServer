from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from courses.models import Course


@database_sync_to_async
def user_has_course_access(user, course_id):
    if not user or not user.is_authenticated:
        return False

    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return False

    if user.is_staff or user.has_perm("accounts.can_administer_profiles"):
        return True

    if course.creator_id == user.id:
        return True

    return course.members.filter(id=user.id).exists()


class CourseChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.course_id = self.scope["url_route"]["kwargs"]["course_id"]
        self.group_name = f"course_chat_{self.course_id}"
        self.user = self.scope.get("user")

        allowed = await user_has_course_access(self.user, self.course_id)

        if not allowed:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send_json({
            "type": "connection_established",
            "course_id": int(self.course_id),
        })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Kept intentionally minimal.
        # REST still handles create/delete/like/unlike.
        # This socket is used for real-time push updates.
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def chat_event(self, event):
        await self.send_json(event["payload"])
