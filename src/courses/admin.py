from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Course


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = (
        "title",
        "creator",
        "creator_code",
        "join_code",
        "image_preview",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "description", "creator__email", "creator_code", "join_code")
    ordering = ("-created_at",)

    readonly_fields = ("join_code", "created_at", "updated_at", "image_preview")

    fieldsets = (
        (None, {
            "fields": ("title", "description", "image", "image_preview")
        }),
        ("Ownership & Codes", {
            "fields": ("creator", "creator_code", "join_code")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    list_editable = ("creator_code",)

    @admin.display(description="Image")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height: 50px; width: 50px; object-fit: cover; border-radius: 6px;" />',
                obj.image.url
            )
        return "No image"
