"""Opening an order card, for viewing or editing."""
from dataclasses import dataclass
from typing import Optional

from brightline import dictionaries, notify, permissions, shipments


@dataclass
class OrderView:
    shipment: object
    mode: str
    dictionaries: Optional[dict]  # only needed by the edit form


def open_order(conn, user, order_id, mode="view"):
    """Open an order card. `mode` is "view" (read-only) or "edit".

    Any unexpected failure is reported to the operations mailbox and re-raised.
    """
    permissions.require(user, "orders.edit" if mode == "edit" else "orders.view")
    try:
        shipment = shipments.get(conn, order_id)
        # Only the edit form has dropdowns that need the dictionaries.
        dicts = dictionaries.load_all(conn, user) if mode == "edit" else None
    except Exception as exc:
        notify.send_error_email(f"open_order({order_id}, mode={mode}) failed for {user.name}: {exc!r}")
        raise
    return OrderView(shipment=shipment, mode=mode, dictionaries=dicts)
