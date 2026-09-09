class ProjectPolicy:
    """Authorization decisions for project-level actions."""

    VIEW_ROLES = {"viewer", "contributor", "manager", "owner"}
    EDIT_ROLES = {"manager", "owner"}

    @staticmethod
    def _is_active(principal) -> bool:
        return principal is not None and principal.get("status") == "active"

    @classmethod
    def role_for(cls, principal, project: dict) -> str | None:
        if not cls._is_active(principal):
            return None
        if principal["role"] == "admin":
            return "admin"
        if principal["id"] == project["owner_id"]:
            return "owner"
        return project.get("member_role")

    @classmethod
    def can_create(cls, principal) -> bool:
        return cls._is_active(principal)

    @classmethod
    def can_view(cls, principal, project: dict) -> bool:
        return cls.role_for(principal, project) in cls.VIEW_ROLES | {"admin"}

    @classmethod
    def can_edit(cls, principal, project: dict) -> bool:
        return cls.role_for(principal, project) in cls.EDIT_ROLES | {"admin"}

    @classmethod
    def can_delete(cls, principal, project: dict) -> bool:
        return cls.role_for(principal, project) in {"owner", "admin"}

    @classmethod
    def can_manage_members(cls, principal, project: dict) -> bool:
        return cls.role_for(principal, project) in {"manager", "owner", "admin"}
