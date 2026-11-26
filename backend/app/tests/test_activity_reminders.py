"""Recordatorios de actividades: alta, edición, eliminación y reprogramación."""
import unittest
import unittest.mock
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.activity import ActivityReminderInput, SaveActivityRequest
from app.services.activity_reminders import apply_reminders, describe_offset

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)


def _activity(hours_ahead: float = 48):
    return SimpleNamespace(tenant_id=uuid.uuid4(), scheduled_at=NOW + timedelta(hours=hours_ahead), reminders=[])


class ActivityReminderTests(unittest.TestCase):
    def test_creates_reminders_and_computes_send_time(self):
        activity = _activity()
        apply_reminders(activity, [ActivityReminderInput(minutes_before=15), ActivityReminderInput(minutes_before=1440)], NOW)
        times = sorted(r.remind_at for r in activity.reminders)
        self.assertEqual(times, [activity.scheduled_at - timedelta(days=1), activity.scheduled_at - timedelta(minutes=15)])
        self.assertTrue(all(r.sent_at is None for r in activity.reminders))

    def test_none_keeps_reminders_but_reschedules_them(self):
        activity = _activity()
        apply_reminders(activity, [ActivityReminderInput(minutes_before=60)], NOW)
        reminder = activity.reminders[0]
        reminder.sent_at = NOW  # ya se había enviado
        activity.scheduled_at += timedelta(days=2)
        apply_reminders(activity, None, NOW)
        self.assertEqual(activity.reminders, [reminder])
        self.assertEqual(reminder.remind_at, activity.scheduled_at - timedelta(hours=1))
        self.assertIsNone(reminder.sent_at)  # vuelve a quedar pendiente

    def test_modifies_by_id_and_removes_missing(self):
        activity = _activity()
        apply_reminders(activity, [ActivityReminderInput(minutes_before=15), ActivityReminderInput(minutes_before=60)], NOW)
        first, second = activity.reminders
        apply_reminders(activity, [ActivityReminderInput(id=str(first.id), minutes_before=30)], NOW)
        self.assertEqual(activity.reminders, [first])
        self.assertEqual(first.minutes_before, 30)
        self.assertNotIn(second, activity.reminders)

    def test_empty_list_removes_all(self):
        activity = _activity()
        apply_reminders(activity, [ActivityReminderInput(minutes_before=15)], NOW)
        apply_reminders(activity, [], NOW)
        self.assertEqual(activity.reminders, [])

    def test_reminder_already_in_the_past_is_not_sent_late(self):
        activity = _activity(hours_ahead=2)
        apply_reminders(activity, [ActivityReminderInput(minutes_before=1440)], NOW)
        self.assertEqual(activity.reminders[0].sent_at, NOW)

    def test_duplicates_are_ignored(self):
        activity = _activity()
        apply_reminders(activity, [ActivityReminderInput(minutes_before=15), ActivityReminderInput(minutes_before=15)], NOW)
        self.assertEqual(len(activity.reminders), 1)

    def test_unknown_reminder_id_is_rejected(self):
        with self.assertRaises(HTTPException):
            apply_reminders(_activity(), [ActivityReminderInput(id=str(uuid.uuid4()), minutes_before=15)], NOW)

    def test_limits_are_validated(self):
        with self.assertRaises(ValidationError):
            ActivityReminderInput(minutes_before=-1)
        with self.assertRaises(ValidationError):
            ActivityReminderInput(minutes_before=31 * 1440)
        with self.assertRaises(ValidationError):
            SaveActivityRequest(client_id="c", owner_user_id="o", activity_type="call", title="Llamada",
                scheduled_at=NOW, reminders=[{"minutes_before": i} for i in range(11)])

    def test_offset_description(self):
        self.assertEqual(describe_offset(0), "Comienza ahora")
        self.assertEqual(describe_offset(15), "Comienza en 15 minutos")
        self.assertEqual(describe_offset(60), "Comienza en 1 hora")
        self.assertEqual(describe_offset(2880), "Comienza en 2 días")
        self.assertEqual(describe_offset(125), "Comienza en 2 horas 5 minutos")
        self.assertEqual(describe_offset(1500), "Comienza en 1 día 1 hora")

    def test_fixed_reminder_uses_exact_time_and_does_not_move_with_activity(self):
        activity = _activity()
        fixed = activity.scheduled_at - timedelta(hours=5, minutes=20)
        apply_reminders(activity, [ActivityReminderInput(fixed_at=fixed), ActivityReminderInput(minutes_before=60)], NOW)
        by_mode = {("fixed" if r.fixed_at else "before"): r for r in activity.reminders}
        self.assertEqual(by_mode["fixed"].remind_at, fixed)
        self.assertIsNone(by_mode["fixed"].minutes_before)

        activity.scheduled_at += timedelta(days=1)
        apply_reminders(activity, None, NOW)
        self.assertEqual(by_mode["fixed"].remind_at, fixed)  # fecha exacta: no se mueve
        self.assertEqual(by_mode["before"].remind_at, activity.scheduled_at - timedelta(hours=1))

    def test_reminder_can_switch_between_modes(self):
        activity = _activity()
        apply_reminders(activity, [ActivityReminderInput(minutes_before=60)], NOW)
        reminder = activity.reminders[0]
        fixed = activity.scheduled_at - timedelta(hours=3)
        apply_reminders(activity, [ActivityReminderInput(id=str(reminder.id), fixed_at=fixed)], NOW)
        self.assertEqual(activity.reminders, [reminder])
        self.assertEqual((reminder.minutes_before, reminder.fixed_at, reminder.remind_at), (None, fixed, fixed))

    def test_fixed_reminder_must_be_before_activity_and_within_30_days(self):
        activity = _activity()
        for fixed in (activity.scheduled_at + timedelta(minutes=1), activity.scheduled_at - timedelta(days=31)):
            with self.assertRaises(HTTPException) as ctx:
                apply_reminders(activity, [ActivityReminderInput(fixed_at=fixed)], NOW)
            self.assertEqual(ctx.exception.status_code, 422)

    def test_reminder_requires_exactly_one_mode(self):
        with self.assertRaises(ValidationError):
            ActivityReminderInput()
        with self.assertRaises(ValidationError):
            ActivityReminderInput(minutes_before=15, fixed_at=NOW)
        with self.assertRaises(ValidationError):
            ActivityReminderInput(fixed_at=datetime(2026, 12, 1, 10, 0))  # sin zona horaria


