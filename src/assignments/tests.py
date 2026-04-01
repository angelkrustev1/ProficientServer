# assignments/tests.py
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from courses.models import Course
from .models import Assignment, AssignmentFile, Submission, SubmissionFile
from .permissions import IsCreatorOrStaffOrReadOnly
from .serializers import (
    AssignmentWriteSerializer,
    AssignmentReadSerializer,
    AssignmentFileSerializer,
    SubmissionReadSerializer,
    SubmissionFileSerializer,
)

User = get_user_model()


def make_user(email="user@example.com", password="pass12345", is_staff=False):
    return User.objects.create_user(email=email, password=password, is_staff=is_staff)


def make_course(creator, creator_code="CRS"):
    course = Course.objects.create(
        title="Course 1",
        description="",
        creator=creator,
        creator_code=creator_code,
    )
    course.members.add(creator)
    return course


def assert_stored_filename_like(testcase: TestCase, stored: str, original: str):
    """
    Your storage may rename files: 'task.pdf' -> 'task_XYZ.pdf'.
    We only assert prefix and extension match.
    """
    base, ext = os.path.splitext(original)
    testcase.assertTrue(
        stored.startswith(base),
        msg=f"Expected filename to start with '{base}', got '{stored}'",
    )
    testcase.assertTrue(
        stored.endswith(ext),
        msg=f"Expected filename to end with '{ext}', got '{stored}'",
    )


@override_settings(MEDIA_ROOT=os.path.join(getattr(settings, "BASE_DIR", ""), "test_media"))
class AssignmentModelTests(TestCase):
    def setUp(self):
        self.creator = make_user("creator_a@example.com")
        self.course = make_course(self.creator, creator_code="ASG")

    def test_assignment_str(self):
        a = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="HW1",
            description="",
        )
        self.assertEqual(str(a), "HW1 (Course 1)")

    def test_assignment_file_filename_property_and_str(self):
        a = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="HW1",
            description="",
        )
        f = SimpleUploadedFile("task.pdf", b"dummy", content_type="application/pdf")
        af = AssignmentFile.objects.create(assignment=a, file=f)

        assert_stored_filename_like(self, af.filename, "task.pdf")
        self.assertIn("HW1", str(af))

    def test_submission_mark_submitted_sets_fields(self):
        a = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="HW1",
            description="",
        )
        student = make_user("student_a@example.com")
        sub = Submission.objects.create(assignment=a, user=student)

        self.assertFalse(sub.is_submitted)
        self.assertIsNone(sub.submitted_at)

        sub.mark_submitted()
        sub.refresh_from_db()

        self.assertTrue(sub.is_submitted)
        self.assertIsNotNone(sub.submitted_at)

    def test_unique_submission_constraint(self):
        a = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="HW1",
            description="",
        )
        student = make_user("student_unique@example.com")

        Submission.objects.create(assignment=a, user=student)
        with self.assertRaises(IntegrityError):
            Submission.objects.create(assignment=a, user=student)

    def test_submission_file_filename_and_str(self):
        a = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="HW1",
            description="",
        )
        student = make_user("student_file@example.com")
        sub = Submission.objects.create(assignment=a, user=student)
        f = SimpleUploadedFile("answer.txt", b"hi", content_type="text/plain")
        sf = SubmissionFile.objects.create(submission=sub, file=f)

        assert_stored_filename_like(self, sf.filename, "answer.txt")
        self.assertIn("HW1", str(sf))


class AssignmentPermissionTests(TestCase):
    def setUp(self):
        self.creator = make_user("p_creator_a@example.com")
        self.other = make_user("p_other_a@example.com")
        self.staff = make_user("p_staff_a@example.com", is_staff=True)

        self.course = make_course(self.creator, creator_code="PER")
        self.assignment = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="A1",
            description="",
        )

        self.perm = IsCreatorOrStaffOrReadOnly()

        class DummyRequest:
            def __init__(self, method, user):
                self.method = method
                self.user = user

        self.DummyRequest = DummyRequest

    def test_has_permission_denies_safe_methods_for_anonymous(self):
        class Anonymous:
            is_authenticated = False
            is_staff = False
            id = None

        req = self.DummyRequest("GET", Anonymous())
        self.assertFalse(self.perm.has_permission(req, None))

    def test_has_permission_denies_write_for_anonymous(self):
        class Anonymous:
            is_authenticated = False
            is_staff = False
            id = None

        req = self.DummyRequest("POST", Anonymous())
        self.assertFalse(self.perm.has_permission(req, None))

    def test_has_permission_allows_safe_methods_for_authenticated_user(self):
        req = self.DummyRequest("GET", self.other)
        self.assertTrue(self.perm.has_permission(req, None))

    def test_object_permission_read_allowed(self):
        req = self.DummyRequest("GET", self.other)
        self.assertTrue(self.perm.has_object_permission(req, None, self.assignment))

    def test_object_permission_write_denied_for_non_creator_non_staff(self):
        req = self.DummyRequest("PATCH", self.other)
        self.assertFalse(self.perm.has_object_permission(req, None, self.assignment))

    def test_object_permission_write_allowed_for_creator(self):
        req = self.DummyRequest("PATCH", self.creator)
        self.assertTrue(self.perm.has_object_permission(req, None, self.assignment))

    def test_object_permission_write_allowed_for_staff(self):
        req = self.DummyRequest("PATCH", self.staff)
        self.assertTrue(self.perm.has_object_permission(req, None, self.assignment))


