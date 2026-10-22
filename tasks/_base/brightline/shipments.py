"""Shipments ("orders" in the UI)."""
from brightline.models import Shipment


class ShipmentNotFound(KeyError):
    pass


def _row(row):
    return Shipment(
        id=row["id"], ref=row["ref"], client_id=row["client_id"],
        origin=row["origin"], destination=row["destination"],
        status=row["status"], departed_on=row["departed_on"],
        amount_cents=row["amount_cents"],
    )


def create_shipment(conn, ref, client_id, origin, destination, status,
                    departed_on, amount_cents):
    cur = conn.execute(
        "INSERT INTO shipments(ref, client_id, origin, destination, status,"
        " departed_on, amount_cents) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ref, client_id, origin, destination, status, departed_on, amount_cents),
    )
    conn.commit()
    return get(conn, cur.lastrowid)


def get(conn, shipment_id):
    row = conn.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
    if row is None:
        raise ShipmentNotFound(shipment_id)
    return _row(row)


def list_shipments(conn, client_ids=None, status=None):
    """Shipments ordered by departure date, then reference.

    `client_ids` limits the result to those clients (None means no limit,
    an empty list means nothing).
    """
    sql = "SELECT * FROM shipments WHERE 1=1"
    params = []
    if client_ids is not None:
        sql += " AND client_id IN (%s)" % ",".join("?" * len(client_ids))
        params.extend(client_ids)
    if status is not None:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY departed_on, ref"
    return [_row(r) for r in conn.execute(sql, params)]
