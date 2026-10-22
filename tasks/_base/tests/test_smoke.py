"""Public smoke tests: the basics every build must keep working."""
import unittest

from brightline import db, notify, orders, payments, permissions, reports, shipments
from brightline.models import Quote
from brightline.quotes import format_money, quote_title, render_quote, total_cents
from brightline.timeline import render_timeline
from brightline.clients import registry
from tests import fixtures


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.conn, self.people = fixtures.world()
        fixtures.add_calls(self.conn)
        notify.reset()

    def test_money_whole_dollars(self):
        self.assertEqual(format_money(100), "$1.00")
        self.assertEqual(format_money(250), "$2.50")

    def test_quote_title_mentions_client_and_route(self):
        q = Quote("Cobalt Retail", "Rotterdam", "Chicago", 4, "pallet")
        title = quote_title(q)
        self.assertIn("Cobalt Retail", title)
        self.assertIn("Rotterdam", title)
        self.assertIn("Chicago", title)

    def test_quote_total_adds_tax(self):
        q = Quote("Tidewater Foods", "Valencia", "Boston", 2, "container",
                  lines=[("Ocean freight", 100000)], tax_rate_bp=1000)
        self.assertEqual(total_cents(q), 110000)
        self.assertIn("Ocean freight", render_quote(q))

    def test_admin_sees_every_client(self):
        self.assertEqual(len(permissions.visible_clients(self.conn, self.people["admin"])), 4)

    def test_manager_sees_only_own_clients(self):
        names = [c.name for c in permissions.visible_clients(self.conn, self.people["mia"])]
        self.assertEqual(names, ["Cobalt Retail", "Tidewater Foods"])

    def test_admin_recent_calls(self):
        calls = reports.recent_calls(self.conn, self.people["admin"], limit=2)
        self.assertEqual(len(calls), 2)

    def test_registry_basic_order(self):
        ids = [c.id for c in registry.list_clients(self.conn)]
        self.assertEqual(ids[0], "CL-0100")
        self.assertEqual(ids[-1], "CL-0400")

    def test_sales_report_has_a_row_per_client(self):
        rows = reports.sales_by_client(self.conn, self.people["admin"])
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["client"], "Cobalt Retail")

    def test_open_order_in_edit_mode_for_manager(self):
        view = orders.open_order(self.conn, self.people["mia"], 1, mode="edit")
        self.assertEqual(view.shipment.ref, "BL-1001")
        self.assertIn("statuses", view.dictionaries)

    def test_single_payment_single_shipment(self):
        pid = payments.create_payment(self.conn, "Harbor Line", 100000, "2026-03-01")
        payments.link_payment(self.conn, pid, [1])
        self.assertEqual(payments.paid_toward_shipment(self.conn, 1), 100000)

    def test_timeline_lists_every_reference(self):
        clients = {c.id: c for c in registry.list_clients(self.conn)}
        text = render_timeline(shipments.list_shipments(self.conn), clients)
        for ref in ("BL-1001", "BL-1005"):
            self.assertIn(ref, text)

    def test_migration_roundtrip(self):
        latest = db.current_version(self.conn)
        self.assertEqual(db.rollback(self.conn), latest - 1)
        self.assertEqual(db.migrate(self.conn), latest)


if __name__ == "__main__":
    unittest.main()