class ActivityReminderPermissionTests(unittest.TestCase):
    """El responsable gestiona sus recordatorios aunque no pueda editar la actividad."""

    def setUp(self):
        from app.api.v1 import activities as api
        from app.schemas.activity import UpdateActivityRemindersRequest
        self.api = api
        self.payload = UpdateActivityRemindersRequest(reminders=[{"minutes_before": 30}])
        self.owner = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        self.other = SimpleNamespace(id=uuid.uuid4(), tenant_id=self.owner.tenant_id)
        self.activity = _activity()
        self.activity.owner_user_id = self.owner.id
        self.db = unittest.mock.MagicMock()
        self.db.query.return_value.filter.return_value.first.return_value = self.activity

    def _call(self, user, permissions):
        with unittest.mock.patch.object(self.api, "get_user_permission_codes", lambda _u: permissions), \
                unittest.mock.patch.object(self.api, "_serialize", lambda item: item):
            return self.api.update_activity_reminders(uuid.uuid4(), self.payload, self.db, user)

    def test_owner_without_update_permission_can_manage_reminders(self):
        result = self._call(self.owner, ["activities.view"])
        self.assertEqual([r.minutes_before for r in result.reminders], [30])

    def test_other_user_without_update_permission_is_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            self._call(self.other, ["activities.view"])
        self.assertEqual(ctx.exception.status_code, 403)

    def test_user_with_update_permission_can_manage_any_activity(self):
        result = self._call(self.other, ["activities.view", "activities.update"])
        self.assertEqual(len(result.reminders), 1)


if __name__ == "__main__":
    unittest.main()
