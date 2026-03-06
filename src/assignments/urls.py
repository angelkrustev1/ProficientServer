from django.urls import path

from .views import (
    AssignmentListView,
    AssignmentDetailView,
    AssignmentCreateView,
    AssignmentUpdateView,
    AssignmentDeleteView,
    SubmitAssignmentView,
)

urlpatterns = [
    path("", AssignmentListView.as_view(), name="assignments-list"),
    path("create/", AssignmentCreateView.as_view(), name="assignments-create"),
    path("<int:pk>/", AssignmentDetailView.as_view(), name="assignments-detail"),
    path("<int:pk>/edit/", AssignmentUpdateView.as_view(), name="assignments-edit"),
    path("<int:pk>/delete/", AssignmentDeleteView.as_view(), name="assignments-delete"),

    path(
        "<int:assignment_id>/submission/",
        SubmitAssignmentView.as_view(),
        name="assignments-submit",
    ),
]
