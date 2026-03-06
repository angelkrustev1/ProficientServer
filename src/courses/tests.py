# courses/tests.py
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Course, normalize_creator_code
from .permissions import IsCourseCreatorOrReadOnly
from .serializers import (
    CourseCreateSerializer,
    CourseJoinSerializer,
    CourseListSerializer,
    CourseDetailSerializer,
)

User = get_user_model()


def make_user(email="user@example.com", password="pass12345"):
    return User.objects.create_user(email=email, password=password)


class CourseModelTests(TestCase):
    def test_normalize_creator_code(self):
        self.assertEqual(normalize_creator_code(" math "), "MATH")
        self.assertEqual(normalize_creator_code("bio-1"), "BIO-1")

    def test_creator_code_invalid_chars_raises(self):
        user = make_user("c1@example.com")
        course = Course(
            title="T",
            description="",
            creator=user,
            creator_code="MA TH",  # space not allowed
        )
        with self.assertRaises(ValidationError):
            course.full_clean()

        course.creator_code = "MATH!"
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_creator_code_too_short_raises(self):
        user = make_user("c2@example.com")
        course = Course(
            title="T",
            description="",
            creator=user,
            creator_code="AB",
        )
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_save_generates_join_code_and_normalizes_creator_code(self):
        user = make_user("c3@example.com")

        course = Course.objects.create(
            title="Math",
            description="",
            creator=user,
            creator_code=" math ",
        )

        # normalized
        self.assertEqual(course.creator_code, "MATH")

        # join_code format: CREATORCODE-XXXXXX (6 alnum)
        self.assertTrue(course.join_code.startswith("MATH-"))
        suffix = course.join_code.split("-", 1)[1]
        self.assertEqual(len(suffix), 6)
        self.assertTrue(re.fullmatch(r"[A-Z0-9]{6}", suffix) is not None)

        # unique constraint should exist
        self.assertTrue(Course._meta.get_field("join_code").unique)

    def test_join_code_generated_only_once(self):
        user = make_user("c4@example.com")
        course = Course.objects.create(
            title="Bio",
            description="",
            creator=user,
            creator_code="BIO",
        )
        first = course.join_code
        course.title = "Biology"
        course.save()
        self.assertEqual(course.join_code, first)

    def test_str(self):
        user = make_user("c5@example.com")
        course = Course.objects.create(
            title="Physics",
            description="",
            creator=user,
            creator_code="PHY",
        )
        self.assertIn("Physics", str(course))
        self.assertIn(course.join_code, str(course))


class CoursePermissionTests(TestCase):
    def setUp(self):
        self.creator = make_user("creator@example.com")
        self.other = make_user("other@example.com")
        self.course = Course.objects.create(
            title="Course",
            description="",
            creator=self.creator,
            creator_code="ABC",
        )
        self.permission = IsCourseCreatorOrReadOnly()

        class DummyRequest:
            def __init__(self, method, user):
                self.method = method
                self.user = user

        self.DummyRequest = DummyRequest

    def test_read_only_allowed_for_any_authenticated_user(self):
        req = self.DummyRequest("GET", self.other)
        self.assertTrue(self.permission.has_object_permission(req, None, self.course))

    def test_write_denied_for_non_creator(self):
        req = self.DummyRequest("PATCH", self.other)
        self.assertFalse(self.permission.has_object_permission(req, None, self.course))

    def test_write_allowed_for_creator(self):
        req = self.DummyRequest("PATCH", self.creator)
        self.assertTrue(self.permission.has_object_permission(req, None, self.course))


class CourseSerializerTests(TestCase):
    def setUp(self):
        self.creator = make_user("s_creator@example.com")
        self.member = make_user("s_member@example.com")

        # creator_code must be >= 3 chars
        self.course = Course.objects.create(
            title="Algorithms",
            description="desc",
            creator=self.creator,
            creator_code="CSC",
        )
        self.course.members.add(self.creator, self.member)

    def test_course_join_serializer_normalizes_code(self):
        s = CourseJoinSerializer(data={"code": f"  {self.course.join_code.lower()}  "})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["code"], self.course.join_code)

    def test_course_list_serializer_members_count(self):
        s = CourseListSerializer(instance=self.course)
        self.assertEqual(s.data["members_count"], 2)

    def test_course_detail_serializer_members_list(self):
        s = CourseDetailSerializer(instance=self.course)
        members = s.data["members"]
        self.assertEqual(len(members), 2)
        self.assertIn("id", members[0])
        self.assertIn("email", members[0])

class CourseAPITests(APITestCase):
    """
    Assumes your urls are something like:
      GET    /courses/
      GET    /courses/<id>/
      POST   /courses/create/
      PATCH  /courses/<id>/edit/
      DELETE /courses/<id>/delete/
      POST   /courses/join/
      POST   /courses/<id>/leave/

    If your URL names differ, replace the reverse(...) calls accordingly,
    or switch to hardcoded paths.
    """

    def setUp(self):
        self.creator = make_user("api_creator@example.com")
        self.other = make_user("api_other@example.com")
        self.client = APIClient()

        self.course = Course.objects.create(
            title="API Course",
            description="",
            creator=self.creator,
            creator_code="API",
        )
        self.course.members.add(self.creator)

    # ---- helpers ----
    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_list_requires_auth(self):
        url = "/courses/"
        res = self.client.get(url)
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_list_authenticated_ok(self):
        self.auth(self.creator)
        url = "/courses/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_detail_returns_members_list(self):
        self.auth(self.creator)
        url = f"/courses/{self.course.id}/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("members", res.data)
        self.assertIsInstance(res.data["members"], list)

    def test_create_course_auto_joins_creator(self):
        self.auth(self.creator)
        url = "/courses/create/"
        payload = {"title": "New", "description": "d", "creator_code": "NEW"}
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        created_id = res.data.get("id")  # might not be returned depending on serializer/response
        # Safer: query the latest course by creator/title
        course = Course.objects.get(creator=self.creator, title="New")
        self.assertTrue(course.members.filter(id=self.creator.id).exists())

    def test_update_denied_for_non_creator(self):
        self.auth(self.other)
        url = f"/courses/{self.course.id}/edit/"
        res = self.client.patch(url, {"title": "Hacked"}, format="json")
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_update_allowed_for_creator(self):
        self.auth(self.creator)
        url = f"/courses/{self.course.id}/edit/"
        res = self.client.patch(url, {"title": "Updated"}, format="json")
        self.assertIn(res.status_code, (status.HTTP_200_OK, status.HTTP_202_ACCEPTED))
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Updated")

    def test_delete_denied_for_non_creator(self):
        self.auth(self.other)
        url = f"/courses/{self.course.id}/delete/"
        res = self.client.delete(url)
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_join_invalid_code(self):
        self.auth(self.other)
        url = "/courses/join/"
        res = self.client.post(url, {"code": "INVALID-CODE"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_success(self):
        self.auth(self.other)
        url = "/courses/join/"
        res = self.client.post(url, {"code": self.course.join_code}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(self.course.members.filter(id=self.other.id).exists())

    def test_leave_success_for_member(self):
        self.course.members.add(self.other)

        self.auth(self.other)
        url = f"/courses/{self.course.id}/leave/"
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(self.course.members.filter(id=self.other.id).exists())

    def test_creator_cannot_leave_own_course(self):
        self.auth(self.creator)
        url = f"/courses/{self.course.id}/leave/"
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(self.course.members.filter(id=self.creator.id).exists())
