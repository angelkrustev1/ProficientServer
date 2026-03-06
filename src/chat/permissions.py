from rest_framework.permissions import BasePermission


class IsCourseMemberOrCreator(BasePermission):
    """
    Access allowed only to the course creator or users who are members of the course.
    Staff / global admins bypass.
    """

    def _is_global_admin(self, user) -> bool:
        return bool(
            user.is_staff or user.has_perm("accounts.can_administer_profiles")
        )

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # NEW: global override
        if self._is_global_admin(user):
            return True

        if hasattr(view, "get_course"):
            course = view.get_course()
            if course.creator_id == user.id:
                return True
            return course.members.filter(id=user.id).exists()

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # NEW: global override
        if self._is_global_admin(user):
            return True

        course = getattr(obj, "course", None)
        if not course:
            return False

        if course.creator_id == user.id:
            return True

        return course.members.filter(id=user.id).exists()


class IsMessageAuthorOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.has_perm("accounts.can_administer_profiles"):
            return True

        return obj.author_id == user.id