@override_settings(MEDIA_ROOT=os.path.join(getattr(settings, "BASE_DIR", ""), "test_media"))
class AssignmentSerializerTests(TestCase):
    def setUp(self):
        self.creator = make_user("s_creator_a@example.com")
        self.course = make_course(self.creator, creator_code="SER")

        self.assignment = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="Lecture HW",
            description="desc",
        )

    def test_assignment_write_serializer_validates_course_id_exists(self):
        s = AssignmentWriteSerializer(data={"course_id": self.course.id, "title": "T", "description": ""})
        self.assertTrue(s.is_valid(), s.errors)

        s2 = AssignmentWriteSerializer(data={"course_id": 999999, "title": "T", "description": ""})
        self.assertFalse(s2.is_valid())
        self.assertIn("course_id", s2.errors)

    def test_assignment_write_serializer_create(self):
        s = AssignmentWriteSerializer(data={"course_id": self.course.id, "title": "New", "description": "d"})
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save(creator=self.creator)
        self.assertEqual(obj.course_id, self.course.id)
        self.assertEqual(obj.creator_id, self.creator.id)
        self.assertEqual(obj.title, "New")

    def test_assignment_write_serializer_update_can_change_course(self):
        other_course = make_course(self.creator, creator_code="S02")
        s = AssignmentWriteSerializer(
            instance=self.assignment,
            data={"course_id": other_course.id, "title": "Updated", "description": "x"},
            partial=True,
        )
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertEqual(obj.course_id, other_course.id)
        self.assertEqual(obj.title, "Updated")

    def test_assignment_file_serializer_filename_and_url_without_request(self):
        f = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
        af = AssignmentFile.objects.create(assignment=self.assignment, file=f)

        s = AssignmentFileSerializer(instance=af, context={})
        assert_stored_filename_like(self, s.data["filename"], "a.txt")
        self.assertTrue(s.data["file_url"])

    def test_assignment_read_serializer_includes_nested_files(self):
        f1 = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
        f2 = SimpleUploadedFile("b.txt", b"hi", content_type="text/plain")
        AssignmentFile.objects.create(assignment=self.assignment, file=f1)
        AssignmentFile.objects.create(assignment=self.assignment, file=f2)

        s = AssignmentReadSerializer(instance=self.assignment)
        self.assertIn("files", s.data)
        self.assertEqual(len(s.data["files"]), 2)

    def test_submission_read_serializer_includes_nested_files(self):
        student = make_user("student_ser@example.com")
        sub = Submission.objects.create(assignment=self.assignment, user=student)
        f1 = SimpleUploadedFile("ans.txt", b"hi", content_type="text/plain")
        SubmissionFile.objects.create(submission=sub, file=f1)

        s = SubmissionReadSerializer(instance=sub)
        self.assertIn("files", s.data)
        self.assertEqual(len(s.data["files"]), 1)

    def test_submission_file_serializer_filename_and_url_without_request(self):
        student = make_user("student_ser2@example.com")
        sub = Submission.objects.create(assignment=self.assignment, user=student)
        f = SimpleUploadedFile("ans2.txt", b"hi", content_type="text/plain")
        sf = SubmissionFile.objects.create(submission=sub, file=f)

        s = SubmissionFileSerializer(instance=sf, context={})
        assert_stored_filename_like(self, s.data["filename"], "ans2.txt")
        self.assertTrue(s.data["file_url"])


