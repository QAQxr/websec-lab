import pytest

from backend.config import Settings
from backend.repositories.mailbox_repository import MailboxRepository
from backend.services.auth_service import AuthError, build_auth_service
from .auth_helpers import account_details, db_query


class FailingMailbox:
    """Inject a Redis write failure after a possible write has occurred."""

    def __init__(self, real_mailbox):
        self.real_mailbox = real_mailbox

    def put_verification(self, verification_id, message, ttl):
        self.real_mailbox.put_verification(verification_id, message, ttl)
        raise RuntimeError("injected mailbox write failure")

    def remove_verification(self, verification_id):
        self.real_mailbox.remove_verification(verification_id)

    def list_verifications(self):
        return self.real_mailbox.list_verifications()


def test_mailbox_failure_compensates_mysql_and_recovery_succeeds():
    settings = Settings.from_env()
    real_mailbox = MailboxRepository(settings)
    account = account_details()
    failing_service = build_auth_service(settings, mailbox=FailingMailbox(real_mailbox))

    with pytest.raises(AuthError) as error:
        failing_service.register(
            account["username"],
            account["email"],
            account["password"],
            account["password"],
        )

    assert error.value.status_code == 503
    assert not db_query("SELECT id FROM users WHERE email = %s", (account["email"],))
    assert not db_query(
        """
        SELECT ev.id
        FROM email_verifications ev
        JOIN users u ON u.id = ev.user_id
        WHERE u.email = %s
        """,
        (account["email"],),
    )
    assert not any(message["to"] == account["email"] for message in real_mailbox.list_verifications())

    recovery_service = build_auth_service(settings, mailbox=real_mailbox)
    recovery_service.register(
        account["username"],
        account["email"],
        account["password"],
        account["password"],
    )
    assert db_query("SELECT id FROM users WHERE email = %s", (account["email"],))
    assert any(message["to"] == account["email"] for message in real_mailbox.list_verifications())
