# courses/admin.py

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Course


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    # what you see in the list page
    list_display = ("title", "creator", "creator_code", "join_code", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "description", "creator__email", "creator_code", "join_code")
    ordering = ("-created_at",)

    # join_code is generated, so keep it read-only in admin too
    readonly_fields = ("join_code", "created_at", "updated_at")

    # nicer layout in the edit page
    fieldsets = (
        (None, {
            "fields": ("title", "description")
        }),
        ("Ownership & Codes", {
            "fields": ("creator", "creator_code", "join_code")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    # optional: if you want to quickly edit some fields from the list view
    list_editable = ("creator_code",)
