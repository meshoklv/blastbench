"""Client registry: who our customers are and who looks after them."""
from brightline.models import Client


class ClientNotFound(KeyError):
    pass


def _row_to_client(row):
    return Client(id=row["id"], name=row["name"],
                  manager_id=row["manager_id"], created_at=row["created_at"])


def add_client(conn, client_id, name, manager_id, created_at):
    """Register a client. `created_at` is a date (YYYY-MM-DD)."""
    conn.execute(
        "INSERT INTO clients(id, name, manager_id, created_at) VALUES (?, ?, ?, ?)",
        (client_id, name, manager_id, created_at),
    )
    conn.commit()
    return get_client(conn, client_id)


def get_client(conn, client_id):
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if row is None:
        raise ClientNotFound(client_id)
    return _row_to_client(row)


def list_clients(conn, manager_id=None):
    """Clients in registration order: whoever was added first comes first.

    Several clients are often registered on the same day, so the date alone does
    not give a stable order; the client id breaks ties (same rule as the reports).
    """
    sql = "SELECT * FROM clients"
    params = []
    if manager_id is not None:
        sql += " WHERE manager_id = ?"
        params.append(manager_id)
    sql += " ORDER BY created_at, id"
    return [_row_to_client(r) for r in conn.execute(sql, params)]
