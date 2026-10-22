import re
import unittest

from brightline.clients import registry
from brightline.models import Shipment
from brightline.timeline import render_timeline
from tests import fixtures

REQUIRED_HEADER_WORDS = ("Ref", "Client", "Status")


def many(n=25):
    """n shipments spread over four months, deliberately not in date order."""
    out = []
    for i in range(n):
        month = 1 + (i * 7) % 4  # 1..4
        day = 1 + (i * 3) % 27
        out.append(Shipment(i + 1, f"BL-{2000 + i}", "CL-0100" if i % 2 else "CL-0300",
                            "Rotterdam", "Chicago", "in_transit" if i % 3 else "booked",
                            f"2026-{month:02d}-{day:02d}", 100000 + i))
    return out


class Compact(unittest.TestCase):
    def setUp(self):
        self.conn, _ = fixtures.world()
        self.clients = {c.id: c for c in registry.list_clients(self.conn)}
        self.ships = many()
        self.full = render_timeline(self.ships, self.clients)
        self.compact = render_timeline(self.ships, self.clients, compact=True)
        self.lines = self.compact.splitlines()

    def ref_lines(self):
        return [l for l in self.lines if re.search(r"BL-\d{4}", l)]

    def test_every_shipment_exactly_once(self):
        refs = re.findall(r"BL-\d{4}", self.compact)
        self.assertEqual(sorted(refs), sorted(s.ref for s in self.ships))

    def test_one_line_per_shipment_with_client_and_status(self):
        by_ref = {s.ref: s for s in self.ships}
        self.assertEqual(len(self.ref_lines()), len(self.ships))
        for line in self.ref_lines():
            ref = re.search(r"BL-\d{4}", line).group(0)
            self.assertIn(self.clients[by_ref[ref].client_id].name, line)
            self.assertIn(by_ref[ref].status, line)

    def test_same_order_as_normal_view(self):
        order = lambda t: re.findall(r"BL-\d{4}", t)
        self.assertEqual(order(self.compact), order(self.full))

    def test_actually_more_compact(self):
        self.assertLess(len(self.lines), len(self.full.splitlines()) * 0.6)
        months = {s.departed_on[:7] for s in self.ships}
        self.assertLessEqual(len(self.lines), len(self.ships) + 3 * len(months))

    def test_grouped_by_month_with_labels(self):
        months = sorted({s.departed_on[:7] for s in self.ships})
        self.assertEqual(len(months), 4)
        by_ref = {s.ref: s for s in self.ships}
        # walk the output: every shipment must sit under the label of its own month
        names = {"01": "January", "02": "February", "03": "March", "04": "April"}
        current = None
        seen_labels = []
        for line in self.lines:
            m = re.search(r"BL-\d{4}", line)
            if not m:
                for mm in months:
                    year, mon = mm.split("-")
                    if mm in line or (names[mon] in line and year in line):
                        current = mm
                        seen_labels.append(mm)
                continue
            self.assertIsNotNone(current, f"shipment before any month label: {line!r}")
            self.assertEqual(by_ref[m.group(0)].departed_on[:7], current, line)
        self.assertEqual(seen_labels, months)  # one label per month, in order

    def test_column_header_repeated_in_every_group(self):
        months = {s.departed_on[:7] for s in self.ships}
        header_lines = [i for i, l in enumerate(self.lines)
                        if all(w in l for w in REQUIRED_HEADER_WORDS) and not re.search(r"BL-\d{4}", l)]
        self.assertEqual(len(header_lines), len(months))
        # each header comes before the first shipment of its group and after the previous group
        ref_idx = [i for i, l in enumerate(self.lines) if re.search(r"BL-\d{4}", l)]
        for h in header_lines:
            nxt = [i for i in ref_idx if i > h]
            self.assertTrue(nxt and nxt[0] - h <= 2, "header must sit right above its group")

    def test_single_month_and_single_shipment(self):
        one = [self.ships[0]]
        text = render_timeline(one, self.clients, compact=True)
        self.assertEqual(re.findall(r"BL-\d{4}", text), [one[0].ref])
        self.assertTrue(all(w in text for w in REQUIRED_HEADER_WORDS))

    def test_empty_input(self):
        self.assertEqual(render_timeline([], self.clients, compact=True),
                         render_timeline([], self.clients))
        self.assertIn("No shipments", render_timeline([], self.clients, compact=True))


class NormalViewUnchanged(unittest.TestCase):
    def test_golden(self):
        conn, _ = fixtures.world()
        clients = {c.id: c for c in registry.list_clients(conn)}
        ships = [Shipment(1, "BL-1001", "CL-0100", "Rotterdam", "Chicago", "delivered",
                          "2026-02-02", 1250000)]
        expected = "\n".join([
            "Ref      | Date       | Client                   | Route                          | Status",
            "-" * 90,
            "BL-1001  | 2026-02-02 | Cobalt Retail            | Rotterdam -> Chicago           | delivered",
            "    Amount: $12,500.00",
            "    Departed on 2026-02-02 from Rotterdam",
        ])
        self.assertEqual(render_timeline(ships, clients), expected)
        self.assertEqual(render_timeline(ships, clients, compact=False), expected)


if __name__ == "__main__":
    unittest.main()
