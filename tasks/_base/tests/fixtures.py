"""Shared test data: a small fictional Brightline world."""
from brightline import db, users
from brightline.clients import registry
from brightline import shipments

ADMIN, MIA, MAX, ALLY = 1, 2, 3, 4  # user ids


def world():
    """Return (conn, users_by_key) with a seeded in-memory database."""
    conn = db.connect()
    people = {
        "admin": users.add_user(conn, ADMIN, "Ada Admin", "admin"),
        "mia": users.add_user(conn, MIA, "Mia Manager", "manager"),
        "max": users.add_user(conn, MAX, "Max Manager", "manager"),
        "ally": users.add_user(conn, ALLY, "Ally Accountant", "accountant"),
    }
    registry.add_client(conn, "CL-0100", "Cobalt Retail", MIA, "2026-01-15")
    registry.add_client(conn, "CL-0200", "Maple & Oak Furniture", MAX, "2026-01-20")
    registry.add_client(conn, "CL-0300", "Tidewater Foods", MIA, "2026-02-03")
    registry.add_client(conn, "CL-0400", "Northgate Paper", MAX, "2026-03-09")
    rows = [
        ("BL-1001", "CL-0100", "Rotterdam", "Chicago", "delivered", "2026-02-02", 1250000),
        ("BL-1002", "CL-0200", "Gdansk", "Savannah", "in_transit", "2026-02-10", 842550),
        ("BL-1003", "CL-0300", "Valencia", "Boston", "customs", "2026-03-05", 2310075),
        ("BL-1004", "CL-0400", "Antwerp", "Houston", "booked", "2026-03-18", 99900),
        ("BL-1005", "CL-0100", "Hamburg", "Newark", "in_transit", "2026-04-01", 560000),
    ]
    for r in rows:
        shipments.create_shipment(conn, *r)
    return conn, people


def add_calls(conn):
    data = [
        ("CL-0100", "2026-04-01T09:00", "Confirmed pickup window"),
        ("CL-0200", "2026-04-02T10:30", "Asked about customs delay"),
        ("CL-0300", "2026-04-03T11:15", "Rate renegotiation"),
        ("CL-0200", "2026-04-04T15:00", "Invoice question"),
        ("CL-0400", "2026-04-05T08:45", "New lane inquiry"),
    ]
    for client_id, at, summary in data:
        conn.execute("INSERT INTO calls(client_id, at, summary) VALUES (?,?,?)",
                     (client_id, at, summary))
    conn.commit()
