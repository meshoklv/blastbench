import random
import unittest

from brightline import db, reports, users
from brightline.clients import registry


def build(rows):
    conn = db.connect()
    users.add_user(conn, 1, "Ada Admin", "admin")
    users.add_user(conn, 2, "Mia Manager", "manager")
    for cid, name, mgr, day in rows:
        registry.add_client(conn, cid, name, mgr, day)
    return conn


# Deliberately scrambled so that neither insertion order nor name order equals id order.
TIES = [
    ("CL-0300", "Alder Goods", 2, "2026-01-10"),
    ("CL-0100", "Zenith Tools", 2, "2026-01-10"),
    ("CL-0200", "Mosaic Tiles", 1, "2026-01-10"),
    ("CL-0900", "Bluefin Seafood", 2, "2026-03-01"),
    ("CL-0500", "Quarry Stone", 2, "2026-03-01"),
    ("CL-0700", "Early Bird Coffee", 2, "2025-12-31"),
]


class RegistryOrder(unittest.TestCase):
    def test_ties_broken_by_id(self):
        conn = build(TIES)
        ids = [c.id for c in registry.list_clients(conn)]
        self.assertEqual(ids, ["CL-0700", "CL-0100", "CL-0200", "CL-0300", "CL-0500", "CL-0900"])

    def test_earlier_registration_still_comes_first(self):
        # An id that sorts last must still win when its date is earliest.
        conn = build([("CL-0001", "Late Co", 2, "2026-05-01"),
                      ("CL-9999", "Early Co", 2, "2020-01-01")])
        self.assertEqual([c.id for c in registry.list_clients(conn)], ["CL-9999", "CL-0001"])

    def test_same_order_whatever_the_insertion_order(self):
        expected = None
        for seed in range(6):
            rows = TIES[:]
            random.Random(seed).shuffle(rows)
            ids = [c.id for c in registry.list_clients(build(rows))]
            expected = expected or ids
            self.assertEqual(ids, expected)

    def test_matches_sales_report_order(self):
        conn = build(TIES)
        admin = users.get_user(conn, 1)
        report_ids = [r["client_id"] for r in reports.sales_by_client(conn, admin)]
        self.assertEqual([c.id for c in registry.list_clients(conn)], report_ids)

    def test_manager_filter_keeps_order(self):
        conn = build(TIES)
        ids = [c.id for c in registry.list_clients(conn, manager_id=2)]
        self.assertEqual(ids, ["CL-0700", "CL-0100", "CL-0300", "CL-0500", "CL-0900"])

    def test_ordering_not_by_name_or_reversed(self):
        conn = build(TIES)
        names = [c.name for c in registry.list_clients(conn)]
        self.assertNotEqual(names, sorted(names))
        self.assertNotEqual(names, sorted(names, reverse=True))
        self.assertEqual(names[0], "Early Bird Coffee")


if __name__ == "__main__":
    unittest.main()
