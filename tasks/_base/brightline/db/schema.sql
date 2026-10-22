-- Baseline schema (version 1). Later changes live in db/migrations/.
CREATE TABLE users (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL,
    role  TEXT NOT NULL
);

CREATE TABLE clients (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    manager_id  INTEGER NOT NULL REFERENCES users(id),
    created_at  TEXT NOT NULL
);

CREATE TABLE shipments (
    id           INTEGER PRIMARY KEY,
    ref          TEXT NOT NULL UNIQUE,
    client_id    TEXT NOT NULL REFERENCES clients(id),
    origin       TEXT NOT NULL,
    destination  TEXT NOT NULL,
    status       TEXT NOT NULL,
    departed_on  TEXT NOT NULL,
    amount_cents INTEGER NOT NULL
);

CREATE TABLE payments (
    id           INTEGER PRIMARY KEY,
    supplier     TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    paid_on      TEXT NOT NULL
);

CREATE TABLE shipment_payments (
    shipment_id INTEGER NOT NULL REFERENCES shipments(id),
    payment_id  INTEGER NOT NULL REFERENCES payments(id),
    PRIMARY KEY (shipment_id, payment_id)
);

CREATE TABLE calls (
    id         INTEGER PRIMARY KEY,
    client_id  TEXT NOT NULL REFERENCES clients(id),
    at         TEXT NOT NULL,
    summary    TEXT NOT NULL
);
