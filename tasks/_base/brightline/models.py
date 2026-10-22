"""Plain data containers shared across the toolkit.

All money is stored as integer cents (USD). Dates are ISO strings (YYYY-MM-DD).
"""
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class User:
    id: int
    name: str
    role: str  # "admin" | "manager" | "accountant"


@dataclass(frozen=True)
class Client:
    id: str  # e.g. "CL-0100"
    name: str
    manager_id: int
    created_at: str


@dataclass(frozen=True)
class Shipment:
    id: int
    ref: str  # human-facing reference, e.g. "BL-1001"
    client_id: str
    origin: str
    destination: str
    status: str
    departed_on: str
    amount_cents: int


@dataclass(frozen=True)
class Payment:
    id: int
    supplier: str
    amount_cents: int
    paid_on: str


@dataclass(frozen=True)
class Call:
    id: int
    client_id: str
    at: str
    summary: str


@dataclass
class Quote:
    """A commercial offer sent to a client."""
    client_name: str
    origin: str
    destination: str
    quantity: int
    unit: str  # singular noun: "pallet", "box", "container"
    lines: List[Tuple[str, int]] = field(default_factory=list)  # (description, cents)
    tax_rate_bp: int = 0  # basis points, 825 == 8.25 %
