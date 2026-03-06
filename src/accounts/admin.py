from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group

from unfold.admin import ModelAdmin

from .models import AppUser
from .forms import AppUserCreationForm, AppUserChangeForm


# Optional but recommended:
# Re-register Group with Unfold styling (same idea as Unfold docs)
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(AppUser)
class AppUserAdmin(BaseUserAdmin, ModelAdmin):
    # Use your forms (these will be used in admin add/change)
    add_form = AppUserCreationForm
    form = AppUserChangeForm

    model = AppUser

    # What you see in list page
    list_display = ("email", "is_staff", "is_superuser", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email",)
    ordering = ("-date_joined",)

    # Fields shown on the edit page
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("profile_picture",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Fields shown on the create page (admin add user)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "profile_picture", "password1", "password2", "is_active", "is_staff", "is_superuser"),
        }),
    )

    # Because you're using email instead of username
    filter_horizontal = ("groups", "user_permissions")
