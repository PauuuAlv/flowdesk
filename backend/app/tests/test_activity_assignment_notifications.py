"""Avisos al asignar, reasignar o modificar actividades."""
import unittest
import uuid
from unittest.mock import MagicMock

from app.services.notifications import notify_activity_assignment


def _user(name: str):
    return MagicMock(id=uuid.uuid4(), full_name=name, email=f"{name.lower()}@example.com")


class ActivityAssignmentNotificationTests(unittest.TestCase):
    def setUp(self):
        self.admin = _user("Admin")
        self.ana = _user("Ana")
        self.beto = _user("Beto")
        self.db = MagicMock()
        self.db.query.return_value.filter.return_value.first.return_value = self.beto
        self.activity = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), title="Llamar",
            client=MagicMock(company_name="ACME"), owner_user_id=self.ana.id)

    def _added(self):
        return {call.args[0].user_id: call.args[0] for call in self.db.add.call_args_list}

    def test_new_activity_notifies_the_assigned_owner(self):
        recipients = notify_activity_assignment(self.db, self.admin, self.activity)
        self.assertEqual(recipients, {self.ana.id})
        item = self._added()[self.ana.id]
        self.assertEqual(item.notification_type, "activity_assigned")
        self.assertIn("Admin te asignó: Llamar · ACME", item.message)

    def test_self_assignment_does_not_notify(self):
        recipients = notify_activity_assignment(self.db, self.ana, self.activity)
        self.assertEqual(recipients, set())
        self.db.add.assert_not_called()

    def test_reassignment_notifies_new_and_previous_owner(self):
        self.activity.owner_user_id = self.beto.id
        recipients = notify_activity_assignment(self.db, self.admin, self.activity, previous_owner_id=self.ana.id)
        self.assertEqual(recipients, {self.ana.id, self.beto.id})
        added = self._added()
        self.assertEqual(added[self.beto.id].notification_type, "activity_assigned")
        self.assertEqual(added[self.ana.id].notification_type, "activity_unassigned")
        self.assertEqual(added[self.ana.id].title, "Se te retiró una actividad")
        self.assertIn("se la asignó a Beto", added[self.ana.id].message)

    def test_owner_who_reassigns_is_not_notified_about_losing_it(self):
        self.activity.owner_user_id = self.beto.id
        recipients = notify_activity_assignment(self.db, self.ana, self.activity, previous_owner_id=self.ana.id)
        self.assertEqual(recipients, {self.beto.id})

    def test_update_by_someone_else_notifies_owner(self):
        recipients = notify_activity_assignment(self.db, self.admin, self.activity,
            previous_owner_id=self.ana.id, changed=True)
        self.assertEqual(recipients, {self.ana.id})
        self.assertEqual(self._added()[self.ana.id].notification_type, "activity_updated")

    def test_save_without_changes_does_not_notify(self):
        recipients = notify_activity_assignment(self.db, self.admin, self.activity,
            previous_owner_id=self.ana.id, changed=False)
        self.assertEqual(recipients, set())

    def test_each_event_gets_a_unique_key(self):
        notify_activity_assignment(self.db, self.admin, self.activity)
        notify_activity_assignment(self.db, self.admin, self.activity)
        keys = [call.args[0].event_key for call in self.db.add.call_args_list]
        self.assertEqual(len(set(keys)), 2)


if __name__ == "__main__":
    unittest.main()
