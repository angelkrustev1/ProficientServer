from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCourseCreatorOrReadOnly(BasePermission):
    """
    - Authenticated users can READ.
    - Only creator can UPDATE/DELETE.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.creator_id == request.user.id