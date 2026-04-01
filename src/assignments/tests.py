# assignments/tests.py
import os
import shutil
import tempfile

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


def make_assignment_base(title="Assignment 1"):
    creator = make_user(email=f"{title.lower().replace(' ', '_')}_creator@example.com")
    course = Course.objects.create(
        title="Course 1",
        description="",
        creator=creator,
        creator_code="ASG",
    )
    course.members.add(creator)
    assignment = Assignment.objects.create(
        course=course,
        creator=creator,
        title=title,
        description="desc",
    )
    return creator, course, assignment


def assert_stored_filename_like(testcase: TestCase, stored: str, original: str):
    base, ext = os.path.splitext(original)
    testcase.assertTrue(
        stored.startswith(base),
        msg=f"Expected filename to start with '{base}', got '{stored}'",
    )
    testcase.assertTrue(
        stored.endswith(ext),
        msg=f"Expected filename to end with '{ext}', got '{stored}'",
    )


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AssignmentModelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.creator, self.course, self.assignment = make_assignment_base("HW1")

    def test_assignment_str(self):
        self.assertEqual(str(self.assignment), "HW1 (Course 1)")

    def test_assignment_file_filename_property_and_str(self):
        f = SimpleUploadedFile("task.pdf", b"dummy", content_type="application/pdf")
        af = AssignmentFile.objects.create(assignment=self.assignment, file=f)

        assert_stored_filename_like(self, af.filename, "task.pdf")
        self.assertIn("HW1", str(af))

    def test_submission_mark_submitted_sets_fields(self):
        student = make_user("student_mark@example.com")
        sub = Submission.objects.create(assignment=self.assignment, user=student)

        self.assertFalse(sub.is_submitted)
        self.assertIsNone(sub.submitted_at)

        sub.mark_submitted()
        sub.refresh_from_db()

        self.assertTrue(sub.is_submitted)
        self.assertIsNotNone(sub.submitted_at)

    def test_submission_is_unique_per_assignment_and_user(self):
        student = make_user("student_unique@example.com")

        Submission.objects.create(assignment=self.assignment, user=student)
        with self.assertRaises(IntegrityError):
            Submission.objects.create(assignment=self.assignment, user=student)

    def test_submission_file_filename_and_str(self):
        student = make_user("student_file@example.com")
        sub = Submission.objects.create(assignment=self.assignment, user=student)
        f = SimpleUploadedFile("answer.txt", b"hi", content_type="text/plain")
        sf = SubmissionFile.objects.create(submission=sub, file=f)

        assert_stored_filename_like(self, sf.filename, "answer.txt")
        self.assertIn("HW1", str(sf))


