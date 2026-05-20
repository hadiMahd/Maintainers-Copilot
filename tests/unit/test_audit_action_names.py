"""Unit tests for reserved audit action names."""

from app.domain.audit import AuditAction


RESERVED_ACTIONS = {
    "memory.write",
    "role.change",
    "admin_invitation.create",
    "widget_config.create",
    "widget_config.update",
    "widget_config.delete",
    "conversation.delete",
}


class TestAuditActionNames:
    def test_all_seven_reserved_actions_defined(self):
        import typing
        args = typing.get_args(AuditAction)
        assert set(args) == RESERVED_ACTIONS

    def test_memory_write_present(self):
        assert "memory.write" in RESERVED_ACTIONS

    def test_role_change_present(self):
        assert "role.change" in RESERVED_ACTIONS

    def test_admin_invitation_create_present(self):
        assert "admin_invitation.create" in RESERVED_ACTIONS

    def test_widget_config_actions_present(self):
        assert "widget_config.create" in RESERVED_ACTIONS
        assert "widget_config.update" in RESERVED_ACTIONS
        assert "widget_config.delete" in RESERVED_ACTIONS

    def test_conversation_delete_present(self):
        assert "conversation.delete" in RESERVED_ACTIONS
