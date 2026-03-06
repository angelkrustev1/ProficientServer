# src/chat/admin.py

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Message, MessageLike


class MessageLikeInline(TabularInline):
    model = MessageLike
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ("id", "course", "author", "short_content", "likes_count", "created_at", "updated_at")
    list_filter = ("course", "created_at", "updated_at")
    search_fields = ("content", "course__title", "author__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("course", "author")

    inlines = [MessageLikeInline]

    @admin.display(description="Content")
    def short_content(self, obj):
        text = obj.content or ""
        return text[:60] + ("..." if len(text) > 60 else "")

    @admin.display(description="Likes")
    def likes_count(self, obj):
        return obj.likes.count()


@admin.register(MessageLike)
class MessageLikeAdmin(ModelAdmin):
    list_display = ("message", "user", "created_at")
    list_filter = ("created_at", "message__course")
    search_fields = ("user__email", "message__content", "message__course__title")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("message", "user")