class AssignmentPermissionTests(TestCase):
    def setUp(self):
        self.creator, self.course, self.assignment = make_assignment_base("A1")
        self.other = make_user("other_perm@example.com")
        self.staff = make_user("staff_perm@example.com", is_staff=True)

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

    def test_has_permission_allows_authenticated_user(self):
        req = self.DummyRequest("GET", self.other)
        self.assertTrue(self.perm.has_permission(req, None))

    def test_object_permission_read_allowed_for_authenticated_user(self):
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


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AssignmentSerializerTests(TestCase):
    def setUp(self):
        self.creator, self.course, self.assignment = make_assignment_base("Lecture HW")

    def test_assignment_write_serializer_validates_course_id_exists(self):
        serializer = AssignmentWriteSerializer(
            data={"course_id": self.course.id, "title": "T", "description": ""}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        serializer_invalid = AssignmentWriteSerializer(
            data={"course_id": 999999, "title": "T", "description": ""}
        )
        self.assertFalse(serializer_invalid.is_valid())
        self.assertIn("course_id", serializer_invalid.errors)

    def test_assignment_write_serializer_create(self):
        serializer = AssignmentWriteSerializer(
            data={"course_id": self.course.id, "title": "New", "description": "d"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        obj = serializer.save(creator=self.creator)
        self.assertEqual(obj.course_id, self.course.id)
        self.assertEqual(obj.creator_id, self.creator.id)
        self.assertEqual(obj.title, "New")

    def test_assignment_write_serializer_update(self):
        other_course = Course.objects.create(
            title="Course 2",
            description="",
            creator=self.creator,
            creator_code="UPD",
        )
        other_course.members.add(self.creator)

        serializer = AssignmentWriteSerializer(
            instance=self.assignment,
            data={"course_id": other_course.id, "title": "Updated", "description": "x"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        obj = serializer.save()

        self.assertEqual(obj.course_id, other_course.id)
        self.assertEqual(obj.title, "Updated")

    def test_assignment_file_serializer(self):
        f = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
        af = AssignmentFile.objects.create(assignment=self.assignment, file=f)

        serializer = AssignmentFileSerializer(instance=af, context={})
        assert_stored_filename_like(self, serializer.data["filename"], "a.txt")
        self.assertTrue(serializer.data["file_url"])

    def test_assignment_read_serializer_includes_files(self):
        AssignmentFile.objects.create(
            assignment=self.assignment,
            file=SimpleUploadedFile("a.txt", b"hi", content_type="text/plain"),
        )
        AssignmentFile.objects.create(
            assignment=self.assignment,
            file=SimpleUploadedFile("b.txt", b"hi", content_type="text/plain"),
        )

        serializer = AssignmentReadSerializer(instance=self.assignment)
        self.assertIn("files", serializer.data)
        self.assertEqual(len(serializer.data["files"]), 2)

    def test_submission_read_serializer_includes_files(self):
        student = make_user("student_serializer@example.com")
        sub = Submission.objects.create(assignment=self.assignment, user=student)
        SubmissionFile.objects.create(
            submission=sub,
            file=SimpleUploadedFile("ans.txt", b"hi", content_type="text/plain"),
        )

        serializer = SubmissionReadSerializer(instance=sub)
        self.assertIn("files", serializer.data)
        self.assertEqual(len(serializer.data["files"]), 1)

    def test_submission_file_serializer(self):
        student = make_user("student_serializer2@example.com")
        sub = Submission.objects.create(assignment=self.assignment, user=student)
        sf = SubmissionFile.objects.create(
            submission=sub,
            file=SimpleUploadedFile("ans2.txt", b"hi", content_type="text/plain"),
        )

        serializer = SubmissionFileSerializer(instance=sf, context={})
        assert_stored_filename_like(self, serializer.data["filename"], "ans2.txt")
        self.assertTrue(serializer.data["file_url"])


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AssignmentAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.creator, self.course, self.assignment = make_assignment_base("Initial")
        self.other = make_user("other_api@example.com")
        self.second_student = make_user("second_api@example.com")
        self.staff = make_user("staff_api@example.com", is_staff=True)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_assignment_list_requires_auth(self):
        url = reverse("assignments-list")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_assignment_detail_requires_auth(self):
        url = reverse("assignments-detail", kwargs={"pk": self.assignment.id})
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_assignment_list_returns_data_for_authenticated_user(self):
        self.auth(self.other)
        url = reverse("assignments-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_assignment_detail_returns_data_for_authenticated_user(self):
        self.auth(self.other)
        url = reverse("assignments-detail", kwargs={"pk": self.assignment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.assignment.id)

    def test_assignment_create_with_files(self):
        self.auth(self.creator)
        url = reverse("assignments-create")

        response = self.client.post(
            url,
            {
                "course_id": str(self.course.id),
                "title": "New Assignment",
                "description": "desc",
                "files": [
                    SimpleUploadedFile("one.txt", b"1", content_type="text/plain"),
                    SimpleUploadedFile("two.txt", b"2", content_type="text/plain"),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_assignment = Assignment.objects.get(pk=response.data["id"])
        self.assertEqual(created_assignment.title, "New Assignment")
        self.assertEqual(created_assignment.files.count(), 2)
        self.assertEqual(len(response.data["files"]), 2)

    def test_assignment_update_denied_for_non_creator_non_staff(self):
        self.auth(self.other)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})
        response = self.client.patch(url, {"title": "Nope"}, format="multipart")

        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_assignment_update_allowed_for_creator(self):
        self.auth(self.creator)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})
        response = self.client.patch(url, {"title": "Changed"}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, "Changed")

    def test_assignment_update_allowed_for_staff(self):
        self.auth(self.staff)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})
        response = self.client.patch(url, {"title": "Staff Changed"}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, "Staff Changed")

    def test_assignment_update_can_add_files(self):
        self.auth(self.creator)
        url = reverse("assignments-edit", kwargs={"pk": self.assignment.id})

        response = self.client.patch(
            url,
            {
                "files": [
                    SimpleUploadedFile("extra.txt", b"x", content_type="text/plain"),
                ]
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.files.count(), 1)

    def test_assignment_delete_allowed_for_creator(self):
        self.auth(self.creator)
        url = reverse("assignments-delete", kwargs={"pk": self.assignment.id})
        response = self.client.delete(url)

        self.assertIn(response.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
        self.assertFalse(Assignment.objects.filter(pk=self.assignment.id).exists())

    def test_assignment_delete_allowed_for_staff(self):
        self.auth(self.staff)
        url = reverse("assignments-delete", kwargs={"pk": self.assignment.id})
        response = self.client.delete(url)

        self.assertIn(response.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
        self.assertFalse(Assignment.objects.filter(pk=self.assignment.id).exists())

    def test_submit_assignment_requires_auth(self):
        url = reverse("assignments-submit", kwargs={"assignment_id": self.assignment.id})
        response = self.client.post(
            url,
            {"files": [SimpleUploadedFile("ans.txt", b"hi", content_type="text/plain")]},
            format="multipart",
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_submit_assignment_creates_submission(self):
        self.auth(self.other)
        url = reverse("assignments-submit", kwargs={"assignment_id": self.assignment.id})

        response = self.client.post(
            url,
            {
                "files": [
                    SimpleUploadedFile("ans1.txt", b"hi", content_type="text/plain"),
                    SimpleUploadedFile("ans2.txt", b"hello", content_type="text/plain"),
                ]
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        submission = Submission.objects.get(
            assignment=self.assignment,
            user=self.other,
        )
        self.assertTrue(submission.is_submitted)
        self.assertIsNotNone(submission.submitted_at)
        self.assertEqual(submission.files.count(), 2)

    def test_submit_assignment_without_files_returns_400(self):
        self.auth(self.other)
        url = reverse("assignments-submit", kwargs={"assignment_id": self.assignment.id})

        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resubmit_assignment_overwrites_previous_files(self):
        self.auth(self.other)
        url = reverse("assignments-submit", kwargs={"assignment_id": self.assignment.id})

        first_response = self.client.post(
            url,
            {
                "files": [
                    SimpleUploadedFile("old1.txt", b"old1", content_type="text/plain"),
                    SimpleUploadedFile("old2.txt", b"old2", content_type="text/plain"),
                ]
            },
            format="multipart",
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        first_submission = Submission.objects.get(
            assignment=self.assignment,
            user=self.other,
        )
        first_submission_id = first_submission.id
        self.assertEqual(first_submission.files.count(), 2)

        second_response = self.client.post(
            url,
            {
                "files": [
                    SimpleUploadedFile("new.txt", b"new", content_type="text/plain"),
                ]
            },
            format="multipart",
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        updated_submission = Submission.objects.get(
            assignment=self.assignment,
            user=self.other,
        )
        self.assertEqual(updated_submission.id, first_submission_id)
        self.assertEqual(updated_submission.files.count(), 1)

        stored_name = updated_submission.files.first().filename
        assert_stored_filename_like(self, stored_name, "new.txt")

        self.assertEqual(
            Submission.objects.filter(assignment=self.assignment, user=self.other).count(),
            1,
        )

    def test_assignment_submissions_list_returns_all_submissions(self):
        Submission.objects.create(assignment=self.assignment, user=self.other, is_submitted=True)
        Submission.objects.create(assignment=self.assignment, user=self.second_student, is_submitted=True)

        self.auth(self.creator)
        url = reverse("assignment-submissions-list", kwargs={"assignment_id": self.assignment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_assignment_submissions_list_denied_for_non_creator_non_staff(self):
        Submission.objects.create(assignment=self.assignment, user=self.second_student, is_submitted=True)

        self.auth(self.other)
        url = reverse("assignment-submissions-list", kwargs={"assignment_id": self.assignment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_submission_returns_empty_response_when_missing(self):
        self.auth(self.other)
        url = reverse("assignment-my-submission", kwargs={"assignment_id": self.assignment.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["has_submission"], False)
        self.assertIsNone(response.data["submission"])

    def test_my_submission_returns_existing_submission(self):
        submission = Submission.objects.create(
            assignment=self.assignment,
            user=self.other,
            is_submitted=True,
        )
        SubmissionFile.objects.create(
            submission=submission,
            file=SimpleUploadedFile("mine.txt", b"mine", content_type="text/plain"),
        )

        self.auth(self.other)
        url = reverse("assignment-my-submission", kwargs={"assignment_id": self.assignment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["has_submission"], True)
        self.assertEqual(response.data["submission"]["id"], submission.id)
        self.assertEqual(len(response.data["submission"]["files"]), 1)