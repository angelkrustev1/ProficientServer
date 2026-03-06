from django.urls import path
from .views import (
    CourseListView,
    CourseDetailView,
    CourseCreateView,
    CourseUpdateView,
    CourseDeleteView,
    CourseJoinView,
    CourseLeaveView,
)

urlpatterns = [
    path("", CourseListView.as_view(), name="course-list"),
    path("create/", CourseCreateView.as_view(), name="course-create"),

    path("<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("<int:pk>/edit/", CourseUpdateView.as_view(), name="course-edit"),
    path("<int:pk>/delete/", CourseDeleteView.as_view(), name="course-delete"),

    # NEW:
    path("join/", CourseJoinView.as_view(), name="course-join"),
    path("<int:pk>/leave/", CourseLeaveView.as_view(), name="course-leave"),
]
