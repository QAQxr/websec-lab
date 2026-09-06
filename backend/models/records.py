from dataclasses import dataclass


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    email: str
    role: str
    status: str


@dataclass(frozen=True)
class ProjectRecord:
    id: int
    owner_id: int
    name: str
    slug: str
    visibility: str


@dataclass(frozen=True)
class ProjectMemberRecord:
    project_id: int
    user_id: int
    member_role: str
