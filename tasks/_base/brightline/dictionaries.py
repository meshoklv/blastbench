"""Reference dictionaries (statuses, units, carriers) used by the order form."""
from brightline import permissions

REQUESTS = []  # names of dictionary fetches attempted, for diagnostics

_DATA = {
    "statuses": ["booked", "in_transit", "customs", "delivered", "cancelled"],
    "units": ["pallet", "box", "container"],
    "carriers": ["Harbor Line", "Greenway Haulage", "Skyhook Air Cargo"],
}


def load_all(conn, user):
    """Fetch every dictionary. Requires the 'dictionaries.read' permission."""
    REQUESTS.append("all")
    permissions.require(user, "dictionaries.read")
    return {name: list(values) for name, values in _DATA.items()}
