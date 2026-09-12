from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectAccess:
    """The complete authorization result for one principal and project."""

    authentication_state: str
    global_role: str | None
    membership_role: str | None
    effective_role: str | None
    visibility: str | None
    is_owner: bool
    is_global_admin: bool
    can_view: bool
    can_edit_metadata: bool
    can_edit_visibility: bool
    can_delete: bool
    can_manage_members: bool
    can_view_members: bool
    can_invite_viewer: bool
    can_invite_contributor: bool
    can_invite_manager: bool
    can_invite_owner: bool
    can_change_member_role: bool
    can_promote_manager: bool
    can_assign_owner: bool
    can_remove_member: bool
    can_transfer_ownership: bool


class ProjectPolicy:
    """Single authorization truth source for project actions and query scope."""

    VIEW_ROLES = {"viewer", "contributor", "manager", "owner"}
    MANAGER_ROLES = {"manager", "owner"}
    MEMBER_ROLES = VIEW_ROLES
    NORMAL_MEMBER_ROLES = {"viewer", "contributor", "manager"}
    ROLE_CHANGE_ROLES = {"viewer", "contributor"}
    QUERY_NONE = "none"
    QUERY_AUTHENTICATED = "authenticated"
    QUERY_GLOBAL = "global"

    @staticmethod
    def _authentication_state(principal) -> str:
        if principal is None:
            return "guest"
        status = principal.get("status")
        if status in {"pending", "active", "locked"}:
            return status
        return "inactive"

    @classmethod
    def _is_active(cls, principal) -> bool:
        return cls._authentication_state(principal) == "active"

    @classmethod
    def access_for(cls, principal, project: dict) -> ProjectAccess:
        authentication_state = cls._authentication_state(principal)
        is_active = authentication_state == "active"
        global_role = principal.get("role") if principal else None
        membership_role = project.get("member_role") if is_active else None
        is_global_admin = is_active and global_role == "admin"
        is_owner = is_active and principal.get("id") == project.get("owner_id")
        visibility = project.get("visibility")

        # An owner membership row cannot manufacture ownership. The project
        # owner_id comparison is the only owner source of truth.
        effective_role = None
        if is_owner:
            effective_role = "owner"
        elif membership_role in {"viewer", "contributor", "manager"}:
            effective_role = membership_role

        has_membership_view = membership_role in cls.MEMBER_ROLES
        can_view = is_active and (
            is_global_admin
            or is_owner
            or has_membership_view
            or visibility == "team"
        )
        can_edit_metadata = is_active and (
            is_global_admin or is_owner or membership_role == "manager"
        )
        can_edit_visibility = is_active and (is_global_admin or is_owner)
        can_delete = is_active and (is_global_admin or is_owner)
        can_manage_members = is_active and (
            is_global_admin or is_owner or membership_role == "manager"
        )
        can_view_members = is_active and (
            is_global_admin or is_owner or membership_role in cls.MEMBER_ROLES
        )
        can_invite_viewer = can_manage_members
        can_invite_contributor = can_manage_members
        can_invite_manager = is_active and (is_global_admin or is_owner)
        can_invite_owner = is_active and (is_global_admin or is_owner)
        can_change_member_role = can_manage_members
        can_promote_manager = is_active and (is_global_admin or is_owner)
        can_assign_owner = is_active and (is_global_admin or is_owner)
        can_remove_member = can_manage_members
        can_transfer_ownership = is_active and (is_global_admin or is_owner)

        return ProjectAccess(
            authentication_state=authentication_state,
            global_role=global_role,
            membership_role=membership_role,
            effective_role=effective_role,
            visibility=visibility,
            is_owner=is_owner,
            is_global_admin=is_global_admin,
            can_view=can_view,
            can_edit_metadata=can_edit_metadata,
            can_edit_visibility=can_edit_visibility,
            can_delete=can_delete,
            can_manage_members=can_manage_members,
            can_view_members=can_view_members,
            can_invite_viewer=can_invite_viewer,
            can_invite_contributor=can_invite_contributor,
            can_invite_manager=can_invite_manager,
            can_invite_owner=can_invite_owner,
            can_change_member_role=can_change_member_role,
            can_promote_manager=can_promote_manager,
            can_assign_owner=can_assign_owner,
            can_remove_member=can_remove_member,
            can_transfer_ownership=can_transfer_ownership,
        )

    @classmethod
    def query_scope(cls, principal) -> str:
        """Return an explicit repository scope without making the repository infer roles."""
        if not cls._is_active(principal):
            return cls.QUERY_NONE
        if principal.get("role") == "admin":
            return cls.QUERY_GLOBAL
        return cls.QUERY_AUTHENTICATED

    @classmethod
    def role_for(cls, principal, project: dict) -> str | None:
        """Compatibility accessor backed by the structured policy result."""
        return cls.access_for(principal, project).effective_role

    @classmethod
    def can_create(cls, principal) -> bool:
        return cls._is_active(principal)

    @classmethod
    def can_view(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_view

    @classmethod
    def can_edit_metadata(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_edit_metadata

    @classmethod
    def can_edit_visibility(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_edit_visibility

    @classmethod
    def can_delete(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_delete

    @classmethod
    def can_manage_members(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_manage_members

    @classmethod
    def can_invite_viewer(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_invite_viewer

    @classmethod
    def can_invite_contributor(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_invite_contributor

    @classmethod
    def can_invite_manager(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_invite_manager

    @classmethod
    def can_invite_owner(cls, principal, project: dict) -> bool:
        return cls.access_for(principal, project).can_invite_owner

    @classmethod
    def can_invite_member(
        cls,
        principal,
        project: dict,
        new_role: str | None,
        target_user_id: int | None = None,
    ) -> bool:
        access = cls.access_for(principal, project)
        if not access.can_manage_members or new_role not in cls.NORMAL_MEMBER_ROLES:
            return False
        if target_user_id is not None and target_user_id == principal.get("id"):
            return False
        if access.is_global_admin or access.is_owner:
            return True
        return access.membership_role == "manager" and new_role in cls.ROLE_CHANGE_ROLES

    @classmethod
    def can_change_member_role(
        cls,
        principal,
        project: dict,
        target_role: str | None = None,
        new_role: str | None = None,
        target_user_id: int | None = None,
    ) -> bool:
        access = cls.access_for(principal, project)
        if not access.can_change_member_role:
            return False
        if target_user_id is not None and target_user_id == principal.get("id"):
            return False
        if target_role not in cls.NORMAL_MEMBER_ROLES:
            return False
        if new_role not in cls.NORMAL_MEMBER_ROLES or target_role == new_role:
            return False
        if access.is_global_admin or access.is_owner:
            return True
        return (
            target_role in cls.ROLE_CHANGE_ROLES
            and new_role in cls.ROLE_CHANGE_ROLES
        )

    @classmethod
    def can_remove_member(
        cls,
        principal,
        project: dict,
        target_role: str | None = None,
        target_user_id: int | None = None,
    ) -> bool:
        access = cls.access_for(principal, project)
        if not access.can_remove_member:
            return False
        if target_user_id is not None and target_user_id == principal.get("id"):
            return False
        if target_role not in cls.NORMAL_MEMBER_ROLES:
            return False
        if access.is_global_admin or access.is_owner:
            return True
        return target_role in cls.ROLE_CHANGE_ROLES
