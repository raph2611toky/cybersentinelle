from rest_framework.permissions import DjangoModelPermissions


class EditorialPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request, view):
        action_permission = {
            "rollback": "change_versioncontenu",
            "publish": "add_versioncontenu",
        }.get(getattr(view, "action", ""))
        if action_permission:
            return bool(
                request.user
                and request.user.is_active
                and request.user.is_staff
                and request.user.has_perm("publication." + action_permission)
            )
        return bool(
            request.user
            and request.user.is_active
            and request.user.is_staff
            and super().has_permission(request, view)
        )
