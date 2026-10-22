import unittest

from brightline import permissions, reports
from brightline.clients import registry
from tests import fixtures


class ManagerScope(unittest.TestCase):
    def setUp(self):
        self.conn, self.p = fixtures.world()
        fixtures.add_calls(self.conn)
        # Newest calls overall belong to Max's clients; Mia has older ones.

    def own_ids(self, user):
        return {c.id for c in permissions.visible_clients(self.conn, user)}

    def test_recent_calls_only_own_clients(self):
        calls = reports.recent_calls(self.conn, self.p["mia"])
        self.assertTrue(calls)
        self.assertLessEqual({c.client_id for c in calls}, self.own_ids(self.p["mia"]))

    def test_recent_calls_limit_applies_after_scoping(self):
        # Mia has 2 calls (CL-0100, CL-0300); the 3 newest overall are not hers.
        calls = reports.recent_calls(self.conn, self.p["mia"], limit=2)
        self.assertEqual([c.summary for c in calls],
                         ["Rate renegotiation", "Confirmed pickup window"])

    def test_recent_calls_limit_for_second_manager(self):
        calls = reports.recent_calls(self.conn, self.p["max"], limit=2)
        self.assertEqual([c.summary for c in calls],
                         ["New lane inquiry", "Invoice question"])

    def test_digest_numbers_cover_only_own_clients(self):
        d = reports.activity_digest(self.conn, self.p["mia"])
        self.assertEqual(d["call_count"], 2)
        self.assertEqual(d["clients_with_calls"], 2)
        self.assertEqual({c.client_id for c in d["calls"]}, {"CL-0100", "CL-0300"})
        # Mia's open shipments: BL-1003 (customs) and BL-1005 (in transit)
        self.assertEqual(d["open_shipments"], 2)
        self.assertEqual(d["open_value_cents"], 2310075 + 560000)

    def test_digest_for_other_manager(self):
        d = reports.activity_digest(self.conn, self.p["max"])
        self.assertEqual(d["call_count"], 3)
        self.assertEqual(d["open_shipments"], 2)
        self.assertEqual(d["open_value_cents"], 842550 + 99900)

    def test_manager_without_clients_sees_nothing(self):
        from brightline import users
        loner = users.add_user(self.conn, 9, "Nora New", "manager")
        self.assertEqual(reports.recent_calls(self.conn, loner), [])
        d = reports.activity_digest(self.conn, loner)
        self.assertEqual((d["call_count"], d["open_shipments"], d["open_value_cents"]), (0, 0, 0))
        self.assertEqual(d["calls"], [])

    def test_admin_still_sees_everything(self):
        d = reports.activity_digest(self.conn, self.p["admin"])
        self.assertEqual(d["call_count"], 5)
        self.assertEqual(d["open_shipments"], 4)
        self.assertEqual(len(reports.recent_calls(self.conn, self.p["admin"], limit=50)), 5)

    def test_accountant_still_sees_everything(self):
        self.assertEqual(reports.activity_digest(self.conn, self.p["ally"])["call_count"], 5)

    def test_sales_report_scoped_and_ordered(self):
        rows = reports.sales_by_client(self.conn, self.p["mia"])
        self.assertEqual([r["client_id"] for r in rows], ["CL-0100", "CL-0300"])

    def test_permission_table_not_widened(self):
        self.assertNotIn("clients.view_all", permissions.ROLE_PERMISSIONS["manager"])


if __name__ == "__main__":
    unittest.main()
