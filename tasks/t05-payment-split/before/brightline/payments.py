"""Supplier payments and how they are attributed to shipments."""


def create_payment(conn, supplier, amount_cents, paid_on):
    cur = conn.execute(
        "INSERT INTO payments(supplier, amount_cents, paid_on) VALUES (?, ?, ?)",
        (supplier, amount_cents, paid_on),
    )
    conn.commit()
    return cur.lastrowid


def link_payment(conn, payment_id, shipment_ids):
    """Attribute a payment to one or more shipments, replacing earlier links."""
    ids = list(dict.fromkeys(shipment_ids))
    if not ids:
        raise ValueError("a payment must be linked to at least one shipment")
    conn.execute("DELETE FROM shipment_payments WHERE payment_id = ?", (payment_id,))
    for sid in ids:
        conn.execute(
            "INSERT INTO shipment_payments(shipment_id, payment_id) VALUES (?, ?)",
            (sid, payment_id),
        )
    conn.commit()


def payment_shares(conn, payment_id):
    """[(shipment_id, cents)] for one payment, ordered by shipment id."""
    rows = conn.execute(
        "SELECT sp.shipment_id, p.amount_cents FROM shipment_payments sp"
        " JOIN payments p ON p.id = sp.payment_id"
        " WHERE sp.payment_id = ? ORDER BY sp.shipment_id",
        (payment_id,),
    )
    return [(r["shipment_id"], r["amount_cents"]) for r in rows]


def paid_toward_shipment(conn, shipment_id):
    """Total supplier cost already paid for a shipment, in cents."""
    row = conn.execute(
        "SELECT COALESCE(SUM(p.amount_cents), 0) AS total FROM shipment_payments sp"
        " JOIN payments p ON p.id = sp.payment_id WHERE sp.shipment_id = ?",
        (shipment_id,),
    ).fetchone()
    return row["total"]


def margin_cents(conn, shipment):
    """Revenue minus supplier cost paid so far."""
    return shipment.amount_cents - paid_toward_shipment(conn, shipment.id)
