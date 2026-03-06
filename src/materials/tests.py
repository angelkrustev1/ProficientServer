# materials/tests.py
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from courses.models import Course
from .models import Material, MaterialFile
from .permissions import IsCreatorOrStaffOrReadOnly
from .serializers import MaterialWriteSerializer, MaterialReadSerializer, MaterialFileSerializer

User = get_user_model()


def make_user(email="user@example.com", password="pass12345", is_staff=False):
    return User.objects.create_user(email=email, password=password, is_staff=is_staff)


def make_course(creator, creator_code="MAT"):
    course = Course.objects.create(
        title="Course 1",
        description="",
        creator=creator,
        creator_code=creator_code,  # must be >= 3
    )
    course.members.add(creator)
    return course


def assert_stored_filename_like(testcase: TestCase, stored: str, original: str):
    """
    Storage may rename files: 'a.txt' -> 'a_XXXX.txt'.
    Assert only prefix + extension.
    """
    base, ext = os.path.splitext(original)
    testcase.assertTrue(stored.startswith(base), f"Expected '{stored}' to start with '{base}'")
    testcase.assertTrue(stored.endswith(ext), f"Expected '{stored}' to end with '{ext}'")


@override_settings(MEDIA_ROOT=os.path.join(getattr(settings, "BASE_DIR", ""), "test_media"))
class MaterialModelTests(TestCase):
    def setUp(self):
        self.creator = make_user("creator_m@example.com")
        self.course = make_course(self.creator, creator_code="MAT")

    def test_material_str(self):
        m = Material.objects.create(
            course=self.course,
            creator=self.creator,
            title="Lecture 1",
            description="",
        )
        self.assertEqual(str(m), "Lecture 1 (Course 1)")

    def test_material_file_filename_property_and_str(self):
        m = Material.objects.create(
            course=self.course,
            creator=self.creator,
            title="Lecture 1",
            description="",
        )
        f = SimpleUploadedFile("notes.pdf", b"dummy", content_type="application/pdf")
        mf = MaterialFile.objects.create(material=m, file=f)

        assert_stored_filename_like(self, mf.filename, "notes.pdf")
        self.assertIn("Lecture 1", str(mf))


class MaterialPermissionTests(TestCase):
    def setUp(self):
        self.creator = make_user("p_creator@example.com")
        self.other = make_user("p_other@example.com")
        self.staff = make_user("p_staff@example.com", is_staff=True)

        self.course = make_course(self.creator, creator_code="PER")
        self.material = Material.objects.create(
            course=self.course,
            creator=self.creator,
            title="M1",
            description="",
        )
        self.perm = IsCreatorOrStaffOrReadOnly()

        class DummyRequest:
            def __init__(self, method, user):
                self.method = method
                self.user = user

        self.DummyRequest = DummyRequest

    def test_has_permission_allows_safe_methods_for_anonymous(self):
        class Anonymous:
            is_authenticated = False
            is_staff = False
            id = None

        req = self.DummyRequest("GET", Anonymous())
        self.assertTrue(self.perm.has_permission(req, None))

    def test_has_permission_denies_write_for_anonymous(self):
        class Anonymous:
            is_authenticated = False
            is_staff = False
            id = None

        req = self.DummyRequest("POST", Anonymous())
        self.assertFalse(self.perm.has_permission(req, None))

    def test_object_permission_read_allowed(self):
        req = self.DummyRequest("GET", self.other)
        self.assertTrue(self.perm.has_object_permission(req, None, self.material))

    def test_object_permission_write_denied_for_non_creator_non_staff(self):
        req = self.DummyRequest("PATCH", self.other)
        self.assertFalse(self.perm.has_object_permission(req, None, self.material))

    def test_object_permission_write_allowed_for_creator(self):
        req = self.DummyRequest("PATCH", self.creator)
        self.assertTrue(self.perm.has_object_permission(req, None, self.material))

    def test_object_permission_write_allowed_for_staff(self):
        req = self.DummyRequest("PATCH", self.staff)
        self.assertTrue(self.perm.has_object_permission(req, None, self.material))


