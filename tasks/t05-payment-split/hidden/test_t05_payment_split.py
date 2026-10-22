import sqlite3
import unittest

from brightline import db, payments, reports
from tests import fixtures


def total_shares(conn, pid):
    return sum(c for _, c in payments.payment_shares(conn, pid))


class Allocation(unittest.TestCase):
    def setUp(self):
        self.conn, self.p = fixtures.world()

    def pay(self, cents, ids):
        pid = payments.create_payment(self.conn, "Harbor Line", cents, "2026-03-01")
        payments.link_payment(self.conn, pid, ids)
        return pid

    def test_shares_add_up_to_payment(self):
        pid = self.pay(100000, [1, 2, 3])
        self.assertEqual(total_shares(self.conn, pid), 100000)
        self.assertEqual(sum(payments.paid_toward_shipment(self.conn, s) for s in (1, 2, 3)), 100000)

    def test_split_is_fair_to_the_cent(self):
        pid = self.pay(100000, [1, 2, 3])
        for _, cents in payments.payment_shares(self.conn, pid):
            self.assertIn(cents, range(33333, 33335))

    def test_odd_cents_nothing_lost_or_created(self):
        for amount, n in ((100001, 3), (1, 3), (999999, 4), (7, 2)):
            conn, _ = fixtures.world()
            pid = payments.create_payment(conn, "Skyhook Air Cargo", amount, "2026-03-02")
            payments.link_payment(conn, pid, list(range(1, n + 1)))
            self.assertEqual(total_shares(conn, pid), amount, (amount, n))
            base = amount // n
            for _, cents in payments.payment_shares(conn, pid):
                self.assertTrue(base <= cents <= base + n - 1, (amount, n, cents))

    def test_single_link_gets_whole_amount(self):
        self.pay(54321, [4])
        self.assertEqual(payments.paid_toward_shipment(self.conn, 4), 54321)

    def test_two_payments_on_one_shipment_add(self):
        self.pay(30000, [1, 2])
        self.pay(10000, [2])
        self.assertEqual(payments.paid_toward_shipment(self.conn, 2), 15000 + 10000)
        self.assertEqual(payments.paid_toward_shipment(self.conn, 1), 15000)

    def test_relinking_replaces_earlier_split(self):
        pid = self.pay(90000, [1, 2, 3])
        payments.link_payment(self.conn, pid, [2, 4])
        self.assertEqual(payments.paid_toward_shipment(self.conn, 1), 0)
        self.assertEqual(payments.paid_toward_shipment(self.conn, 3), 0)
        self.assertEqual(total_shares(self.conn, pid), 90000)

    def test_empty_link_still_rejected(self):
        pid = payments.create_payment(self.conn, "Harbor Line", 100, "2026-03-01")
        with self.assertRaises(ValueError):
            payments.link_payment(self.conn, pid, [])

    def test_report_costs_add_up_to_payments(self):
        self.pay(100000, [1, 2, 3])
        self.pay(50050, [3, 5])
        rows = reports.sales_by_client(self.conn, self.p["admin"])
        self.assertEqual(sum(r["cost_cents"] for r in rows), 150050)
        revenue = sum(r["revenue_cents"] for r in rows)
        self.assertEqual(sum(r["margin_cents"] for r in rows), revenue - 150050)

    def test_margin_uses_share(self):
        from brightline import shipments
        self.pay(100000, [1, 2])
        s1 = shipments.get(self.conn, 1)
        self.assertEqual(payments.margin_cents(self.conn, s1), s1.amount_cents - 50000)


def legacy_db():
    """A database as it was before the change: links exist, no shares stored."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.migrate(conn, target=2)
    conn.execute("INSERT INTO users VALUES (2, 'Mia Manager', 'manager')")
    conn.execute("INSERT INTO clients VALUES ('CL-1', 'Cobalt Retail', 2, '2026-01-01')")
    for i in (1, 2, 3):
        conn.execute("INSERT INTO shipments VALUES (?, ?, 'CL-1', 'A', 'B', 'booked', '2026-02-01', 1000)",
                     (i, f"BL-{i}"))
    conn.execute("INSERT INTO payments VALUES (1, 'Harbor Line', 100000, '2026-02-02')")
    conn.execute("INSERT INTO payments VALUES (2, 'Greenway Haulage', 5000, '2026-02-03')")
    for sid in (1, 2, 3):
        conn.execute("INSERT INTO shipment_payments(shipment_id, payment_id) VALUES (?, 1)", (sid,))
    conn.execute("INSERT INTO shipment_payments(shipment_id, payment_id) VALUES (2, 2)")
    conn.commit()
    return conn


class Migration(unittest.TestCase):
    def test_existing_data_is_split_without_losing_a_cent(self):
        conn = legacy_db()
        version = db.migrate(conn)
        self.assertGreater(version, 2)
        shares = payments.payment_shares(conn, 1)
        self.assertEqual(len(shares), 3)
        self.assertEqual(sum(c for _, c in shares), 100000)
        for _, c in shares:
            self.assertTrue(33333 <= c <= 33335)
        self.assertEqual(payments.payment_shares(conn, 2), [(2, 5000)])

    def test_every_migration_has_a_rollback(self):
        ups = {p.name[:-len(".up.sql")] for p in db.MIGRATIONS_DIR.glob("*.up.sql")}
        downs = {p.name[:-len(".down.sql")] for p in db.MIGRATIONS_DIR.glob("*.down.sql")}
        self.assertEqual(ups, downs)
        self.assertGreaterEqual(len(ups), 2)

    def test_rollback_and_reapply_keeps_data(self):
        conn = legacy_db()
        latest = db.migrate(conn)
        before = conn.execute("SELECT COUNT(*) FROM shipment_payments").fetchone()[0]
        self.assertEqual(db.rollback(conn), latest - 1)
        self.assertEqual(latest - 1, 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM shipment_payments").fetchone()[0], before)
        self.assertEqual(db.migrate(conn), latest)
        self.assertEqual(sum(c for _, c in payments.payment_shares(conn, 1)), 100000)

    def test_rollback_actually_changes_the_schema(self):
        conn = legacy_db()
        db.migrate(conn)
        after_up = [r[0] for r in conn.execute("SELECT sql FROM sqlite_master ORDER BY name")]
        db.rollback(conn)
        after_down = [r[0] for r in conn.execute("SELECT sql FROM sqlite_master ORDER BY name")]
        self.assertNotEqual(after_up, after_down)

    def test_baseline_schema_untouched(self):
        text = (db.MIGRATIONS_DIR.parent / "schema.sql").read_text()
        self.assertNotIn("allocated", text)  # changes go through migrations


if __name__ == "__main__":
    unittest.main()
