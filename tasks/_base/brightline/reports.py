"""Management reports. Every report is scoped to what the viewer may see."""
from collections import namedtuple

from brightline import payments, permissions, shipments
from brightline.models import Call

_Collected = namedtuple("_Collected", "calls shipments")


def _collect(conn, clients):
    """Calls and shipments belonging to exactly the given clients."""
    ids = [c.id for c in clients]
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM calls WHERE client_id IN ({marks}) ORDER BY at DESC, id DESC", ids
    )
    calls = [Call(r["id"], r["client_id"], r["at"], r["summary"]) for r in rows]
    return _Collected(calls, shipments.list_shipments(conn, client_ids=ids))


def recent_calls(conn, user, limit=20):
    """The newest `limit` calls with clients the user may see."""
    permissions.require(user, "reports.view")
    clients = permissions.visible_clients(conn, user)
    return _collect(conn, clients).calls[:limit]


def activity_digest(conn, user):
    """Headline numbers for the dashboard, limited to the user's clients."""
    permissions.require(user, "reports.view")
    clients = permissions.visible_clients(conn, user)
    data = _collect(conn, clients)
    open_shipments = [s for s in data.shipments if s.status not in ("delivered", "cancelled")]
    return {
        "calls": data.calls[:5],
        "call_count": len(data.calls),
        "clients_with_calls": len({c.client_id for c in data.calls}),
        "open_shipments": len(open_shipments),
        "open_value_cents": sum(s.amount_cents for s in open_shipments),
    }


def sales_by_client(conn, user):
    """One row per visible client: revenue, supplier cost and margin.

    Ordered by registration: earliest created_at first, ties broken by id.
    """
    permissions.require(user, "reports.view")
    clients = sorted(permissions.visible_clients(conn, user),
                     key=lambda c: (c.created_at, c.id))
    rows = []
    for client in clients:
        ships = shipments.list_shipments(conn, client_ids=[client.id])
        revenue = sum(s.amount_cents for s in ships)
        cost = sum(payments.paid_toward_shipment(conn, s.id) for s in ships)
        rows.append({
            "client_id": client.id,
            "client": client.name,
            "shipments": len(ships),
            "revenue_cents": revenue,
            "cost_cents": cost,
            "margin_cents": revenue - cost,
        })
    return rows
