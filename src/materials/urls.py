from django.urls import path
from .views import (
    MaterialListView,
    MaterialDetailView,
    MaterialCreateView,
    MaterialUpdateView,
    MaterialDeleteView,
)

urlpatterns = [
    path("", MaterialListView.as_view(), name="materials-list"),
    path("<int:pk>/", MaterialDetailView.as_view(), name="materials-detail"),
    path("create/", MaterialCreateView.as_view(), name="materials-create"),
    path("<int:pk>/edit/", MaterialUpdateView.as_view(), name="materials-edit"),
    path("<int:pk>/delete/", MaterialDeleteView.as_view(), name="materials-delete"),
]