@override_settings(MEDIA_ROOT=os.path.join(getattr(settings, "BASE_DIR", ""), "test_media"))
class MaterialSerializerTests(TestCase):
    def setUp(self):
        self.creator = make_user("s_creator_m@example.com")
        self.course = make_course(self.creator, creator_code="SER")

        self.material = Material.objects.create(
            course=self.course,
            creator=self.creator,
            title="Lecture",
            description="desc",
        )

    def test_write_serializer_validates_course_id_exists(self):
        s = MaterialWriteSerializer(data={"course_id": self.course.id, "title": "T", "description": ""})
        self.assertTrue(s.is_valid(), s.errors)

        s2 = MaterialWriteSerializer(data={"course_id": 999999, "title": "T", "description": ""})
        self.assertFalse(s2.is_valid())
        self.assertIn("course_id", s2.errors)

    def test_write_serializer_create_sets_course(self):
        s = MaterialWriteSerializer(data={"course_id": self.course.id, "title": "New", "description": "d"})
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save(creator=self.creator)
        self.assertEqual(obj.course_id, self.course.id)
        self.assertEqual(obj.creator_id, self.creator.id)
        self.assertEqual(obj.title, "New")

    def test_write_serializer_update_can_change_course(self):
        other_course = make_course(self.creator, creator_code="S02")
        s = MaterialWriteSerializer(
            instance=self.material,
            data={"course_id": other_course.id, "title": "Updated", "description": "x"},
            partial=True,
        )
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertEqual(obj.course_id, other_course.id)
        self.assertEqual(obj.title, "Updated")

    def test_file_serializer_filename_and_url_without_request(self):
        f = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
        mf = MaterialFile.objects.create(material=self.material, file=f)

        s = MaterialFileSerializer(instance=mf, context={})
        assert_stored_filename_like(self, s.data["filename"], "a.txt")
        self.assertTrue(s.data["file_url"])

    def test_read_serializer_includes_nested_files(self):
        f1 = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
        f2 = SimpleUploadedFile("b.txt", b"hi", content_type="text/plain")
        MaterialFile.objects.create(material=self.material, file=f1)
        MaterialFile.objects.create(material=self.material, file=f2)

        s = MaterialReadSerializer(instance=self.material)
        self.assertIn("files", s.data)
        self.assertEqual(len(s.data["files"]), 2)


@override_settings(MEDIA_ROOT=os.path.join(getattr(settings, "BASE_DIR", ""), "test_media"))
class MaterialAPITests(APITestCase):
    """
    IMPORTANT: Use reverse() so it works even if you mount under /api/.
    Adjust these names if your materials/urls.py uses different ones.
    """

    def setUp(self):
        self.client = APIClient()
        self.creator = make_user("api_mat_creator@example.com")
        self.other = make_user("api_mat_other@example.com")
        self.staff = make_user("api_mat_staff@example.com", is_staff=True)

        self.course = make_course(self.creator, creator_code="API")

        self.material = Material.objects.create(
            course=self.course,
            creator=self.creator,
            title="Initial",
            description="",
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_list_allows_anonymous(self):
        url = reverse("materials-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_detail_allows_anonymous(self):
        url = reverse("materials-detail", kwargs={"pk": self.material.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_requires_auth(self):
        url = reverse("materials-create")
        res = self.client.post(url, {"course_id": self.course.id, "title": "T"}, format="multipart")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_with_files_creates_material_and_files(self):
        self.auth(self.creator)
        url = reverse("materials-create")

        f1 = SimpleUploadedFile("one.txt", b"1", content_type="text/plain")
        f2 = SimpleUploadedFile("two.txt", b"2", content_type="text/plain")

        data = {
            "course_id": str(self.course.id),
            "title": "New Mat",
            "description": "d",
            "files": [f1, f2],
        }
        res = self.client.post(url, data, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        mat = Material.objects.get(pk=res.data["id"])
        self.assertEqual(mat.creator_id, self.creator.id)
        self.assertEqual(mat.course_id, self.course.id)

        self.assertEqual(mat.files.count(), 2)
        for mf in mat.files.all():
            self.assertTrue(mf.filename.endswith(".txt"))

        self.assertIn("files", res.data)
        self.assertEqual(len(res.data["files"]), 2)

    def test_update_denied_for_non_creator_non_staff(self):
        self.auth(self.other)
        url = reverse("materials-edit", kwargs={"pk": self.material.id})
        res = self.client.patch(url, {"title": "Nope"}, format="multipart")
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_update_allowed_for_creator(self):
        self.auth(self.creator)
        url = reverse("materials-edit", kwargs={"pk": self.material.id})
        res = self.client.patch(url, {"title": "Changed"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.material.refresh_from_db()
        self.assertEqual(self.material.title, "Changed")

    def test_update_allowed_for_staff(self):
        self.auth(self.staff)
        url = reverse("materials-edit", kwargs={"pk": self.material.id})
        res = self.client.patch(url, {"title": "StaffChanged"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.material.refresh_from_db()
        self.assertEqual(self.material.title, "StaffChanged")

    def test_update_can_append_files(self):
        self.auth(self.creator)
        url = reverse("materials-edit", kwargs={"pk": self.material.id})
        f1 = SimpleUploadedFile("add.txt", b"x", content_type="text/plain")

        res = self.client.patch(url, {"files": [f1]}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.material.refresh_from_db()
        self.assertEqual(self.material.files.count(), 1)
        self.assertTrue(self.material.files.first().filename.endswith(".txt"))

    def test_delete_denied_for_non_creator_non_staff(self):
        self.auth(self.other)
        url = reverse("materials-delete", kwargs={"pk": self.material.id})
        res = self.client.delete(url)
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_delete_allowed_for_creator(self):
        self.auth(self.creator)
        url = reverse("materials-delete", kwargs={"pk": self.material.id})
        res = self.client.delete(url)
        self.assertIn(res.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
        self.assertFalse(Material.objects.filter(id=self.material.id).exists())

    def test_delete_allowed_for_staff(self):
        mat = Material.objects.create(course=self.course, creator=self.creator, title="ToDel", description="")
        self.auth(self.staff)
        url = reverse("materials-delete", kwargs={"pk": mat.id})
        res = self.client.delete(url)
        self.assertIn(res.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
        self.assertFalse(Material.objects.filter(id=mat.id).exists())
