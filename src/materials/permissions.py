from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCreatorOrStaffOrReadOnly(BasePermission):
    """
    Read for everyone.
    Write requires authentication.
    Update/Delete only for creator or staff.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and (request.user.is_staff or obj.creator_id == request.user.id))