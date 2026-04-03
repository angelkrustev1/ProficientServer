from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course
from .models import Message, MessageLike

User = get_user_model()


class ChatMessageAPITests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            email="creator@test.com",
            password="pass1234",
        )
        self.member = User.objects.create_user(
            email="member@test.com",
            password="pass1234",
        )
        self.outsider = User.objects.create_user(
            email="outsider@test.com",
            password="pass1234",
        )
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="pass1234",
            is_staff=True,
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            creator=self.creator,
            creator_code="TEST",
        )
        self.course.members.add(self.member)

        self.msg_by_creator = Message.objects.create(
            course=self.course,
            author=self.creator,
            content="Hello from creator",
        )
        self.msg_by_member = Message.objects.create(
            course=self.course,
            author=self.member,
            content="Hello from member",
        )

        self.list_url = reverse(
            "course-message-list",
            kwargs={"course_id": self.course.id},
        )
        self.create_url = reverse(
            "message-create",
            kwargs={"course_id": self.course.id},
        )
        self.delete_creator_msg_url = reverse(
            "message-delete",
            kwargs={"course_id": self.course.id, "pk": self.msg_by_creator.id},
        )
        self.like_creator_msg_url = reverse(
            "message-like",
            kwargs={"message_id": self.msg_by_creator.id},
        )
        self.unlike_creator_msg_url = reverse(
            "message-unlike",
            kwargs={"message_id": self.msg_by_creator.id},
        )

    # --------- LIST MESSAGES ---------

    def test_list_messages_creator_allowed_returns_array(self):
        self.client.force_authenticate(user=self.creator)
        res = self.client.get(self.list_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)
        self.assertGreaterEqual(len(res.data), 2)

        first = res.data[0]
        self.assertIn("id", first)
        self.assertIn("content", first)
        self.assertIn("likes_count", first)
        self.assertIn("liked_by_me", first)
        self.assertIn("author_email", first)
        self.assertIn("course", first)

    def test_list_messages_member_allowed(self):
        self.client.force_authenticate(user=self.member)
        res = self.client.get(self.list_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)

    def test_list_messages_outsider_forbidden(self):
        self.client.force_authenticate(user=self.outsider)
        res = self.client.get(self.list_url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_messages_admin_allowed(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(self.list_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)

    def test_list_messages_liked_by_me_is_true_when_user_liked_message(self):
        MessageLike.objects.create(message=self.msg_by_creator, user=self.member)

        self.client.force_authenticate(user=self.member)
        res = self.client.get(self.list_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        creator_message = next(
            item for item in res.data if item["id"] == self.msg_by_creator.id
        )
        self.assertTrue(creator_message["liked_by_me"])

    # --------- CREATE MESSAGE ---------

    def test_create_message_creator_allowed(self):
        self.client.force_authenticate(user=self.creator)
        res = self.client.post(
            self.create_url,
            {"content": "New message"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["content"], "New message")
        self.assertEqual(res.data["course"], self.course.id)
        self.assertEqual(res.data["author_email"], self.creator.email)

        self.assertTrue(
            Message.objects.filter(
                course=self.course,
                author=self.creator,
                content="New message",
            ).exists()
        )

    def test_create_message_member_allowed(self):
        self.client.force_authenticate(user=self.member)
        res = self.client.post(
            self.create_url,
            {"content": "Member message"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["author_email"], self.member.email)

    def test_create_message_admin_allowed(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            self.create_url,
            {"content": "Admin message"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["author_email"], self.admin.email)

    def test_create_message_outsider_forbidden(self):
        self.client.force_authenticate(user=self.outsider)
        res = self.client.post(
            self.create_url,
            {"content": "Should fail"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --------- DELETE MESSAGE ---------

    def test_delete_message_author_allowed(self):
        self.client.force_authenticate(user=self.creator)
        res = self.client.delete(self.delete_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Message.objects.filter(id=self.msg_by_creator.id).exists())

    def test_delete_message_non_author_forbidden_even_if_in_course(self):
        self.client.force_authenticate(user=self.member)
        res = self.client.delete(self.delete_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Message.objects.filter(id=self.msg_by_creator.id).exists())

    def test_delete_message_admin_allowed(self):
        msg = Message.objects.create(
            course=self.course,
            author=self.creator,
            content="To be deleted by admin",
        )
        url = reverse(
            "message-delete",
            kwargs={"course_id": self.course.id, "pk": msg.id},
        )

        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Message.objects.filter(id=msg.id).exists())

    def test_delete_message_outsider_forbidden(self):
        self.client.force_authenticate(user=self.outsider)
        res = self.client.delete(self.delete_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --------- LIKE / UNLIKE ---------

    def test_like_message_creator_allowed(self):
        self.client.force_authenticate(user=self.creator)
        res = self.client.post(self.like_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            MessageLike.objects.filter(
                message=self.msg_by_creator,
                user=self.creator,
            ).exists()
        )
        self.assertEqual(res.data["likes_count"], 1)

    def test_like_message_member_allowed(self):
        self.client.force_authenticate(user=self.member)
        res = self.client.post(self.like_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            MessageLike.objects.filter(
                message=self.msg_by_creator,
                user=self.member,
            ).exists()
        )

    def test_like_message_admin_allowed(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(self.like_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            MessageLike.objects.filter(
                message=self.msg_by_creator,
                user=self.admin,
            ).exists()
        )

    def test_like_message_twice_returns_400(self):
        self.client.force_authenticate(user=self.creator)

        res1 = self.client.post(self.like_creator_msg_url)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(self.like_creator_msg_url)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like_message_outsider_forbidden(self):
        self.client.force_authenticate(user=self.outsider)
        res = self.client.post(self.like_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unlike_message_after_like_works(self):
        self.client.force_authenticate(user=self.creator)

        like_res = self.client.post(self.like_creator_msg_url)
        self.assertEqual(like_res.status_code, status.HTTP_201_CREATED)

        unlike_res = self.client.delete(self.unlike_creator_msg_url)
        self.assertEqual(unlike_res.status_code, status.HTTP_200_OK)
        self.assertEqual(unlike_res.data["likes_count"], 0)

        self.assertFalse(
            MessageLike.objects.filter(
                message=self.msg_by_creator,
                user=self.creator,
            ).exists()
        )

    def test_unlike_without_like_returns_400(self):
        self.client.force_authenticate(user=self.creator)

        res = self.client.delete(self.unlike_creator_msg_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unlike_outsider_forbidden(self):
        self.client.force_authenticate(user=self.outsider)
        res = self.client.delete(self.unlike_creator_msg_url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --------- ORDERING / BASIC INTEGRITY ---------

    def test_messages_are_returned_newest_first(self):
        newer_message = Message.objects.create(
            course=self.course,
            author=self.creator,
            content="Newest message",
        )

        self.client.force_authenticate(user=self.creator)
        res = self.client.get(self.list_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 3)
        self.assertEqual(res.data[0]["id"], newer_message.id)
