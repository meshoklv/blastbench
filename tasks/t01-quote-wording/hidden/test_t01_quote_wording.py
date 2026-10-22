import unittest

from brightline.models import Quote
from brightline.quotes import format_money, quote_title, render_quote, total_cents


class MoneyFormat(unittest.TestCase):
    def test_thousands_separators(self):
        self.assertEqual(format_money(1234567), "$12,345.67")
        self.assertEqual(format_money(100000000), "$1,000,000.00")
        self.assertEqual(format_money(1000000), "$10,000.00")

    def test_two_decimals_always(self):
        self.assertEqual(format_money(5), "$0.05")
        self.assertEqual(format_money(0), "$0.00")
        self.assertEqual(format_money(99900), "$999.00")

    def test_negative_amounts(self):
        self.assertEqual(format_money(-250), "-$2.50")
        self.assertEqual(format_money(-123456), "-$1,234.56")


class Title(unittest.TestCase):
    def q(self, n, unit, client="Cobalt Retail"):
        return Quote(client, "Rotterdam", "Chicago", n, unit)

    def test_wording_uses_for(self):
        title = quote_title(self.q(4, "pallet"))
        self.assertIn("for Cobalt Retail", title)
        self.assertNotIn("quote to", title.lower())

    def test_singular_and_plural(self):
        self.assertIn("1 pallet ", quote_title(self.q(1, "pallet")))
        self.assertNotIn("pallets", quote_title(self.q(1, "pallet")))
        self.assertIn("2 pallets ", quote_title(self.q(2, "pallet")))
        self.assertIn("1 container ", quote_title(self.q(1, "container")))

    def test_plural_of_box(self):
        self.assertIn("3 boxes ", quote_title(self.q(3, "box")))
        self.assertIn("1 box ", quote_title(self.q(1, "box")))

    def test_route_and_client_name_untouched(self):
        title = quote_title(self.q(2, "container", client="Maple & Oak Furniture"))
        self.assertIn("Maple & Oak Furniture", title)
        self.assertTrue(title.endswith("from Rotterdam to Chicago"))


class Rendered(unittest.TestCase):
    def setUp(self):
        self.q = Quote("Tidewater Foods", "Valencia", "Boston", 1, "container",
                       lines=[("Ocean freight", 1250000), ("Handling", 4550)],
                       tax_rate_bp=825)

    def test_totals_unchanged(self):
        # subtotal 12,545.50; tax 8.25 % rounded half up = 1,035.00
        self.assertEqual(total_cents(self.q), 1254550 + 103500)

    def test_body_uses_formatted_money(self):
        text = render_quote(self.q)
        self.assertIn("$12,500.00", text)
        self.assertIn("$45.50", text)
        self.assertIn("1 container", text)
        self.assertNotIn("1 containers", text)
        self.assertIn("Tax (8.25%)", text)


if __name__ == "__main__":
    unittest.main()
