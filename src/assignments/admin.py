# src/assignments/admin.py

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Assignment, AssignmentFile, Submission, SubmissionFile


class AssignmentFileInline(TabularInline):
    model = AssignmentFile
    extra = 2


@admin.register(Assignment)
class AssignmentAdmin(ModelAdmin):
    list_display = ("title", "course", "creator", "created_at", "updated_at")
    list_filter = ("course", "created_at", "updated_at")
    search_fields = ("title", "description", "course__title", "creator__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [AssignmentFileInline]


class SubmissionFileInline(TabularInline):
    model = SubmissionFile
    extra = 2


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ("assignment", "user", "is_submitted", "submitted_at", "created_at", "updated_at")
    list_filter = ("is_submitted", "submitted_at", "created_at", "updated_at", "assignment__course")
    search_fields = ("assignment__title", "assignment__course__title", "user__email")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [SubmissionFileInline]


# Optional: manage files directly (usually you’ll just use the inlines)
@admin.register(AssignmentFile)
class AssignmentFileAdmin(ModelAdmin):
    list_display = ("filename_display", "assignment", "uploaded_at")
    search_fields = ("assignment__title", "assignment__course__title")
    ordering = ("-uploaded_at",)

    @admin.display(description="Filename")
    def filename_display(self, obj):
        return obj.filename


@admin.register(SubmissionFile)
class SubmissionFileAdmin(ModelAdmin):
    list_display = ("filename_display", "submission", "uploaded_at")
    search_fields = ("submission__assignment__title", "submission__user__email")
    ordering = ("-uploaded_at",)

    @admin.display(description="Filename")
    def filename_display(self, obj):
        return obj.filename
