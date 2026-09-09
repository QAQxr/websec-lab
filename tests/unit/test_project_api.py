from datetime import datetime

from flask import Flask, g

from backend.routes.project_api import create_project_api_blueprint


class SpyProjectService:
    def __init__(self):
        self.calls = []
        self.project = {
            "id": 9,
            "name": "Spy project",
            "slug": "spy-project",
            "description": "Test project",
            "visibility": "private",
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 1),
            "membership_role": "owner",
            "effective_role": "owner",
            "global_role": "user",
            "is_owner": True,
            "is_global_admin": False,
            "can_edit_metadata": True,
            "can_edit_visibility": True,
            "can_delete": True,
            "can_manage_members": True,
        }

    def list_projects(self, principal):
        self.calls.append(("list_projects", principal))
        return [self.project]

    def create_project(self, principal, name, description, visibility):
        self.calls.append(("create_project", principal, name, description, visibility))
        return self.project

    def get_project(self, principal, project_id):
        self.calls.append(("get_project", principal, project_id))
        return self.project

    def update_project(self, principal, project_id, name, description, visibility):
        self.calls.append(("update_project", principal, project_id, name, description, visibility))
        return self.project

    def delete_project(self, principal, project_id):
        self.calls.append(("delete_project", principal, project_id))


def test_project_api_routes_delegate_to_project_service():
    app = Flask(__name__)
    service = SpyProjectService()
    app.register_blueprint(create_project_api_blueprint(service))

    @app.before_request
    def set_principal():
        g.current_user = {"id": 7, "role": "user", "status": "active"}

    client = app.test_client()
    assert client.get("/api/projects").status_code == 200
    assert client.post(
        "/api/projects",
        json={"name": "Created", "description": "Description", "visibility": "private"},
    ).status_code == 201
    assert client.get("/api/projects/9").status_code == 200
    assert client.patch("/api/projects/9", json={"name": "Updated"}).status_code == 200
    assert client.delete("/api/projects/9").status_code == 200

    assert [call[0] for call in service.calls] == [
        "list_projects",
        "create_project",
        "get_project",
        "get_project",
        "update_project",
        "delete_project",
    ]
    update_call = service.calls[4]
    assert update_call[2:] == (9, "Updated", "Test project", "private")
