"""Outgoing notifications. The outbox is in-memory in this demo build."""

OUTBOX = []  # list of {"to": str, "subject": str, "body": str}

SUPPORT_ADDRESS = "ops-alerts@brightline.example"


def send_error_email(body):
    """Alert the operations mailbox about an unexpected failure."""
    OUTBOX.append({"to": SUPPORT_ADDRESS, "subject": "Brightline error", "body": body})


def reset():
    del OUTBOX[:]
