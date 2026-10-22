"""Role-based access rules."""
from brightline.clients import registry


class PermissionDenied(Exception):
    pass


ROLE_PERMISSIONS = {
    "admin": {
        "orders.view", "orders.edit", "dictionaries.read", "dictionaries.edit",
        "reports.view", "payments.view", "payments.edit", "clients.view_all",
    },
    "manager": {
        "orders.view", "orders.edit", "dictionaries.read", "reports.view",
        "clients.view_own",
    },
    "accountant": {
        "orders.view", "payments.view", "payments.edit", "reports.view",
        "clients.view_all",
    },
}


def has(user, permission):
    return permission in ROLE_PERMISSIONS.get(user.role, set())


def require(user, permission):
    if not has(user, permission):
        raise PermissionDenied(f"{user.name} ({user.role}) lacks '{permission}'")


def visible_clients(conn, user):
    """Clients this user is allowed to see, in registry order."""
    if has(user, "clients.view_all"):
        return registry.list_clients(conn)
    if has(user, "clients.view_own"):
        return registry.list_clients(conn, manager_id=user.id)
    return []
