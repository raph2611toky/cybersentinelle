from rest_framework.permissions import BasePermission


class StudioPermissions(BasePermission):
    """L'accès Swagger n'accorde jamais une permission métier."""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff
                    and user.has_perm(getattr(view, 'required_permission', 'media_studio.view_mediaasset')))
