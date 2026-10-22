"""Plain-text shipment timeline."""
from brightline.quotes import format_money

COLUMNS = ("Ref", "Date", "Client", "Route", "Status")
_WIDTHS = (8, 10, 24, 30, 11)


def _fmt_row(cells):
    return " | ".join(str(c).ljust(w) for c, w in zip(cells, _WIDTHS)).rstrip()


def _sorted(shipments):
    return sorted(shipments, key=lambda s: (s.departed_on, s.ref))


def _cells(s, clients_by_id):
    client = clients_by_id[s.client_id].name
    return (s.ref, s.departed_on, client, f"{s.origin} -> {s.destination}", s.status)


def render_timeline(shipments, clients_by_id, compact=False):
    """Render shipments (oldest first) as text.

    The normal view shows one multi-line card per shipment.
    """
    if not shipments:
        return "No shipments."
    ordered = _sorted(shipments)
    if compact:
        raise NotImplementedError("compact timeline is not implemented yet")
    header = _fmt_row(COLUMNS)
    lines = [header, "-" * len(header)]
    for s in ordered:
        lines.append(_fmt_row(_cells(s, clients_by_id)))
        lines.append(f"    Amount: {format_money(s.amount_cents)}")
        lines.append(f"    Departed on {s.departed_on} from {s.origin}")
        lines.append("")
    return "\n".join(lines).rstrip("\n")