@override_settings(MEDIA_ROOT=os.path.join(getattr(settings, "BASE_DIR", ""), "test_media"))
class AssignmentAPITests(APITestCase):
    """
    Uses reverse() with your URL names:
      - assignments-list
      - assignments-create
      - assignments-detail
      - assignments-edit
      - assignments-delete
      - assignments-submit
    """

    def setUp(self):
        self.client = APIClient()

        self.creator = make_user("api_asg_creator@example.com")
        self.other = make_user("api_asg_other@example.com")
        self.staff = make_user("api_asg_staff@example.com", is_staff=True)

        self.course = make_course(self.creator, creator_code="API")

        self.assignment = Assignment.objects.create(
            course=self.course,
            creator=self.creator,
            title="Initial",
            description="",
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_list_requires_auth(self):
        url = reverse("assignments-list")
        res = self.client.get(url)
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_detail_requires_auth(self):
        url = reverse("assignments-detail", kwargs={"pk": self.assignment.id})
        res = self.client.get(url)
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_list_allows_authenticated_user(self):
        self.auth(self.other)
        url = reverse("assignments-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_detail_allows_authenticated_user(self):
        self.auth(self.other)
        url = reverse("assignments-detail", kwargs={"pk": self.assignment.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_requires_auth(self):
        url = reverse("assignments-create")
        res = self.client.post(
            url,
            {"course_id": self.course.id, "title": "T"},
            format="multipart",
        )
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_with_files_creates_assignment_and_files(self):
        self.auth(self.creator)
        url = reverse("assignments-create")

        f1 = SimpleUploadedFile("one.txt", b"1", content_type="text/plain")
        f2 = SimpleUploadedFile("two.txt", b"2", content_type="text/plain")

        data = {
            "course_id": str(self.course.id),
            "title": "New Assignment",
            "description": "d",
            "files": [f1, f2],
        }
        res = self.client.post(url, data, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        a_id = res.data["id"]
        a = Assignment.objects.get(pk=a_id)
        self.assertEqual(a.creator_id, self.creator.id)
        self.assertEqual(a.course_id, self.course.id)

        self.assertEqual(a.files.count(), 2)
        filenames = sorted([x.filename for x in a.files.all()])
        self.assertEqual(len(filenames), 2)
        self.assertTrue(filenames[0].endswith(".txt"))
        self.assertTrue(filenames[1].endswith(".txt"))

        self.assertIn("files", res.data)
        self.assertEqual(len(res.data["files"]), 2)

    def test_update_denied_for_non_creator_non_staff(self):
        self.auth(self.other)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})
        res = self.client.patch(url, {"title": "Nope"}, format="multipart")
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_update_allowed_for_creator(self):
        self.auth(self.creator)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})
        res = self.client.patch(url, {"title": "Changed"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, "Changed")

    def test_update_allowed_for_staff(self):
        self.auth(self.staff)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})
        res = self.client.patch(url, {"title": "StaffChanged"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, "StaffChanged")

    def test_update_can_append_files(self):
        self.auth(self.creator)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})
        f1 = SimpleUploadedFile("add.txt", b"x", content_type="text/plain")

        res = self.client.patch(url, {"files": [f1]}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.files.count(), 1)
        self.assertTrue(self.assignment.files.first().filename.endswith(".txt"))

    def test_delete_denied_for_non_creator_non_staff(self):
        self.auth(self.other)
        url = reverse("assignments-delete", kwargs={"pk": self.assignment.id})
        res = self.client.delete(url)
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_delete_allowed_for_creator(self):
        self.auth(self.creator)
        url = reverse("assignments-delete", kwargs={"pk": self.assignment.id})
        res = self.client.delete(url)
        self.assertIn(res.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
        self.assertFalse(Assignment.objects.filter(id=self.assignment.id).exists())

    def test_delete_allowed_for_staff(self):
        a = Assignment.objects.create(course=self.course, creator=self.creator, title="ToDel", description="")
        self.auth(self.staff)
        url = reverse("assignments-delete", kwargs={"pk": a.id})
        res = self.client.delete(url)
        self.assertIn(res.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
        self.assertFalse(Assignment.objects.filter(id=a.id).exists())

    def test_submit_requires_auth(self):
        url = reverse("assignments-submit", kwargs={"assignment_id": self.assignment.id})
        res = self.client.post(
            url,
            {"files": [SimpleUploadedFile("ans.txt", b"hi")]},
            format="multipart",
        )
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_submit_creates_submission_files_and_marks_submitted(self):
        student = self.other
        self.auth(student)

        url = reverse("assignments-submit", kwargs={"assignment_id": self.assignment.id})
        f1 = SimpleUploadedFile("ans1.txt", b"hi", content_type="text/plain")
        f2 = SimpleUploadedFile("ans2.txt", b"hi", content_type="text/plain")

        res = self.client.post(url, {"files": [f1, f2]}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        sub = Submission.objects.get(assignment=self.assignment, user=student)
        self.assertTrue(sub.is_submitted)
        self.assertIsNotNone(sub.submitted_at)
        self.assertEqual(sub.files.count(), 2)

        self.assertIn("files", res.data)
        self.assertEqual(len(res.data["files"]), 2)

    def test_submit_twice_returns_400(self):
        student = self.other
        self.auth(student)

        url = reverse("assignments-submit", kwargs={"assignment_id": self.assignment.id})

        res1 = self.client.post(
            url,
            {"files": [SimpleUploadedFile("ans1.txt", b"hi", content_type="text/plain")]},
            format="multipart",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(
            url,
            {"files": [SimpleUploadedFile("ans2.txt", b"hi", content_type="text/plain")]},
            format="multipart",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
