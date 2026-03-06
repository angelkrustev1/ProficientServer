from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCreatorOrStaffOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return request.user and (
            request.user.is_staff or obj.creator_id == request.user.id
        )
