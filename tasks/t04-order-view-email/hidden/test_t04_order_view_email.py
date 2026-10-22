import unittest

from brightline import dictionaries, notify, orders, permissions
from brightline.permissions import PermissionDenied
from brightline.shipments import ShipmentNotFound
from tests import fixtures


class ReadOnlyView(unittest.TestCase):
    def setUp(self):
        self.conn, self.p = fixtures.world()
        notify.reset()
        del dictionaries.REQUESTS[:]

    def test_accountant_can_view_without_error(self):
        view = orders.open_order(self.conn, self.p["ally"], 1)  # default mode is view
        self.assertEqual(view.shipment.ref, "BL-1001")
        self.assertEqual(view.mode, "view")

    def test_no_error_email_for_accountant_view(self):
        orders.open_order(self.conn, self.p["ally"], 1, mode="view")
        self.assertEqual(notify.OUTBOX, [])

    def test_dictionaries_are_not_requested_in_view_mode(self):
        orders.open_order(self.conn, self.p["ally"], 1, mode="view")
        self.assertEqual(dictionaries.REQUESTS, [])  # fix the cause, not the symptom

    def test_view_mode_does_not_request_dictionaries_for_managers_either(self):
        orders.open_order(self.conn, self.p["mia"], 1, mode="view")
        self.assertEqual(dictionaries.REQUESTS, [])

    def test_role_permissions_unchanged(self):
        self.assertEqual(permissions.ROLE_PERMISSIONS["accountant"], {
            "orders.view", "payments.view", "payments.edit", "reports.view", "clients.view_all"})
        self.assertEqual(permissions.ROLE_PERMISSIONS["manager"], {
            "orders.view", "orders.edit", "dictionaries.read", "reports.view", "clients.view_own"})
        self.assertFalse(permissions.has(self.p["ally"], "dictionaries.read"))

    def test_dictionaries_still_denied_to_accountant(self):
        with self.assertRaises(PermissionDenied):
            dictionaries.load_all(self.conn, self.p["ally"])

    def test_edit_mode_still_loads_dictionaries_for_manager(self):
        view = orders.open_order(self.conn, self.p["mia"], 1, mode="edit")
        self.assertEqual(dictionaries.REQUESTS, ["all"])
        self.assertIn("carriers", view.dictionaries)

    def test_accountant_cannot_edit(self):
        with self.assertRaises(PermissionDenied):
            orders.open_order(self.conn, self.p["ally"], 1, mode="edit")

    def test_real_failures_still_email_and_raise(self):
        with self.assertRaises(ShipmentNotFound):
            orders.open_order(self.conn, self.p["ally"], 9999, mode="view")
        self.assertEqual(len(notify.OUTBOX), 1)
        self.assertIn("9999", notify.OUTBOX[0]["body"])


if __name__ == "__main__":
    unittest.main()
