"""Supplier payments and how they are attributed to shipments."""


def create_payment(conn, supplier, amount_cents, paid_on):
    cur = conn.execute(
        "INSERT INTO payments(supplier, amount_cents, paid_on) VALUES (?, ?, ?)",
        (supplier, amount_cents, paid_on),
    )
    conn.commit()
    return cur.lastrowid


def link_payment(conn, payment_id, shipment_ids):
    """Attribute a payment to one or more shipments, replacing earlier links.

    The payment amount is split evenly between the shipments; any leftover
    cents go to the last one, so the shares always add up to the payment.
    """
    ids = list(dict.fromkeys(shipment_ids))
    if not ids:
        raise ValueError("a payment must be linked to at least one shipment")
    amount = conn.execute(
        "SELECT amount_cents FROM payments WHERE id = ?", (payment_id,)
    ).fetchone()["amount_cents"]
    share, remainder = divmod(amount, len(ids))
    conn.execute("DELETE FROM shipment_payments WHERE payment_id = ?", (payment_id,))
    for i, sid in enumerate(ids):
        cents = share + (remainder if i == len(ids) - 1 else 0)
        conn.execute(
            "INSERT INTO shipment_payments(shipment_id, payment_id, allocated_cents)"
            " VALUES (?, ?, ?)",
            (sid, payment_id, cents),
        )
    conn.commit()


def payment_shares(conn, payment_id):
    """[(shipment_id, cents)] for one payment, ordered by shipment id."""
    rows = conn.execute(
        "SELECT shipment_id, allocated_cents FROM shipment_payments"
        " WHERE payment_id = ? ORDER BY shipment_id",
        (payment_id,),
    )
    return [(r["shipment_id"], r["allocated_cents"]) for r in rows]


def paid_toward_shipment(conn, shipment_id):
    """Total supplier cost already paid for a shipment, in cents."""
    row = conn.execute(
        "SELECT COALESCE(SUM(allocated_cents), 0) AS total"
        " FROM shipment_payments WHERE shipment_id = ?",
        (shipment_id,),
    ).fetchone()
    return row["total"]


def margin_cents(conn, shipment):
    """Revenue minus supplier cost paid so far."""
    return shipment.amount_cents - paid_toward_shipment(conn, shipment.id)
