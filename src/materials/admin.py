from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Material, MaterialFile


class MaterialFileInline(TabularInline):
    model = MaterialFile
    extra = 2  # shows 2 empty file fields by default


@admin.register(Material)
class MaterialAdmin(ModelAdmin):
    list_display = (
        "title",
        "course",
        "creator",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "course",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "course__title",
        "creator__email",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [MaterialFileInline]
