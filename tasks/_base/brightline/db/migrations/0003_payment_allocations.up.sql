-- Store how much of a payment is attributed to each linked shipment.
ALTER TABLE shipment_payments ADD COLUMN allocated_cents INTEGER NOT NULL DEFAULT 0;

-- Backfill: split every existing payment evenly across its links ...
UPDATE shipment_payments
SET allocated_cents = (SELECT p.amount_cents FROM payments p WHERE p.id = shipment_payments.payment_id)
                      / (SELECT COUNT(*) FROM shipment_payments s2 WHERE s2.payment_id = shipment_payments.payment_id);

-- ... and give the leftover cents to the link with the highest shipment id.
UPDATE shipment_payments
SET allocated_cents = allocated_cents + (
        (SELECT p.amount_cents FROM payments p WHERE p.id = shipment_payments.payment_id)
        - (SELECT SUM(s2.allocated_cents) FROM shipment_payments s2 WHERE s2.payment_id = shipment_payments.payment_id))
WHERE shipment_id = (SELECT MAX(s3.shipment_id) FROM shipment_payments s3 WHERE s3.payment_id = shipment_payments.payment_id);
