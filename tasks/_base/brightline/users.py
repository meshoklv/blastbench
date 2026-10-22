"""User directory."""
from brightline.models import User


def add_user(conn, user_id, name, role):
    conn.execute("INSERT INTO users(id, name, role) VALUES (?, ?, ?)", (user_id, name, role))
    conn.commit()
    return User(user_id, name, role)


def get_user(conn, user_id):
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise KeyError(user_id)
    return User(row["id"], row["name"], row["role"])
