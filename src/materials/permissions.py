from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsCreatorOrStaffOrReadOnly(BasePermission):
    """
    - Authenticated users can read
    - Authenticated users can create
    - Only creator or staff can update/delete
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)

        return bool(
            request.user
            and request.user.is_authenticated
            and (obj.creator == request.user or request.user.is_staff)
        )
